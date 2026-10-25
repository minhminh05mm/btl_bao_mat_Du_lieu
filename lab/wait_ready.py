import time,httpx
from .client import LabClient
for attempt in range(120):
    client=None
    try:
        client=LabClient()
        responses=[client.request('alice','GET','/health',mode=mode) for mode in ['B1','B0']]
        modes=all(response.status_code==200 and response.headers.get('X-Policy-Mode')==mode
                  for mode,response in zip(['B1','B0'],responses))
        with httpx.Client(timeout=3,trust_env=False) as checks:
            opa=checks.get('http://opa:8181/health')
            bao=checks.get('http://openbao:8200/v1/sys/seal-status')
            web=checks.get('http://lab:8088/lab/bootstrap')
        if modes and opa.status_code==200 and bao.status_code==200 and not bao.json()['sealed'] and web.status_code==200:
            print('Ready: both policy modes, Keycloak JWT, gateway mTLS, database, PDP, unsealed KMS and localhost console');break
    except Exception:pass
    finally:
        if client:client.close()
    time.sleep(.5)
else:raise SystemExit('Services did not become ready; inspect project container logs')
