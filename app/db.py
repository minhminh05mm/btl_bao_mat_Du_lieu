"""PostgreSQL schema, deterministic synthetic fixtures and startup bootstrap."""
import hashlib
import json
import time
import uuid

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from . import config
from .fixture_data import DATASET_VERSION, fixture_definition, fixture_payload
from .security import normalize_serial, transit

USERS = [
    ("alice", "staff", "A"), ("anna", "staff", "A"), ("adam", "manager", "A"),
    ("bob", "staff", "B"), ("bea", "staff", "B"), ("brian", "manager", "B"),
    ("auditor", "auditor", "OPS"), ("secadmin", "security_admin", "OPS"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS principals (
 id text PRIMARY KEY, username text UNIQUE NOT NULL, subject_id text UNIQUE NOT NULL,
 role text NOT NULL, department text NOT NULL, active boolean NOT NULL DEFAULT true,
 permission_version integer NOT NULL DEFAULT 1, updated_at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS devices (
 id text PRIMARY KEY, principal_id text NOT NULL REFERENCES principals(id),
 cert_serial text UNIQUE NOT NULL, compliant boolean, revoked boolean NOT NULL DEFAULT false,
 risk text, observed_at double precision, risk_at double precision,
 auto_refresh boolean NOT NULL DEFAULT true, updated_at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
 id text PRIMARY KEY, title text NOT NULL, owner_id text NOT NULL REFERENCES principals(id),
 department text NOT NULL, label text NOT NULL, version integer NOT NULL DEFAULT 1,
 retention_until double precision NOT NULL, legal_hold boolean NOT NULL DEFAULT false,
 deleted boolean NOT NULL DEFAULT false, ciphertext text NOT NULL, sha256 text NOT NULL,
 created_at double precision NOT NULL, updated_at double precision NOT NULL,
 deleted_at double precision
);
CREATE TABLE IF NOT EXISTS grants (
 id text PRIMARY KEY, principal_id text NOT NULL REFERENCES principals(id),
 doc_id text NOT NULL REFERENCES documents(id), doc_version integer NOT NULL,
 action text NOT NULL DEFAULT 'download', expires_at double precision NOT NULL,
 revoked boolean NOT NULL DEFAULT false, approver text NOT NULL REFERENCES principals(id),
 created_at double precision NOT NULL, updated_at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS restricted_approvals (
 id text PRIMARY KEY, principal_id text NOT NULL REFERENCES principals(id),
 doc_id text NOT NULL, doc_version integer NOT NULL, department text NOT NULL,
 approver text NOT NULL REFERENCES principals(id), expires_at double precision NOT NULL,
 consumed boolean NOT NULL DEFAULT false, purpose text NOT NULL, created_at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
 id bigserial PRIMARY KEY, event_id text UNIQUE NOT NULL, request_id text NOT NULL,
 principal_id text, subject_id text, device_id text, doc_id text,
 action text NOT NULL, decision text NOT NULL, reason text NOT NULL,
 policy_version text NOT NULL, phase text NOT NULL, mode text NOT NULL,
 created_at double precision NOT NULL, details jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS audit_subject_time ON audit(principal_id,created_at);
CREATE INDEX IF NOT EXISTS grants_target ON grants(principal_id,doc_id,expires_at);
CREATE TABLE IF NOT EXISTS alerts (
 id text PRIMARY KEY, principal_id text NOT NULL, reason text NOT NULL,
 count integer NOT NULL, window_seconds integer NOT NULL,
 created_at double precision NOT NULL, acknowledged boolean NOT NULL DEFAULT false,
 acknowledged_by text, acknowledged_at double precision
);
CREATE TABLE IF NOT EXISTS ledger_outbox (
 sequence bigserial PRIMARY KEY, event_id text UNIQUE NOT NULL, event jsonb NOT NULL,
 delivered boolean NOT NULL DEFAULT false
);
CREATE TABLE IF NOT EXISTS app_state (key text PRIMARY KEY, value text NOT NULL);
"""


def connect():
    return psycopg.connect(config.DATABASE_URL, row_factory=dict_row, connect_timeout=4)


def bootstrap(*, reset=False):
    registry = json.loads((config.RUNTIME / "pki/registry.json").read_text(encoding="utf-8"))
    if "users" in registry and isinstance(registry["users"], dict):
        registry = registry["users"]
    with connect() as conn:
        # B0 and B1 start simultaneously; only one may initialize fixtures.
        conn.execute("SELECT pg_advisory_xact_lock(20261015)")
        conn.execute(SCHEMA)
        if reset:
            # Only the trusted operator CLI calls this; no business reset route.
            conn.execute("TRUNCATE restricted_approvals,grants,documents,devices,principals,audit,alerts,ledger_outbox,app_state RESTART IDENTITY CASCADE")
        if conn.execute("SELECT 1 FROM app_state WHERE key='seed_version' AND value='1'").fetchone():
            return
        if conn.execute("SELECT count(*) AS n FROM principals").fetchone()["n"]:
            # Existing state must not be silently overwritten on a restart.
            raise RuntimeError("Existing data has no completed seed marker; operator reconciliation required")
        now = time.time()
        for username, role, department in USERS:
            entry = registry[username]
            subject_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"bmdl:{username}"))
            if entry.get("subject_id", subject_id) != subject_id:
                raise RuntimeError("Fixture subject mapping mismatch")
            conn.execute(
                "INSERT INTO principals(id,username,subject_id,role,department,updated_at) VALUES (%s,%s,%s,%s,%s,%s)",
                (username, username, subject_id, role, department, now),
            )
            conn.execute(
                "INSERT INTO devices(id,principal_id,cert_serial,compliant,risk,observed_at,risk_at,updated_at) "
                "VALUES (%s,%s,%s,true,'NORMAL',%s,%s,%s)",
                (f"dev-{username}", username, normalize_serial(entry["serial"]), now, now, now),
            )
        for dept, owners in (("A", ["alice", "anna", "adam"]), ("B", ["bob", "bea", "brian"])):
            for letter, count, label in (("I", 5, "internal"), ("C", 3, "confidential"), ("R", 2, "restricted")):
                for i in range(1, count + 1):
                    doc_id = f"{dept}-{letter}{i:02d}"
                    owner = owners[(i - 1) % 3] if letter != "R" else owners[0 if i == 1 else 2]
                    definition = fixture_definition(doc_id)
                    if definition["owner_id"] != owner or definition["baseline_label"] != label:
                        raise RuntimeError("Reviewed fixture policy mapping mismatch")
                    payload = fixture_payload(doc_id)
                    ciphertext = transit("encrypt", payload)
                    conn.execute(
                        "INSERT INTO documents(id,title,owner_id,department,label,version,retention_until,ciphertext,sha256,created_at,updated_at) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (doc_id, definition["title"], owner, dept, label, 2 if letter == "R" else 1,
                         now + config.LABEL_DAYS[label] * 86400, ciphertext, hashlib.sha256(payload).hexdigest(), now, now),
                    )
                    if letter == "R":
                        conn.execute(
                            "INSERT INTO audit(event_id,request_id,principal_id,subject_id,doc_id,action,decision,reason,policy_version,phase,mode,created_at,details) "
                            "VALUES (%s,%s,'trusted-fixture-operator','trusted-fixture-operator',%s,'raise_label','ALLOW','ALLOW',%s,'completion','B1',%s,%s)",
                            (str(uuid.uuid4()), f"seed-{doc_id}", doc_id, config.POLICY_VERSION, now,
                             Jsonb({"fixture_setup": True, "from": "confidential", "to": "restricted", "version": 2})),
                        )
        conn.execute("INSERT INTO app_state(key,value) VALUES ('seed_version','1')")
        conn.execute("INSERT INTO app_state(key,value) VALUES ('dataset_version',%s)", (DATASET_VERSION,))


def refresh_devices():
    with connect() as conn:
        now = time.time()
        conn.execute(
            "UPDATE devices SET observed_at=%s,risk_at=%s WHERE auto_refresh=true", (now, now)
        )
