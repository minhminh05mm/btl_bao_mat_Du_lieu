"""Trusted localhost operator helpers. Never mounted in either authority service."""
import base64,json,time
from pathlib import Path
import httpx
from federation.bootstrap import private, register
from federation.common import tls_client
from . import operations as ops
from .client import LabClient

def state():
    return {'partner':private('partner','/ops/state',method='GET'),
            'coordinator':private('coordinator','/ops/state',method='GET'),
            'resource':ops.state()}

def source_change(body):
    actor=body.get('actor','p_admin');kind=body.get('kind','principal');target=str(body.get('target',''))
    if kind not in {'principal','device'}:raise ValueError('Loại đối tượng không hợp lệ.')
    patch=body.get('patch',{})
    c=LabClient()
    try:
        token=c.token(actor)
        with tls_client()as client:
            r=client.patch('https://partner:8080/admin/'+('principals'if kind=='principal'else'devices')+'/'+target,
                json=patch,headers={'Authorization':'Bearer '+token})
        result={'status':r.status_code,'ok':r.is_success,'payload':r.json()}
        if not r.is_success:return result
        # IdP sync is supplementary. The partner state remains authoritative even if this fails.
        if kind=='principal'and 'active'in patch:
            user=next((u for u in ops.rows('principals')if u['id']==target),None)
            try:
                with httpx.Client(base_url='http://keycloak:8080',timeout=10,trust_env=False)as kc:
                    cfg=ops.config()
                    a=kc.post('/realms/master/protocol/openid-connect/token',data={'grant_type':'password',
                        'client_id':'admin-cli','username':'lab-root','password':cfg['keycloak_admin_password']})
                    a.raise_for_status();kc.headers['Authorization']='Bearer '+a.json()['access_token']
                    kc.put('/admin/realms/bmdl/users/'+user['subject_id'],json={'enabled':patch['active']}).raise_for_status()
                result['identity_sync']='completed'
            except Exception:result['identity_sync']='pending';result['warning']='Trạng thái nguồn đã đổi; đồng bộ đăng nhập chưa hoàn tất.'
        return result
    finally:c.close()

def result(response):
    ctype=response.headers.get('content-type','')
    try:payload=response.json()
    except ValueError:payload=None
    detail=(payload or{}).get('detail',{})if isinstance(payload,dict)else{}
    if not isinstance(detail,dict):detail={}
    return {'status':response.status_code,'ok':response.is_success,
        'reason':response.headers.get('x-policy-reason')or detail.get('reason'),
        'request_id':response.headers.get('x-request-id')or detail.get('request_id'),
        'latency_ms':round(response.extensions.get('lab_latency_ms',0),2),
        'payload':payload,'size':len(response.content),'content_type':ctype,
        'content_b64':base64.b64encode(response.content).decode()if response.is_success and payload is None else None}

def run_suite(progress):
    from federation.verify import run
    return run(progress)
