import json,secrets,traceback
from lab.management import create_employee
from lab import operations as ops
try:
    result=create_employee({'username':'demo_probe_'+secrets.token_hex(2),'display_name':'Nguyễn An (thử nghiệm)','password':secrets.token_urlsafe(24),'role':'staff','department':'A','active':True})
    print(json.dumps({'created':result['id']}))
except Exception as error:
    original=error.__context__ or error
    result={'error_type':type(original).__name__,'frames':[{'function':x.name,'line':x.lineno,'file':x.filename} for x in traceback.extract_tb(original.__traceback__)]}
    if hasattr(original,'response'):
        result['status']=original.response.status_code
        try:
            body=original.response.json()
            result['error']=body.get('error');result['description']=body.get('error_description') or body.get('errorMessage')
        except ValueError:pass
    print(json.dumps(result))
