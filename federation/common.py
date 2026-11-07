"""Shared wire validation; no authority database or private key is shared."""
from __future__ import annotations

import hashlib
import hmac
import math
import os
import ssl
import threading
import time
import uuid
from pathlib import Path

import httpx
import jwt
import psycopg
from fastapi import Request
from fastapi.responses import JSONResponse
from psycopg.rows import dict_row

PARTNER_ISSUER = 'bmdl-partner-state'
RESOURCE_ISSUER = 'bmdl-resource-state'
STATE_AUDIENCE = 'bmdl-coordinator'
IDENTITY_ISSUER = os.getenv('OIDC_ISSUER', 'https://localhost:9443/realms/bmdl')
JWKS_URL = os.getenv('OIDC_JWKS_URL', 'http://keycloak:8080/realms/bmdl/protocol/openid-connect/certs')
SIGNAL_TTL = 60.0
MODES = {'F0', 'F1', 'F2'}
_jwks = {}
_jwks_at = 0.0
_jwks_guard = threading.RLock()


class FederationError(Exception):
    def __init__(self, reason: str, status: int = 403):
        self.reason, self.status = reason, status
        super().__init__(reason)


def read_secret(path):
    value = Path(path).read_text(encoding='utf-8').strip()
    if not value:
        raise FederationError('SERVICE_CREDENTIAL_UNAVAILABLE', 503)
    return value


def database():
    return psycopg.connect(read_secret(os.environ['SERVICE_DATABASE_URL_FILE']),
                           row_factory=dict_row, connect_timeout=4)


def require_credential(request: Request, path):
    supplied = request.headers.get('authorization', '')
    expected = 'Bearer ' + read_secret(path)
    if not hmac.compare_digest(supplied, expected):
        raise FederationError('SERVICE_AUTH_REQUIRED', 401)


def tls_client(timeout=5):
    ca = os.getenv('FEDERATION_CA_FILE', '/runtime/pki/ca.crt')
    return httpx.Client(verify=ssl.create_default_context(cafile=ca),
                        timeout=timeout, trust_env=False)


def install_error_handler(app):
    @app.exception_handler(FederationError)
    async def federation_error(request, error):
        return JSONResponse({'detail': {'reason': error.reason}}, status_code=error.status,
                            headers={'Cache-Control': 'no-store'})


def mint_proof(payload, key_file, issuer, *, lifetime=15):
    now = time.time()
    claims = {**payload, 'iss': issuer, 'aud': STATE_AUDIENCE,
              'iat': now, 'exp': now + lifetime, 'jti': str(uuid.uuid4())}
    return jwt.encode(claims, Path(key_file).read_bytes(), algorithm='RS256')


def verify_proof(token, public_key, issuer, *, kind=None):
    try:
        header = jwt.get_unverified_header(token)
        if header.get('alg') != 'RS256':
            raise ValueError('algorithm')
        value = jwt.decode(token, Path(public_key).read_bytes(), algorithms=['RS256'],
                           issuer=issuer, audience=STATE_AUDIENCE, leeway=1,
                           options={'require': ['iss', 'aud', 'sub', 'iat', 'exp', 'jti', 'kind']})
        if kind is not None and value['kind'] != kind:
            raise ValueError('kind')
        if not isinstance(value['sub'], str) or not value['sub']:
            raise ValueError('subject')
        if not isinstance(value['jti'], str) or not value['jti']:
            raise ValueError('event id')
        for field in ('iat', 'exp'):
            number(value.get(field))
        if value['exp'] <= value['iat'] or value['exp']-value['iat'] > 301:
            raise ValueError('lifetime')
        return value
    except FederationError:
        raise
    except Exception:
        raise FederationError('SOURCE_PROOF_INVALID', 401) from None


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise FederationError('SOURCE_SCHEMA_INVALID', 503)
    return float(value)


def version(value):
    if type(value) is not int or value < 1:
        raise FederationError('SOURCE_SCHEMA_INVALID', 503)
    return value


def serial(value):
    try:
        return format(int(str(value).replace(':', '').strip(), 16), 'X')
    except (ValueError, TypeError):
        raise FederationError('DEVICE_MISMATCH') from None


def state_reason(state, *, now=None, check_fresh=True):
    """An authentic source can still provide ineligible or old observations."""
    now = time.time() if now is None else now
    for key in ('active', 'compliant', 'revoked'):
        if type(state.get(key)) is not bool:
            raise FederationError('SOURCE_SCHEMA_INVALID', 503)
    for key in ('subject_version', 'device_version', 'subject_epoch', 'device_epoch'):
        version(state.get(key))
    if state.get('risk') not in {'NORMAL', 'HIGH'}:
        raise FederationError('SOURCE_SCHEMA_INVALID', 503)
    for key in ('observed_at','risk_at'):
        number(state.get(key))
    if not state['active']:
        return 'SOURCE_ACCOUNT_DISABLED'
    if state['revoked']:
        return 'SOURCE_DEVICE_REVOKED'
    if not state['compliant']:
        return 'SOURCE_DEVICE_NONCOMPLIANT'
    if state['risk'] != 'NORMAL':
        return 'SOURCE_DEVICE_RISK'
    for key in ('observed_at', 'risk_at'):
        at = number(state.get(key))
        if at > now + 1:
            return 'SOURCE_CLOCK_INVALID'
        if check_fresh and now-at > SIGNAL_TTL:
            return 'SOURCE_OBSERVATION_STALE'
    return None


def validate_snapshot(state, *, subject, device_serial, organization, nonce, now=None, require_eligible=True):
    now = time.time() if now is None else now
    if state.get('sub') != subject or state.get('organization') != organization:
        raise FederationError('SOURCE_BINDING_MISMATCH', 401)
    if state.get('nonce') != nonce:
        raise FederationError('SOURCE_NONCE_MISMATCH', 401)
    if serial(state.get('cert_serial')) != serial(device_serial):
        raise FederationError('DEVICE_MISMATCH')
    if not isinstance(state.get('device_id'), str) or not state['device_id']:
        raise FederationError('SOURCE_SCHEMA_INVALID', 503)
    reason = state_reason(state, now=now)
    if reason and require_eligible:
        raise FederationError(reason)
    return state


def identity(token):
    global _jwks_at, _jwks
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get('kid')
        if header.get('alg') != 'RS256' or not isinstance(kid, str):
            raise FederationError('INVALID_TOKEN', 401)
        with _jwks_guard:
            if kid not in _jwks or time.monotonic()-_jwks_at > 60:
                try:
                    r = httpx.get(JWKS_URL, timeout=4, trust_env=False)
                    r.raise_for_status()
                    _jwks = {k['kid']: jwt.PyJWK.from_dict(k).key for k in r.json()['keys']
                             if k.get('kty') == 'RSA' and k.get('use', 'sig') == 'sig'}
                    _jwks_at = time.monotonic()
                except Exception:
                    raise FederationError('IDENTITY_UNAVAILABLE', 503) from None
            key = _jwks.get(kid)
        if key is None:
            raise FederationError('INVALID_TOKEN', 401)
        claims = jwt.decode(token, key, algorithms=['RS256'], issuer=IDENTITY_ISSUER,
                            audience='zt-api', options={'require': ['sub', 'iss', 'aud', 'exp', 'iat']})
        if not isinstance(claims['sub'], str) or not claims['sub']:
            raise ValueError('subject')
        return claims
    except FederationError:
        raise
    except Exception:
        raise FederationError('INVALID_TOKEN', 401) from None


def bearer(request):
    value = request.headers.get('authorization', '')
    if not value.startswith('Bearer '):
        raise FederationError('INVALID_TOKEN', 401)
    return value[7:]


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()
