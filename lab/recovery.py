"""Real encrypted backups and disposable, isolated PostgreSQL/OpenBao recovery.

This module belongs to the trusted local operator. Business containers never see
the Docker socket, backup repository, root token or unseal recovery material.
Only resources created by a particular recovery run are destroyed by cleanup.
"""
from __future__ import annotations

import base64
import fcntl
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import ssl
import subprocess
import tarfile
import time
import uuid
from pathlib import Path

import httpx
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from . import operations as ops

BACKUPS = ops.RT / "backups"
RESULTS = ops.ROOT / "results/recovery"
PG_IMAGE = "postgres:17-alpine@sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24"
BAO_IMAGE = "ghcr.io/openbao/openbao:2.7.1@sha256:6d2b93856e3fcf7b18ad855a0b51eaba474dc8b79cf554379ea32034797d2acf"
RUN_LABEL = "bmdl.recovery.run"


def _write_json(path, value, private=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    if private:
        temporary.chmod(0o600)
    os.replace(temporary, path)


def _sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _keyset_fingerprint(material):
    """Reference only: recovery keys remain outside the backup repository."""
    selected = {"keys_base64": material["keys_base64"], "root_token": material["root_token"]}
    return hashlib.sha256(json.dumps(selected, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _remove_scratch(path, parent):
    resolved = path.resolve()
    boundary = parent.resolve()
    if resolved == boundary or not resolved.is_relative_to(boundary):
        raise RuntimeError("Recovery scratch cleanup target rejected")
    if resolved.exists():
        shutil.rmtree(resolved)


def _restic(arguments):
    env = os.environ.copy()
    env.update({
        "RESTIC_REPOSITORY": str(BACKUPS / "repository"),
        "RESTIC_PASSWORD_FILE": str(ops.RT / "secrets/restic-password"),
        "RESTIC_CACHE_DIR": str(BACKUPS / "cache"),
    })
    process = subprocess.run(["restic", *arguments], env=env, capture_output=True,
                             text=True, timeout=300, check=False)
    if process.returncode:
        # restic output can reveal recovery file paths; return a narrow failure.
        raise RuntimeError(f"Encrypted repository operation failed ({arguments[0]}, exit {process.returncode})")
    return process.stdout


def _http(method, url, *, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["X-Vault-Token"] = token
    response = httpx.request(method, url, headers=headers, timeout=120,
                            trust_env=False, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"Recovery KMS operation failed (HTTP {response.status_code})")
    return response


def _wait_api(service):
    for _ in range(90):
        try:
            response = httpx.get(f"http://{service}:8000/health", timeout=2, trust_env=False)
            if response.status_code == 200 and response.json().get("status") == "ready":
                return
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(.5)
    raise RuntimeError(f"Business service did not become ready after backup ({service})")


def _refresh_gateway_routes():
    # Docker may reassign freed addresses when both APIs restart. Static NGINX
    # upstream DNS must be refreshed, or B0/B1 could silently swap endpoints.
    gateway = ops.container("gateway")
    result = gateway.exec_run(["nginx", "-s", "reload"])
    if result.exit_code:
        raise RuntimeError("Gateway route refresh failed after API restart")
    context = ssl.create_default_context(cafile=str(ops.RT / "pki/ca.crt"))
    context.load_cert_chain(str(ops.RT / "pki/secadmin.crt"), str(ops.RT / "pki/secadmin.key"))
    for _ in range(40):
        try:
            matched = True
            for port, expected in ((8443, "B1"), (8444, "B0")):
                response = httpx.get(f"https://gateway:{port}/api/health", verify=context,
                                     timeout=2, trust_env=False)
                matched = matched and response.status_code == 200 and response.json().get("mode") == expected
            if matched:
                return
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(.25)
    raise RuntimeError("Gateway policy-mode route verification failed")


def backup():
    """Capture a frozen DB/KMS pair, encrypt it with restic and verify the repo."""
    started = time.time()
    run_id = "pair-" + uuid.uuid4().hex
    stage = BACKUPS / "staging" / run_id
    stage.mkdir(parents=True, mode=0o700)
    stage.chmod(0o700)
    stopped = []
    stage_name = "preparing"
    with ops.LOCK:
        try:
            try:
                stage_name = "freezing_business_writes"
                for service in ("api", "api-baseline"):
                    target = ops.container(service)
                    target.reload()
                    if target.status == "running":
                        target.stop(timeout=15)
                        stopped.append((service, target))
                checkpoint = time.time()
                stage_name = "postgres_snapshot"
                dump = ops.container("postgres").exec_run([
                    "pg_dump", "-U", "postgres", "-d", "bmdl", "-Fc",
                    "--no-owner", "--no-privileges",
                ])
                if dump.exit_code or not dump.output.startswith(b"PGDMP"):
                    raise RuntimeError("PostgreSQL custom archive creation failed")
                (stage / "db.dump").write_bytes(dump.output)
                stage_name = "raft_snapshot"
                material = ops._bao_root()
                if not material.get("root_token") or not material.get("keys_base64"):
                    raise RuntimeError("Primary recovery material unavailable")
                raft = _http("GET", "http://openbao:8200/v1/sys/storage/raft/snapshot",
                             token=material["root_token"])
                (stage / "bao.snap").write_bytes(raft.content)
                keyset_fingerprint = _keyset_fingerprint(material)
                hashes = {name: _sha(stage / name) for name in
                          ("db.dump", "bao.snap")}
                _write_json(stage / "checkpoint.json", {
                    "checkpoint": checkpoint, "pair_id": run_id,
                    "hashes": hashes, "business_writes_frozen": True,
                    "recovery_keyset_reference": "local-operator-unseal-set-v1",
                    "recovery_keyset_fingerprint": keyset_fingerprint,
                })
            finally:
                restart_errors = []
                for service, target in stopped:
                    try:
                        target.start()
                        _wait_api(service)
                    except Exception:
                        restart_errors.append(service)
                if stopped and not restart_errors:
                    _refresh_gateway_routes()
                if restart_errors:
                    raise RuntimeError("Business service restart requires attention: " + ",".join(restart_errors))
            stage_name = "encrypted_repository"
            (BACKUPS / "cache").mkdir(parents=True, exist_ok=True)
            if not (BACKUPS / "repository/config").exists():
                _restic(["init"])
            output = _restic(["backup", str(stage), "--json", "--tag", "bmdl-consistent-pair",
                              "--tag", run_id])
            summary = None
            for line in output.splitlines():
                try:
                    record = json.loads(line)
                    if record.get("message_type") == "summary":
                        summary = record
                except ValueError:
                    continue
            snapshot_id = summary.get("snapshot_id") if summary else None
            if not isinstance(snapshot_id, str) or not re.fullmatch(r"[a-f0-9]{64}", snapshot_id):
                raise RuntimeError("Encrypted backup did not produce a complete snapshot ID")
            stage_name = "repository_verification"
            _restic(["check", "--read-data"])
            manifest = {
                "snapshot_id": snapshot_id, "restic_snapshot_id": snapshot_id,
                "pair_id": run_id, "checkpoint": checkpoint,
                "archive_path": str(stage), "hashes": hashes,
                "files": ["db.dump", "bao.snap", "checkpoint.json"],
                "recovery_material_external": True,
                "recovery_keyset_reference": "local-operator-unseal-set-v1",
                "recovery_keyset_fingerprint": keyset_fingerprint,
                "created_at": started, "finished_at": time.time(),
                "business_writes_frozen": True, "repository_verified": True,
                "encrypted": True, "db_format": "PostgreSQL custom archive",
                "kms_format": "OpenBao integrated Raft snapshot",
                "duration_seconds": round(time.time() - started, 3),
            }
            _write_json(BACKUPS / "manifests" / (snapshot_id + ".json"), manifest)
            _write_json(RESULTS / (run_id + ".json"), {"operation": "backup", "status": "passed", **manifest})
            return manifest
        except Exception as error:
            _write_json(RESULTS / (run_id + ".json"), {
                "operation": "backup", "status": "failed", "stage": stage_name,
                "error_type": type(error).__name__, "duration_seconds": round(time.time() - started, 3),
            })
            raise RuntimeError(f"Consistent encrypted backup failed at {stage_name} ({type(error).__name__})") from None
        finally:
            _remove_scratch(stage, BACKUPS / "staging")


def _snapshot_manifest(value):
    snapshot_id = value.get("snapshot_id") if isinstance(value, dict) else value
    if not isinstance(snapshot_id, str) or not re.fullmatch(r"[a-f0-9]{64}", snapshot_id):
        raise ValueError("A complete local snapshot ID is required")
    path = BACKUPS / "manifests" / (snapshot_id + ".json")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("snapshot_id") != snapshot_id or not manifest.get("repository_verified"):
        raise RuntimeError("Snapshot manifest is inconsistent or unverified")
    return manifest


def _container_ip(target, network):
    target.reload()
    return target.attrs["NetworkSettings"]["Networks"][network.name]["IPAddress"]


def _put_file(target, path, content):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        member = tarfile.TarInfo(Path(path).name)
        member.size = len(content)
        member.mode = 0o600
        archive.addfile(member, io.BytesIO(content))
    if not target.put_archive(str(Path(path).parent), buffer.getvalue()):
        raise RuntimeError("Recovery container archive transfer failed")


def _wait_pg(host, password):
    for _ in range(100):
        try:
            conn = psycopg.connect(host=host, port=5432, dbname="bmdl", user="postgres",
                                   password=password, connect_timeout=2, row_factory=dict_row)
            conn.close()
            return
        except psycopg.OperationalError:
            time.sleep(.3)
    raise RuntimeError("Isolated PostgreSQL readiness failed")


def _wait_bao(address):
    for _ in range(100):
        try:
            response = httpx.get(address + "/v1/sys/init", timeout=2, trust_env=False)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(.3)
    raise RuntimeError("Isolated OpenBao readiness failed")


def _ledger_events(checkpoint):
    path = ops.RT / "shared/ledger/events.jsonl"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
        try:
            text = stream.read()
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    unique = {}
    for index, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        event = json.loads(line)
        if not isinstance(event.get("at"), (float, int)):
            raise RuntimeError("Ledger timestamp invalid")
        if event["at"] <= checkpoint:
            continue
        if event.get("kind") not in {"principal", "device", "document", "grant"}:
            raise RuntimeError("Ledger record kind invalid")
        if not isinstance(event.get("id"), str) or not isinstance(event.get("changes"), dict):
            raise RuntimeError("Ledger security record invalid")
        key = event.get("event_id") or hashlib.sha256(line.encode()).hexdigest()
        if key not in unique:
            unique[key] = (event["at"], index, event)
    return [entry[2] for entry in sorted(unique.values(), key=lambda item: (item[0], item[1]))]


REPLAY = {
    "principal": ("principals", {"active", "role", "department", "permission_version", "updated_at"}),
    "device": ("devices", {"compliant", "revoked", "risk", "observed_at", "risk_at", "auto_refresh", "updated_at"}),
    "document": ("documents", {"label", "version", "retention_until", "legal_hold", "deleted", "deleted_at", "updated_at"}),
    "grant": ("grants", {"principal_id", "doc_id", "doc_version", "action", "expires_at", "revoked", "approver", "created_at", "updated_at"}),
}


def _reconcile(conn, events):
    applied = 0
    absent = set()
    expected = {}
    for event in events:
        kind, record_id = event["kind"], event["id"]
        table, allowed = REPLAY[kind]
        changes = {key: value for key, value in event["changes"].items() if key in allowed}
        if not changes:
            # Upload metadata is deliberately not a backup of document content.
            absent.add((kind, record_id))
            continue
        found = conn.execute(sql.SQL("SELECT id FROM {} WHERE id=%s FOR UPDATE").format(sql.Identifier(table)),
                             (record_id,)).fetchone()
        if not found:
            required = {"principal_id", "doc_id", "doc_version", "action", "expires_at", "revoked", "approver", "created_at", "updated_at"}
            if kind == "grant" and required.issubset(changes):
                doc_exists = conn.execute("SELECT 1 FROM documents WHERE id=%s", (changes["doc_id"],)).fetchone()
                if doc_exists:
                    values = {"id": record_id, **changes}
                    conn.execute(sql.SQL("INSERT INTO grants ({}) VALUES ({})").format(
                        sql.SQL(",").join(map(sql.Identifier, values)),
                        sql.SQL(",").join(sql.Placeholder() for _ in values)), list(values.values()))
                    found = {"id": record_id}
            if not found:
                # A post-snapshot document has no saved ciphertext and stays
                # unavailable. Missing entities cannot gain access by replay.
                absent.add((kind, record_id))
                continue
        conn.execute(sql.SQL("UPDATE {} SET {} WHERE id=%s").format(
            sql.Identifier(table),
            sql.SQL(",").join(sql.SQL("{}=%s").format(sql.Identifier(key)) for key in changes)),
            [*changes.values(), record_id])
        expected.setdefault((kind, record_id), {}).update(changes)
        applied += 1
    for (kind, record_id), changes in expected.items():
        table = REPLAY[kind][0]
        record = conn.execute(sql.SQL("SELECT * FROM {} WHERE id=%s").format(sql.Identifier(table)),
                              (record_id,)).fetchone()
        if not record or any(record[key] != value for key, value in changes.items()):
            raise RuntimeError("Replayed security state did not match ledger")
    return {"events_available": len(events), "events_applied": applied,
            "absent_post_snapshot_entities": [{"kind": kind, "id": record_id} for kind, record_id in sorted(absent)]}


def _verify_live_security(conn):
    """Ensure restoration does not revive current revocations or tombstones."""
    checks = {"inactive_principals": 0, "revoked_devices": 0, "tombstones": 0, "revoked_grants": 0}
    for kind, table, flag, counter in (
        ("principal", "principals", "active", "inactive_principals"),
        ("device", "devices", "revoked", "revoked_devices"),
        ("document", "documents", "deleted", "tombstones"),
        ("grant", "grants", "revoked", "revoked_grants"),
    ):
        for source in ops.rows(table):
            blocked = source[flag] is False if flag == "active" else source[flag] is True
            if not blocked:
                continue
            target = conn.execute(sql.SQL("SELECT {} FROM {} WHERE id=%s").format(
                sql.Identifier(flag), sql.Identifier(table)), (source["id"],)).fetchone()
            if target is not None and target[flag] != source[flag]:
                raise RuntimeError("Restored state would revive a revoked entity")
            if target is None and kind == "principal":
                raise RuntimeError("Restored principal missing from snapshot")
            checks[counter] += 1
    return checks


def restore(snapshot):
    """Restore and verify a pair in temporary services, leaving primary data intact."""
    started = time.time()
    manifest = _snapshot_manifest(snapshot)
    run_id = "bmdl-restore-" + uuid.uuid4().hex[:16]
    scratch_parent = BACKUPS / "restore"
    scratch = scratch_parent / run_id
    scratch.mkdir(parents=True, mode=0o700)
    scratch.chmod(0o700)
    dk = ops.engine()
    created_containers, created_volumes = [], []
    network = None
    lab = None
    attached = False
    stage_name = "encrypted_snapshot_restore"
    outcome = None
    cleanup_errors = []
    with ops.LOCK:
        try:
            _restic(["restore", manifest["restic_snapshot_id"], "--target", str(scratch)])
            saved = scratch / str(manifest["archive_path"]).lstrip("/")
            if not saved.resolve().is_relative_to(scratch.resolve()):
                raise RuntimeError("Snapshot archive path rejected")
            for filename, expected in manifest["hashes"].items():
                if filename not in {"db.dump", "bao.snap"} or _sha(saved / filename) != expected:
                    raise RuntimeError("Snapshot pair hash verification failed")
            # Independent operator material is necessary: a stolen repository
            # must not contain both the encrypted state and its unseal keys.
            material = ops._bao_root()
            if _keyset_fingerprint(material) != manifest["recovery_keyset_fingerprint"]:
                raise RuntimeError("Required independent operator recovery keyset unavailable")
            stage_name = "isolated_topology"
            network = dk.networks.create(run_id, driver="bridge", internal=True,
                                         labels={RUN_LABEL: run_id}, check_duplicate=True)
            lab = dk.containers.get(os.environ["HOSTNAME"])
            network.connect(lab)
            attached = True
            for suffix in ("pg", "bao"):
                created_volumes.append(dk.volumes.create(name=run_id + "-" + suffix, labels={RUN_LABEL: run_id}))
            pg_password = secrets.token_urlsafe(32)
            pg = dk.containers.run(PG_IMAGE, name=run_id + "-pg", detach=True,
                environment={"POSTGRES_PASSWORD": pg_password, "POSTGRES_DB": "bmdl"},
                volumes={created_volumes[0].name: {"bind": "/var/lib/postgresql/data", "mode": "rw"}},
                network=network.name, labels={RUN_LABEL: run_id}, mem_limit="512m")
            created_containers.append(pg)
            configuration = (
                'ui = false\n'
                f'api_addr = "http://{run_id}-bao:8200"\n'
                f'cluster_addr = "https://{run_id}-bao:8201"\n'
                'storage "raft" { path = "/bao/data" node_id = "recovery-1" }\n'
                'listener "tcp" { address = "0.0.0.0:8200" tls_disable = true }\n'
            )
            config_file = scratch / "bao.hcl"
            config_file.write_text(configuration)
            config_file.chmod(0o644)
            project_host = os.environ.get("PROJECT_HOST_PATH", "/mnt/e/btl_bao_mat_Du_lieu")
            host_config = project_host.rstrip("/") + "/runtime/backups/restore/" + run_id + "/bao.hcl"
            # The image entrypoint drops to uid 100/gid 1000 even when Docker
            # starts as root; give only this new, labeled volume that ownership.
            dk.containers.run(BAO_IMAGE, ["-c", "chown -R 100:1000 /bao/data"],
                entrypoint="sh", user="0:0", remove=True, network_disabled=True,
                labels={RUN_LABEL: run_id},
                volumes={created_volumes[1].name: {"bind": "/bao/data", "mode": "rw"}})
            bao = dk.containers.run(BAO_IMAGE, ["server", "-config=/bao/config/recovery.hcl"],
                name=run_id + "-bao", detach=True, user="0:0",
                volumes={created_volumes[1].name: {"bind": "/bao/data", "mode": "rw"},
                         host_config: {"bind": "/bao/config/recovery.hcl", "mode": "ro"}},
                network=network.name, labels={RUN_LABEL: run_id}, mem_limit="512m")
            created_containers.append(bao)
            pg_host = _container_ip(pg, network)
            bao_address = "http://" + _container_ip(bao, network) + ":8200"
            network.reload()
            if network.attrs.get("Internal") is not True:
                raise RuntimeError("Recovery network is not internal")
            for target in created_containers:
                target.reload()
                if target.attrs["HostConfig"].get("PortBindings"):
                    raise RuntimeError("Recovery container published a host port")
                if set(target.attrs["NetworkSettings"]["Networks"]) != {network.name}:
                    raise RuntimeError("Recovery target attached to a non-isolated network")
            stage_name = "postgres_restore"
            _wait_pg(pg_host, pg_password)
            _put_file(pg, "/tmp/bmdl.dump", (saved / "db.dump").read_bytes())
            restored = pg.exec_run(["pg_restore", "-U", "postgres", "-d", "bmdl", "--clean", "--if-exists",
                                    "--no-owner", "--no-privileges", "/tmp/bmdl.dump"])
            if restored.exit_code:
                raise RuntimeError("Isolated PostgreSQL archive restore failed")
            stage_name = "raft_restore"
            _wait_bao(bao_address)
            temporary = _http("PUT", bao_address + "/v1/sys/init",
                              json={"secret_shares": 1, "secret_threshold": 1}).json()
            ops.unseal(bao_address, temporary)
            _http("POST", bao_address + "/v1/sys/storage/raft/snapshot-force",
                  token=temporary["root_token"], content=(saved / "bao.snap").read_bytes(),
                  headers={"Content-Type": "application/octet-stream"})
            ops.unseal(bao_address, material)
            stage_name = "content_verification"
            conn = psycopg.connect(host=pg_host, port=5432, dbname="bmdl", user="postgres",
                                    password=pg_password, connect_timeout=3, row_factory=dict_row)
            with conn:
                documents = conn.execute("SELECT id,ciphertext,sha256 FROM documents WHERE deleted=false ORDER BY id").fetchall()
                if not documents:
                    raise RuntimeError("Snapshot contains no verifiable document")
                verified = 0
                for document in documents:
                    data = _http("POST", bao_address + "/v1/transit/decrypt/documents",
                                 token=material["root_token"], json={"ciphertext": document["ciphertext"]}).json()["data"]
                    plaintext = base64.b64decode(data["plaintext"], validate=True)
                    if hashlib.sha256(plaintext).hexdigest() != document["sha256"]:
                        raise RuntimeError("Recovered document did not match its stored hash")
                    verified += 1
                    del plaintext
                if conn.execute("SELECT to_regclass('public.restricted_approvals') AS name").fetchone()["name"]:
                    conn.execute("DELETE FROM restricted_approvals")
                stage_name = "security_reconciliation"
                events = _ledger_events(manifest["checkpoint"])
                reconciliation = _reconcile(conn, events)
                safety = _verify_live_security(conn)
                remaining = conn.execute("SELECT count(*) AS n FROM documents WHERE deleted=false").fetchone()["n"]
                blocked = conn.execute("SELECT count(*) AS n FROM documents WHERE deleted=true").fetchone()["n"]
            stage_name = "completed"
            outcome = {
                "snapshot_id": manifest["snapshot_id"], "run_id": run_id,
                "isolated": True, "reconciled": True, "contents_verified": True,
                "verified_documents": verified, "available_documents": remaining,
                "blocked_documents": blocked, "revocation_checks": safety,
                "reconciliation": reconciliation, "reconciliation_checked_at": time.time(),
                "rto_seconds": round(time.time() - started, 3),
                "rpo_seconds": round(max(0, started - manifest["checkpoint"]), 3),
                "rpo_definition": "Snapshot age at recovery start; exposure window, not a measurement of lost business content",
                "checkpoint": manifest["checkpoint"], "pair_hashes_verified": True,
                "internal_network": True, "published_ports": False,
                "primary_replaced": False, "kms_driver": "actual isolated OpenBao Raft snapshot",
                "recovery_material_external": True,
                "database_driver": "actual isolated PostgreSQL pg_restore",
            }
        except Exception as error:
            outcome = {"snapshot_id": manifest["snapshot_id"], "run_id": run_id,
                       "status": "failed", "stage": stage_name, "error_type": type(error).__name__,
                       "duration_seconds": round(time.time() - started, 3)}
            raise RuntimeError(f"Isolated recovery failed at {stage_name} ({type(error).__name__})") from None
        finally:
            for target in reversed(created_containers):
                try:
                    target.reload()
                    if target.labels.get(RUN_LABEL) != run_id:
                        raise RuntimeError("Recovery cleanup ownership mismatch")
                    target.remove(force=True, v=True)
                except Exception:
                    cleanup_errors.append("container")
            if attached and network and lab:
                try:
                    network.disconnect(lab, force=True)
                except Exception:
                    cleanup_errors.append("lab-network")
            if network:
                try:
                    network.reload()
                    if network.attrs.get("Labels", {}).get(RUN_LABEL) != run_id:
                        raise RuntimeError("Recovery cleanup ownership mismatch")
                    network.remove()
                except Exception:
                    cleanup_errors.append("network")
            for volume in created_volumes:
                try:
                    volume.reload()
                    if volume.attrs.get("Labels", {}).get(RUN_LABEL) != run_id:
                        raise RuntimeError("Recovery cleanup ownership mismatch")
                    volume.remove()
                except Exception:
                    cleanup_errors.append("volume")
            try:
                _remove_scratch(scratch, scratch_parent)
            except Exception:
                cleanup_errors.append("scratch")
            if outcome is not None:
                outcome["temporary_resources_removed"] = not cleanup_errors
                outcome["cleanup_errors"] = cleanup_errors
                _write_json(RESULTS / (run_id + ".json"), outcome)
    if cleanup_errors:
        raise RuntimeError("Recovery verified but temporary resource cleanup requires operator attention")
    return outcome


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["backup"]:
        print(json.dumps(backup(), ensure_ascii=False))
    elif len(sys.argv) == 3 and sys.argv[1] == "restore":
        print(json.dumps(restore(sys.argv[2]), ensure_ascii=False))
    else:
        raise SystemExit("Usage: python -m lab.recovery backup | restore SNAPSHOT_ID")
