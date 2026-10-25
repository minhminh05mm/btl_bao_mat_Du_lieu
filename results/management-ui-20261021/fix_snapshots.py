import json,httpx
from lab import operations as ops
from lab.management import ensure_snapshot_attributes,read_json,profiles
cfg=ops.config();registry=read_json(ops.RT/'pki/registry.json')
with httpx.Client(base_url='http://keycloak:8080',timeout=20,trust_env=False) as kc:
    r=kc.post('/realms/master/protocol/openid-connect/token',data={'grant_type':'password','client_id':'admin-cli','username':'lab-root','password':cfg['keycloak_admin_password']});r.raise_for_status()
    kc.headers['Authorization']='Bearer '+r.json()['access_token'];ensure_snapshot_attributes(kc)
    count=0
    for name,record in profiles().items():
        if 'created_at' not in record:continue
        entry=registry[name];url='/admin/realms/bmdl/users/'+entry['subject_id']
        r=kc.get(url);r.raise_for_status();user=r.json()
        attributes=user.setdefault('attributes',{});attributes['b0_role']=[entry['role']];attributes['b0_department']=[entry['department']]
        kc.put(url,json=user).raise_for_status();count+=1
    print(json.dumps({'repaired_accounts':count,'snapshot_claims_admin_only':True}))
