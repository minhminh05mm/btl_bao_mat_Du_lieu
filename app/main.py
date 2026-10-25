"""Fail-closed PEP for the local synthetic-document demonstration.

Run with uvicorn app.main:app. Only the verified gateway is a business ingress.
"""
import asyncio
import base64
import hashlib
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import PurePath

import psycopg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from psycopg.types.json import Jsonb

from . import config, db, ledger
from .security import Context, Problem, authenticate, decide, transit

logger = logging.getLogger("bmdl.backend")
ready = False


async def heartbeat():
    while True:
        try:
            await asyncio.to_thread(db.refresh_devices)
        except Exception:
            # Stale data will fail policy checks; do not fabricate fresh timestamps.
            logger.warning("Device refresh unavailable")
        await asyncio.sleep(20)


@asynccontextmanager
async def lifespan(application):
    global ready
    for attempt in range(180):
        try:
            await asyncio.to_thread(db.bootstrap)
            with db.connect() as conn:
                ledger.flush(conn)
            ready = True
            break
        except Exception:
            if attempt == 179:
                raise RuntimeError("Backend initialization failed; inspect service readiness without exposing secrets") from None
            await asyncio.sleep(2)
    task = asyncio.create_task(heartbeat()) if config.POLICY_MODE == "B1" else None
    try:
        yield
    finally:
        ready = False
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="Kho tài liệu Zero Trust", version="1.0.0", lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    try:
        response = await call_next(request)
    except Exception:
        logger.error("Unhandled backend request failure")
        response = JSONResponse(status_code=503, content={"detail": {
            "reason": "SERVICE_UNAVAILABLE", "request_id": request.state.request_id}})
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Policy-Version"] = config.POLICY_VERSION
    response.headers["X-Policy-Mode"] = config.POLICY_MODE
    return response


@app.exception_handler(Problem)
async def problem_handler(request: Request, exc: Problem):
    return JSONResponse(status_code=exc.status, content={"detail": {
        "reason": exc.reason, "request_id": request.state.request_id}},
        headers={"X-Policy-Reason": exc.reason, "X-Policy-Version": exc.policy_version})


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    # Never echo body contents, claims or document material in validation errors.
    return JSONResponse(status_code=422, content={"detail": {
        "reason": "INVALID_INPUT", "request_id": request.state.request_id}})


def audit_event(conn, ctx, request_id, action, doc_id, decision, reason, phase="pre_event", details=None):
    if config.faults().get("audit_write_failure"):
        raise Problem("AUDIT_UNAVAILABLE", 503)
    principal_id = ctx.id if ctx else None
    now = time.time()
    conn.execute(
        "INSERT INTO audit(event_id,request_id,principal_id,subject_id,device_id,doc_id,action,decision,reason,policy_version,phase,mode,created_at,details) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (str(uuid.uuid4()), request_id, principal_id,
         ctx.subject["subject_id"] if ctx else None,
         ctx.device["id"] if ctx else None, doc_id, action, decision, reason,
         config.POLICY_VERSION, phase, ctx.mode if ctx else config.POLICY_MODE,
         now, Jsonb(details or {})),
    )
    if decision == "DENY" and principal_id:
        # Serialize the alert threshold per principal to avoid duplicate races.
        conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"alerts:{principal_id}",))
        count = conn.execute(
            "SELECT count(DISTINCT request_id) AS n FROM audit "
            "WHERE principal_id=%s AND decision='DENY' AND created_at>=%s",
            (principal_id, now - 60),
        ).fetchone()["n"]
        recent = conn.execute(
            "SELECT 1 FROM alerts WHERE principal_id=%s AND created_at>=%s",
            (principal_id, now - 60),
        ).fetchone()
        if count >= 5 and not recent:
            conn.execute(
                "INSERT INTO alerts(id,principal_id,reason,count,window_seconds,created_at) "
                "VALUES (%s,%s,'DENIAL_THRESHOLD',%s,60,%s)",
                (str(uuid.uuid4()), principal_id, count, now),
            )


def run(request, action, operation, doc_id=None):
    """Keep auth/state locks through policy, KMS and audit; commit before return."""
    ctx = None
    conn = None
    try:
        if not ready:
            raise Problem("INITIALIZING", 503)
        conn = db.connect()
        conn.execute("SET LOCAL lock_timeout='6s'")
        conn.execute("SET LOCAL statement_timeout='20s'")
        ctx = authenticate(request, conn)
        result = operation(conn, ctx)
        # Locks prevent concurrent state changes, but time itself may invalidate
        # signals, retention or a grant while PDP/KMS/audit work is in progress.
        for deadline, reason in ctx.deadlines:
            if time.time() >= deadline:
                raise Problem(reason)
        conn.commit()
        try:
            ledger.flush(conn)
        except Exception:
            # An outbox remains durable if journal delivery fails. Do not return
            # successful mutation acknowledgement before its reconciliation log.
            conn.rollback()
            raise Problem("LEDGER_UNAVAILABLE", 503)
        if isinstance(result, Response):
            result.headers["X-Policy-Reason"] = "ALLOW"
            return result
        return JSONResponse(content=result, headers={"X-Policy-Reason": "ALLOW"})
    except Problem as exc:
        if conn:
            conn.rollback()
            try:
                audit_event(conn, ctx, request.state.request_id, action, doc_id,
                            "DENY", exc.reason, phase="decision")
                conn.commit()
            except Exception:
                conn.rollback()
                if exc.reason != "AUDIT_UNAVAILABLE":
                    exc = Problem("AUDIT_UNAVAILABLE", 503)
        raise exc
    except Exception:
        if conn:
            conn.rollback()
            try:
                audit_event(conn, ctx, request.state.request_id, action, doc_id,
                            "DENY", "SERVICE_UNAVAILABLE", phase="decision")
                conn.commit()
            except Exception:
                conn.rollback()
        raise Problem("SERVICE_UNAVAILABLE", 503) from None
    finally:
        if conn:
            conn.close()


def resource(row):
    return {key: row[key] for key in (
        "id", "owner_id", "department", "label", "version", "retention_until", "legal_hold", "deleted"
    )}


def metadata(row):
    return {key: row[key] for key in (
        "id", "title", "owner_id", "department", "label", "version", "retention_until", "legal_hold"
    )}


def get_document(conn, doc_id, *, update=False):
    row = conn.execute(
        "SELECT * FROM documents WHERE id=%s " + ("FOR UPDATE" if update else "FOR SHARE"), (doc_id,)
    ).fetchone()
    if not row or row["deleted"]:
        raise Problem("NOT_FOUND", 404)
    return row


def get_grant(conn, principal_id, doc):
    # Even expired/revoked grant state is explicit policy input, not silently reused.
    return conn.execute(
        "SELECT * FROM grants WHERE principal_id=%s AND doc_id=%s "
        "ORDER BY (doc_version=%s AND action='download' AND revoked=false AND expires_at>%s) DESC, "
        "expires_at DESC,created_at DESC LIMIT 1 FOR SHARE",
        (principal_id, doc["id"], doc["version"], time.time()),
    ).fetchone()


def check(conn, ctx, action, doc=None, grant=None, *, admin=False):
    if doc and grant is None and action == "download":
        grant = get_grant(conn, ctx.id, doc)
    decision = decide(ctx, action, resource(doc) if doc else None, grant, force_b1=admin)
    if ctx.mode == "B1" or admin or action not in {"me", "list", "metadata", "download"}:
        for field in ("observed_at", "risk_at"):
            assessed = ctx.device.get(field)
            if not isinstance(assessed, (int, float)):
                raise Problem("MISSING_OR_STALE")
            ctx.deadlines.append((assessed + config.SIGNAL_TTL, "MISSING_OR_STALE"))
        if doc and action == "download" and doc["label"] == "restricted" and grant:
            ctx.deadlines.append((grant["expires_at"], "RESTRICTED_GRANT"))
    if doc and action in {"metadata", "download", "list"}:
        ctx.deadlines.append((doc["retention_until"], "RETENTION_EXPIRED"))
    return decision


def success_audit(conn, ctx, action, doc_id=None, details=None):
    audit_event(conn, ctx, ctx.request_id, action, doc_id, "ALLOW", "ALLOW", details=details)


class Upload(BaseModel):
    approval_id: str | None = None
    title: str = Field(min_length=1, max_length=200)
    label: str
    content_b64: str = Field(max_length=1_400_000)


class RestrictedApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")
    principal_id: str
    doc_id: str | None = None
    ttl_seconds: float = Field(default=900, gt=0, le=3600)


class DocumentEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    label: str
    legal_hold: bool
    retention_until: float = Field(ge=0, le=253402300799)
    approval_id: str | None = None


class RaiseLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str


class PrincipalUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active: bool | None = None
    role: str | None = None
    department: str | None = None


class DeviceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    compliant: bool | None = None
    revoked: bool | None = None
    risk: str | None = None
    observed_at: float | None = None
    risk_at: float | None = None
    auto_refresh: bool | None = None


class GrantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    principal_id: str
    doc_id: str
    ttl_seconds: float = Field(default=300, gt=0, le=3600)


@app.get("/health")
def health():
    if not ready:
        return JSONResponse(status_code=503, content={"status": "initializing"})
    try:
        with db.connect() as conn:
            conn.execute("SELECT 1")
        return {"status": "ready", "mode": config.POLICY_MODE}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})


@app.get("/me")
def me(request: Request):
    def operation(conn, ctx):
        check(conn, ctx, "me")
        success_audit(conn, ctx, "me")
        return {"id": ctx.id, "username": ctx.subject["username"], "role": ctx.subject["role"],
                "department": ctx.subject["department"], "active": ctx.subject["active"],
                "permission_version": ctx.subject["permission_version"], "device_id": ctx.device["id"],
                "policy_mode": ctx.mode, "signal_ttl_seconds": config.SIGNAL_TTL}
    return run(request, "me", operation)


@app.get("/documents")
def documents(request: Request):
    def operation(conn, ctx):
        check(conn, ctx, "me")
        rows = conn.execute("SELECT * FROM documents WHERE deleted=false ORDER BY id FOR SHARE").fetchall()
        items = []
        for row in rows:
            try:
                check(conn, ctx, "metadata", row)
                items.append(metadata(row))
            except Problem as exc:
                if exc.status != 403:
                    raise
                # Do not expose rejected resources or mistake PDP outage for an empty list.
        success_audit(conn, ctx, "list", details={"returned_count": len(items)})
        return {"items": items}
    return run(request, "list", operation)


@app.get("/documents/{doc_id}/metadata")
def document_metadata(doc_id: str, request: Request):
    def operation(conn, ctx):
        row = get_document(conn, doc_id)
        check(conn, ctx, "metadata", row)
        success_audit(conn, ctx, "metadata", doc_id)
        return metadata(row)
    return run(request, "metadata", operation, doc_id)


@app.get("/documents/{doc_id}/download")
def download(doc_id: str, request: Request):
    def operation(conn, ctx):
        row = get_document(conn, doc_id)
        check(conn, ctx, "download", row)
        # All state rows remain FOR SHARE locked until decrypt, audit and commit.
        data = transit("decrypt", row["ciphertext"])
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise Problem("INTEGRITY_FAILURE", 503)
        success_audit(conn, ctx, "download", doc_id,
                      {"document_version": row["version"], "bytes_prepared": len(data)})
        audit_event(conn, ctx, ctx.request_id, "download", doc_id, "ALLOW", "ALLOW",
                    phase="completion", details={"server_response_prepared": True, "client_delivery_confirmed": False})
        return Response(content=data, media_type="application/octet-stream",
                        headers={"Content-Disposition": f'attachment; filename="{row["id"]}.bin"'})
    return run(request, "download", operation, doc_id)


@app.post("/documents")
def upload(body: Upload, request: Request):
    def operation(conn, ctx):
        title = body.title.strip()
        if (body.label not in {"internal", "confidential", "restricted"} or PurePath(title).suffix.lower() not in {".txt", ".csv", ".pdf"}
                or any(c in title for c in "\\/\r\n\x00")):
            raise Problem("INVALID_INPUT", 400)
        try:
            data = base64.b64decode(body.content_b64, validate=True)
        except Exception:
            raise Problem("INVALID_INPUT", 400)
        if not data or len(data) > 1024 * 1024:
            raise Problem("INVALID_SIZE", 400)
        now = time.time()
        row = {"id": "U-" + uuid.uuid4().hex, "title": title, "owner_id": ctx.id,
               "department": ctx.subject["department"], "label": body.label, "version": 1,
               "retention_until": now + config.LABEL_DAYS[body.label] * 86400,
               "legal_hold": False, "deleted": False}
        grant = None
        if body.label == "restricted":
            row, grant = approved_resource(conn, ctx, body.approval_id, row, creating=True)
        check(conn, ctx, "upload", row, grant=grant)
        ciphertext = transit("encrypt", data)
        success_audit(conn, ctx, "upload", row["id"], {"document_version": 1, "bytes": len(data)})
        conn.execute(
            "INSERT INTO documents(id,title,owner_id,department,label,version,retention_until,legal_hold,deleted,ciphertext,sha256,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,%s,1,%s,false,false,%s,%s,%s,%s)",
            (row["id"], title, ctx.id, row["department"], body.label, row["retention_until"],
             ciphertext, hashlib.sha256(data).hexdigest(), now, now),
        )
        if grant:
            commit_approval(conn, ctx, body.approval_id, grant)
        ledger.enqueue(conn, "document_uploaded", row["id"], resource(row), ctx.id)
        return metadata(row)
    return run(request, "upload", operation)


def approved_resource(conn, ctx, approval_id, row, *, creating=False):
    approval = conn.execute("SELECT * FROM restricted_approvals WHERE id=%s FOR UPDATE", (approval_id or "",)).fetchone()
    if (not approval or approval["consumed"] or approval["expires_at"] <= time.time()
            or approval["principal_id"] != ctx.id or approval["department"] != ctx.subject["department"]
            or approval["purpose"] != ("create" if creating else "upgrade")
            or (not creating and (approval["doc_id"] != row["id"] or approval["doc_version"] != row["version"]))):
        raise Problem("RESTRICTED_APPROVAL")
    approver = conn.execute("SELECT * FROM principals WHERE id=%s FOR SHARE", (approval["approver"],)).fetchone()
    if not approver or not approver["active"] or approver["role"] != "security_admin" or approver["id"] == ctx.id:
        raise Problem("RESTRICTED_APPROVAL")
    if creating:
        row = {**row, "id": approval["doc_id"]}
    grant = {"id": str(uuid.uuid4()), "principal_id": ctx.id, "doc_id": row["id"],
             "doc_version": row["version"], "action": "download", "expires_at": approval["expires_at"],
             "revoked": False, "approver": approval["approver"], "created_at": time.time(), "updated_at": time.time()}
    ctx.deadlines.append((approval["expires_at"], "RESTRICTED_APPROVAL"))
    return row, grant


def commit_approval(conn, ctx, approval_id, grant):
    conn.execute("INSERT INTO grants(id,principal_id,doc_id,doc_version,action,expires_at,revoked,approver,created_at,updated_at) "
                 "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", tuple(grant.values()))
    conn.execute("UPDATE restricted_approvals SET consumed=true WHERE id=%s", (approval_id,))
    success_audit(conn, ctx, "grant", grant["doc_id"], {"grant_id": grant["id"], "approver": grant["approver"], "approval_id": approval_id})
    ledger.enqueue(conn, "grant_created", grant["id"], grant, ctx.id)


@app.post("/admin/restricted-approvals")
def approve_restricted(body: RestrictedApproval, request: Request):
    def operation(conn, ctx):
        check(conn, ctx, "admin", admin=True)
        target = conn.execute("SELECT * FROM principals WHERE id=%s FOR SHARE", (body.principal_id,)).fetchone()
        if not target or not target["active"] or target["role"] != "manager" or target["id"] == ctx.id:
            raise Problem("RESTRICTED_ROLE")
        doc_id, version = "U-" + uuid.uuid4().hex, 1
        if body.doc_id:
            doc = get_document(conn, body.doc_id)
            if doc["department"] != target["department"]:
                raise Problem("DEPARTMENT")
            if doc["label"] == "restricted":
                raise Problem("INVALID_INPUT", 400)
            doc_id, version = doc["id"], doc["version"] + 1
        now = time.time()
        result = {"id": str(uuid.uuid4()), "principal_id": target["id"], "doc_id": doc_id,
                  "doc_version": version, "department": target["department"], "approver": ctx.id,
                  "expires_at": now + body.ttl_seconds, "consumed": False,
                  "purpose": "upgrade" if body.doc_id else "create", "created_at": now}
        conn.execute("INSERT INTO restricted_approvals(id,principal_id,doc_id,doc_version,department,approver,expires_at,consumed,purpose,created_at) "
                     "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", tuple(result.values()))
        success_audit(conn, ctx, "grant", doc_id, {"operation": "approve_restricted", "target_id": target["id"], "approval_id": result["id"]})
        return result
    return run(request, "grant", operation, body.doc_id)


@app.put("/documents/{doc_id}")
def edit_document(doc_id: str, body: DocumentEdit, request: Request):
    def operation(conn, ctx):
        row = get_document(conn, doc_id, update=True)
        # Editing always uses current B1 download permission, including a live
        # per-document approval. The B0 comparison cannot bypass a mutation.
        check(conn, ctx, "download", row, admin=True)
        title = body.title.strip()
        if (body.label not in config.LABEL_RANK or not title or PurePath(title).suffix.lower() not in {".txt", ".csv", ".pdf"}
                or any(c in title for c in "\\/\r\n\x00")):
            raise Problem("INVALID_INPUT", 400)
        if config.LABEL_RANK[body.label] < config.LABEL_RANK[row["label"]]:
            raise Problem("LABEL_DOWNGRADE")
        if body.legal_hold != row["legal_hold"] or abs(body.retention_until-row["retention_until"]) >= 60:
            raise Problem("LIFECYCLE_ADMIN_REQUIRED")
        retention = row["retention_until"]
        if body.label != row["label"]:
            retention = min(retention, time.time() + config.LABEL_DAYS[body.label]*86400)
        version = row["version"] + (body.label != row["label"])
        updated = {**row, "title": title, "label": body.label, "version": version,
                   "legal_hold": row["legal_hold"], "retention_until": retention}
        grant = None
        if body.label == "restricted" and row["label"] != "restricted":
            updated, grant = approved_resource(conn, ctx, body.approval_id, updated)
            check(conn, ctx, "download", updated, grant=grant, admin=True)
        now = time.time()
        conn.execute("UPDATE documents SET title=%s,label=%s,legal_hold=%s,retention_until=%s,version=%s,updated_at=%s WHERE id=%s",
                     (title,body.label,row["legal_hold"],retention,version,now,doc_id))
        if grant:
            commit_approval(conn, ctx, body.approval_id, grant)
        success_audit(conn, ctx, "update_document", doc_id, {"from_label": row["label"], "to_label": body.label, "version": version})
        ledger.enqueue(conn, "document_updated", doc_id, {**resource(updated), "updated_at": now}, ctx.id)
        return metadata(updated)
    return run(request, "update_document", operation, doc_id)


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str, request: Request):
    def operation(conn, ctx):
        row = get_document(conn, doc_id, update=True)
        check(conn, ctx, "delete", row)
        success_audit(conn, ctx, "delete", doc_id)
        now = time.time()
        conn.execute("UPDATE documents SET deleted=true,deleted_at=%s,updated_at=%s,version=version+1 WHERE id=%s",
                     (now, now, doc_id))
        payload = {"deleted": True, "deleted_at": now, "version": row["version"] + 1}
        ledger.enqueue(conn, "document_deleted", doc_id, payload, ctx.id)
        return {"id": doc_id, **payload}
    return run(request, "delete", operation, doc_id)


@app.post("/admin/documents/{doc_id}/raise-label")
def raise_label(doc_id: str, body: RaiseLabel, request: Request):
    def operation(conn, ctx):
        row = get_document(conn, doc_id, update=True)
        check(conn, ctx, "raise_label", row, admin=True)
        if body.label not in config.LABEL_RANK or config.LABEL_RANK[body.label] <= config.LABEL_RANK.get(row["label"], 99):
            raise Problem("LABEL_DOWNGRADE", 403)
        success_audit(conn, ctx, "raise_label", doc_id,
                      {"from": row["label"], "to": body.label, "version": row["version"] + 1})
        now = time.time()
        retention = min(row["retention_until"], now + config.LABEL_DAYS[body.label] * 86400)
        conn.execute("UPDATE documents SET label=%s,version=version+1,retention_until=%s,updated_at=%s WHERE id=%s",
                     (body.label, retention, now, doc_id))
        payload = {"label": body.label, "version": row["version"] + 1, "retention_until": retention, "updated_at": now}
        ledger.enqueue(conn, "document_label_raised", doc_id, payload, ctx.id)
        return {"id": doc_id, **payload}
    return run(request, "raise_label", operation, doc_id)


@app.put("/admin/principals/{principal_id}")
def update_principal(principal_id: str, body: PrincipalUpdate, request: Request):
    def operation(conn, ctx):
        check(conn, ctx, "admin", admin=True)
        changes = body.model_dump(exclude_unset=True)
        if not changes or any(value is None for value in changes.values()):
            raise Problem("INVALID_INPUT", 400)
        if principal_id == ctx.id and ("role" in changes or "department" in changes):
            raise Problem("SELF_PRIVILEGE_CHANGE", 403)
        if changes.get("role") == "security_admin":
            raise Problem("PRIVILEGE_ESCALATION", 403)
        if "role" in changes and changes["role"] not in {"staff", "manager", "auditor"}:
            raise Problem("INVALID_INPUT", 400)
        if "department" in changes and changes["department"] not in {"A", "B", "OPS"}:
            raise Problem("INVALID_INPUT", 400)
        target = conn.execute("SELECT * FROM principals WHERE id=%s FOR UPDATE", (principal_id,)).fetchone()
        if not target:
            raise Problem("NOT_FOUND", 404)
        if target["role"] == "security_admin" and principal_id != ctx.id:
            raise Problem("PRIVILEGE_ESCALATION", 403)
        success_audit(conn, ctx, "admin", details={"target_type": "principal", "target_id": principal_id, "changes": changes})
        assignments = ",".join(f"{column}=%s" for column in changes)
        now = time.time()
        conn.execute(f"UPDATE principals SET {assignments},permission_version=permission_version+1,updated_at=%s WHERE id=%s",
                     [*changes.values(), now, principal_id])
        updated = conn.execute("SELECT * FROM principals WHERE id=%s", (principal_id,)).fetchone()
        payload = {key: updated[key] for key in ("active", "role", "department", "permission_version", "updated_at")}
        ledger.enqueue(conn, "principal_updated", principal_id, payload, ctx.id)
        return {"id": principal_id, **payload}
    return run(request, "admin", operation)


@app.put("/admin/devices/{device_id}")
def update_device(device_id: str, body: DeviceUpdate, request: Request):
    def operation(conn, ctx):
        check(conn, ctx, "admin", admin=True)
        changes = body.model_dump(exclude_unset=True)
        if not changes or ("risk" in changes and changes["risk"] not in {None, "NORMAL", "HIGH"}):
            raise Problem("INVALID_INPUT", 400)
        if any(changes.get(key) is None for key in ("revoked", "auto_refresh") if key in changes):
            raise Problem("INVALID_INPUT", 400)
        row = conn.execute("SELECT * FROM devices WHERE id=%s FOR UPDATE", (device_id,)).fetchone()
        if not row:
            raise Problem("NOT_FOUND", 404)
        success_audit(conn, ctx, "admin", details={"target_type": "device", "target_id": device_id, "changes": changes})
        assignments = ",".join(f"{column}=%s" for column in changes)
        now = time.time()
        conn.execute(f"UPDATE devices SET {assignments},updated_at=%s WHERE id=%s", [*changes.values(), now, device_id])
        updated = conn.execute("SELECT * FROM devices WHERE id=%s", (device_id,)).fetchone()
        payload = {key: updated[key] for key in (
            "compliant", "revoked", "risk", "observed_at", "risk_at", "auto_refresh", "updated_at"
        )}
        ledger.enqueue(conn, "device_updated", device_id, payload, ctx.id)
        return {"id": device_id, "principal_id": row["principal_id"], **payload}
    return run(request, "admin", operation)


@app.post("/admin/grants")
def create_grant(body: GrantCreate, request: Request):
    def operation(conn, ctx):
        doc = get_document(conn, body.doc_id, update=True)
        check(conn, ctx, "admin", admin=True)
        if body.principal_id == ctx.id:
            raise Problem("SELF_APPROVAL", 403)
        target = conn.execute("SELECT * FROM principals WHERE id=%s FOR SHARE", (body.principal_id,)).fetchone()
        if not target:
            raise Problem("NOT_FOUND", 404)
        now = time.time()
        grant = {"id": str(uuid.uuid4()), "principal_id": body.principal_id, "doc_id": doc["id"],
                 "doc_version": doc["version"], "action": "download", "expires_at": now + body.ttl_seconds,
                 "revoked": False, "approver": ctx.id, "created_at": now, "updated_at": now}
        check(conn, ctx, "grant", doc, grant=grant, admin=True)
        if doc["label"] != "restricted":
            raise Problem("INVALID_METADATA", 400)
        success_audit(conn, ctx, "grant", doc["id"], {"target_id": body.principal_id, "grant_id": grant["id"]})
        conn.execute(
            "INSERT INTO grants(id,principal_id,doc_id,doc_version,action,expires_at,revoked,approver,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", tuple(grant.values()),
        )
        ledger.enqueue(conn, "grant_created", grant["id"], grant, ctx.id)
        return grant
    return run(request, "grant", operation, body.doc_id)


@app.delete("/admin/grants/{grant_id}")
def revoke_grant(grant_id: str, request: Request):
    def operation(conn, ctx):
        check(conn, ctx, "admin", admin=True)
        row = conn.execute("SELECT * FROM grants WHERE id=%s FOR UPDATE", (grant_id,)).fetchone()
        if not row:
            raise Problem("NOT_FOUND", 404)
        success_audit(conn, ctx, "grant", row["doc_id"], {"grant_id": grant_id, "revoked": True})
        now = time.time()
        conn.execute("UPDATE grants SET revoked=true,updated_at=%s WHERE id=%s", (now, grant_id))
        ledger.enqueue(conn, "grant_revoked", grant_id, {"revoked": True, "updated_at": now}, ctx.id)
        return {"id": grant_id, "revoked": True, "updated_at": now}
    return run(request, "grant", operation)


@app.get("/admin/state")
def admin_state(request: Request):
    def operation(conn, ctx):
        check(conn, ctx, "admin", admin=True)
        principals = conn.execute("SELECT id,username,role,department,active,permission_version,updated_at FROM principals ORDER BY id").fetchall()
        devices = conn.execute("SELECT id,principal_id,compliant,revoked,risk,observed_at,risk_at,auto_refresh,updated_at FROM devices ORDER BY id").fetchall()
        docs = conn.execute("SELECT id,owner_id,department,label,version,retention_until,legal_hold,deleted,deleted_at,updated_at FROM documents ORDER BY id").fetchall()
        grants = conn.execute("SELECT * FROM grants ORDER BY created_at DESC").fetchall()
        success_audit(conn, ctx, "admin", details={"operation": "state"})
        return {"principals": principals, "devices": devices, "documents": docs, "grants": grants,
                "signal_ttl_seconds": config.SIGNAL_TTL, "policy_version": config.POLICY_VERSION}
    return run(request, "admin", operation)


@app.get("/audit")
def audit(request: Request, limit: int = 200):
    def operation(conn, ctx):
        check(conn, ctx, "audit", admin=True)
        limit_value = max(1, min(limit, 5000))
        if ctx.subject["role"] == "security_admin":
            rows = conn.execute(
                "SELECT * FROM audit WHERE action IN ('admin','raise_label','grant','alert') OR reason IN "
                "('PDP_UNAVAILABLE','PDP_INVALID','KMS_UNAVAILABLE','AUDIT_UNAVAILABLE','SERVICE_UNAVAILABLE') "
                "ORDER BY id DESC LIMIT %s", (limit_value,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM audit ORDER BY id DESC LIMIT %s", (limit_value,)).fetchall()
        success_audit(conn, ctx, "audit", details={"returned_count": len(rows)})
        return {"items": rows}
    return run(request, "audit", operation)


@app.get("/alerts")
def alerts(request: Request):
    def operation(conn, ctx):
        check(conn, ctx, "audit", admin=True)
        rows = conn.execute("SELECT * FROM alerts ORDER BY created_at DESC LIMIT 500").fetchall()
        success_audit(conn, ctx, "alert", details={"operation": "list", "returned_count": len(rows)})
        return {"items": rows}
    return run(request, "audit", operation)


@app.post("/alerts/{alert_id}/ack")
def acknowledge_alert(alert_id: str, request: Request):
    def operation(conn, ctx):
        check(conn, ctx, "admin", admin=True)
        row = conn.execute("SELECT * FROM alerts WHERE id=%s FOR UPDATE", (alert_id,)).fetchone()
        if not row:
            raise Problem("NOT_FOUND", 404)
        success_audit(conn, ctx, "alert", details={"alert_id": alert_id, "operation": "ack"})
        now = time.time()
        conn.execute("UPDATE alerts SET acknowledged=true,acknowledged_by=%s,acknowledged_at=%s WHERE id=%s", (ctx.id, now, alert_id))
        return {"id": alert_id, "acknowledged": True, "acknowledged_by": ctx.id, "acknowledged_at": now}
    return run(request, "admin", operation)
