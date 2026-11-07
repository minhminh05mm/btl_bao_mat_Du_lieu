"""End-to-end checks against real TLS gateways and independently stored authorities."""
import base64,csv,hashlib,html,io,json,os,re,tarfile,time,uuid
from pathlib import Path
import httpx,psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict,make_conninfo
from .bootstrap import private
from .common import tls_client,verify_proof,validate_snapshot,FederationError,PARTNER_ISSUER,mint_proof
from lab.client import LabClient
from lab import operations as ops

ROOT=Path('/project');RT=Path('/runtime');MODES=('F0','F1','F2')
def why(r):
    try:d=r.json().get('detail',{})
    except Exception:d={}
    return r.headers.get('x-policy-reason')or(d.get('reason')if isinstance(d,dict)else None)
def evidence(r):return {'status':r.status_code,'reason':why(r),'request_id':r.headers.get('x-request-id'),
    'bytes':len(r.content),'sha256':hashlib.sha256(r.content).hexdigest()if r.is_success else None,
    'latency_ms':round(r.extensions.get('lab_latency_ms',0),3),'at':time.time()}
def wait(check,timeout=7):
    end=time.monotonic()+timeout
    while True:
        value=check()
        if value:return value
        if time.monotonic()>=end:raise AssertionError('Không đạt điều kiện trước thời hạn '+str(timeout)+' giây')
        time.sleep(.15)
def state():return private('partner','/ops/state',method='GET')
def settled():return wait(lambda:not any(e['status']=='pending'for e in state()['events']))
def pchange(kind,target,patch):return private('partner','/ops/'+('principals'if kind=='principal'else'devices')+'/'+target,patch,'PATCH')
def normal():
    private('partner','/ops/faults',{},'PUT');private('coordinator','/ops/config',{'cache_seconds':1,'poll_seconds':1},'PUT')
    pchange('principal','p_alice',{'active':True});pchange('device','dev-p_alice',{'compliant':True,'revoked':False,'risk':'NORMAL','auto_refresh':True,'observed_at':time.time(),'risk_at':time.time()})
    settled()
def login(c,modes=MODES,user='p_alice'):
    for mode in modes:
        r=c.request(user,'POST','/sessions',mode=mode);assert r.status_code==200,evidence(r)
def request(c,mode,path):return c.request('p_alice','GET',path,mode=mode)
def denied(r,reason=None,status=(401,403,503)):
    assert r.status_code in status,evidence(r)
    assert why(r)not in {None,'TRANSPORT_BLOCKED','SERVICE_UNAVAILABLE','AUDIT_UNAVAILABLE'},evidence(r)
    if reason:assert why(r)==reason,evidence(r)
    assert 'application/json'in r.headers.get('content-type',''),evidence(r)
    return evidence(r)

def restore_check(c):
    """Actual dump/restore into a uniquely named scratch database; never restore over a live DB."""
    engine=ops.engine();suffix=uuid.uuid4().hex[:10];dbname='bmdl_restore_'+suffix
    assert re.fullmatch('bmdl_restore_[a-f0-9]{10}',dbname)
    pg=ops.container('postgres');temp=RT/'federation'/('restore-'+suffix);temp.mkdir()
    container=None;created=False;dumpdir='/tmp/bmdl-restore-'+suffix
    sample=c._resource_sessions[('p_alice','p_alice','F2')]
    try:
        with ops.db()as conn:
            conn.autocommit=True
            conn.execute(sql.SQL('CREATE DATABASE {} OWNER bmdl_coordinator').format(sql.Identifier(dbname)));created=True
            conn.execute(sql.SQL('REVOKE CONNECT ON DATABASE {} FROM PUBLIC').format(sql.Identifier(dbname)))
        dumped=pg.exec_run(['pg_dump','-U','postgres','-d','bmdl_coordinator','-Fc','--no-owner','--no-acl'])
        assert dumped.exit_code==0,'pg_dump failed'
        pg.exec_run(['mkdir','-p',dumpdir])
        buffer=io.BytesIO()
        with tarfile.open(fileobj=buffer,mode='w')as tar:
            info=tarfile.TarInfo('coordinator.dump');info.size=len(dumped.output);tar.addfile(info,io.BytesIO(dumped.output))
        pg.put_archive(dumpdir,buffer.getvalue())
        restored=pg.exec_run(['pg_restore','-U','postgres','--role=bmdl_coordinator','-d',dbname,'--no-owner','--no-acl','--clean','--if-exists',dumpdir+'/coordinator.dump'])
        assert restored.exit_code==0,'pg_restore failed'
        original=(RT/'federation/coordinator/database-url').read_text()
        scratchdsn=make_conninfo(**{**conninfo_to_dict(original),'dbname':dbname})
        (temp/'database-url').write_text(scratchdsn)
        with psycopg.connect(scratchdsn)as conn:
            before=conn.execute('SELECT revoked FROM sessions WHERE id=%s',(sample['session']['id'],)).fetchone()
        assert before and before[0]is False,'Original active session absent from restored DB'
        hostroot=os.getenv('PROJECT_HOST_PATH','/mnt/e/btl_bao_mat_Du_lieu')
        mounts={hostroot+'/federation':{'bind':'/project/federation','mode':'ro'},hostroot+'/runtime/federation/coordinator':{'bind':'/runtime/service','mode':'ro'},
            hostroot+'/runtime/federation/public':{'bind':'/runtime/source-public','mode':'ro'},hostroot+'/runtime/pki/ca.crt':{'bind':'/runtime/pki/ca.crt','mode':'ro'},
            hostroot+'/runtime/federation/'+temp.name+'/database-url':{'bind':'/runtime/restore-url','mode':'ro'}}
        container=engine.containers.create('bmdl-app:local',name='bmdl-coordinator-restore-'+suffix,
            command=['uvicorn','federation.coordinator:app','--host','0.0.0.0','--port','8080','--ssl-keyfile','/runtime/service/server.key','--ssl-certfile','/runtime/service/server.crt','--no-access-log'],
            working_dir='/project',volumes=mounts,environment={'SERVICE_DATABASE_URL_FILE':'/runtime/restore-url','PYTHONDONTWRITEBYTECODE':'1'},
            network='bmdl_data',mem_limit='256m')
        engine.networks.get('bmdl_control').connect(container,aliases=['coordinator-restore']);container.start()
        def ready():
            try:
                with tls_client()as client:return client.get('https://coordinator-restore:8080/health').json().get('ready')
            except Exception:return False
        wait(ready,15)
        token=(RT/'federation/coordinator/api-token').read_text().strip()
        from cryptography import x509
        serial=format(x509.load_pem_x509_certificate((RT/'pki/p_alice.crt').read_bytes()).serial_number,'X')
        with tls_client()as client:
            response=client.post('https://coordinator-restore:8080/introspect',headers={'Authorization':'Bearer '+token},
                json={'resource_token':sample['resource_token'],'cert_serial':serial,'mode':'F2','phase':'recovery-check'})
        check=denied(response,'SESSION_SERVICE_RESTARTED',status=(401,))
        with psycopg.connect(scratchdsn)as conn:
            after=conn.execute('SELECT revoked,reason FROM sessions WHERE id=%s',(sample['session']['id'],)).fetchone()
        assert after==(True,'SESSION_SERVICE_RESTARTED')
        return {'dump_bytes':len(dumped.output),'dump_sha256':hashlib.sha256(dumped.output).hexdigest(),'scratch_database':dbname,
            'before_restore_boot':{'revoked':before[0]},'after_boot':{'revoked':after[0],'reason':after[1]},'introspection':check,'isolated':True}
    finally:
        if container:container.remove(force=True)
        if created:
            with ops.db()as conn:
                conn.autocommit=True
                conn.execute('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s',(dbname,))
                conn.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(dbname)))
        pg.exec_run(['rm','-rf',dumpdir]) # fixed /tmp prefix plus UUID, inside disposable scratch directory
        (temp/'database-url').unlink(missing_ok=True);temp.rmdir()

def run(progress=lambda event:None):
    started=time.time();cases=[];c=LabClient();doc=None;expected=b'Federation verification: synthetic document.\n';path=None
    initial_sessions={s['id']for s in private('coordinator','/ops/state',method='GET')['sessions']}
    original_p=state();original_c=private('coordinator','/ops/state',method='GET')['config']
    original_u=next(u for u in original_p['identities']if u['id']=='p_alice')
    original_d=next(d for d in original_p['devices']if d['id']=='dev-p_alice')
    operator_faults=ops.state()['faults']
    def case(identifier,name,fn):
        progress({'message':identifier+' · '+name});at=time.time()
        try:
            data=fn();cases.append({'id':identifier,'name':name,'pass':True,'duration_seconds':round(time.time()-at,3),'evidence':data,'summary':'Đúng điều kiện và phản hồi yêu cầu.'})
        except Exception as error:
            cases.append({'id':identifier,'name':name,'pass':False,'duration_seconds':round(time.time()-at,3),'error':type(error).__name__+': '+str(error)[:1000]})
    try:
        for name in ('opa_response_invalid','audit_write_failure','registry_unavailable'):ops.set_fault(name,False)
        normal();login(c)
        created=c.request('p_alice','POST','/documents',mode='F2',json={'title':'federation-verification-'+uuid.uuid4().hex[:8]+'.txt','label':'internal','content_b64':base64.b64encode(expected).decode()})
        assert created.status_code==200 or created.status_code==201,evidence(created)
        doc=created.json()['id'];path='/documents/'+doc+'/download'
        def k01():
            rows={}
            for mode in MODES:
                r=request(c,mode,path);assert r.status_code==200 and r.content==expected,evidence(r);rows[mode]=evidence(r)
            return {'requests':rows,'same_policy':'B1','expected_sha256':hashlib.sha256(expected).hexdigest()}
        case('K01','Cùng quyền tài liệu, ba chế độ đều tải đúng nội dung',k01)
        def k02():
            login(c,MODES,user='r_bob');rows={}
            for mode in MODES:
                rows[mode]=denied(c.request('r_bob','GET',path,mode=mode),'DEPARTMENT',status=(403,))
            return rows
        case('K02','Quyền tài liệu tại R vẫn được kiểm tra trong mọi chế độ',k02)
        def k03():
            normal();login(c);jwt=c.token('p_alice');old_sessions={m:c.session('p_alice',mode=m)['id']for m in MODES}
            changed=pchange('principal','p_alice',{'active':False});settled()
            old_token_provider=c.token
            def forbidden_token_refresh(*args,**kwargs):raise AssertionError('Held resource session unexpectedly called IdP login')
            c.token=forbidden_token_refresh
            try:rows={m:request(c,m,path)for m in MODES}
            finally:c.token=old_token_provider
            assert rows['F0'].status_code==200 and rows['F0'].content==expected,evidence(rows['F0'])
            for m in ('F1','F2'):denied(rows[m],'SOURCE_ACCOUNT_DISABLED',status=(403,))
            import jwt as jw
            claims=jw.decode(jwt,options={'verify_signature':False})
            assert claims['exp']>time.time()
            return {'source_changed_at':changed['source_changed_at'],'jwt_still_unexpired':True,'jwt_expires_at':claims['exp'],'sessions':old_sessions,'requests':{m:evidence(r)for m,r in rows.items()}}
        case('K03','Khóa nguồn thu hồi F1/F2 dù JWT và phiên còn hạn',k03)
        def reopen():
            pchange('principal','p_alice',{'active':True});settled()
            old=denied(request(c,'F2',path),'SOURCE_ACCOUNT_DISABLED',status=(403,))
            login(c,('F2',));new=request(c,'F2',path);assert new.content==expected and new.status_code==200,evidence(new)
            return {'old_session':old,'new_session':evidence(new)}
        case('K03b','Mở khóa không phục hồi phiên cũ; đăng nhập mới được phép',reopen)
        def k04():
            normal();login(c);changed=pchange('device','dev-p_alice',{'revoked':True});settled()
            out={m:request(c,m,path)for m in MODES};assert out['F0'].status_code==200 and out['F0'].content==expected
            for m in ('F1','F2'):denied(out[m],'SOURCE_DEVICE_REVOKED',status=(403,))
            return {'source_changed_at':changed['source_changed_at'],'requests':{m:evidence(r)for m,r in out.items()}}
        case('K04','Thu hồi thiết bị làm mất hiệu lực phiên đúng người',k04)
        def k05():
            normal();login(c);private('partner','/ops/faults',{'drop_events':True},'PUT');changed=pchange('principal','p_alice',{'active':False});settled()
            wait(lambda:any(s['id']==c.session('p_alice',mode='F2')['id']and s['revoked']for s in private('coordinator','/ops/state',method='GET')['sessions']))
            out={m:request(c,m,path)for m in MODES}
            for m in ('F0','F1'):assert out[m].status_code==200 and out[m].content==expected,evidence(out[m])
            denied(out['F2'],'SOURCE_ACCOUNT_DISABLED',status=(403,))
            return {'source_changed_at':changed['source_changed_at'],'event_lost':True,'requests':{m:evidence(r)for m,r in out.items()}}
        case('K05','Mất sự kiện: F1 giữ phiên, F2 đối soát và chặn',k05)
        def k06():
            normal();private('coordinator','/ops/config',{'cache_seconds':1,'poll_seconds':1,'disable_poll':True},'PUT');login(c)
            private('partner','/ops/faults',{'source_unavailable':True},'PUT');time.sleep(1.2)
            out={m:request(c,m,path)for m in MODES}
            for m in ('F0','F1'):assert out[m].status_code==200 and out[m].content==expected,evidence(out[m])
            denied(out['F2'],'SOURCE_UNAVAILABLE',status=(503,))
            return {'cache_seconds':1,'poll_disabled':True,'requests':{m:evidence(r)for m,r in out.items()}}
        case('K06','Nguồn không phản hồi: F2 dừng khi trạng thái hết độ mới',k06)
        def k07():
            normal();private('partner','/ops/faults',{'pause_events':True},'PUT')
            first=pchange('principal','p_alice',{'active':False});second=pchange('principal','p_alice',{'active':True})
            proofs=[private('partner','/ops/events/'+e['event_id']+'/proof',method='GET')['proof']for e in (first,second)]
            with tls_client()as client:
                def send(proof):return client.post('https://coordinator:8080/events',json={'proof':proof})
                valid=send(proofs[1]);assert valid.json()['outcome']=='applied'
                duplicate=send(proofs[1]);assert duplicate.json()['outcome']=='duplicate'
                old=send(proofs[0]);assert old.json()['outcome']=='stale'
                a,b,z=proofs[1].split('.');bad=send(a+'.'+b+'.'+('A'if z[0]!='A'else'B')+z[1:]);denied(bad,'SOURCE_PROOF_INVALID',status=(401,))
            private('partner','/ops/faults',{},'PUT');settled()
            return {'newer':valid.json(),'duplicate':duplicate.json(),'older':old.json(),'forged':evidence(bad)}
        case('K07','Sự kiện giả bị loại; trùng và sai thứ tự không hồi sinh phiên',k07)
        def k08():normal();login(c,('F2',));return restore_check(c)
        case('K08','Phục hồi cơ sở dữ liệu thật vào môi trường riêng không phục hồi phiên cũ',k08)
        def binding():
            normal();login(c,('F2',));raw=c.request('p_alice','GET',path,mode='F2',token=c.token('p_alice'),raw_token=True)
            a=denied(raw,'RESOURCE_SESSION_REQUIRED',status=(401,))
            mismatch=c.request('p_alice','POST','/sessions',mode='F2',device='p_adam');b=denied(mismatch,'DEVICE_MISMATCH',status=(403,))
            held=c._resource_sessions[('p_alice','p_alice','F2')]['resource_token']
            wrongmode=c.request('p_alice','GET',path,mode='F0',token=held,raw_token=True);d=denied(wrongmode,'SESSION_MODE_MISMATCH',status=(401,))
            return {'jwt_without_resource_session':a,'wrong_device':b,'wrong_gateway_mode':d}
        case('S01','Không vượt qua bằng JWT thô, chứng thư khác hoặc cổng khác chế độ',binding)
        def ownership():
            token=c.token('r_secadmin')
            with tls_client()as client:
                r=client.patch('https://partner:8080/admin/principals/p_alice',json={'active':False},headers={'Authorization':'Bearer '+token})
                denied(r,'PARTNER_ADMIN_REQUIRED',status=(403,))
                r2=client.patch('https://partner:8080/admin/principals/r_bob',json={'active':False},headers={'Authorization':'Bearer '+c.token('p_admin')})
                denied(r2,'PARTNER_OBJECT_NOT_FOUND',status=(404,))
                selflock=client.patch('https://partner:8080/admin/principals/p_admin',json={'active':False},headers={'Authorization':'Bearer '+c.token('p_admin')})
                denied(selflock,'SOURCE_SELF_LOCK_FORBIDDEN',status=(409,))
            login(c,('F2',),user='p_admin');r3=c.request('p_admin','GET','/admin/state',mode='F2');denied(r3,'ROLE',status=(403,))
            login(c,('F2',),user='r_secadmin');r4=c.request('r_secadmin','PUT','/admin/devices/dev-p_alice',mode='F2',json={'revoked':True});denied(r4,'PARTNER_DEVICE_AUTHORITY_REQUIRED',status=(403,))
            return {'resource_admin_cannot_manage_source':evidence(r),'source_cannot_manage_R':evidence(r2),'source_admin_has_no_resource_admin':evidence(r3),'resource_cannot_change_P_device':evidence(r4)}
        case('S02','Tách quyền quản trị nguồn P và tài nguyên R',ownership)
        def dbisolation():
            checks=[]
            for dsn,dbname in [(os.environ['DATABASE_URL'],'bmdl_partner'),(os.environ['DATABASE_URL'],'bmdl_coordinator'),((RT/'federation/partner/database-url').read_text(),'bmdl')]:
                with psycopg.connect(dsn,connect_timeout=3)as own:
                    own_database=own.execute('SELECT current_database(),current_user').fetchone()
                params=conninfo_to_dict(dsn);params['dbname']=dbname
                try:
                    with psycopg.connect(make_conninfo(**params),connect_timeout=3)as conn:conn.execute('SELECT 1')
                except psycopg.Error as e:
                    # libpq connect-time FATAL errors need not expose sqlstate.
                    # Match the explicit admission failure, never a generic socket/auth error.
                    permission_message=f'permission denied for database "{dbname}"'in str(e).lower()
                    assert e.sqlstate=='42501'or permission_message,{'reason':'Not a database permission rejection','sqlstate':e.sqlstate}
                    checks.append({'role':params['user'],'database':dbname,'blocked':True,'sqlstate':e.sqlstate,
                        'reason':'CONNECT_PRIVILEGE_DENIED','own_database_connection_verified':True,'own_database':own_database[0]})
                else:raise AssertionError('Cross-authority database access was allowed')
            return checks
        case('S03','Tài khoản dịch vụ không được đọc cơ sở dữ liệu của miền kia',dbisolation)
        def stale():
            normal();private('partner','/ops/faults',{'drop_events':True},'PUT')
            pchange('device','dev-p_alice',{'auto_refresh':False,'observed_at':time.time()-90,'risk_at':time.time()-90});settled()
            r=c.request('p_alice','POST','/sessions',mode='F2');return denied(r,'SOURCE_OBSERVATION_STALE',status=(403,))
        case('S04','Ký trạng thái mới không làm mới một quan sát thiết bị đã cũ',stale)
        def fast_reenable():
            normal();private('coordinator','/ops/config',{'disable_poll':True,'cache_seconds':1},'PUT');login(c)
            private('partner','/ops/faults',{'drop_events':True},'PUT');pchange('principal','p_alice',{'active':False});pchange('principal','p_alice',{'active':True});settled();time.sleep(1.2)
            return denied(request(c,'F2',path),'SOURCE_STATE_CHANGED',status=(403,))
        case('S05','Khóa rồi mở nhanh giữa hai lần đối soát vẫn thu hồi phiên cũ',fast_reenable)
        def nonce():
            normal()
            from .common import read_secret
            from cryptography import x509
            sn=format(x509.load_pem_x509_certificate((RT/'pki/p_alice.crt').read_bytes()).serial_number,'X')
            u=next(u for u in state()['identities']if u['id']=='p_alice');n=uuid.uuid4().hex
            with tls_client()as client:
                r=client.post('https://partner:8080/eligibility',json={'subject':u['subject_id'],'cert_serial':sn,'nonce':n},headers={'Authorization':'Bearer '+read_secret(RT/'federation/partner/source-read-token')})
            s=verify_proof(r.json()['proof'],RT/'federation/public/partner.pub',PARTNER_ISSUER,kind='state')
            checks=[]
            for args,expected_reason in [({'nonce':'wrongnonce0123456789'},'SOURCE_NONCE_MISMATCH'),({'subject':'another-subject'},'SOURCE_BINDING_MISMATCH'),({'organization':'R'},'SOURCE_BINDING_MISMATCH'),({'device_serial':'1'},'DEVICE_MISMATCH')]:
                try:validate_snapshot(s,**{'subject':u['subject_id'],'device_serial':sn,'organization':'P','nonce':n,**args})
                except FederationError as e:assert e.reason==expected_reason;checks.append(e.reason)
                else:raise AssertionError('Invalid source binding accepted')
            return {'validation_rejections':checks,'signed_state_observed_at':s['observed_at'],'signed_state_issued_at':s['iat']}
        case('S06','Kiểm tra nonce, đúng người, đúng miền và đúng chứng thư',nonce)
        def failures():
            normal();login(c,('F2',));rows={}
            for fault,reason in [('opa_response_invalid','PDP_INVALID'),('audit_write_failure','AUDIT_UNAVAILABLE')]:
                try:
                    ops.set_fault(fault,True);r=request(c,'F2',path)
                    assert r.status_code==503 and why(r)==reason and r.content!=expected,evidence(r)
                    rows[fault]=evidence(r)
                finally:ops.set_fault(fault,False)
            target=ops.container('openbao')
            try:
                target.pause();r=request(c,'F2',path)
                assert r.status_code==503 and why(r)=='KMS_UNAVAILABLE'and r.content!=expected,evidence(r)
                rows['kms_paused']=evidence(r)
            finally:target.unpause()
            return {'dependency_failures':rows,'not_counted_as_policy_denials':True}
        case('S07','Lỗi chính sách, nhật ký hoặc mã hóa đều dừng yêu cầu và không trả nội dung',failures)
        def tamper_state():
            normal();private('partner','/ops/faults',{'tamper_state':True},'PUT')
            try:return denied(c.request('p_alice','POST','/sessions',mode='F2'),'SOURCE_PROOF_INVALID',status=(401,))
            finally:private('partner','/ops/faults',{},'PUT')
        case('S08','Bằng chứng trạng thái bị sửa chữ ký không tạo được phiên',tamper_state)
        def regression():
            normal();login(c,('F2',));login(c,('F2',),user='r_auditor');login(c,('F2',),user='r_secadmin')
            audit=c.request('r_auditor','GET','/audit',mode='F2');alerts=c.request('r_auditor','GET','/alerts',mode='F2')
            assert audit.status_code==200 and alerts.status_code==200
            manager=LabClient()
            try:
                from lab.management import create_document,update_document,grant_document
                create=create_document({'filename':'restricted-demo.txt','title':'restricted-demo-'+uuid.uuid4().hex[:6],
                    'label':'restricted','owner_id':'p_adam','approver_id':'r_secadmin','ttl_seconds':120,'content_b64':base64.b64encode(expected).decode()})
                update=update_document(create['id'],{'title':create['title'],'label':'restricted','actor_id':'p_adam',
                    'legal_hold':create['legal_hold'],'retention_until':create['retention_until']})
                loaded=manager.request('p_adam','GET','/documents/'+create['id']+'/download',mode='F2');assert loaded.status_code==200 and loaded.content==expected,evidence(loaded)
            finally:manager.close()
            return {'audit':evidence(audit),'alerts':evidence(alerts),'restricted_document_created':create['id'],'edit_success':update['id'],'download':evidence(loaded)}
        case('R01','Tạo, sửa, tải tài liệu Hạn chế và đọc audit/cảnh báo vẫn hoạt động',regression)
        def new_employee():
            from lab.management import create_employee,known_users,update_employee
            import secrets
            name='case_resource_user'
            if name not in known_users():
                member=create_employee({'username':name,'display_name':'Nhân viên kiểm chứng','password':'Bmdl-'+secrets.token_urlsafe(12)+'9',
                    'organization':'R','role':'staff','department':'A','active':True})
                assert not member.get('registration_pending'),member
            update_employee(name,{'display_name':'Nhân viên kiểm chứng','role':'staff','department':'A','active':True})
            assert not any(u['id']==name for u in state()['identities'])
            login(c,('F2',),user=name);allowed=c.request(name,'GET',path,mode='F2');assert allowed.status_code==200 and allowed.content==expected,evidence(allowed)
            try:
                update_employee(name,{'display_name':'Nhân viên kiểm chứng','role':'staff','department':'B','active':True})
                blocked=c.request(name,'GET',path,mode='F2');denied(blocked,'DEPARTMENT',status=(403,))
            finally:update_employee(name,{'display_name':'Nhân viên kiểm chứng','role':'staff','department':'A','active':True})
            return {'new_resource_member':name,'absent_from_partner_database':True,'before_role_change':evidence(allowed),'after_role_change':evidence(blocked)}
        case('R02','Thêm nhân viên R và đổi quyền hiện tại có hiệu lực với phiên đang dùng',new_employee)
    finally:
        try:
            private('partner','/ops/faults',{},'PUT')
            pchange('principal','p_alice',{'active':original_u['active']})
            pchange('device','dev-p_alice',{k:original_d[k]for k in ('compliant','revoked','risk','auto_refresh')})
            settled();private('partner','/ops/faults',original_p['faults'],'PUT');private('coordinator','/ops/config',original_c,'PUT')
        except Exception as e:cases.append({'id':'CLEANUP','name':'Khôi phục cấu hình sau kiểm chứng','pass':False,'error':type(e).__name__})
        for name in ('opa_response_invalid','audit_write_failure','registry_unavailable'):
            ops.set_fault(name,bool(operator_faults.get(name,False)))
        try:
            for session in private('coordinator','/ops/state',method='GET')['sessions']:
                if session['id']not in initial_sessions and session['created_at']>=started and not session['revoked']:
                    private('coordinator','/ops/invalidate',{'session_id':session['id']})
        except Exception:cases.append({'id':'SESSION_CLEANUP','name':'Thu hồi phiên kiểm chứng','pass':False,'error':'SESSION_CLEANUP_FAILED'})
        c.close()
    finished=time.time()
    versions={}
    import importlib.metadata
    for name in ('fastapi','uvicorn','httpx','PyJWT','psycopg','cryptography'):
        versions[name]=importlib.metadata.version(name)
    import platform
    result={'schema':'federation-evidence-v1','started_at':started,'finished_at':finished,'duration_seconds':round(finished-started,3),
        'passed':sum(c['pass']for c in cases),'total':len(cases),'policy':'B1 for all F0/F1/F2','versions':{'python':platform.python_version(),**versions},
        'test_document':doc,'scope':'New requests in a local two-authority prototype; shared Keycloak and host; no real vendor cloud integration.', 'cases':cases}
    folder=ROOT/'results';folder.mkdir(exist_ok=True);stem='federation-'+time.strftime('%Y%m%d-%H%M%S',time.gmtime(finished))
    raw=json.dumps(result,ensure_ascii=False,indent=2)
    for name in (stem,'federation-latest'):(folder/(name+'.json')).write_text(raw)
    output=io.StringIO();writer=csv.writer(output);writer.writerow(['case','name','pass','duration_seconds','summary'])
    for item in cases:writer.writerow([item['id'],item['name'],item['pass'],item.get('duration_seconds'),item.get('summary')or item.get('error')])
    for name in (stem,'federation-latest'):(folder/(name+'.csv')).write_text('\ufeff'+output.getvalue())
    page='<!doctype html><meta charset="utf-8"><title>Kiểm chứng truy cập liên miền</title><style>body{font:15px Segoe UI;max-width:1100px;margin:35px auto;line-height:1.6}article{border:1px solid #ddd;padding:16px;margin:14px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}.pass{color:#17804e}.fail{color:#ac3838}</style><h1>Kết quả kiểm chứng liên miền</h1><p>'+str(result['passed'])+'/'+str(result['total'])+' ca đạt. Cùng chính sách tài liệu B1.</p><p>'+html.escape(json.dumps(result['versions']))+'</p>'
    for item in cases:page+='<article><h2 class="'+('pass'if item['pass']else'fail')+'">'+html.escape(item['id']+' · '+item['name'])+' · '+('Đạt'if item['pass']else'Không đạt')+'</h2><pre>'+html.escape(json.dumps(item.get('evidence',item.get('error')),ensure_ascii=False,indent=2))+'</pre></article>'
    for name in (stem,'federation-latest'):(folder/(name+'.html')).write_text(page)
    progress({'message':str(result['passed'])+'/'+str(result['total'])+' ca đạt; đã lưu JSON, CSV và HTML.'})
    return result

if __name__=='__main__':
    result=run(lambda e:print(e['message'],flush=True));print(json.dumps({'passed':result['passed'],'total':result['total']}))
    if result['passed']!=result['total']:raise SystemExit(1)
