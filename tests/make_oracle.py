"""Regenerate the initial reviewed oracle; never run automatically on web edits."""
import base64
import json
from pathlib import Path


def main():
    cases = []

    def case(identifier, name, user, path, *, allow, reason=None, method="GET", setup=None,
             device=None, payload=None, checks=None, statuses=None):
        expected = {"allow": allow, "statuses": statuses or ([200] if allow else [403])}
        if reason:
            expected["reason"] = reason
        entry = {"id": identifier, "group": "oracle", "name": name, "username": user,
                 "method": method, "path": path, "mode": "B1", "expected": expected}
        if setup:
            entry["setup"] = setup
        if device:
            entry["device"] = device
        if payload is not None:
            entry["json"] = payload
        if checks:
            entry["checks"] = checks
        cases.append(entry)

    # The labels below are the independent access matrix, not calls to the PDP.
    for identifier, name, user, path in [
        ("O-A01", "Nhân viên A tải nội bộ cùng phòng", "alice", "/documents/A-I01/download"),
        ("O-A02", "Alice tải mật do mình sở hữu", "alice", "/documents/A-C01/download"),
        ("O-A03", "Anna tải mật do mình sở hữu", "anna", "/documents/A-C02/download"),
        ("O-A04", "Trưởng phòng A tải mật của Alice", "adam", "/documents/A-C01/download"),
        ("O-A05", "Trưởng phòng A tải mật của Anna", "adam", "/documents/A-C02/download"),
        ("O-A06", "Nhân viên B tải nội bộ cùng phòng", "bob", "/documents/B-I01/download"),
        ("O-A07", "Bea tải mật do mình sở hữu", "bea", "/documents/B-C02/download"),
        ("O-A08", "Trưởng phòng B tải mật của Bob", "brian", "/documents/B-C01/download"),
        ("O-A09", "Trưởng phòng B tải mật của Bea", "brian", "/documents/B-C02/download"),
        ("O-A10", "Trưởng phòng A xem metadata hạn chế", "adam", "/documents/A-R01/metadata"),
        ("O-A11", "Trưởng phòng B xem metadata hạn chế", "brian", "/documents/B-R01/metadata"),
        ("O-A12", "Alice nhận danh sách đã lọc quyền", "alice", "/documents"),
        ("O-A13", "Bob nhận danh sách đã lọc quyền", "bob", "/documents"),
        ("O-A14", "Kiểm toán viên đọc audit", "auditor", "/audit"),
        ("O-A15", "Quản trị an toàn đọc trạng thái vận hành", "secadmin", "/admin/state"),
        ("O-A16", "Chủ thể đọc thông tin đăng nhập của mình", "alice", "/me"),
    ]:
        checks = None
        if identifier in {"O-A12", "O-A13"}:
            prefix = "A" if identifier == "O-A12" else "B"
            checks = {"allowed_ids": [f"{prefix}-I{n:02}" for n in range(1, 6)] + [f"{prefix}-C01"]}
        case(identifier, name, user, path, allow=True, checks=checks)
    for identifier, user, doc in [("O-A17", "adam", "A-R01"), ("O-A18", "brian", "B-R01")]:
        case(identifier, "Trưởng phòng tải hạn chế với grant hợp lệ", user,
             f"/documents/{doc}/download", allow=True,
             setup=[{"operation": "grant", "principal_id": user, "doc_id": doc, "ttl_seconds": 120}])
    for identifier, user, label in [("O-A19", "alice", "internal"), ("O-A20", "bob", "confidential")]:
        content = (f"ORACLE-INDEPENDENT-{identifier}\n" * 700).encode()
        case(identifier, "Tải lên hợp lệ với nhãn ban đầu", user, "/documents", allow=True,
             method="POST", payload={"title": f"{identifier}.txt", "label": label,
                                      "content_b64": base64.b64encode(content).decode()},
             statuses=[200, 201], checks={"owner_id": user})

    for identifier, name, user, path, reason in [
        ("O-D01", "Nhân viên không sở hữu tài liệu mật", "alice", "/documents/A-C02/download", "OWNER_OR_LABEL"),
        ("O-D02", "Sở hữu không vượt nhãn hạn chế", "alice", "/documents/A-R01/download", "OWNER_OR_LABEL"),
        ("O-D03", "Trưởng phòng thiếu grant hạn chế", "adam", "/documents/A-R01/download", "RESTRICTED_GRANT"),
        ("O-D04", "Trưởng phòng A không đọc phòng B", "adam", "/documents/B-I01/download", "DEPARTMENT"),
        ("O-D05", "Trưởng phòng B không đọc phòng A", "brian", "/documents/A-I01/download", "DEPARTMENT"),
        ("O-D06", "Kiểm toán viên không đọc nội dung", "auditor", "/documents/A-I01/download", "ROLE"),
        ("O-D07", "Quản trị an toàn không đọc nội dung", "secadmin", "/documents/A-I01/download", "ROLE"),
        ("O-D08", "Nhân viên không đọc audit", "alice", "/audit", "ROLE"),
        ("O-D09", "Nhân viên không đọc trạng thái quản trị", "alice", "/admin/state", "ROLE"),
    ]:
        case(identifier, name, user, path, allow=False, reason=reason)
    case("O-D10", "Chứng thư thuộc người khác", "alice", "/documents/A-I01/download",
         allow=False, reason="DEVICE_MISMATCH", device="anna")
    for identifier, name, changes, reason in [
        ("O-D11", "Thiết bị đã thu hồi", {"revoked": True}, "DEVICE_REVOKED"),
        ("O-D12", "Thiết bị không tuân thủ", {"compliant": False}, "NONCOMPLIANT"),
        ("O-D13", "Rủi ro cao", {"risk": "HIGH"}, "RISK_HIGH"),
        ("O-D14", "Tín hiệu đã hết thời hạn", {"observed_at": {"seconds_ago": 120},
                 "risk_at": {"seconds_ago": 120}, "auto_refresh": False}, "MISSING_OR_STALE"),
    ]:
        case(identifier, name, "alice", "/documents/A-I01/download", allow=False, reason=reason,
             setup=[{"operation": "device", "id": "dev-alice", "changes": changes}])
    case("O-D15", "Tài khoản hiện tại bị vô hiệu", "alice", "/documents/A-I01/download",
         allow=False, reason="INACTIVE", setup=[{"operation": "principal", "id": "alice",
                                                   "changes": {"active": False}}])
    case("O-D16", "Hết thời hạn đọc nghiệp vụ", "alice", "/documents/A-I01/download",
         allow=False, reason="RETENTION_EXPIRED", setup=[{"operation": "document", "id": "A-I01",
                    "changes": {"retention_until": {"seconds_ago": 120}}}])
    case("O-D17", "Legal hold chặn hủy sau thời hạn", "alice", "/documents/A-I01",
         method="DELETE", allow=False, reason="LEGAL_HOLD", setup=[{"operation": "document", "id": "A-I01",
                    "changes": {"retention_until": {"seconds_ago": 120}, "legal_hold": True}}])
    case("O-D18", "Chưa hết thời hạn không được hủy", "alice", "/documents/A-I01",
         method="DELETE", allow=False, reason="RETENTION_ACTIVE")
    case("O-D19", "Tài liệu không tồn tại", "alice", "/documents/unknown-document/download",
         allow=False, reason="NOT_FOUND", statuses=[404])
    case("O-D20", "Không có chứng thư client", "alice", "/documents/A-I01/download",
         allow=False, device="none", statuses=[400, 401, 403, 495, 496])
    assert len(cases) == 40
    assert sum(c["expected"]["allow"] for c in cases) == 20
    target = Path(__file__).resolve().parents[1] / "fixtures" / "cases.json"
    target.write_text(json.dumps({"schema_version": 1, "oracle_note":
        "Expected outcomes are fixed by the access matrix and must not be inferred from an observed PDP response.",
        "cases": cases}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
