from lab.client import LabClient
from federation.bootstrap import private
from lab import operations as ops
import json,time
c=LabClient()
for mode in ('F0','F1','F2'):
 r=c.request('p_alice','GET','/documents',mode=mode)
 print(mode,r.status_code,r.headers.get('x-policy-reason'),len(r.json().get('documents',[])) if isinstance(r.json(),dict)else len(r.json()))
 if not r.is_success:print(r.json())
print('Sessions',len(private('coordinator','/ops/state',method='GET')['sessions']))
c.close()
