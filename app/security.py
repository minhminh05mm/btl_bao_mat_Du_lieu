"""Validated identity, policy decisions and actual OpenBao Transit operations."""
import base64
import hmac
import threading
import time
from dataclasses import dataclass, field

import httpx
import jwt

from . import config


class Problem(Exception):
    def __init__(self, reason, status=403, *, policy_version=None):
        self.reason = reason
        self.status = status
        self.policy_version = policy_version or config.POLICY_VERSION
        super().__init__(reason)


@dataclass
class Context:
    subject: dict
    device: dict
    claims: dict
    request_id: str
    mode: str = config.POLICY_MODE
    deadlines: list = field(default_factory=list)

    @property
    def id(self):
        return self.subject["id"]


def normalize_serial(value):
    try:
        return format(int(str(value).replace(":", "").strip(), 16), "X")
    except (ValueError, TypeError):
        raise Problem("DEVICE_MISMATCH")


_jwks_lock = threading.Lock()
_jwks_keys = {}
_jwks_at = 0.0


def validate_jwt(token):
    global _jwks_keys, _jwks_at
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if header.get("alg") != "RS256" or not isinstance(kid, str):
            raise Problem("INVALID_TOKEN", 401)
        with _jwks_lock:
            if kid not in _jwks_keys or time.monotonic() - _jwks_at > 60:
                try:
                    response = httpx.get(config.OIDC_JWKS_URL, timeout=4)
                    response.raise_for_status()
                    keys = response.json()["keys"]
                    _jwks_keys = {
                        key["kid"]: jwt.PyJWK.from_dict(key).key
                        for key in keys
                        if key.get("kty") == "RSA" and key.get("use", "sig") == "sig"
                    }
                    _jwks_at = time.monotonic()
                except Exception:
                    raise Problem("IDENTITY_UNAVAILABLE", 503)
            key = _jwks_keys.get(kid)
        if key is None:
            raise Problem("INVALID_TOKEN", 401)
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience="zt-api",
            issuer=config.OIDC_ISSUER,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            leeway=0,
        )
        if not isinstance(claims.get("sub"), str):
            raise Problem("INVALID_TOKEN", 401)
        return claims
    except Problem:
        raise
    except Exception:
        raise Problem("INVALID_TOKEN", 401)


def authenticate(request, conn):
    try:
        trusted = config.secret(config.PROXY_SECRET_FILE)
    except OSError:
        raise Problem("GATEWAY_UNAVAILABLE", 503)
    supplied = request.headers.get("x-proxy-secret", "")
    if not trusted or not hmac.compare_digest(supplied, trusted):
        raise Problem("UNTRUSTED_GATEWAY", 401)
    if request.headers.get("x-expected-policy-mode") != config.POLICY_MODE:
        raise Problem("GATEWAY_MODE_MISMATCH", 503)
    if request.headers.get("x-verified-tls") != "SUCCESS":
        raise Problem("DEVICE_MISMATCH", 401)
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise Problem("INVALID_TOKEN", 401)
    claims = validate_jwt(authorization[7:])
    if config.faults().get("registry_unavailable"):
        raise Problem("REGISTRY_UNAVAILABLE", 503)
    subject = conn.execute(
        "SELECT * FROM principals WHERE subject_id=%s FOR SHARE", (claims["sub"],)
    ).fetchone()
    if not subject:
        raise Problem("UNKNOWN_SUBJECT", 401)
    serial = normalize_serial(request.headers.get("x-verified-serial", ""))
    device = conn.execute(
        "SELECT * FROM devices WHERE cert_serial=%s FOR SHARE", (serial,)
    ).fetchone()
    if not device or device["principal_id"] != subject["id"]:
        raise Problem("DEVICE_MISMATCH")
    return Context(subject, device, claims, request.state.request_id)


def decide(ctx, action, resource=None, grant=None, *, force_b1=False):
    mode = "B1" if force_b1 else ctx.mode
    snapshot = {
        "role": ctx.claims.get("b0_role"),
        "department": ctx.claims.get("b0_department"),
    }
    subject = {k: ctx.subject[k] for k in ("id", "role", "department", "active")}
    device = {k: ctx.device.get(k) for k in (
        "principal_id", "compliant", "revoked", "risk", "observed_at", "risk_at"
    )}
    payload = {"input": {
        "subject": subject,
        "device": device,
        "resource": resource,
        "action": action,
        "now": time.time(),
        "grant": grant,
        "mode": mode,
        "snapshot": snapshot,
    }}
    if config.faults().get("opa_response_invalid"):
        raise Problem("PDP_INVALID", 503)
    try:
        response = httpx.post(config.OPA_URL, json=payload, timeout=4)
        response.raise_for_status()
        decision = response.json()["result"]
        if (
            not isinstance(decision, dict)
            or type(decision.get("allow")) is not bool
            or not isinstance(decision.get("reason"), str)
            or decision.get("policy_version") != config.POLICY_VERSION
        ):
            raise Problem("PDP_INVALID", 503)
    except Problem:
        raise
    except Exception:
        raise Problem("PDP_UNAVAILABLE", 503)
    if not decision["allow"]:
        raise Problem(decision["reason"], 403, policy_version=decision["policy_version"])
    return decision


def transit(operation, value):
    if operation not in {"encrypt", "decrypt"}:
        raise ValueError("Unsupported Transit operation")
    try:
        token = config.secret(config.BAO_TOKEN_FILE)
        payload = {"plaintext": base64.b64encode(value).decode("ascii")} if operation == "encrypt" else {"ciphertext": value}
        response = httpx.post(
            f"{config.BAO_ADDR}/v1/transit/{operation}/documents",
            headers={"X-Vault-Token": token}, json=payload, timeout=5,
        )
        if response.status_code == 400 and operation == "decrypt":
            raise Problem("INTEGRITY_FAILURE", 503)
        response.raise_for_status()
        data = response.json()["data"]
        if operation == "encrypt":
            result = data["ciphertext"]
            if not isinstance(result, str) or not result.startswith("vault:v"):
                raise ValueError()
            return result
        return base64.b64decode(data["plaintext"], validate=True)
    except Problem:
        raise
    except Exception:
        raise Problem("KMS_UNAVAILABLE", 503)
