"""Stateful tests against the real gateway and operator-controlled lab.

Public API: run_case(client, operations, case), run_oracle(client, operations),
run_suite(client, operations). No service is mocked in the integration suite.
The trusted operator is used for fixture preparation/faults, never as the
identity performing the tested business request.
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
from pathlib import Path


ORACLE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "cases.json"
PRIVATE_RESPONSE_KEYS = {"title", "owner_id", "department", "label", "ciphertext", "content_b64"}


def _json(response):
    try:
        value = response.json()
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _keys(value):
    if isinstance(value, dict):
        return set(value) | set().union(*(_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_keys(item) for item in value), set())
    return set()


def _relative(value):
    if isinstance(value, dict) and set(value) == {"seconds_ago"}:
        return time.time() - float(value["seconds_ago"])
    if isinstance(value, dict):
        return {key: _relative(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_relative(item) for item in value]
    return value


def _require_response(response):
    if not 200 <= response.status_code < 300:
        detail = _json(response).get("detail", {})
        reason = detail.get("reason", "HTTP_ERROR") if isinstance(detail, dict) else "HTTP_ERROR"
        raise RuntimeError(f"Setup failed: status={response.status_code}, reason={reason}")
    return _json(response)


def _setup(client, operations, steps):
    for step in steps:
        operation = step["operation"]
        if operation in {"device", "document", "grant_patch"}:
            method = {"device": "patch_device", "document": "patch_document", "grant_patch": "patch_grant"}[operation]
            getattr(operations, method)(step["id"], _relative(step["changes"]))
        elif operation == "principal":
            _require_response(client.request("secadmin", "PUT", f"/admin/principals/{step['id']}",
                                             json=_relative(step["changes"])))
        elif operation == "grant":
            _require_response(client.request("secadmin", "POST", "/admin/grants", json={
                "principal_id": step["principal_id"], "doc_id": step["doc_id"],
                "ttl_seconds": step.get("ttl_seconds", 120)}))
        else:
            raise ValueError(f"Unknown setup operation: {operation}")


def _tls_failure(error):
    """Only a TLS/certificate failure can satisfy a certificate-negative case.

    A refused connection or arbitrary runtime error is never an expected deny.
    The exception text is inspected locally, not included in evidence.
    """
    current = error
    for _ in range(5):
        if current is None:
            break
        text = f"{type(current).__name__} {current}".lower()
        if any(marker in text for marker in ("certificate", "tlsv1", "ssl:", "sslerror", "sslcertverification")):
            return True
        current = current.__cause__ or current.__context__
    return False


class Suite:
    def __init__(self, client, operations):
        self.client = client
        self.operations = operations
        self.records = []

    def check(self, identifier, group, name, expected, actual, passed, *, evidence=None, latency_ms=None):
        record = {"id": identifier, "group": group, "name": name, "expected": expected,
                  "actual": actual, "passed": bool(passed), "request_id": None,
                  "latency_ms": latency_ms, "evidence": evidence or {}}
        self.records.append(record)
        return record

    def request(self, identifier, group, name, username, method, path, *, allow,
                statuses=None, reason=None, device=None, token=None, headers=None,
                payload=None, evidence=None, checks=None, mode="B1"):
        expected = {"allow": bool(allow), "statuses": statuses or ([200] if allow else [403])}
        if reason:
            expected["reason"] = reason
        started = time.perf_counter()
        try:
            response = self.client.request(username, method, path, json=payload, device=device,
                                           mode=mode, token=token, headers=headers)
        except Exception as error:
            tls_rejected = device in {"none", "bad"} and _tls_failure(error)
            passed = not allow and tls_rejected
            self.check(identifier, group, name, expected,
                       {"allow": False, "status": None, "transport_error": type(error).__name__,
                        "certificate_rejected": tls_rejected}, passed,
                       evidence=evidence, latency_ms=round((time.perf_counter() - started) * 1000, 3))
            return None
        elapsed = round((time.perf_counter() - started) * 1000, 3)
        body = _json(response)
        detail = body.get("detail", {})
        response_reason = (detail.get("reason") if isinstance(detail, dict) else None)
        response_reason = response.headers.get("X-Policy-Reason", response_reason)
        request_id = response.headers.get("X-Request-ID")
        if not request_id and isinstance(detail, dict):
            request_id = detail.get("request_id")
        actual_allow = 200 <= response.status_code < 300
        actual = {"allow": actual_allow, "status": response.status_code,
                  "reason": response_reason, "body_length": len(response.content)}
        if actual_allow and "/download" in path:
            actual["sha256"] = hashlib.sha256(response.content).hexdigest()
        passed = actual_allow == bool(allow) and response.status_code in expected["statuses"]
        if reason:
            passed = passed and response_reason == reason
        if not allow:
            disclosed = sorted(_keys(body) & PRIVATE_RESPONSE_KEYS)
            actual["disclosed_resource_fields"] = disclosed
            passed = passed and not disclosed
            if response.status_code not in {400, 495, 496}:
                structured_error = (set(body) == {"detail"} and isinstance(detail, dict)
                                    and isinstance(detail.get("reason"), str)
                                    and set(detail) <= {"reason", "request_id", "policy_version",
                                                       "transport_error", "error_type"})
                actual["structured_error"] = structured_error
                passed = passed and structured_error
        for key, value in (checks or {}).items():
            if key == "allowed_ids":
                observed = sorted(item.get("id") for item in body.get("items", []))
                actual["item_ids"] = observed
                passed = passed and observed == sorted(value)
            elif key == "sha256":
                passed = passed and actual.get("sha256") == value
            else:
                actual[key] = body.get(key)
                passed = passed and body.get(key) == value
        safe_evidence = {"method": method, "path": path, "username": username, "mode": mode,
                         **(evidence or {})}
        record = self.check(identifier, group, name, expected, actual, passed,
                            evidence=safe_evidence, latency_ms=elapsed)
        record["request_id"] = request_id
        # Gateway rejections can occur before the API assigns a request ID.
        if response.status_code != 400 and actual_allow and not request_id:
            record["passed"] = False
            record["evidence"]["missing_request_id"] = True
        return response

    def group(self, group, function):
        try:
            self.operations.reset()
            function()
        except Exception as error:
            self.check(f"{group}-execution", group, "Nhóm kiểm thử thực thi đầy đủ", "completed",
                       {"exception": type(error).__name__, "stage": "group execution"}, False)
        finally:
            try:
                self.operations.reset()
            except Exception as error:
                self.check(f"{group}-cleanup", group, "Khôi phục fixture sau nhóm", "reset",
                           {"exception": type(error).__name__}, False)


def run_case(client, operations, case, *, reset=True):
    """Run one editable JSON oracle case. Expected is always supplied by author."""
    suite = Suite(client, operations)
    try:
        if reset:
            operations.reset()
        _setup(client, operations, case.get("setup", []))
        expected = case["expected"]
        checks = dict(case.get("checks", {}))
        suite.request(case["id"], case.get("group", "oracle"), case["name"],
                      case["username"], case.get("method", "GET"), case["path"],
                      allow=expected["allow"], statuses=expected.get("statuses"),
                      reason=expected.get("reason"), device=case.get("device"),
                      token=case.get("token"), headers=case.get("headers"), payload=case.get("json"),
                      mode=case.get("mode", "B1"), checks=checks)
    except Exception as error:
        suite.check(case.get("id", "custom"), case.get("group", "oracle"), case.get("name", "Custom case"),
                    case.get("expected", {}), {"setup_error": type(error).__name__}, False)
    finally:
        if reset:
            try:
                operations.reset()
            except Exception as error:
                suite.check(f"{case.get('id', 'custom')}-cleanup", "oracle", "Khôi phục fixture", "reset",
                            {"exception": type(error).__name__}, False)
    return suite.records


def run_oracle(client, operations, cases=None, *, mode=None):
    if cases is None:
        source = json.loads(ORACLE_PATH.read_text(encoding="utf-8"))
        cases = source["cases"] if isinstance(source, dict) else source
    records = []
    if mode is not None and mode not in {"B0", "B1"}:
        raise ValueError("Only B0 or B1 deployment mode is accepted")
    operations.reset()
    try:
        for case in cases:
            if mode is not None:
                # Keep the independently authored B1 oracle unchanged. A B0
                # false allow must remain visible as a failed expectation.
                case = {**case, "mode": mode}
            destructive = bool(case.get("setup")) or case.get("method", "GET") not in {"GET", "HEAD"}
            records.extend(run_case(client, operations, case, reset=destructive))
    finally:
        operations.reset()
    return records


def _tampered(token, changes=None, *, signature=False):
    parts = token.split(".")
    if signature:
        parts[2] = ("B" if parts[2][0] == "A" else "A") + parts[2][1:]
    else:
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
        payload.update(changes or {})
        parts[1] = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    return ".".join(parts)


def _create_grant(client, principal="adam", document="A-R01", ttl=120):
    result = _require_response(client.request("secadmin", "POST", "/admin/grants", json={
        "principal_id": principal, "doc_id": document, "ttl_seconds": ttl}))
    identifier = result.get("id") or result.get("grant", {}).get("id")
    if not identifier:
        raise RuntimeError("Grant response missing id")
    return identifier


def _basic(s):
    for identifier, name, user, path, allow, reason in [
        ("T01", "Nội bộ cùng phòng", "alice", "/documents/A-I01/download", True, None),
        ("T02", "Mật do mình sở hữu", "alice", "/documents/A-C01/download", True, None),
        ("T03", "Mật thuộc người khác", "alice", "/documents/A-C02/download", False, "OWNER_OR_LABEL"),
        ("T04", "Trưởng phòng đọc mật trong phòng", "adam", "/documents/A-C02/download", True, None),
        ("T05a", "Tải khác phòng bị chặn", "adam", "/documents/B-I01/download", False, "DEPARTMENT"),
        ("T05b", "Metadata khác phòng không được lộ", "adam", "/documents/B-I01/metadata", False, "DEPARTMENT"),
        ("T06", "Sở hữu không vượt nhãn hạn chế", "alice", "/documents/A-R01/download", False, "OWNER_OR_LABEL"),
        ("T08a", "Kiểm toán đọc audit", "auditor", "/audit", True, None),
        ("T08b", "Kiểm toán không đọc nội dung", "auditor", "/documents/A-I01/download", False, "ROLE"),
        ("T09b", "Quản trị an toàn không đọc nội dung", "secadmin", "/documents/A-I01/download", False, "ROLE"),
    ]:
        s.request(identifier, "access", name, user, "GET", path, allow=allow, reason=reason)
    allowed = [f"A-I{n:02}" for n in range(1, 6)] + [f"A-C{n:02}" for n in range(1, 4)] + ["A-R01", "A-R02"]
    s.request("T05c", "access", "Danh sách trưởng phòng chỉ có tài liệu phòng A", "adam", "GET", "/documents",
              allow=True, checks={"allowed_ids": allowed})
    s.request("T09a", "access", "Quản trị cập nhật registry hợp lệ", "secadmin", "PUT",
              "/admin/devices/dev-alice", allow=True, payload={"compliant": True})


def _identity(s):
    valid = s.client.token("alice")
    token_cases = [("T10a", "Không có bearer token", ""),
                   ("T10b", "Chữ ký JWT bị sửa", _tampered(valid, signature=True)),
                   ("T10c", "Payload issuer bị sửa không ký lại", _tampered(valid, {"iss": "https://wrong.invalid"})),
                   ("T10d", "Payload audience bị sửa không ký lại", _tampered(valid, {"aud": "wrong-api"})),
                   ("T10e", "Payload expiry bị sửa không ký lại", _tampered(valid, {"exp": 1}))]
    for identifier, name, token in token_cases:
        s.request(identifier, "identity", name, "alice", "GET", "/documents/A-I01/download",
                  allow=False, statuses=[401], reason="INVALID_TOKEN", token=token,
                  headers={"Authorization": ""} if identifier == "T10a" else None,
                  evidence={"isolated_claim_test": False,
                            "claim_isolation_suite": "tests/test_auth_verifier.py"})
    for identifier, device in [("T11a", "none"), ("T11b", "bad"), ("T11c", "rogue"), ("T11d", "anna")]:
        s.request(identifier, "identity", f"Chứng thư {device} không cấp nội dung", "alice", "GET",
                  "/documents/A-I01/download", allow=False, device=device,
                  statuses=[400, 401, 403, 495, 496])
    s.request("T12a", "identity", "Header client không tự nâng quyền", "alice", "GET",
              "/documents/A-C02/download", allow=False, reason="OWNER_OR_LABEL", headers={
                  "X-Role": "manager", "X-Department": "B", "X-Verified-Serial": "ABCD",
                  "X-Verified-TLS": "SUCCESS", "X-Proxy-Secret": "client-assertion",
                  "X-Policy-Mode": "B0"})
    for identifier, changes in [("T12b", {"role": "manager"}), ("T12c", {"department": "A"})]:
        s.request(identifier, "identity", "Quản trị không tự đổi đặc quyền", "secadmin", "PUT",
                  "/admin/principals/secadmin", payload=changes, allow=False, statuses=[403])


def _grants(s):
    path = "/documents/A-R01/download"
    current_version = _require_response(
        s.client.request("adam", "GET", "/documents/A-R01/metadata"))["version"]
    s.request("T07a", "grants", "Hạn chế thiếu grant", "adam", "GET", path,
              allow=False, reason="RESTRICTED_GRANT")
    identifier = _create_grant(s.client)
    s.request("T07b", "grants", "Grant hiện tại cho phép", "adam", "GET", path, allow=True)
    s.operations.patch_grant(identifier, {"expires_at": time.time() - 1})
    s.request("T07c", "grants", "Grant hết hạn bị từ chối", "adam", "GET", path,
              allow=False, reason="RESTRICTED_GRANT")
    s.operations.patch_grant(identifier, {"expires_at": time.time() + 120, "revoked": True})
    s.request("T07d", "grants", "Grant thu hồi bị từ chối", "adam", "GET", path,
              allow=False, reason="RESTRICTED_GRANT")
    s.operations.patch_grant(identifier, {"revoked": False, "doc_version": 0})
    s.request("T07e", "grants", "Grant sai phiên bản bị từ chối", "adam", "GET", path,
              allow=False, reason="RESTRICTED_GRANT")
    # Restore the correct version so only the action is invalid in this case.
    s.operations.patch_grant(identifier, {"doc_version": current_version, "action": "metadata"})
    s.request("T07f", "grants", "Grant sai hành động bị từ chối", "adam", "GET", path,
              allow=False, reason="RESTRICTED_GRANT")
    s.request("T07g", "grants", "Không tự cấp grant cho chính mình", "secadmin", "POST", "/admin/grants",
              allow=False, statuses=[403], payload={"principal_id": "secadmin", "doc_id": "A-R01", "ttl_seconds": 120})


def _context(s):
    for identifier, patch, reason in [
        ("T13a", {"compliant": False}, "NONCOMPLIANT"),
        ("T13b", {"compliant": True, "revoked": True}, "DEVICE_REVOKED"),
        ("T13c", {"revoked": False, "risk": "HIGH"}, "RISK_HIGH"),
        ("T14a", {"risk": "NORMAL", "auto_refresh": False, "observed_at": time.time() - 120,
                  "risk_at": time.time()}, "MISSING_OR_STALE"),
        ("T14b", {"observed_at": time.time(), "risk_at": None}, "MISSING_OR_STALE"),
        ("T14c", {"observed_at": time.time() + 3600, "risk_at": time.time()}, "MISSING_OR_STALE"),
    ]:
        s.operations.patch_device("dev-alice", patch)
        s.request(identifier, "context", "Điều kiện thiết bị được đánh giá ở yêu cầu mới", "alice", "GET",
                  "/documents/A-I01/download", allow=False, reason=reason)


def _revocation(s):
    token = s.client.token("alice")
    s.request("T15a", "revocation", "Trước thu hồi có quyền", "alice", "GET", "/documents/A-I01/download",
              allow=True, token=token)
    mutation_start = time.time()
    response = s.request("T15b", "revocation", "Quản trị thu hồi quyền hiện tại", "secadmin", "PUT",
                         "/admin/principals/alice", allow=True, payload={"active": False})
    _require_response(response)
    mutation_received = time.time()
    response = s.request("T15c", "revocation", "JWT cũ không giữ quyền B1", "alice", "GET",
                         "/documents/A-I01/download", allow=False, reason="INACTIVE", token=token)
    deny_received = time.time()
    s.check("T15-time", "revocation", "Đo cửa sổ hiệu lực thu hồi", "first B1 request denied",
            {"mutation_started_at": mutation_start, "mutation_response_at": mutation_received,
             "first_probe_response_at": deny_received,
             "upper_bound_ms": round((deny_received - mutation_start) * 1000, 3)},
            response is not None and response.status_code == 403,
            evidence={"origin": "upper bound includes mutation request; not an exact database commit timestamp"})
    s.request("T15-B0", "revocation", "B0 cố ý còn dùng quyền snapshot", "alice", "GET",
              "/documents/A-I01/download", allow=True, token=token, mode="B0")


def _label_change(s):
    token = s.client.token("alice")
    s.request("T16a", "labels", "Trước tăng nhãn cho phép", "alice", "GET", "/documents/A-I01/download",
              allow=True, token=token)
    response = s.request("T16b", "labels", "Quản trị tăng nhãn", "secadmin", "POST",
                         "/admin/documents/A-I01/raise-label", allow=True, payload={"label": "restricted"})
    _require_response(response)
    s.request("T16c", "labels", "Yêu cầu mới dùng nhãn hiện tại", "alice", "GET", "/documents/A-I01/download",
              allow=False, reason="OWNER_OR_LABEL", token=token)
    s.request("T16d", "labels", "Không hạ nhãn bằng endpoint tăng nhãn", "secadmin", "POST",
              "/admin/documents/A-I01/raise-label", allow=False, statuses=[400, 403, 409, 422],
              payload={"label": "internal"})
    s.request("T16-B0", "labels", "B0 bỏ qua nhãn trong phép đối chứng", "alice", "GET",
              "/documents/A-I01/download", allow=True, token=token, mode="B0")


def _faults(s):
    try:
        s.operations.stop_service("opa")
        s.request("T17a", "faults", "OPA thực sự dừng thì không trả dữ liệu", "alice", "GET",
                  "/documents/A-I01/download", allow=False, statuses=[503], reason="PDP_UNAVAILABLE",
                  evidence={"fault": "actual container stop: opa"})
    finally:
        s.operations.start_service("opa")
    for identifier, fault, reason in [("T17b", "opa_response_invalid", "PDP_INVALID"),
                                      ("T17c", "registry_unavailable", "REGISTRY_UNAVAILABLE")]:
        try:
            s.operations.set_fault(fault, True)
            s.request(identifier, "faults", "Lỗi kiểm soát không biến thành allow", "alice", "GET",
                      "/documents/A-I01/download", allow=False, statuses=[503], reason=reason,
                      evidence={"fault": fault, "injection": "operator-controlled fault file"})
        finally:
            s.operations.set_fault(fault, False)
    state_before = _require_response(s.client.request("secadmin", "GET", "/admin/state"))
    try:
        s.operations.set_fault("audit_write_failure", True)
        s.request("T18a", "faults", "Audit lỗi không được trả bản rõ", "alice", "GET",
                  "/documents/A-I01/download", allow=False, statuses=[503], reason="AUDIT_UNAVAILABLE")
        s.request("T18b", "faults", "Audit lỗi không commit upload", "alice", "POST", "/documents",
                  allow=False, statuses=[503], reason="AUDIT_UNAVAILABLE",
                  payload={"title": "rollback-audit.txt", "label": "internal",
                  "content_b64": base64.b64encode(b"AUDIT-ROLLBACK-TEST\n" * 1000).decode()})
    finally:
        s.operations.set_fault("audit_write_failure", False)
    state_after = _require_response(s.client.request("secadmin", "GET", "/admin/state"))
    before = sorted(item["id"] for item in state_before["documents"])
    after = sorted(item["id"] for item in state_after["documents"])
    s.check("T18c", "faults", "Upload bị rollback khi audit lỗi", before, after, before == after)


def _retention(s):
    path = "/documents/A-I01"
    s.request("T19a", "retention", "Không hủy trước thời hạn", "alice", "DELETE", path,
              allow=False, reason="RETENTION_ACTIVE")
    s.operations.patch_document("A-I01", {"retention_until": time.time() - 10, "legal_hold": True})
    s.request("T19b", "retention", "Legal hold chặn hủy", "alice", "DELETE", path,
              allow=False, reason="LEGAL_HOLD")
    s.operations.patch_document("A-I01", {"legal_hold": False})
    s.request("T19c", "retention", "Hết hạn không đọc nghiệp vụ", "alice", "GET", path + "/download",
              allow=False, reason="RETENTION_EXPIRED")
    s.request("T19d", "retention", "Chủ sở hữu hủy sau thời hạn", "alice", "DELETE", path,
              allow=True, statuses=[200, 204])
    state = _require_response(s.client.request("secadmin", "GET", "/admin/state"))
    doc = next((item for item in state["documents"] if item["id"] == "A-I01"), None)
    s.check("T19e", "retention", "Tombstone được giữ sau hủy", {"deleted": True},
            {"deleted": doc.get("deleted") if doc else None}, bool(doc and doc.get("deleted") is True))
    s.request("T19f", "retention", "Tài liệu đã hủy không phục vụ lại", "adam", "GET", path + "/metadata",
              allow=False, statuses=[404], reason="NOT_FOUND")


def _alerts(s):
    for number in range(5):
        s.request(f"T20-deny-{number + 1}", "alerts", "Yêu cầu ngoài quyền được ghi nhận", "alice", "GET",
                  "/documents/A-C02/download", allow=False, reason="OWNER_OR_LABEL")
    response = s.request("T20a", "alerts", "Đọc cảnh báo tổng hợp", "secadmin", "GET", "/alerts", allow=True)
    items = _json(response).get("items", []) if response is not None else []
    alerts = [item for item in items if item.get("principal_id", item.get("subject_id")) == "alice"]
    s.check("T20b", "alerts", "Năm lần từ chối tạo cảnh báo cho Alice", {"min_alerts": 1},
            {"matching_alerts": len(alerts)}, len(alerts) >= 1,
            evidence={"threshold": 5, "window_seconds": 60})
    if alerts:
        s.request("T20c", "alerts", "Người vận hành xác nhận cảnh báo", "secadmin", "POST",
                  f"/alerts/{alerts[0]['id']}/ack", allow=True)
    s.request("T20d", "alerts", "Người vận hành khóa tài khoản", "secadmin", "PUT",
              "/admin/principals/alice", allow=True, payload={"active": False})
    s.request("T20e", "alerts", "Sau phản ứng, yêu cầu mới bị chặn", "alice", "GET",
              "/documents/A-I01/download", allow=False, reason="INACTIVE")


def _storage(s):
    info = s.operations.inspect_storage("A-I01")
    expected = {"ciphertext_prefix": "vault:v", "plaintext_present": False,
                "key_material_present": False, "app_kms_admin_allowed": False}
    observed = {"ciphertext_prefix": str(info.get("ciphertext", ""))[:7],
                "plaintext_present": info.get("plaintext_present"),
                "key_material_present": info.get("key_material_present"),
                "app_kms_admin_allowed": info.get("app_kms_admin_allowed")}
    ok = str(info.get("ciphertext", "")).startswith("vault:v") and all(
        info.get(key) is False for key in ("plaintext_present", "key_material_present", "app_kms_admin_allowed"))
    s.check("T21", "storage", "Kho dữ liệu không chứa bản rõ hoặc khóa Transit", expected, observed, ok,
            evidence={"inspection": "actual stored values and application-token permission probes"})
    response = s.request("T01-integrity", "storage", "Giải mã hợp lệ khớp fixture gốc", "alice", "GET",
                         "/documents/A-I01/download", allow=True)
    sha = hashlib.sha256(response.content).hexdigest() if response is not None else None
    s.check("T21-fixture", "storage", "Nội dung khớp hash fixture độc lập", info.get("expected_sha256"), sha,
            bool(info.get("expected_sha256")) and sha == info["expected_sha256"])
    s.operations.tamper_ciphertext("A-I01")
    s.request("T22a", "storage", "Sửa bản mã làm giải mã thất bại", "alice", "GET",
              "/documents/A-I01/download", allow=False, statuses=[503], reason="INTEGRITY_FAILURE")
    events = _require_response(s.client.request("auditor", "GET", "/audit")).get("items", [])
    found = any(event.get("reason") == "INTEGRITY_FAILURE" for event in events)
    s.check("T22b", "storage", "Audit có bằng chứng lỗi toàn vẹn", True, found, found)


def _restore(s):
    content = s.client.request("adam", "GET", "/documents/A-I03/download")
    _require_response(content)  # Raw bytes return an empty JSON object, still checks HTTP status.
    expected_hash = hashlib.sha256(content.content).hexdigest()
    backup_started = time.perf_counter()
    snapshot = s.operations.backup()
    s.check("T23a", "restore", "Tạo cặp snapshot DB và KMS thực", "snapshot_id present",
            {"snapshot_id": snapshot.get("snapshot_id")}, bool(snapshot.get("snapshot_id")),
            latency_ms=round((time.perf_counter() - backup_started) * 1000, 3))
    _require_response(s.client.request("secadmin", "PUT", "/admin/principals/alice", json={"active": False}))
    s.operations.patch_document("A-I02", {"retention_until": time.time() - 10, "legal_hold": False})
    _require_response(s.client.request("adam", "DELETE", "/documents/A-I02"))
    restore_started = time.perf_counter()
    result = s.operations.restore(snapshot)
    observed = {key: result.get(key) for key in ("isolated", "reconciled", "contents_verified")}
    s.check("T23b", "restore", "Phục hồi cô lập và đối chiếu ledger", dict.fromkeys(observed, True), observed,
            all(value is True for value in observed.values()),
            latency_ms=round((time.perf_counter() - restore_started) * 1000, 3),
            evidence={"snapshot_id": snapshot.get("snapshot_id"), "driver": "real DB/KMS restore"})
    for mode in ("B1", "B0"):
        response = s.request(f"T23-mode-{mode}", "restore", "Sau restart, cổng vẫn tới đúng cấu hình chính sách",
                             "alice", "GET", "/health", allow=True, mode=mode)
        observed_mode = response.headers.get("X-Policy-Mode") if response is not None else None
        record = s.records[-1]
        record["expected"]["response_policy_mode"] = mode
        record["actual"]["response_policy_mode"] = observed_mode
        record["passed"] = record["passed"] and observed_mode == mode
    primary_scope = {"target": "unchanged primary", "isolated_recovery_evidence": "T23b and recovery JSON"}
    s.request("T23c", "restore", "Primary vẫn chặn quyền thu hồi sau kiểm chứng phục hồi cô lập", "alice", "GET",
              "/documents/A-I01/download", allow=False, reason="INACTIVE", evidence=primary_scope)
    s.request("T23d", "restore", "Primary vẫn giữ tombstone sau kiểm chứng phục hồi cô lập", "adam", "GET",
              "/documents/A-I02/metadata", allow=False, statuses=[404], reason="NOT_FOUND", evidence=primary_scope)
    s.request("T23e", "restore", "Primary vẫn phục vụ đúng tài liệu sau kiểm chứng phục hồi cô lập", "adam", "GET",
              "/documents/A-I03/download", allow=True, checks={"sha256": expected_hash}, evidence=primary_scope)


def _isolation(s):
    result = s.operations.probe_isolation()
    required = {"api", "api-baseline", "postgres", "opa", "openbao"}
    ok = (required <= set(result) and all(result[name] is False for name in required)
          and result.get('published_internal_ports') is False)
    s.check("T24a", "isolation", "Mạng client không đi thẳng API, DB, PDP hoặc KMS",
            {name: False for name in sorted(required)}, result, ok,
            evidence={"probe": "actual TCP from dedicated untrusted client network"})
    try:
        s.operations.stop_service("openbao")
        s.request("T24b", "isolation", "KMS thực sự ngừng thì không trả bản rõ", "alice", "GET",
                  "/documents/A-I01/download", allow=False, statuses=[503], reason="KMS_UNAVAILABLE",
                  evidence={"fault": "actual container stop: openbao"})
    finally:
        s.operations.start_service("openbao")
    s.request("T24c", "isolation", "Sau phục hồi KMS, luồng hợp lệ hoạt động", "alice", "GET",
              "/documents/A-I01/download", allow=True)
    s.request("T24d", "isolation", "Header client không hạ B1 xuống chính sách B0", "alice", "GET",
              "/documents/A-R01/download", allow=False, statuses=[403], mode="B1",
              headers={"X-Expected-Policy-Mode": "B0", "X-Lab-Policy-Mode": "B0"},
              evidence={"deployment_mode": "B1", "client_asserted_mode": "B0"})


def run_suite(client, operations):
    suite = Suite(client, operations)
    try:
        suite.records.extend(run_oracle(client, operations))
    except Exception as error:
        suite.check("oracle-execution", "oracle", "Thực thi đủ bộ oracle", "40 decisions",
                    {"exception": type(error).__name__}, False)
    for name, function in [("access", _basic), ("identity", _identity), ("grants", _grants),
                           ("context", _context), ("revocation", _revocation), ("labels", _label_change),
                           ("faults", _faults), ("retention", _retention), ("alerts", _alerts),
                           ("storage", _storage), ("restore", _restore), ("isolation", _isolation)]:
        suite.group(name, lambda action=function: action(suite))
    return suite.records
