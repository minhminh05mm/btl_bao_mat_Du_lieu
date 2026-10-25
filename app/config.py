"""Configuration without secret values in logs or application responses."""
import json
import os
from pathlib import Path

RUNTIME = Path(os.getenv("RUNTIME_DIR", "/runtime"))
DATABASE_URL = os.environ.get("DATABASE_URL", "")
OPA_URL = os.getenv("OPA_URL", "http://opa:8181/v1/data/bmdl/decision")
BAO_ADDR = os.getenv("BAO_ADDR", "http://openbao:8200").rstrip("/")
BAO_TOKEN_FILE = Path(os.getenv("BAO_TOKEN_FILE", str(RUNTIME / "secrets/bao-app-token")))
PROXY_SECRET_FILE = Path(os.getenv("PROXY_SECRET_FILE", str(RUNTIME / "secrets/proxy-secret")))
OIDC_ISSUER = os.getenv("OIDC_ISSUER", "https://localhost:9443/realms/bmdl")
OIDC_JWKS_URL = os.getenv("OIDC_JWKS_URL", "http://keycloak:8080/realms/bmdl/protocol/openid-connect/certs")
POLICY_MODE = os.getenv("POLICY_MODE", "B1")
if POLICY_MODE not in {"B0", "B1"}:
    raise RuntimeError("Unsupported deployment policy mode")
POLICY_VERSION = "bmdl-v1"
SIGNAL_TTL = 60
LABEL_DAYS = {"internal": 180, "confidential": 90, "restricted": 30}
LABEL_RANK = {"internal": 0, "confidential": 1, "restricted": 2}


def faults():
    path = RUNTIME / "lab-faults.json"
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, OSError):
        # A malformed operator fault file is a service fault, never a bypass.
        return {"registry_unavailable": True, "audit_write_failure": True}


def secret(path):
    return Path(path).read_text(encoding="utf-8").strip()
