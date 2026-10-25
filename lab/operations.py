"""Trusted localhost operator only; never mounted into the business API."""
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime,timezone
import os,json,time,uuid,hashlib,subprocess,threading,base64,io,tarfile,shutil,socket
import docker,httpx,psycopg
from psycopg.rows import dict_row
from psycopg import sql

ROOT=Path('/project');RT=Path('/runtime');LOCK=threading.RLock()
SERVICES={'api','api-baseline','opa','openbao','postgres','keycloak','gateway'}
def config():return json.loads((RT/'secrets/config.json').read_text())
def engine():return docker.from_env(timeout=120)
def container(service):
    if service not in SERVICES|{'lab'}:raise ValueError('Unknown service')
    found=engine().containers.list(all=True,filters={'label':['com.docker.compose.project=bmdl',f'com.docker.compose.service={service}']})
    if not found:raise RuntimeError('Service not found: '+service)
    return found[0]
@contextmanager
def db(url=None):
    with psycopg.connect(url or config()['db_admin_url'],row_factory=dict_row) as conn:yield conn
def rows(table):
    with db() as conn:return conn.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier(table))).fetchall()
def safe(value):
    if isinstance(value,dict):return {k:safe(v) for k,v in value.items() if k not in {'ciphertext','password','token','root_token','unseal_keys_b64','access_token','refresh_token','key','content'}}
    if isinstance(value,(list,tuple)):return [safe(v) for v in value]
    if isinstance(value,datetime):return value.isoformat()
    if isinstance(value,bytes):return f'<{len(value)} bytes>'
    return value
def state():
    result={}
    for table in ['principals','devices','documents','grants','audit','alerts']:
        try:result[table]=safe(rows(table))[-300:]
        except Exception:result[table]=[]
    from .management import profiles
    employee_profiles=profiles()
    for principal in result.get('principals',[]):
        principal['display_name']=employee_profiles.get(principal['id'],{}).get('display_name',principal['username'])
    result['services']=[]
    for service in sorted(SERVICES|{'lab'}):
        found=engine().containers.list(all=True,filters={'label':['com.docker.compose.project=bmdl',f'com.docker.compose.service={service}']})
        result['services'].append({'name':service,'status':found[0].status if found else 'missing','health':'running' if found and found[0].status=='running' else 'unavailable'})
    result['snapshots']=[json.loads(p.read_text()) for p in sorted((RT/'backups/manifests').glob('*.json'))] if (RT/'backups/manifests').exists() else []
    result['faults']=json.loads((RT/'shared/lab-faults.json').read_text()) if (RT/'shared/lab-faults.json').exists() else {}
    result['disk']={'project_free_gb':round(shutil.disk_usage(ROOT).free/2**30,2),'data_root':'E:\\btl_bao_mat_Du_lieu\\runtime\\wsl'}
    return safe(result)
def set_fault(name,enabled):
    if name not in {'audit_write_failure','opa_response_invalid','registry_unavailable'}:raise ValueError('Unknown fault')
    with LOCK:
        path=RT/'shared/lab-faults.json';data=json.loads(path.read_text()) if path.exists() else {}
        data[name]=bool(enabled);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data));os.replace(tmp,path)
    return {'fault':name,'enabled':bool(enabled),'simulated':True}
def _bao_root():return json.loads((RT/'secrets/bao-init.json').read_text())
def unseal(addr='http://openbao:8200',keys=None):
    key=(keys or _bao_root())['keys_base64'][0]
    for _ in range(60):
        try:
            r=httpx.put(addr+'/v1/sys/unseal',json={'key':key},timeout=5,trust_env=False)
            if r.status_code==200 and not r.json().get('sealed',True):return
        except httpx.HTTPError:pass
        time.sleep(.5)
    raise RuntimeError('OpenBao did not unseal')
def initialize():
    for _ in range(80):
        try:
            status=httpx.get('http://openbao:8200/v1/sys/init',timeout=3,trust_env=False)
            if status.status_code==200:break
        except httpx.HTTPError:pass
        time.sleep(.5)
    if not status.json().get('initialized'):
        response=httpx.put('http://openbao:8200/v1/sys/init',json={'secret_shares':1,'secret_threshold':1},trust_env=False,timeout=120)
        response.raise_for_status();data=response.json()
        (RT/'secrets/bao-init.json').write_text(json.dumps(data))
    unseal()
    root=_bao_root()['root_token'];headers={'X-Vault-Token':root}
    with httpx.Client(base_url='http://openbao:8200/v1',headers=headers,trust_env=False,timeout=20) as c:
        mounts=c.get('/sys/mounts').json()['data']
        if 'transit/' not in mounts:c.post('/sys/mounts/transit',json={'type':'transit'}).raise_for_status()
        c.post('/transit/keys/documents',json={'type':'aes256-gcm96','exportable':False,'allow_plaintext_backup':False}).raise_for_status()
        policy='path "transit/encrypt/documents" { capabilities = ["update"] }\npath "transit/decrypt/documents" { capabilities = ["update"] }'
        c.put('/sys/policies/acl/bmdl-app',json={'policy':policy}).raise_for_status()
        tokenfile=RT/'secrets/bao-app-token'
        if tokenfile.read_text().strip()=='initialization-pending':
            result=c.post('/auth/token/create',json={'policies':['bmdl-app'],'no_default_policy':True,'ttl':'0','renewable':False}).json()
            tokenfile.write_text(result['auth']['client_token'])
        (RT/'api-secrets/bao-app-token').write_text(tokenfile.read_text())
    return {'initialized':True,'persistent':True,'key':'documents','app_token_scoped':True}
def stop_service(name):
    with LOCK:container(name).stop(timeout=8)
    return {'service':name,'running':False,'actual_container_outage':True}
def start_service(name):
    with LOCK:
        container(name).start()
        if name=='openbao':unseal()
        time.sleep(.4)
    return {'service':name,'running':True}
def fault(service,enabled):
    if service in {'audit_write_failure','opa_response_invalid','registry_unavailable'}:return set_fault(service,enabled)
    return stop_service(service) if enabled else start_service(service)
PATCHES={
 'principal':('principals',{'active','role','department','permission_version'}),
 'device':('devices',{'compliant','revoked','risk','observed_at','risk_at','auto_refresh'}),
 'document':('documents',{'retention_until','legal_hold','label','version','deleted'}),
 'grant':('grants',{'expires_at','revoked','doc_version','action','approver'})}
def _ledger(kind,recordid,changes):
    path=RT/'shared/ledger/events.jsonl';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as f:f.write(json.dumps({'at':time.time(),'kind':kind,'id':recordid,'changes':safe(changes),'actor':'local-lab-operator'})+'\n')
def edit_state(kind,recordid,patch):
    kind=kind.rstrip('s')
    if kind=='principal':kind='principal'
    if kind not in PATCHES:raise ValueError('Unknown record kind')
    table,allowed=PATCHES[kind]
    if not patch or not set(patch).issubset(allowed):raise ValueError('Field not allowed in operator editor')
    with LOCK,db() as conn:
        query=sql.SQL('UPDATE {} SET {} WHERE id=%s RETURNING *').format(sql.Identifier(table),sql.SQL(',').join(sql.SQL('{}=%s').format(sql.Identifier(k)) for k in patch))
        row=conn.execute(query,[*patch.values(),recordid]).fetchone()
        if not row:raise ValueError('Unknown ID')
        _ledger(kind,recordid,patch)
    return safe(row)
def patch_document(doc_id,changes):return edit_state('document',doc_id,changes)
def patch_device(device_id,changes):return edit_state('device',device_id,changes)
def patch_grant(grant_id,changes):return edit_state('grant',grant_id,changes)
def reset():
    with LOCK:
        for service in ['postgres','openbao','opa','keycloak','api','api-baseline','gateway']:
            if container(service).status!='running':start_service(service)
        (RT/'shared/lab-faults.json').write_text('{}')
        result=container('api').exec_run(['python','-m','app.bootstrap','reset'])
        if result.exit_code:raise RuntimeError('Fixture reset failed: '+result.output.decode()[-1800:])
        from .management import restore_employees_after_reset
        restore_employees_after_reset()
        return {'reset':True,'documents':20,'principals':len(rows('principals'))}
def inspect_storage(doc_id):
    with db() as conn:record=conn.execute('SELECT ciphertext,sha256 FROM documents WHERE id=%s',(doc_id,)).fetchone()
    if not record:raise ValueError('Unknown document')
    ciphertext=record['ciphertext'];text=ciphertext if isinstance(ciphertext,str) else str(ciphertext)
    dumped=container('postgres').exec_run(['pg_dump','-U','postgres','--data-only','--format=plain','bmdl'])
    if dumped.exit_code:raise RuntimeError('Database inspection failed')
    storage=dumped.output
    private_paths=container('api').exec_run(['python','-c',
        "import os,json;print(json.dumps({p:os.path.exists(p) for p in ['/runtime/secrets/bao-init.json','/runtime/secrets/config.json','/project/runtime/secrets','/runtime/pki/alice.key','/runtime/pki/server.key']}))"])
    if private_paths.exit_code:raise RuntimeError('Application mount inspection failed')
    mounts=json.loads(private_paths.output)
    secret_values=[_bao_root()['root_token'].encode(),(RT/'secrets/ca.key').read_bytes()]
    key_found=any(x in storage for x in secret_values) or b'PRIVATE KEY-----' in storage
    from app.db import fixture_payload
    expected_hash=hashlib.sha256(fixture_payload(doc_id)).hexdigest()
    token=(RT/'secrets/bao-app-token').read_text().strip()
    probes={}
    for name,method,path in [('read','GET','transit/keys/documents'),('rotate','POST','transit/keys/documents/rotate'),('export','GET','transit/export/encryption-key/documents')]:
        response=httpx.request(method,'http://openbao:8200/v1/'+path,headers={'X-Vault-Token':token},trust_env=False)
        probes[name]=response.status_code
    with db() as conn:db_role=conn.execute("SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname='bmdl_app'").fetchone()
    return {'ciphertext':text,'plaintext_present':b'BMDL synthetic fixture ' in storage or fixture_payload(doc_id) in storage,
            'key_material_present':bool(key_found),'app_kms_admin_allowed':any(v<400 for v in probes.values()),
            'app_kms_admin_http_status':probes['read'],'kms_permission_probes':probes,
            'sha256':record['sha256'],'expected_sha256':expected_hash,'database_dump_bytes_scanned':len(storage),
            'private_paths_visible_to_api':mounts,'db_role':dict(db_role)}
def tamper_ciphertext(doc_id):
    with LOCK,db() as conn:
        old=conn.execute('SELECT ciphertext FROM documents WHERE id=%s',(doc_id,)).fetchone()['ciphertext']
        parts=old.split(':');raw=bytearray(base64.b64decode(parts[-1]));raw[len(raw)//2]^=1
        parts[-1]=base64.b64encode(raw).decode();conn.execute('UPDATE documents SET ciphertext=%s WHERE id=%s',(':'.join(parts),doc_id))
    return {'doc_id':doc_id,'modified':True}
def probe_isolation():
    """Probe from an external client network, not the trusted controller networks."""
    dk=engine();network=dk.networks.get('bmdl_edge')
    probes={};inspection={}
    for name,port in [('api',8000),('api-baseline',8000),('postgres',5432),('opa',8181),('openbao',8200)]:
        target=container(name);inspection[name]=target.attrs['HostConfig'].get('PortBindings') or {}
        ips=[v['IPAddress'] for v in target.attrs['NetworkSettings']['Networks'].values() if v.get('IPAddress')]
        code='import socket,json; ips='+repr(ips)+'; r=[]\nfor ip in ips:\n s=socket.socket();s.settimeout(.5);r.append(s.connect_ex((ip,'+str(port)+'))==0);s.close()\nprint(json.dumps(any(r)))'
        output=dk.containers.run('bmdl-app:local',['python','-c',code],network=network.name,remove=True)
        probes[name]=json.loads(output.decode().strip())
    return {**probes,'published_internal_ports':any(bool(v) for v in inspection.values())}

def backup():
    from .recovery import backup as execute
    return execute()
def restore(snapshot_id):
    from .recovery import restore as execute
    return execute(snapshot_id)

if __name__=='__main__':
    import sys
    if sys.argv[1:] == ['init']:print(json.dumps(initialize()))
