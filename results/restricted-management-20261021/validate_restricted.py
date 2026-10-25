import base64,json,time
from pathlib import Path
import httpx
from lab.client import LabClient
from lab import operations as ops

out=Path('/project/results/restricted-management-20261021');out.mkdir(parents=True,exist_ok=True)
results=[];client=LabClient();web=httpx.Client(base_url='http://lab:8088',timeout=30,trust_env=False)
boot=web.get('/lab/bootstrap').json();web.headers.update({'x-lab-csrf':boot['csrf'],'origin':'http://localhost:8088'})
content=base64.b64encode('Tài liệu tổng hợp để kiểm tra quyền tải và sửa.\n'.encode()).decode()
def test(name,condition,**evidence):
    results.append({'test':name,'passed':bool(condition),**evidence})
    if not condition:raise AssertionError(name+': '+str(evidence))
def body(actor='adam',label='restricted',**extra):
    return {'filename':'kiem_tra_han_che.txt','title':'Kiểm tra quyền Hạn chế 21-10','owner_id':actor,'label':label,'content_b64':content,**extra}
def update(doc,actor='adam',**extra):
    return {'actor_id':actor,'title':doc['title'],'label':doc['label'],'retention_until':doc['retention_until'],'legal_hold':doc['legal_hold'],**extra}
def direct(user,method,path,**kwargs):return client.request(user,method,path,**kwargs)
def approval(**kw):
    r=direct('secadmin','POST','/admin/restricted-approvals',json={'principal_id':'adam','ttl_seconds':900,**kw});test('Approval authenticated by security admin',r.status_code==200,status=r.status_code);return r.json()
before=len(ops.rows('documents'))
created=[]
try:
    r=web.post('/lab/documents',json=body('alice'))
    test('Staff cannot create restricted document',r.status_code==403 and 'owner_id' in r.json()['detail']['fields'],status=r.status_code)
    r=web.post('/lab/documents',json=body())
    test('Manager needs explicit approver',r.status_code==403 and 'approver_id' in r.json()['detail']['fields'],status=r.status_code)
    r=direct('adam','POST','/documents',json={'title':'khong_phe_duyet.txt','label':'restricted','content_b64':content})
    test('Business API rejects restricted upload without approval',r.status_code==403 and r.headers.get('x-policy-reason')=='RESTRICTED_APPROVAL',status=r.status_code)
    test('Denied creates do not save documents',len(ops.rows('documents'))==before)
    r=web.post('/lab/documents',json=body(approver_id='secadmin',ttl_seconds=900))
    test('Restricted upload saves directly with approved label',r.status_code==200 and r.json()['label']=='restricted' and r.json()['version']==1,status=r.status_code)
    doc=r.json();created.append(doc['id'])
    r=direct('adam','GET',f"/documents/{doc['id']}/download")
    test('Creator can download immediately',r.status_code==200 and r.content==base64.b64decode(content),status=r.status_code)
    r=web.put('/lab/documents/'+doc['id'],json=update(doc,title='Kiểm tra quyền Hạn chế đã sửa'))
    test('Live download permission allows metadata edit',r.status_code==200 and 'đã sửa' in r.json()['title'],status=r.status_code)
    doc=r.json()
    for actor in ['alice','brian','secadmin','auditor']:
        r=web.put('/lab/documents/'+doc['id'],json=update(doc,actor=actor,title='Không được ghi'))
        test('Disallowed editor '+actor,r.status_code==403,status=r.status_code)
    r=web.put('/lab/documents/'+doc['id'],json=update(doc,label='internal'))
    test('Restricted content cannot be downgraded through editor',r.status_code==403,status=r.status_code)
    for changed in [{'legal_hold':True},{'retention_until':doc['retention_until']+86400}]:
        r=web.put('/lab/documents/'+doc['id'],json=update(doc,**changed))
        test('Download permission cannot change lifecycle '+next(iter(changed)),r.status_code==403 and r.json()['detail']['reason']=='LIFECYCLE_ADMIN_REQUIRED',status=r.status_code)
    r=web.post('/lab/documents/'+doc['id']+'/grants',json={'principal_id':'brian','approver_id':'secadmin','ttl_seconds':900})
    test('Grant form rejects cross-department manager',r.status_code==403 and 'principal_id' in r.json()['detail']['fields'],status=r.status_code)
    grants=[g for g in ops.rows('grants') if g['doc_id']==doc['id']]
    grant=grants[-1]
    r=web.request('DELETE',f"/lab/documents/{doc['id']}/grants/{grant['id']}",json={'approver_id':'secadmin'})
    test('Explicit approver can revoke document permission',r.status_code==200,status=r.status_code)
    for method,path,payload in [('GET',f"/documents/{doc['id']}/download",None),('PUT',f"/documents/{doc['id']}",{k:v for k,v in update(doc).items() if k!='actor_id'})]:
        r=direct('adam',method,path,json=payload)
        test('Revocation blocks '+method,r.status_code==403 and r.headers.get('x-policy-reason')=='RESTRICTED_GRANT',status=r.status_code)
    r=direct('adam','GET',f"/documents/{doc['id']}/metadata")
    test('Metadata visibility does not imply download/edit permission',r.status_code==200,status=r.status_code)
    r=direct('adam','PUT',f"/documents/{doc['id']}",json={k:v for k,v in update(doc).items() if k!='actor_id'},mode='B0')
    test('B0 cannot bypass mutation permission',r.status_code==403,status=r.status_code)
    r=web.post('/lab/documents/'+doc['id']+'/grants',json={'principal_id':'adam','approver_id':'secadmin','ttl_seconds':900})
    test('Grant panel can restore download and edit permission',r.status_code==200,status=r.status_code)
    currentgrant=r.json()
    r=web.put('/lab/documents/'+doc['id'],json=update(doc,title='Kiểm tra quyền Hạn chế 21-10'))
    test('Edit works after grant is restored',r.status_code==200,status=r.status_code);doc=r.json()
    with ops.db() as conn:conn.execute('UPDATE grants SET expires_at=%s WHERE id=%s',(time.time()-1,currentgrant['id']))
    r=web.put('/lab/documents/'+doc['id'],json=update(doc))
    test('Expired grant blocks edit with actionable error',r.status_code==403 and 'actor_id' in r.json()['detail']['fields'] and 'Quyền tải và sửa' in r.json()['detail']['message'],status=r.status_code)
    r=web.post('/lab/documents/'+doc['id']+'/grants',json={'principal_id':'adam','approver_id':'secadmin','ttl_seconds':900});test('Restore usable test document',r.status_code==200,status=r.status_code)
    a=approval()
    r=direct('brian','POST','/documents',json={'title':'sai_nguoi.txt','label':'restricted','content_b64':content,'approval_id':a['id']})
    test('Creation approval is bound to approved principal',r.status_code==403,status=r.status_code)
    count=len(ops.rows('documents'))
    originalfault=ops.set_fault('audit_write_failure',True)
    try:
        r=direct('adam','POST','/documents',json={'title':'rollback.txt','label':'restricted','content_b64':content,'approval_id':a['id']})
        test('Audit failure rejects creation',r.status_code==503,status=r.status_code)
    finally:ops.set_fault('audit_write_failure',False)
    test('Failed creation leaves no partial document',len(ops.rows('documents'))==count)
    r=direct('adam','POST','/documents',json={'title':'phe_duyet_mot_lan.txt','label':'restricted','content_b64':content,'approval_id':a['id']})
    test('Rolled-back approval remains usable for a successful retry',r.status_code==200,status=r.status_code);created.append(r.json()['id'])
    r=direct('adam','POST','/documents',json={'title':'lap_lai.txt','label':'restricted','content_b64':content,'approval_id':a['id']})
    test('Consumed approval cannot be replayed',r.status_code==403,status=r.status_code)
    a=approval()
    with ops.db() as conn:conn.execute('UPDATE restricted_approvals SET expires_at=%s WHERE id=%s',(time.time()-1,a['id']))
    r=direct('adam','POST','/documents',json={'title':'het_han.txt','label':'restricted','content_b64':content,'approval_id':a['id']})
    test('Expired creation approval rejected',r.status_code==403,status=r.status_code)
    r=web.post('/lab/documents',json=body(label='confidential',title='Tài liệu kiểm tra nâng nhãn'))
    test('Ordinary upload remains usable',r.status_code==200,status=r.status_code);ordinary=r.json();created.append(ordinary['id'])
    a=approval(doc_id=ordinary['id'])
    r=direct('adam','POST','/documents',json={'title':'sai_muc_dich.txt','label':'restricted','content_b64':content,'approval_id':a['id']})
    test('Upgrade approval cannot be used for new upload',r.status_code==403,status=r.status_code)
    r=web.put('/lab/documents/'+ordinary['id'],json=update(ordinary,label='restricted',approver_id='secadmin',ttl_seconds=900))
    test('Label upgrade binds grant to new document version',r.status_code==200 and r.json()['version']==ordinary['version']+1 and r.json()['label']=='restricted',status=r.status_code)
    test('Upgraded restricted document receives shorter retention limit',r.json()['retention_until']<=time.time()+30*86400)
    r=direct('adam','GET',f"/documents/{ordinary['id']}/download")
    test('Approved upgrade remains downloadable',r.status_code==200,status=r.status_code)
    test('Existing documents retained',len(ops.rows('documents'))==before+len(created))
finally:
    client.close();web.close()
    output={'total':len(results),'passed':sum(x['passed'] for x in results),'failed':sum(not x['passed'] for x in results),'created_documents':created,'checks':results}
    (out/'validation.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in output.items() if k!='checks'},ensure_ascii=False))
