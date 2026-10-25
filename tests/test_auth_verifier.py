"""Exercise the production decoder, isolating claims from signature failures.

Only the JWKS network lookup is replaced. The real RS256/PyJWT validation path
is called, so wrong issuer/audience/expiry are tested with a valid signature.
"""
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app import config
from app import security


@pytest.fixture
def issuer(monkeypatch):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(security, "_jwks_keys", {"unit-key": private.public_key()})
    monkeypatch.setattr(security, "_jwks_at", time.monotonic())

    def issue(changes=None, *, algorithm="RS256", key=None, omit=()):
        now = int(time.time())
        claims = {"iss": config.OIDC_ISSUER, "aud": "zt-api", "sub": "unit-subject",
                  "iat": now - 2, "exp": now + 120}
        claims.update(changes or {})
        for claim in omit:
            claims.pop(claim, None)
        signing_key = private if key is None else key
        return jwt.encode(claims, signing_key, algorithm=algorithm, headers={"kid": "unit-key"})
    return issue


def test_valid_signed_identity(issuer):
    assert security.validate_jwt(issuer())["sub"] == "unit-subject"


@pytest.mark.parametrize("changes", [
    {"iss": "https://another-issuer.invalid/realms/bmdl"},
    {"aud": "unrelated-api"},
    {"exp": int(time.time()) - 30},
    {"iat": int(time.time()) + 3600},
    {"sub": 123},
])
def test_signed_but_invalid_claims_are_rejected(issuer, changes):
    with pytest.raises(security.Problem) as failure:
        security.validate_jwt(issuer(changes))
    assert failure.value.status == 401
    assert failure.value.reason == "INVALID_TOKEN"


@pytest.mark.parametrize("claim", ["sub", "exp", "iat", "iss", "aud"])
def test_required_claim_is_checked(issuer, claim):
    with pytest.raises(security.Problem) as failure:
        security.validate_jwt(issuer(omit=(claim,)))
    assert failure.value.status == 401


def test_wrong_signature_is_rejected(issuer):
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(security.Problem) as failure:
        security.validate_jwt(issuer(key=attacker_key))
    assert failure.value.status == 401


def test_algorithm_confusion_is_rejected(issuer):
    with pytest.raises(security.Problem) as failure:
        security.validate_jwt(issuer(algorithm="HS256", key="untrusted-unit-test-secret-at-least-32-bytes"))
    assert failure.value.status == 401


def test_malformed_token_is_rejected():
    with pytest.raises(security.Problem) as failure:
        security.validate_jwt("not.a.valid.jwt")
    assert failure.value.status == 401
