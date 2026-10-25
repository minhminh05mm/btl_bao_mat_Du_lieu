"""Local trusted lab console. Business traffic always goes through LabClient.

The operator console is deliberately a trusted management surface, bound to the
loopback interface by Compose. It is not part of the business authorization API.
"""
from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import html
import importlib
import inspect
import io
import json
import os
from pathlib import Path
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
PROJECT = Path(os.getenv("PROJECT_DIR", "/project"))
if not PROJECT.exists():
    PROJECT = HERE.parent
RUNTIME = Path(os.getenv("RUNTIME_DIR", "/runtime"))
ISSUER = os.getenv("OIDC_ISSUER", "https://localhost:9443/realms/bmdl")
OIDC_INTERNAL = os.getenv("OIDC_WEB_INTERNAL", "https://gateway:9443/realms/bmdl")
REDIRECT_URI = "http://localhost:8088/auth/callback"
def _known_users():
    from .management import known_users
    return known_users()
app = FastAPI(title="BMDL · Zero Trust Lab", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lab-task")
_jobs: dict[str, dict] = {}
_sessions: dict[str, dict] = {}
_guard = threading.RLock()
_client = None


def _clean(value):
    if isinstance(value, dict):
        return {str(k): ("[redacted]" if str(k).lower() in {
            "access_token", "refresh_token", "id_token", "password", "client_secret",
            "authorization", "bao_token", "proxy_secret", "private_key", "verifier",
        } else _clean(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _lab_client():
    global _client
    if _client is None:
        _client = importlib.import_module("lab.client").LabClient()
    return _client


def _operation(name, *args, **kwargs):
    function = getattr(importlib.import_module("lab.operations"), name)
    return _clean(function(*args, **kwargs))


def _stale_signals(enabled):
    now = time.time()
    devices = _operation("state").get("devices", [])
    changes = {"observed_at": now - 120 if enabled else now,
               "risk_at": now - 120 if enabled else now, "auto_refresh": not enabled}
    updated = [_operation("edit_state", "device", device["id"], changes) for device in devices]
    return {"fault": "stale_signals", "enabled": enabled, "devices_updated": len(updated),
            "simulated": True, "auto_refresh": not enabled}


def _session(request: Request, create=False):
    sid = request.cookies.get("bmdl_console")
    with _guard:
        session = _sessions.get(sid or "")
        if session and session["expires_at"] < time.time():
            _sessions.pop(sid, None)
            session = None
        if session is None and create:
            sid = secrets.token_urlsafe(32)
            session = {"csrf": secrets.token_urlsafe(32), "expires_at": time.time() + 28800}
            _sessions[sid] = session
    return sid, session


def _set_cookie(response, sid):
    response.set_cookie("bmdl_console", sid, httponly=True, samesite="lax", max_age=28800)


@app.middleware("http")
async def local_security(request: Request, call_next):
    host = request.headers.get("host", "").split(":")[0].lower()
    if host not in {"localhost", "127.0.0.1", "lab", "testserver"}:
        return JSONResponse({"error": "Console chỉ nhận truy cập cục bộ."}, status_code=400)
    if request.method in {"POST", "PUT", "DELETE", "PATCH"}:
        origin = request.headers.get("origin")
        if origin and origin not in {"http://localhost:8088", "http://127.0.0.1:8088"}:
            return JSONResponse({"error": "Nguồn yêu cầu không hợp lệ."}, status_code=403)
        _, session = _session(request)
        if not session or not secrets.compare_digest(
            request.headers.get("x-lab-csrf", ""), session["csrf"]
        ):
            return JSONResponse({"error": "Phiên quản trị đã hết hạn; tải lại trang."}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self' https://localhost:9443"
    )
    return response


@app.exception_handler(Exception)
async def uncaught_error(request, exception):
    return JSONResponse({"error": f"{type(exception).__name__}: {str(exception)[:500]}"}, status_code=500)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    sid, _ = _session(request, create=True)
    response = HTMLResponse((HERE / "templates" / "index.html").read_text(encoding="utf-8"))
    _set_cookie(response, sid)
    return response


@app.get("/lab/bootstrap")
async def bootstrap(request: Request):
    sid, session = _session(request, create=True)
    auth = session.get("auth")
    if auth and auth["expires_at"] <= time.time():
        session.pop("auth", None)
        auth = None
    response = JSONResponse({
        "csrf": session["csrf"], "users": sorted(_known_users()),
        "auth": {"username": auth["username"], "expires_at": auth["expires_at"]} if auth else None,
        "issuer": ISSUER, "trusted_operator": True,
    })
    _set_cookie(response, sid)
    return response


@app.get("/lab/state")
async def lab_state():
    return await asyncio.to_thread(_operation, "state")


async def _manage(name, *args):
    from . import management
    _ensure_idle()
    try:
        return _clean(await asyncio.to_thread(getattr(management, name), *args))
    except management.InputError as error:
        return JSONResponse({"detail": error.detail}, status_code=error.status)


@app.post("/lab/employees")
async def create_employee(request: Request):
    return await _manage("create_employee", await request.json())


@app.put("/lab/employees/{identifier}")
async def update_employee(identifier: str, request: Request):
    return await _manage("update_employee", identifier, await request.json())


@app.post("/lab/documents")
async def create_workspace_document(request: Request):
    body,token=_document_identity(request,await request.json(),creating=True)
    return await _manage("create_document",body,token)


@app.put("/lab/documents/{identifier}")
async def update_workspace_document(identifier: str, request: Request):
    body,token=_document_identity(request,await request.json())
    return await _manage("update_document",identifier,body,token)


def _document_identity(request,body,creating=False):
    if not isinstance(body,dict):return body,None
    _,session=_session(request)
    auth=(session or {}).get("auth")
    if auth:
        if auth["expires_at"]<=time.time():
            raise HTTPException(401,"Phiên đăng nhập đã hết hạn. Đăng nhập lại trước khi thay đổi tài liệu.")
        body={**body,"owner_id" if creating else "actor_id":auth["username"]}
        return body,auth["access_token"]
    return body,None


@app.post("/lab/documents/{identifier}/grants")
async def grant_workspace_document(identifier:str,request:Request):
    return await _manage("grant_document",identifier,await request.json())


@app.delete("/lab/documents/{identifier}/grants/{grant_id}")
async def revoke_workspace_document_grant(identifier:str,grant_id:str,request:Request):
    return await _manage("revoke_document_grant",identifier,grant_id,await request.json())


@app.get("/lab/lessons")
async def lesson_catalog():
    from .lessons import catalog
    return {"items": catalog()}


@app.post("/lab/lessons/{lesson_id}/run")
async def run_lesson(lesson_id: str, request: Request):
    from .lessons import catalog, run
    if lesson_id not in {item["id"] for item in catalog()}:
        raise HTTPException(404, "Không tìm thấy bài thử.")
    body = await request.json()
    compare = body.get("compare", False)
    if not isinstance(compare, bool):
        raise HTTPException(422, "compare phải là true hoặc false.")
    return _start_job("lesson", lambda progress: run(lesson_id, compare=compare, progress=progress), lesson_id=lesson_id)


@app.get("/lab/dataset")
async def lab_dataset():
    # This local operator catalog does not serve document content and does not
    # participate in business authorization; current SQL state remains decisive.
    from app.fixture_data import dataset_catalog
    return dataset_catalog()


def _ensure_idle():
    with _guard:
        if any(j["status"] in {"queued", "running"} for j in _jobs.values()):
            raise HTTPException(409, "Một tác vụ đang chạy. Đợi hoàn thành trước khi thay đổi môi trường.")


def _start_job(kind, work, *, lesson_id=None):
    _ensure_idle()
    job_id = secrets.token_hex(8)
    job = {"id": job_id, "kind": kind, "status": "queued", "started_at": time.time(),
           "finished_at": None, "events": [], "result": None, "error": None}
    if lesson_id is not None:
        job["lesson_id"] = lesson_id
    with _guard:
        _jobs[job_id] = job

    def progress(event=None, **kwargs):
        data = event if isinstance(event, dict) else {"message": str(event or "")}
        data.update(kwargs)
        with _guard:
            job["events"].append({"time": time.time(), **_clean(data)})

    def execute():
        job["status"] = "running"
        try:
            job["result"] = _clean(work(progress))
            job["status"] = "completed"
        except Exception as error:
            job["status"] = "failed"
            job["error"] = f"{type(error).__name__}: {str(error)[:1000]}"
        finally:
            job["finished_at"] = time.time()
            output = RUNTIME / "lab-results"
            output.mkdir(parents=True, exist_ok=True)
            temporary = output / f"{job_id}.tmp"
            temporary.write_text(json.dumps(_clean(job), ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(output / f"{job_id}.json")
    _pool.submit(execute)
    return _clean(job)


@app.get("/lab/tasks")
async def tasks():
    output = RUNTIME / "lab-results"
    if output.exists():
        for path in sorted(output.glob("*.json"), key=lambda p: p.stat().st_mtime)[-100:]:
            if path.stem in _jobs:
                continue
            try:
                old = json.loads(path.read_text(encoding="utf-8"))
                if old.get("id") != path.stem:
                    continue
                if old.get("status") in {"running", "queued"}:
                    old.update(status="failed", error="Tiến trình console đã dừng trước khi ghi nhận hoàn thành.")
                _jobs[path.stem] = _clean(old)
            except (ValueError, OSError):
                continue
    with _guard:
        return {"items": [_clean(j) for j in reversed(list(_jobs.values()))]}


@app.get("/lab/tasks/{job_id}")
@app.get("/lab/runs/{job_id}")
async def task(job_id: str):
    with _guard:
        if job_id not in _jobs:
            raise HTTPException(404, "Không tìm thấy tác vụ.")
        return _clean(_jobs[job_id])


@app.post("/lab/reset")
async def reset_lab():
    return _start_job("reset", lambda progress: _operation("reset"))


@app.post("/lab/backup")
async def backup_lab():
    return _start_job("backup", lambda progress: _operation("backup"))


@app.post("/lab/restore")
async def restore_lab(request: Request):
    body = await request.json()
    snapshot_id = str(body.get("snapshot_id", "")).strip()
    if not snapshot_id:
        raise HTTPException(422, "Chọn snapshot cần phục hồi.")
    return _start_job("restore", lambda progress: _operation("restore", snapshot_id))


@app.post("/lab/fault")
async def fault_lab(request: Request):
    body = await request.json()
    service = body.get("service")
    if service not in {"opa", "openbao", "audit_write_failure", "opa_response_invalid", "registry_unavailable", "stale_signals"}:
        raise HTTPException(422, "Loại lỗi không được hỗ trợ.")
    if service == "stale_signals":
        return _start_job("fault", lambda progress: _stale_signals(bool(body.get("enabled"))))
    return _start_job("fault", lambda progress: _operation("fault", service, bool(body.get("enabled"))))


@app.post("/lab/edit")
async def edit_lab(request: Request):
    _ensure_idle()
    body = await request.json()
    if body.get("kind") not in {"principal", "device", "document", "grant", "principals", "devices", "documents", "grants"}:
        raise HTTPException(422, "Đối tượng không hợp lệ.")
    if not isinstance(body.get("patch"), dict):
        raise HTTPException(422, "Patch phải là một JSON object.")
    return await asyncio.to_thread(_operation, "edit_state", body["kind"], str(body.get("id", "")), body["patch"])


@app.post("/lab/request")
async def business_request(request: Request):
    _ensure_idle()
    body = await request.json()
    username = str(body.get("username", "alice"))
    token = None
    interactive = body.get("identity_source") == "interactive"
    if interactive:
        _, session = _session(request)
        auth = (session or {}).get("auth")
        if not auth or auth["expires_at"] <= time.time():
            raise HTTPException(401, "Đăng nhập Keycloak trước khi gửi yêu cầu với danh tính thật.")
        username, token = auth["username"], auth["access_token"]
    if username not in _known_users():
        raise HTTPException(422, "Tài khoản không tồn tại. Thêm tài khoản tại Nhân viên rồi thử lại.")
    method = str(body.get("method", "GET")).upper()
    path = str(body.get("path", "/documents"))
    if method not in {"GET", "POST", "PUT", "DELETE"} or not path.startswith("/") or "://" in path or path.startswith("//"):
        raise HTTPException(422, "Phương thức hoặc đường dẫn API không hợp lệ.")
    mode = body.get("mode", "B1")
    if mode not in {"B0", "B1"}:
        raise HTTPException(422, "Chọn B0 hoặc B1.")
    headers = body.get("headers") or {}
    if not isinstance(headers, dict) or any(str(k).lower() in {"authorization", "host", "cookie"} for k in headers):
        raise HTTPException(422, "Không được nhập token, cookie hoặc host qua trình thử nghiệm.")
    start = time.perf_counter()
    try:
        response = await asyncio.to_thread(
            _lab_client().request, username, method, path, json=body.get("json"),
            device=body.get("device") or username, mode=mode, token=token, headers=headers,
        )
        elapsed = (time.perf_counter() - start) * 1000
        ctype = response.headers.get("content-type", "")
        is_json = "json" in ctype
        try:
            payload = response.json() if is_json else None
        except ValueError:
            payload = {"error": "Máy chủ trả JSON không hợp lệ."}
        detail = payload.get("detail", {}) if isinstance(payload, dict) else {}
        if not isinstance(detail, dict):
            detail = {"message": detail}
        download = "download" in path and response.is_success and not is_json
        return {"status": response.status_code, "ok": response.is_success,
                "latency_ms": round(elapsed, 2), "request_id": response.headers.get("x-request-id") or detail.get("request_id"),
                "reason": response.headers.get("x-policy-reason") or detail.get("reason"),
                "policy_version": response.headers.get("x-policy-version"), "payload": _clean(payload),
                "text": response.text[:100000] if not download and not is_json else None,
                "content_b64": base64.b64encode(response.content).decode() if download else None,
                "content_type": ctype, "size": len(response.content),
                "request": {"username": username, "method": method, "path": path, "mode": mode,
                            "device": body.get("device") or username, "identity_source": "interactive" if interactive else "trusted_operator"}}
    except Exception as error:
        return {"status": None, "ok": False, "latency_ms": round((time.perf_counter()-start)*1000, 2),
                "reason": "TRANSPORT_ERROR", "error": f"{type(error).__name__}: {str(error)[:500]}"}


def _cases_path():
    return RUNTIME / "lab-custom-cases.json"


def _load_cases():
    custom = _cases_path()
    source = custom if custom.exists() else PROJECT / "fixtures" / "cases.json"
    if not source.exists():
        return []
    return json.loads(source.read_text(encoding="utf-8"))


@app.get("/lab/cases")
async def cases():
    return {"cases": _load_cases(), "custom": _cases_path().exists()}


@app.put("/lab/cases")
async def save_cases(request: Request):
    _ensure_idle()
    body = await request.json()
    cases = body.get("cases")
    if not isinstance(cases, (list, dict)):
        raise HTTPException(422, "Bộ kiểm thử phải là JSON array hoặc object.")
    data = json.dumps(cases, ensure_ascii=False, indent=2)
    if len(data.encode()) > 2_000_000:
        raise HTTPException(413, "Bộ kiểm thử tối đa 2 MB.")
    _cases_path().parent.mkdir(parents=True, exist_ok=True)
    _cases_path().write_text(data, encoding="utf-8")
    return {"saved": True, "cases": cases}


@app.delete("/lab/cases")
async def restore_cases():
    _ensure_idle()
    _cases_path().unlink(missing_ok=True)
    return {"cases": _load_cases(), "custom": False}


def _run_suite(body, progress):
    runner = importlib.import_module("lab.runner")
    function = runner.run_suite
    parameters = inspect.signature(function).parameters
    kwargs = {}
    if "cases" in parameters:
        cases = body.get("cases")
        if isinstance(cases, dict):
            cases = cases.get("cases", cases)
        kwargs["cases"] = cases
    if "progress" in parameters:
        kwargs["progress"] = progress
    elif "on_progress" in parameters:
        kwargs["on_progress"] = progress
    for key in ("suite", "mode", "include_oracle", "reset_first"):
        if key in parameters and key in body:
            kwargs[key] = body[key]
    return function(**kwargs)


@app.post("/lab/runs")
async def run_suite(request: Request):
    body = await request.json()
    return _start_job("suite", lambda progress: _run_suite(body, progress))


@app.get("/lab/export/{job_id}/{format}")
async def export_run(job_id: str, format: str):
    job = await task(job_id)
    if job["status"] not in {"completed", "failed"}:
        raise HTTPException(409, "Tác vụ chưa hoàn thành.")
    filename = f"bmdl-{job_id}.{format}"
    disposition = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if format == "json":
        return Response(json.dumps(job, ensure_ascii=False, indent=2), media_type="application/json", headers=disposition)
    result = job.get("result") or {}
    rows = result.get("results", result.get("cases", [])) if isinstance(result, dict) else result
    rows = rows if isinstance(rows, list) else []
    rows = [{**row, "title": row.get("title", row.get("name", "")),
             "reason": row.get("reason") or (row.get("actual", {}).get("reason") if isinstance(row.get("actual"), dict) else None),
             "request_id": row.get("request_id") or (row.get("actual", {}).get("request_id") if isinstance(row.get("actual"), dict) else None)}
            for row in rows if isinstance(row, dict)]
    columns = ["id", "title", "expected", "actual", "passed", "reason", "latency_ms", "request_id"]
    if format == "csv":
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            if isinstance(row, dict):
                writer.writerow({k: json.dumps(row.get(k), ensure_ascii=False) if isinstance(row.get(k), (list, dict)) else row.get(k, "") for k in columns})
        return Response("\ufeff" + stream.getvalue(), media_type="text/csv; charset=utf-8", headers=disposition)
    if format == "html":
        headings = "".join(f"<th>{c}</th>" for c in columns)
        table = "".join("<tr>"+"".join(f"<td>{html.escape(str(row.get(c, '')))}</td>" for c in columns)+"</tr>" for row in rows if isinstance(row, dict))
        markup = f'<!doctype html><html lang="vi"><meta charset="utf-8"><title>Kết quả BMDL</title><style>body{{font:14px system-ui;margin:32px;color:#14243b}}table{{border-collapse:collapse;width:100%}}td,th{{padding:9px;border:1px solid #ccd6e1;text-align:left}}th{{background:#eaf0f7}}pre{{white-space:pre-wrap}}</style><h1>Kết quả thử nghiệm Zero Trust</h1><p>Tác vụ {html.escape(job_id)} · {html.escape(job["status"])}</p><p>Số liệu được lấy từ lần chạy thực tế trong môi trường lab.</p><table><thead><tr>{headings}</tr></thead><tbody>{table}</tbody></table><h2>Tổng hợp</h2><pre>{html.escape(json.dumps(result.get("summary", result), ensure_ascii=False, indent=2))}</pre></html>'
        return HTMLResponse(markup, headers=disposition)
    raise HTTPException(404, "Hỗ trợ JSON, CSV hoặc HTML.")


@app.get("/auth/login")
async def login(request: Request):
    sid, session = _session(request, create=True)
    verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    session["oauth"] = {"verifier": verifier, "state": state, "nonce": nonce, "expires_at": time.time()+600}
    query = urlencode({"client_id": "zt-web", "redirect_uri": REDIRECT_URI,
                       "response_type": "code", "scope": "openid profile", "state": state,
                       "nonce": nonce, "code_challenge": challenge, "code_challenge_method": "S256"})
    response = RedirectResponse(f"{ISSUER}/protocol/openid-connect/auth?{query}")
    _set_cookie(response, sid)
    return response


@app.get("/auth/callback")
async def callback(request: Request, state: str = "", code: str = "", error: str = ""):
    _, session = _session(request)
    pending = (session or {}).pop("oauth", None)
    if not pending or pending["expires_at"] < time.time() or not secrets.compare_digest(pending["state"], state):
        raise HTTPException(400, "State đăng nhập không hợp lệ hoặc đã hết hạn.")
    if error or not code:
        raise HTTPException(400, "Keycloak không hoàn tất đăng nhập.")
    ca = RUNTIME / "pki" / "ca.crt"
    async with httpx.AsyncClient(verify=str(ca), timeout=20) as client:
        response = await client.post(f"{OIDC_INTERNAL}/protocol/openid-connect/token", data={
            "grant_type": "authorization_code", "client_id": "zt-web", "code": code,
            "redirect_uri": REDIRECT_URI, "code_verifier": pending["verifier"],
        })
        if response.status_code != 200:
            raise HTTPException(400, "Trao đổi mã đăng nhập thất bại.")
        tokens = response.json()
        jwks = await client.get(f"{OIDC_INTERNAL}/protocol/openid-connect/certs")
        jwks.raise_for_status()
    try:
        header = jwt.get_unverified_header(tokens["id_token"])
        key_data = next(k for k in jwks.json()["keys"] if k["kid"] == header["kid"])
        key = jwt.PyJWK.from_dict(key_data).key
        claims = jwt.decode(tokens["id_token"], key, algorithms=["RS256"], audience="zt-web", issuer=ISSUER,
                            options={"require": ["exp", "iat", "sub", "nonce"]})
        if not secrets.compare_digest(claims.get("nonce", ""), pending["nonce"]):
            raise ValueError("nonce mismatch")
        username = claims.get("preferred_username", "")
        if username not in _known_users():
            raise ValueError("no lab certificate mapped to user")
        session["auth"] = {"username": username, "access_token": tokens["access_token"],
                           "expires_at": time.time() + int(tokens.get("expires_in", 300))}
    except Exception:
        raise HTTPException(400, "Không xác minh được chữ ký, nonce hoặc danh tính phiên đăng nhập.")
    return RedirectResponse("/?auth=success", status_code=303)


@app.post("/auth/logout")
async def logout(request: Request):
    _, session = _session(request)
    if session:
        session.pop("auth", None)
    return {"logged_out": True}
