import json,os,ssl,time
from pathlib import Path
import httpx

RUNTIME=Path(os.getenv('LAB_RUNTIME_DIR','/runtime'))
class LabClient:
    def __init__(self):
        self.config=json.loads((RUNTIME/'secrets/config.json').read_text())
        self._tokens={};self._clients={}
    def token(self,username,force=False):
        cached=self._tokens.get(username)
        if not force and cached and cached[1]>time.time():return cached[0]
        self.config=json.loads((RUNTIME/'secrets/config.json').read_text())
        password=self.config['users'][username]
        if isinstance(password,dict):password=password.get('password')
        with httpx.Client(timeout=20,trust_env=False) as client:
            response=client.post('http://keycloak:8080/realms/bmdl/protocol/openid-connect/token',data={
                'grant_type':'password','client_id':'zt-tests','username':username,'password':password})
            response.raise_for_status();data=response.json()
        self._tokens[username]=(data['access_token'],time.time()+data['expires_in']-10)
        return data['access_token']
    def request(self,username,method,path,json=None,device=None,mode='B1',token=None,headers=None,**kwargs):
        identity=device or username
        if identity.startswith('dev-'):identity=identity[4:]
        if identity not in self._clients:
            context=ssl.create_default_context(cafile=str(RUNTIME/'pki/ca.crt'))
            if identity!='none':context.load_cert_chain(str(RUNTIME/f'pki/{identity}.crt'),str(RUNTIME/f'pki/{identity}.key'))
            self._clients[identity]=httpx.Client(verify=context,timeout=15,trust_env=False)
        auth=token if token is not None else self.token(username)
        h=httpx.Headers({'Authorization':'Bearer '+auth});h.update(headers or {})
        url=f"https://gateway:{8444 if mode=='B0' else 8443}/api/"+path.lstrip('/')
        started=time.perf_counter()
        try:
            response=self._clients[identity].request(method,url,json=json,headers=h,**kwargs)
        except httpx.TransportError as exc:
            response=httpx.Response(495 if isinstance(exc,httpx.ConnectError) and 'CERTIFICATE' in str(exc).upper() else 503,
                json={'detail':{'reason':'TRANSPORT_BLOCKED','transport_error':True,'error_type':type(exc).__name__}},request=httpx.Request(method,url))
        response.extensions['lab_latency_ms']=(time.perf_counter()-started)*1000
        return response
    def close(self):
        for c in self._clients.values():c.close()
