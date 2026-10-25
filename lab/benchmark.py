"""Reproducible B0/B1 comparison; each observed value comes from a request."""
from pathlib import Path
from datetime import datetime,timezone
import csv,hashlib,json,math,time,uuid
from .client import LabClient
from . import operations
from .runner import _write_report
from tests.scenarios import run_oracle

def percentile(values,p):
    values=sorted(values)
    return values[max(0,math.ceil(len(values)*p)-1)] if values else None
def run_benchmark(progress=None,requests=200,repetitions=3,warmup=20):
    if not 10<=requests<=2000 or not 1<=repetitions<=5:raise ValueError('Workload outside lab limits')
    run_id=datetime.now(timezone.utc).strftime('benchmark-%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:6]
    folder=Path('/project/results')/run_id;folder.mkdir(parents=True,exist_ok=True)
    c=LabClient();samples=[];comparisons=[];decision_metrics={};performance=[]
    started=time.time()
    try:
        with operations.LOCK:
            for mode in ['B0','B1']:
                if progress:progress({'type':'phase','message':'Decision oracle '+mode})
                decisions=run_oracle(c,operations,mode=mode)
                for record in decisions:record['configuration']=mode
                comparisons.extend(decisions)
                allow=[x for x in decisions if x['expected']['allow']]
                deny=[x for x in decisions if not x['expected']['allow']]
                fa=sum(x.get('actual',{}).get('allow') is True for x in deny)
                fd=sum(x.get('actual',{}).get('allow') is False for x in allow)
                decision_metrics[mode]={'expected_allow':len(allow),'expected_deny':len(deny),'false_allow':fa,'false_deny':fd,
                    'false_allow_rate':fa/len(deny),'false_deny_rate':fd/len(allow),
                    'operational_errors':sum((x.get('actual',{}).get('status') or 0)>=500 for x in decisions)}
            operations.reset()
            from app.db import fixture_payload
            expected_hash=hashlib.sha256(fixture_payload('A-I01')).hexdigest()
            for repeat in range(1,repetitions+1):
                for mode in (['B0','B1'] if repeat%2 else ['B1','B0']):
                    for action in ['metadata','download']:
                        path=f'/documents/A-I01/{action}'
                        for _ in range(warmup):
                            response=c.request('alice','GET',path,mode=mode)
                            if response.status_code!=200:raise RuntimeError('Warmup request failed: '+str(response.status_code))
                        latencies=[];errors=0
                        for index in range(requests):
                            response=c.request('alice','GET',path,mode=mode)
                            elapsed=response.extensions['lab_latency_ms']
                            correct=response.status_code==200 and (action!='download' or hashlib.sha256(response.content).hexdigest()==expected_hash)
                            if not correct:errors+=1
                            latencies.append(elapsed)
                            samples.append({'mode':mode,'action':action,'repetition':repeat,'index':index,'status':response.status_code,
                               'latency_ms':round(elapsed,4),'body_bytes':len(response.content),'correct_content':correct,'request_id':response.headers.get('X-Request-ID')})
                        performance.append({'mode':mode,'action':action,'repetition':repeat,'n':requests,'warmup':warmup,'errors':errors,
                           'mean_ms':round(sum(latencies)/len(latencies),3),'p50_ms':round(percentile(latencies,.5),3),'p95_ms':round(percentile(latencies,.95),3)})
                        if progress:progress({'type':'measurement','completed':len(samples),'measurement':performance[-1]})
            records=[{'id':f"{r['configuration']}-{r['id']}",**{k:v for k,v in r.items() if k!='id'}} for r in comparisons]
            summary={'run_id':run_id,'started_at':started,'finished_at':time.time(),'duration_seconds':round(time.time()-started,3),
                'decision_metrics':decision_metrics,'performance':performance,'request_samples':len(samples),
                'method':{'seed':123,'requests_per_action_configuration_repeat':requests,'warmup':warmup,'repetitions':repetitions,
                  'concurrency':1,'percentile':'nearest rank','document':'A-I01','transport':'TLS verified + real client certificate','identity':'real Keycloak JWT cached after login',
                  'order':'alternate configuration order across repetitions','data_and_crypto':'same PostgreSQL ciphertext and OpenBao key for B0/B1'},
                'scope':'B0 is a deliberately weak local role/department snapshot baseline; not Google/Microsoft performance.',
                'total_errors':sum(r['errors'] for r in performance)}
            _write_report(folder,records,summary)
            with (folder/'latency-samples.csv').open('w',newline='',encoding='utf-8-sig') as f:
                writer=csv.DictWriter(f,fieldnames=list(samples[0]));writer.writeheader();writer.writerows(samples)
            with (folder/'performance-summary.csv').open('w',newline='',encoding='utf-8-sig') as f:
                writer=csv.DictWriter(f,fieldnames=list(performance[0]));writer.writeheader();writer.writerows(performance)
            (folder/'environment.json').write_text(json.dumps({'docker':operations.engine().version(),'images':[{x:ct.attrs.get(x) for x in ['Name','Image']} for ct in operations.engine().containers.list(filters={'label':'com.docker.compose.project=bmdl'})]},indent=2))
            return {'run_id':run_id,'summary':summary,'results':records}
    finally:c.close()

if __name__=='__main__':
    r=run_benchmark(progress=lambda e:print(json.dumps(e),flush=True))
    print(json.dumps(r['summary'],indent=2));raise SystemExit(1 if r['summary']['total_errors'] else 0)
