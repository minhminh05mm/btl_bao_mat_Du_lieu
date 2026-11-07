"""Resource-side adapter. No partner database or partner private key is available here."""
import os
from pathlib import Path
from federation.common import FederationError, read_secret, tls_client, mint_proof, RESOURCE_ISSUER, require_credential, serial
from . import config, db

SERVICE = Path(os.getenv('RESOURCE_SERVICE_DIR', '/runtime/federation'))

def call(path, body):
    try:
        with tls_client() as client:
            response = client.post('https://coordinator:8080' + path, json=body,
                headers={'Authorization': 'Bearer ' + read_secret(SERVICE/'api-token')})
        if not response.is_success:
            raise FederationError(response.json().get('detail', {}).get('reason', 'COORDINATOR_UNAVAILABLE'), response.status_code)
        return response.json()
    except FederationError: raise
    except Exception: raise FederationError('COORDINATOR_UNAVAILABLE', 503) from None

def request_data(request, token, phase='request'):
    return {'resource_token': token, 'mode': request.headers.get('x-verified-federation-mode'),
            'cert_serial': request.headers.get('x-verified-serial'),
            'request_id': request.state.request_id, 'phase': phase}

def local_state(request, body):
    require_credential(request, SERVICE/'resource-read-token')
    nonce = body.get('nonce')
    if not isinstance(nonce, str) or not 16 <= len(nonce) <= 128:
        raise FederationError('SOURCE_NONCE_REQUIRED', 422)
    with db.connect() as conn:
        user = conn.execute("SELECT * FROM principals WHERE subject_id=%s AND organization='R'", (body.get('subject'),)).fetchone()
        if not user: raise FederationError('SOURCE_SUBJECT_UNKNOWN')
        device = conn.execute('SELECT * FROM devices WHERE principal_id=%s AND cert_serial=%s', (user['id'], serial(body.get('cert_serial')))).fetchone()
        if not device: raise FederationError('DEVICE_MISMATCH')
    state = {'kind':'state', 'sub':user['subject_id'], 'identity_issuer':config.OIDC_ISSUER,
        'organization':'R', 'principal_id':user['id'], 'username':user['username'], 'active':user['active'],
        'subject_version':user['permission_version'], 'subject_epoch':user['permission_version'],
        'device_id':device['id'], 'cert_serial':device['cert_serial'],
        'device_version':device['state_version'], 'device_epoch':device['state_version'], 'nonce':nonce,
        'changed_at':max(user['updated_at'],device['updated_at']),
        **{k:device[k] for k in ('compliant','revoked','risk','observed_at','risk_at')}}
    return {'proof':mint_proof(state,SERVICE/'signing.key',RESOURCE_ISSUER)}
