package bmdl

import rego.v1

# B0 is a deliberately weaker, operator-selected reference configuration. The
# HTTP client must never be allowed to choose input.mode; the API owns it.
policy_version := "bmdl-v1"
read_actions := {"list", "metadata", "download"}
document_actions := {"list", "metadata", "download", "upload", "delete", "raise_label", "grant"}
known_actions := {"me", "list", "metadata", "download", "upload", "delete", "audit", "admin", "raise_label", "grant"}
business_roles := {"staff", "manager"}
known_labels := {"internal", "confidential", "restricted"}

baseline if {
    input.mode == "B0"
    input.action in read_actions
}
baseline if {
    input.mode == "B0"
    input.action == "me"
}

effective_role := input.snapshot.role if baseline else := input.subject.role
effective_department := input.snapshot.department if baseline else := input.subject.department

valid_envelope if {
    is_object(input.subject)
    is_string(input.subject.id)
    input.subject.id != ""
    is_object(input.device)
    is_string(input.action)
    input.action in known_actions
    input.mode in {"B0", "B1"}
    is_number(input.now)
    input.now >= 0
}

valid_resource if {
    is_object(input.resource)
    is_string(input.resource.id)
    input.resource.id != ""
    is_string(input.resource.department)
    input.resource.department != ""
    is_number(input.resource.retention_until)
    is_boolean(input.resource.deleted)
    baseline
}
valid_resource if {
    is_object(input.resource)
    is_string(input.resource.id)
    input.resource.id != ""
    is_string(input.resource.owner_id)
    input.resource.owner_id != ""
    is_string(input.resource.department)
    input.resource.department != ""
    input.resource.label in known_labels
    is_number(input.resource.version)
    input.resource.version >= 1
    input.resource.version == floor(input.resource.version)
    is_number(input.resource.retention_until)
    is_boolean(input.resource.legal_hold)
    is_boolean(input.resource.deleted)
    not baseline
}

fresh_signal(timestamp) if {
    is_number(timestamp)
    input.now >= timestamp
    input.now - timestamp <= 60
}

device_context_valid if {
    is_boolean(input.device.compliant)
    is_boolean(input.device.revoked)
    input.device.risk in {"NORMAL", "HIGH"}
    fresh_signal(input.device.observed_at)
    fresh_signal(input.device.risk_at)
}

download_grant_valid if {
    is_object(input.grant)
    input.grant.principal_id == input.subject.id
    input.grant.doc_id == input.resource.id
    input.grant.doc_version == input.resource.version
    input.grant.action == "download"
    is_number(input.grant.expires_at)
    input.grant.expires_at > input.now
    input.grant.revoked == false
    is_string(input.grant.approver)
    input.grant.approver != ""
    input.grant.approver != input.subject.id
}

proposal_grant_valid if {
    is_object(input.grant)
    is_string(input.grant.principal_id)
    input.grant.principal_id != ""
    input.grant.approver == input.subject.id
    input.grant.principal_id != input.grant.approver
    input.grant.doc_id == input.resource.id
    input.grant.doc_version == input.resource.version
    input.grant.action == "download"
    is_number(input.grant.expires_at)
    input.grant.expires_at > input.now
    input.grant.revoked == false
}

role_valid if input.action == "me"
role_valid if {
    input.action == "audit"
    input.subject.role in {"auditor", "security_admin"}
}
role_valid if {
    input.action in {"admin", "raise_label", "grant"}
    input.subject.role == "security_admin"
}
role_valid if {
    input.action in {"list", "metadata", "download", "upload", "delete"}
    effective_role in business_roles
}

authorized if input.action == "me"
authorized if {
    input.action in {"audit", "admin", "raise_label"}
    role_valid
}
authorized if {
    input.action == "grant"
    input.subject.role == "security_admin"
    input.resource.label == "restricted"
    proposal_grant_valid
}
authorized if {
    baseline
    input.action in read_actions
    effective_role in business_roles
    input.resource.department == effective_department
}
authorized if {
    not baseline
    input.action in read_actions
    effective_role in business_roles
    input.resource.department == effective_department
    input.resource.label == "internal"
}
authorized if {
    not baseline
    input.action in read_actions
    input.resource.department == effective_department
    input.resource.label == "confidential"
    effective_role == "manager"
}
authorized if {
    not baseline
    input.action in read_actions
    input.resource.department == effective_department
    input.resource.label == "confidential"
    effective_role == "staff"
    input.resource.owner_id == input.subject.id
}
authorized if {
    not baseline
    input.action in {"list", "metadata"}
    effective_role == "manager"
    input.resource.department == effective_department
    input.resource.label == "restricted"
}
authorized if {
    not baseline
    input.action == "download"
    effective_role == "manager"
    input.resource.department == effective_department
    input.resource.label == "restricted"
    download_grant_valid
}
authorized if {
    input.action == "upload"
    input.subject.role in business_roles
    input.resource.department == input.subject.department
    input.resource.owner_id == input.subject.id
    input.resource.label in {"internal", "confidential"}
}
authorized if {
    input.action == "upload"
    input.subject.role == "manager"
    input.resource.department == input.subject.department
    input.resource.owner_id == input.subject.id
    input.resource.label == "restricted"
    download_grant_valid
}
authorized if {
    input.action == "delete"
    input.resource.department == input.subject.department
    input.subject.role == "manager"
}
authorized if {
    input.action == "delete"
    input.resource.department == input.subject.department
    input.subject.role == "staff"
    input.resource.owner_id == input.subject.id
}

# Ordered reasons make multiple simultaneous failures deterministic. Authentication,
# gateway identity verification and dependency faults are enforced by the API.
reason := "INVALID_METADATA" if {
    not valid_envelope
} else := "DEVICE_MISMATCH" if {
    not input.device.principal_id == input.subject.id
} else := "INACTIVE" if {
    not baseline
    not input.subject.active == true
} else := "DEVICE_REVOKED" if {
    not baseline
    input.device.revoked == true
} else := "NONCOMPLIANT" if {
    not baseline
    input.device.compliant == false
} else := "RISK_HIGH" if {
    not baseline
    input.device.risk == "HIGH"
} else := "MISSING_OR_STALE" if {
    not baseline
    not device_context_valid
} else := "INVALID_METADATA" if {
    input.action in document_actions
    not valid_resource
} else := "NOT_FOUND" if {
    input.action in document_actions
    input.resource.deleted == true
} else := "ROLE" if {
    not role_valid
} else := "LEGAL_HOLD" if {
    input.action == "delete"
    input.resource.legal_hold == true
} else := "RETENTION_ACTIVE" if {
    input.action == "delete"
    input.resource.retention_until > input.now
} else := "RETENTION_EXPIRED" if {
    input.action in read_actions
    input.resource.retention_until <= input.now
} else := "DEPARTMENT" if {
    input.action in {"list", "metadata", "download", "upload", "delete"}
    not input.resource.department == effective_department
} else := "RESTRICTED_GRANT" if {
    not baseline
    input.action in {"download", "upload"}
    input.resource.label == "restricted"
    effective_role == "manager"
    not download_grant_valid
} else := "RESTRICTED_GRANT" if {
    input.action == "grant"
    not proposal_grant_valid
} else := "ALLOW" if {
    authorized
} else := "OWNER_OR_LABEL"

decision := {"allow": reason == "ALLOW", "reason": reason, "policy_version": policy_version}
