"""Read-only sanitized inventory. Only the named manifest is written; no app imports."""
from __future__ import annotations
import argparse, ast, hashlib, importlib.metadata, json, platform, re, ssl
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICES = {'api','api-baseline','gateway','keycloak','lab','opa','openbao','postgres'}
PACKAGES = ('fastapi','uvicorn','psycopg','psycopg-binary','httpx','PyJWT','cryptography',
            'python-multipart','docker','pytest','Jinja2','psutil','pydantic','starlette')

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def result_path(value):
    p=Path(value); p=(p if p.is_absolute() else ROOT/p).resolve()
    if not p.is_relative_to((ROOT/'results').resolve()): raise ValueError('Path outside project/results')
    return p

def source_hashes():
    files=[]
    for directory in ['app','lab','tests','scripts','policies','fixtures']:
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts
                     and p.suffix in {'.py','.ps1','.sh','.rego','.json','.css','.js','.html'})
    for name in ['compose.yaml','compose.lock.yaml','requirements.txt','requirements.lock.txt','infra/Dockerfile',
                 'infra/images.lock.json','infra/openbao.hcl','infra/postgres-init.sql','Start-Demo.ps1','Stop-Demo.ps1','Run-Tests.ps1']:
        if (ROOT/name).exists(): files.append(ROOT/name)
    return {p.relative_to(ROOT).as_posix():digest(p) for p in sorted(set(files))}

def conditions():
    constants={}
    for node in ast.parse((ROOT/'app/config.py').read_text(encoding='utf-8-sig')).body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in {'POLICY_VERSION','SIGNAL_TTL','LABEL_DAYS'}:
                    constants[target.id]=ast.literal_eval(node.value)
    fixture=json.loads((ROOT/'fixtures/cases.json').read_text(encoding='utf-8-sig'))
    cases=fixture['cases'] if isinstance(fixture,dict) else fixture
    definitions={name:digest(ROOT/name) for name in ['app/db.py','app/fixture_data.py','tests/make_oracle.py'] if (ROOT/name).exists()}
    catalog_path=ROOT/'fixtures/dataset-manifest.json'
    catalog={}
    if catalog_path.exists():
        data=json.loads(catalog_path.read_text(encoding='utf-8-sig'))
        catalog={'path':'fixtures/dataset-manifest.json','sha256':digest(catalog_path),
            'dataset_version':data.get('dataset_version'),'document_count':len(data.get('items',[])),
            'document_id_content_sha256':canonical(sorted(
                [{'id':d['id'],'sha256':d['sha256']} for d in data.get('items',[])],key=lambda d:d['id']))}
    return {'source':'Static source/config; actual statistics are recorded in run.summary',
            'policy_constants':constants,'oracle_cases':len(cases),
            'dataset_definition_sha256':definitions,
            'dataset_catalog':catalog,
            'oracle_schema_version':fixture.get('schema_version') if isinstance(fixture,dict) else None,
            'oracle_expected_allow':sum(c.get('expected',{}).get('allow') is True for c in cases),
            'oracle_expected_deny':sum(c.get('expected',{}).get('allow') is False for c in cases),
            'oracle_sha256':digest(ROOT/'fixtures/cases.json'),
            'transport':'Real Keycloak JWT, TLS validation and client certificate through gateway',
            'declared_operator_condition':'One trusted local operator, no concurrent operator mutations',
            'limitations':['Simulated device/risk signals','Synthetic data; one shared physical host']}

def dataset():
    try:
        import psycopg
        from psycopg.rows import dict_row
        secret=json.loads(Path('/runtime/secrets/config.json').read_text())
        with psycopg.connect(secret['db_admin_url'],connect_timeout=5,row_factory=dict_row,
                              options='-c default_transaction_read_only=on') as conn:
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            readonly=conn.execute('SHOW transaction_read_only').fetchone()['transaction_read_only']=='on'
            version=conn.execute('SHOW server_version').fetchone()['server_version']
            seed=conn.execute("SELECT value FROM app_state WHERE key='seed_version'").fetchone()
            dataset_version=conn.execute("SELECT value FROM app_state WHERE key='dataset_version'").fetchone()
            docs=conn.execute('SELECT id,owner_id,department,label,version,legal_hold,deleted,sha256 FROM documents ORDER BY id').fetchall()
            principals=conn.execute('SELECT id,role,department,active,permission_version FROM principals ORDER BY id').fetchall()
            devices=conn.execute('SELECT id,principal_id,compliant,revoked,risk,auto_refresh FROM devices ORDER BY id').fetchall()
            grants=conn.execute('SELECT principal_id,doc_id,doc_version,action,revoked,approver FROM grants '
                               'ORDER BY principal_id,doc_id,doc_version,action,revoked,approver').fetchall()
        return {'status':'observed','transaction_read_only':readonly,'postgresql_server_version':version,
                'seed_version':seed['value'] if seed else None,
                'dataset_version':dataset_version['value'] if dataset_version else None,'document_count':len(docs),
                'active_documents':sum(not d['deleted'] for d in docs),'principals':len(principals),
                'active_principals':sum(p['active'] for p in principals),'devices':len(devices),'grants':len(grants),
                'documents_by_label':dict(Counter(d['label'] for d in docs)),
                'documents_by_department':dict(Counter(d['department'] for d in docs)),
                'document_id_content_sha256':canonical([{'id':d['id'],'sha256':d['sha256']} for d in docs]),
                'logical_state_sha256':canonical({'documents':docs,'principals':principals,'devices':devices,'grants':grants}),
                'hash_definition':'Sorted compact JSON. Content hash uses ID+stored plaintext SHA256. Logical state adds '
                  'ownership/labels/versions/rights/device flags/grants, excluding timestamps. No plaintext or full DB dump.'}
    except Exception as error:
        return {'status':'unknown','reason':type(error).__name__}

def version(container,command,pattern):
    try:
        result=container.exec_run(command)
        if result.exit_code: return {'status':'unknown','exit_code':result.exit_code}
        match=re.search(pattern,result.output.decode(errors='replace'),re.I)
        return {'status':'observed','value':match.group(1)} if match else {'status':'unknown','reason':'Unrecognized output'}
    except Exception as error: return {'status':'unknown','reason':type(error).__name__}

def services():
    import docker
    engine=docker.from_env(); observed=engine.version(); info=engine.info()
    runtime={k:observed.get(k) for k in ['Version','ApiVersion','Os','Arch','KernelVersion','GitCommit','GoVersion']}
    runtime.update(storage_driver=info.get('Driver'),cpus_available=info.get('NCPU'),memory_available_bytes=info.get('MemTotal'))
    inventory={}; versions={}
    commands={'postgres':(['postgres','--version'],r'PostgreSQL\)\s+([^\s]+)'),
              'keycloak':(['/opt/keycloak/bin/kc.sh','--version'],r'Keycloak\s+([^\s]+)'),
              'opa':(['/opa','version'],r'Version:\s*([^\s]+)'),
              'openbao':(['bao','version'],r'OpenBao\s+v([^\s]+)'),
              'gateway':(['nginx','-v'],r'nginx/([^\s]+)')}
    for ct in engine.containers.list(all=True,filters={'label':'com.docker.compose.project=bmdl'}):
        d=ct.attrs; name=d['Config']['Labels'].get('com.docker.compose.service')
        if name not in SERVICES: continue
        image=ct.image.attrs; host=d['HostConfig']
        inventory[name]={'container_name':ct.name,'state':d['State']['Status'],
            'created_at_utc':d.get('Created'),'started_at_utc':d['State'].get('StartedAt'),
            'configured_reference':d['Config']['Image'],'image_id':d['Image'],
            'repo_digests':image.get('RepoDigests',[]),'architecture':image.get('Architecture'),'os':image.get('Os'),
            'user':d['Config'].get('User'),'limits':{k:host.get(k) for k in
                ['Memory','MemorySwap','NanoCpus','CpuQuota','CpuPeriod','CpusetCpus']},
            'networks':sorted(d['NetworkSettings'].get('Networks',{})),
            'published_ports':host.get('PortBindings') or {},
            'mount_destinations':[{'destination':m['Destination'],'read_only':not m['RW']} for m in d['Mounts']]}
        if d['State']['Running'] and name in commands: versions[name]=version(ct,*commands[name])
        if d['State']['Running'] and name=='lab': versions['restic']=version(ct,['restic','version'],r'restic\s+([^\s]+)')
    runtime['networks']={n.name:{'driver':n.attrs.get('Driver'),'internal':n.attrs.get('Internal')}
        for n in engine.networks.list(filters={'label':'com.docker.compose.project=bmdl'})}
    return runtime,{'services':dict(sorted(inventory.items())),'versions':versions}

def run_provenance(run_id):
    path=ROOT/'results'/run_id/'results.json'
    if not path.exists(): return {'status':'pending','run_id':run_id}
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    allowed={'run_id','started_at','finished_at','duration_seconds','total','passed','failed','expected_allow_count',
             'expected_deny_count','false_allow','false_deny','false_allow_rate','false_deny_rate','scope',
             'request_samples','method','total_errors','decision_metrics'}
    return {'status':'observed','run_id':data['summary'].get('run_id'),'results_sha256':digest(path),
            'summary':{k:v for k,v in data['summary'].items() if k in allowed},'record_count':len(data['results'])}

def compare_before(path,report):
    before=json.loads(path.read_text(encoding='utf-8-sig')); old=before.get('source_sha256',{}); new=report['source_sha256']
    changed=sorted(k for k in old.keys()|new.keys() if old.get(k)!=new.get(k))
    images=lambda d:{k:v['image_id'] for k,v in d.get('containers',{}).get('services',{}).items()}
    return {'before_manifest':path.relative_to(ROOT).as_posix(),'before_manifest_sha256':digest(path),
        'before_captured_at_utc':before.get('captured_at_utc'),'source_unchanged':not changed,'changed_source_files':changed,
        'service_images_unchanged':images(before)==images(report),
        'dataset_content_unchanged':before.get('dataset',{}).get('document_id_content_sha256')==report['dataset'].get('document_id_content_sha256'),
        'logical_state_unchanged':before.get('dataset',{}).get('logical_state_sha256')==report['dataset'].get('logical_state_sha256'),
        'interpretation':'Suites intentionally mutate state. Differences are reported, never reset by capture.'}

def validate_manifest(report):
    errors=[]; warnings=[]; inventory=report.get('containers',{}).get('services',{})
    if set(inventory)!=SERVICES: errors.append('Incomplete primary service inventory')
    for name,item in inventory.items():
        if not re.fullmatch(r'sha256:[a-f0-9]{64}',item.get('image_id','')): errors.append('Missing concrete image ID: '+name)
        if item.get('state')!='running': errors.append('Service is not running: '+name)
    for section in ['host','engine','python','dependencies','source_sha256','dataset','test_conditions']:
        if not report.get(section): errors.append('Missing section: '+section)
    data=report.get('dataset',{})
    if data.get('status')!='observed' or not data.get('transaction_read_only'): errors.append('Dataset not observed read-only')
    catalog=report.get('test_conditions',{}).get('dataset_catalog',{})
    if catalog:
        mismatched=(data.get('dataset_version')!=catalog.get('dataset_version') or
                    data.get('document_id_content_sha256')!=catalog.get('document_id_content_sha256'))
        if mismatched:
            message='Live dataset differs from the static baseline catalog'
            (errors if report.get('phase')=='before' else warnings).append(message)
    for field in ['physical_memory_bytes','cpu_model']:
        if not report.get('host',{}).get('hardware',{}).get(field): warnings.append('Unknown host '+field)
    for name in ['postgres','keycloak','opa','openbao','gateway','restic']:
        if report.get('containers',{}).get('versions',{}).get(name,{}).get('status')!='observed': warnings.append('Unknown version: '+name)
    run=report.get('run',{})
    if report.get('phase')=='after' and run.get('status')!='observed': errors.append('After manifest has no results.json')
    if run.get('status')=='observed' and run.get('run_id')!=report.get('run_id'): errors.append('Run ID mismatch')
    comparison=report.get('comparison',{})
    if report.get('phase')=='after' and not comparison: warnings.append('No before manifest supplied')
    for key in ['source_unchanged','service_images_unchanged']:
        if comparison.get(key) is False: errors.append('Before/after mismatch: '+key)
    encoded=json.dumps(report)
    if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|Bearer\s+[A-Za-z0-9_.-]+|postgres(?:ql)?://[^\s\"]+',encoded):
        errors.append('Forbidden secret-shaped material; do not publish')
    return {'complete':not errors,'errors':errors,'warnings':warnings}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True); parser.add_argument('--phase',choices=['before','after','draft'],default='draft')
    parser.add_argument('--host-manifest',required=True); parser.add_argument('--before-manifest'); parser.add_argument('--output')
    args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,120}',args.run_id): parser.error('Unsafe run ID')
    host_path=result_path(args.host_manifest); output=result_path(args.output or f'results/{args.run_id}/environment.{args.phase}.json')
    if output.exists(): parser.error('Refusing to overwrite existing manifest')
    runtime,containers=services(); dependencies={}
    for name in PACKAGES:
        try: dependencies[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: dependencies[name]=None
    installed={}
    for package in importlib.metadata.distributions():
        name=package.metadata.get('Name',''); value=package.version
        if re.fullmatch(r'[A-Za-z0-9_.-]+',name) and re.fullmatch(r'[A-Za-z0-9_.+!-]+',value): installed[name]=value
    shared_image=containers['services'].get('lab',{}).get('image_id')
    report={'schema_version':2,'run_id':args.run_id,'phase':args.phase,
        'captured_at_utc':datetime.now(timezone.utc).isoformat(),'timezone_for_display':'Asia/Saigon',
        'host':json.loads(host_path.read_text(encoding='utf-8-sig')),'host_manifest_sha256':digest(host_path),
        'engine':runtime,'containers':containers,'python':{'version':platform.python_version(),
            'observed_in_service':'lab','same_image_services':sorted(k for k,v in containers['services'].items() if v['image_id']==shared_image),
            'implementation':platform.python_implementation(),'platform':platform.platform(),'machine':platform.machine(),
            'container_os':platform.freedesktop_os_release(),'openssl':ssl.OPENSSL_VERSION},
        'dependencies':dependencies,'installed_dependencies':dict(sorted(installed.items())),
        'dependency_lock_sha256':digest(ROOT/'requirements.lock.txt'),
        'source_sha256':source_hashes(),'dataset':dataset(),'test_conditions':conditions(),'run':run_provenance(args.run_id),
        'privacy':{'credentials_environment_dumped':False,'document_contents_dumped':False,
            'excluded':['.env','runtime/secrets','private keys','JWTs','database URLs',
                        'generated infra/nginx.conf and infra/keycloak-realm.json']}}
    if args.before_manifest: report['comparison']=compare_before(result_path(args.before_manifest),report)
    report['validation']=validate_manifest(report)
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(output),'run_id':args.run_id,'phase':args.phase,'validation':report['validation']}))
    return 0 if report['validation']['complete'] else 1
