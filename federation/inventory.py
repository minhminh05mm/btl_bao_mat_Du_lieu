"""Safe, reproducible environment inventory; no credentials or container env exported."""
from pathlib import Path
import hashlib,json,platform,subprocess,time
import importlib.metadata
from lab import operations as ops

def collect():
    result={'captured_at':time.time(),'python':platform.python_version(),'platform':platform.platform(),'libraries':{},'containers':[],'source_sha256':{}}
    for name in ('fastapi','uvicorn','httpx','PyJWT','psycopg','cryptography'):
        result['libraries'][name]=importlib.metadata.version(name)
    for service in ('postgres','keycloak','opa','openbao','api','gateway','partner','coordinator','lab'):
        c=ops.container(service);c.reload()
        result['containers'].append({'service':service,'status':c.status,'image_id':c.image.id,
            'image_reference':c.attrs['Config']['Image'],'repo_digests':c.image.attrs.get('RepoDigests',[]),
            'memory_limit_bytes':c.attrs['HostConfig'].get('Memory'),'networks':sorted(c.attrs['NetworkSettings']['Networks']),
            'mount_destinations':sorted(m['Destination']for m in c.attrs.get('Mounts',[]))})
    commands={'postgres':['postgres','--version'],'gateway':['nginx','-v'],'opa':['/opa','version'],
        'openbao':['bao','version'],'keycloak':['/opt/keycloak/bin/kc.sh','--version']}
    result['service_versions']={}
    for name,command in commands.items():
        r=ops.container(name).exec_run(command)
        result['service_versions'][name]=r.output.decode(errors='replace').strip()[:1000]if r.exit_code==0 else 'not available'
    for folder in ('app','federation','lab','policies'):
        for path in (ops.ROOT/folder).rglob('*'):
            if path.is_file()and path.suffix in {'.py','.rego','.js','.css','.html'}:
                result['source_sha256'][str(path.relative_to(ops.ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ('compose.yaml','compose.lock.yaml','requirements.lock.txt'):
        path=ops.ROOT/name
        if path.exists():result['source_sha256'][name]=hashlib.sha256(path.read_bytes()).hexdigest()
    (ops.ROOT/'results').mkdir(exist_ok=True)
    (ops.ROOT/'results/federation-environment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':
    r=collect();print(json.dumps({'inventoried_services':len(r['containers']),'hashed_files':len(r['source_sha256']),'service_versions':r['service_versions']}))
