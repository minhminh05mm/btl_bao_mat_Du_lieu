package bmdl_test

import rego.v1

sample := {
    "subject": {"id": "alice", "role": "staff", "department": "A", "active": true},
    "device": {"principal_id": "alice", "compliant": true, "revoked": false,
        "risk": "NORMAL", "observed_at": 1000, "risk_at": 1000},
    "resource": {"id": "A-C01", "owner_id": "alice", "department": "A",
        "label": "confidential", "version": 1, "retention_until": 2000,
        "legal_hold": false, "deleted": false},
    "action": "download", "now": 1000, "grant": null, "mode": "B1",
    "snapshot": {"role": "staff", "department": "A"},
}

patched_decision(patches) := response if {
    supplied := json.patch(sample, patches)
    response := data.bmdl.decision with input as supplied
}

test_own_confidential_allowed if {
    result := data.bmdl.decision with input as sample
    result == {"allow": true, "reason": "ALLOW", "policy_version": "bmdl-v1"}
}
test_other_owner_denied if {
    result := patched_decision([{"op": "replace", "path": "/resource/owner_id", "value": "anna"}])
    result.reason == "OWNER_OR_LABEL"
}
test_department_denied if {
    result := patched_decision([{"op": "replace", "path": "/resource/department", "value": "B"}])
    result.reason == "DEPARTMENT"
}
test_inactive_denied if {
    result := patched_decision([{"op": "replace", "path": "/subject/active", "value": false}])
    result.reason == "INACTIVE"
}
test_device_owner_must_match if {
    result := patched_decision([{"op": "replace", "path": "/device/principal_id", "value": "anna"}])
    result.reason == "DEVICE_MISMATCH"
}
test_revoked_device_denied if {
    result := patched_decision([{"op": "replace", "path": "/device/revoked", "value": true}])
    result.reason == "DEVICE_REVOKED"
}
test_noncompliant_denied if {
    result := patched_decision([{"op": "replace", "path": "/device/compliant", "value": false}])
    result.reason == "NONCOMPLIANT"
}
test_high_risk_denied if {
    result := patched_decision([{"op": "replace", "path": "/device/risk", "value": "HIGH"}])
    result.reason == "RISK_HIGH"
}
test_exact_ttl_boundary_accepted if {
    result := patched_decision([{"op": "replace", "path": "/now", "value": 1060}])
    result.allow
}
test_expired_signal_denied if {
    result := patched_decision([{"op": "replace", "path": "/now", "value": 1060.001}])
    result.reason == "MISSING_OR_STALE"
}
test_missing_risk_timestamp_denied if {
    result := patched_decision([{"op": "remove", "path": "/device/risk_at"}])
    result.reason == "MISSING_OR_STALE"
}
test_future_signal_denied if {
    result := patched_decision([{"op": "replace", "path": "/device/observed_at", "value": 1001}])
    result.reason == "MISSING_OR_STALE"
}
test_unknown_label_denied if {
    result := patched_decision([{"op": "replace", "path": "/resource/label", "value": "unknown"}])
    result.reason == "INVALID_METADATA"
}
test_missing_metadata_denied if {
    result := patched_decision([{"op": "remove", "path": "/resource/owner_id"}])
    result.reason == "INVALID_METADATA"
}
test_deleted_not_found if {
    result := patched_decision([{"op": "replace", "path": "/resource/deleted", "value": true}])
    result.reason == "NOT_FOUND"
}
test_retention_read_expired if {
    result := patched_decision([{"op": "replace", "path": "/resource/retention_until", "value": 1000}])
    result.reason == "RETENTION_EXPIRED"
}
test_delete_before_retention_denied if {
    result := patched_decision([{"op": "replace", "path": "/action", "value": "delete"}])
    result.reason == "RETENTION_ACTIVE"
}
test_legal_hold_blocks_delete if {
    result := patched_decision([
        {"op": "replace", "path": "/action", "value": "delete"},
        {"op": "replace", "path": "/resource/retention_until", "value": 999},
        {"op": "replace", "path": "/resource/legal_hold", "value": true},
    ])
    result.reason == "LEGAL_HOLD"
}
test_owner_delete_after_retention if {
    result := patched_decision([
        {"op": "replace", "path": "/action", "value": "delete"},
        {"op": "replace", "path": "/resource/retention_until", "value": 999},
    ])
    result.allow
}
test_auditor_cannot_download if {
    result := patched_decision([{"op": "replace", "path": "/subject/role", "value": "auditor"}])
    result.reason == "ROLE"
}
test_auditor_can_audit if {
    result := patched_decision([
        {"op": "replace", "path": "/subject/role", "value": "auditor"},
        {"op": "replace", "path": "/action", "value": "audit"},
    ])
    result.allow
}
test_secadmin_can_admin_but_not_read if {
    input1 := json.patch(sample, [{"op": "replace", "path": "/subject/role", "value": "security_admin"}])
    admin_input := object.union(input1, {"action": "admin"})
    admin_result := data.bmdl.decision with input as admin_input
    read_result := data.bmdl.decision with input as input1
    admin_result.allow
    read_result.reason == "ROLE"
}
test_staff_cannot_access_restricted_even_as_owner if {
    result := patched_decision([{"op": "replace", "path": "/resource/label", "value": "restricted"}])
    result.reason == "OWNER_OR_LABEL"
}
restricted := json.patch(sample, [
    {"op": "replace", "path": "/subject/role", "value": "manager"},
    {"op": "replace", "path": "/resource/label", "value": "restricted"},
])
valid_grant := {"principal_id": "alice", "doc_id": "A-C01", "doc_version": 1,
    "action": "download", "expires_at": 1001, "revoked": false, "approver": "secadmin"}

test_manager_restricted_metadata_without_grant if {
    supplied := object.union(restricted, {"action": "metadata"})
    result := data.bmdl.decision with input as supplied
    result.allow
}
test_manager_restricted_requires_grant if {
    result := data.bmdl.decision with input as restricted
    result.reason == "RESTRICTED_GRANT"
}
test_manager_restricted_valid_grant if {
    supplied := object.union(restricted, {"grant": valid_grant})
    result := data.bmdl.decision with input as supplied
    result.allow
}
test_grant_expiry_is_exclusive if {
    supplied := object.union(restricted, {"grant": object.union(valid_grant, {"expires_at": 1000})})
    result := data.bmdl.decision with input as supplied
    result.reason == "RESTRICTED_GRANT"
}
test_revoked_or_wrong_grant_does_not_allow if {
    every change in [{"revoked": true}, {"doc_version": 2}, {"doc_id": "A-C02"},
        {"action": "metadata"}, {"principal_id": "anna"}, {"approver": "alice"}] {
        supplied := object.union(restricted, {"grant": object.union(valid_grant, change)})
        result := data.bmdl.decision with input as supplied
        result.reason == "RESTRICTED_GRANT"
    }
}
test_b0_ignores_dynamic_controls_but_not_certificate_owner if {
    supplied := json.patch(sample, [
        {"op": "replace", "path": "/mode", "value": "B0"},
        {"op": "replace", "path": "/subject/active", "value": false},
        {"op": "replace", "path": "/subject/role", "value": "auditor"},
        {"op": "replace", "path": "/device/compliant", "value": false},
        {"op": "replace", "path": "/device/risk", "value": "HIGH"},
        {"op": "replace", "path": "/resource/label", "value": "restricted"},
    ])
    result := data.bmdl.decision with input as supplied
    result.allow
    mismatched := json.patch(supplied, [{"op": "replace", "path": "/device/principal_id", "value": "anna"}])
    mismatch_result := data.bmdl.decision with input as mismatched
    mismatch_result.reason == "DEVICE_MISMATCH"
}
test_b0_admin_still_uses_current_controls if {
    supplied := json.patch(sample, [
        {"op": "replace", "path": "/mode", "value": "B0"},
        {"op": "replace", "path": "/subject/role", "value": "security_admin"},
        {"op": "replace", "path": "/device/compliant", "value": false},
        {"op": "replace", "path": "/action", "value": "admin"},
    ])
    result := data.bmdl.decision with input as supplied
    result.reason == "NONCOMPLIANT"
}
test_total_decision_on_missing_or_unknown_input if {
    every supplied in [{}, {"subject": null}, object.union(sample, {"action": "export_all"})] {
        result := data.bmdl.decision with input as supplied
        result.allow == false
        result.reason == "INVALID_METADATA"
    }
}
