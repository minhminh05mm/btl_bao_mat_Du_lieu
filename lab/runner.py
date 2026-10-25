"""Run real tests and write redacted, reproducible evidence files."""
from pathlib import Path
from datetime import datetime,timezone
import csv,html,json,re,time,uuid,statistics
from .client import LabClient
from . import operations
from tests import scenarios

RESULTS=Path('/project/results')
def _write_report(folder,records,summary):
    folder.mkdir(parents=True,exist_ok=True)
    result={'results':operations.safe(records),'summary':operations.safe(summary)}
    (folder/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    columns=['id','group','name','passed','expected','actual','request_id','latency_ms','evidence']
    with (folder/'results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for row in records:writer.writerow({k:json.dumps(row.get(k),ensure_ascii=False) if isinstance(row.get(k),(dict,list)) else row.get(k,'') for k in columns})
    cells=lambda r:''.join('<td>'+html.escape(str(r.get(k,'')))+'</td>' for k in columns)
    content='<!doctype html><meta charset="utf-8"><title>Kết quả kiểm thử</title><style>body{font:14px system-ui;margin:30px}td,th{border:1px solid #cbd5e1;padding:8px;text-align:left;vertical-align:top}table{border-collapse:collapse}pre{white-space:pre-wrap}</style><h1>Kết quả kiểm thử Zero Trust</h1><pre>'+html.escape(json.dumps(summary,ensure_ascii=False,indent=2))+'</pre><table><tr>'+''.join('<th>'+k+'</th>' for k in columns)+'</tr>'+''.join('<tr>'+cells(r)+'</tr>' for r in records)+'</table>'
    (folder/'report.html').write_text(content,encoding='utf-8')
    return result

def run_suite(cases=None,progress=None):
    run_id=datetime.now(timezone.utc).strftime('run-%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:6]
    folder=RESULTS/run_id;folder.mkdir(parents=True,exist_ok=True)
    client=LabClient();started=time.time();count=0
    original=scenarios.Suite.check
    def checked(suite,*args,**kwargs):
        nonlocal count
        record=original(suite,*args,**kwargs);count+=1
        if progress:progress({'type':'case','completed':count,'id':record['id'],'passed':record['passed'],'result':record})
        return record
    with operations.LOCK:
        scenarios.Suite.check=checked
        try:
            if isinstance(cases,dict):cases=cases['cases']
            records=scenarios.run_suite(client,operations) if cases is None else scenarios.run_oracle(client,operations,cases)
        finally:
            scenarios.Suite.check=original;client.close()
        native=operations.container('opa').exec_run(['/opa','test','/policies','-v'])
        native_text=native.output.decode(errors='replace');(folder/'opa-tests.txt').write_text(native_text)
        native_count=len(re.findall(r': PASS',native_text))
        records.append({'id':'OPA-native','group':'unit-policy','name':'Kiểm thử Rego bằng OPA thật','expected':'all pass','actual':{'exit_code':native.exit_code,'tests':native_count},'passed':native.exit_code==0,'request_id':None,'latency_ms':None})
        unit=operations.container('lab').exec_run(['python','-m','pytest','tests/test_auth_verifier.py','tests/test_oracle.py','tests/test_scenario_harness.py','tests/test_fixture_data.py','tests/test_fixture_seed.py','-k','not real_architecture_scenarios','-q','--disable-warnings'])
        unit_text=unit.output.decode(errors='replace');(folder/'identity-tests.txt').write_text(unit_text)
        records.append({'id':'JWT-native','group':'unit-identity','name':'Xác minh token, hợp đồng kiểm thử và dữ liệu nghiệp vụ tổng hợp','expected':'all pass','actual':{'exit_code':unit.exit_code},'passed':unit.exit_code==0,'request_id':None,'latency_ms':None})
    allowed=[r for r in records if isinstance(r.get('expected'),dict) and r['expected'].get('allow') is True]
    denied=[r for r in records if isinstance(r.get('expected'),dict) and r['expected'].get('allow') is False]
    false_allow=sum(r.get('actual',{}).get('allow') is True for r in denied if isinstance(r.get('actual'),dict))
    false_deny=sum(r.get('actual',{}).get('allow') is False for r in allowed if isinstance(r.get('actual'),dict))
    summary={'run_id':run_id,'started_at':started,'finished_at':time.time(),'duration_seconds':round(time.time()-started,3),
       'total':len(records),'passed':sum(r['passed'] for r in records),'failed':sum(not r['passed'] for r in records),
       'expected_allow_count':len(allowed),'expected_deny_count':len(denied),
       'false_allow':false_allow,'false_deny':false_deny,
       'false_allow_rate':false_allow/len(denied) if denied else None,'false_deny_rate':false_deny/len(allowed) if allowed else None,
       'scope':'Real gateway/JWT/mTLS/OPA/Transit/PostgreSQL; synthetic fixtures; unit tests reported separately',
       'output_dir':str(folder)}
    result=_write_report(folder,records,summary);result['run_id']=run_id
    (RESULTS/'latest.json').write_text(json.dumps({'run_id':run_id,'summary':summary},ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':
    result=run_suite(progress=lambda e:print(json.dumps(e,ensure_ascii=False),flush=True))
    print(json.dumps(result['summary'],ensure_ascii=False,indent=2))
    raise SystemExit(1 if result['summary']['failed'] else 0)
