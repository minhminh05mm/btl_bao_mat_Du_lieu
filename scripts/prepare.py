from pathlib import Path
from datetime import datetime,timedelta,timezone
import ipaddress,json,secrets,uuid
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12

ROOT=Path(__file__).resolve().parent.parent
runtime=ROOT/'runtime';pki=runtime/'pki';secret=runtime/'secrets'
for path in [pki,secret,runtime/'api-secrets',runtime/'pki-public',runtime/'shared/ledger',runtime/'shared/secrets',runtime/'shared/pki',runtime/'backups',ROOT/'results']:
    path.mkdir(parents=True,exist_ok=True)
configpath=secret/'config.json'
if configpath.exists():
    print('Existing local configuration preserved');raise SystemExit()
password=secrets.token_urlsafe(18)
config={'users':{u:password for u in ['alice','anna','adam','bob','bea','brian','auditor','secadmin']},
        'lab_password':password,'postgres_password':secrets.token_urlsafe(25),
        'app_db_password':secrets.token_urlsafe(25),'keycloak_admin_password':secrets.token_urlsafe(25),
        'proxy_secret':secrets.token_urlsafe(40),'restic_password':secrets.token_urlsafe(40)}
config['db_admin_url']=f"postgresql://postgres:{config['postgres_password']}@postgres:5432/bmdl"
config['db_app_url']=f"postgresql://bmdl_app:{config['app_db_password']}@postgres:5432/bmdl"
configpath.write_text(json.dumps(config,indent=2),encoding='utf-8')
(secret/'proxy-secret').write_text(config['proxy_secret'])
(secret/'restic-password').write_text(config['restic_password'])
(secret/'bao-app-token').write_text('initialization-pending')
(runtime/'shared/lab-faults.json').write_text('{}')
(runtime/'lab-faults.json').write_text('{}')
(ROOT/'.env').write_text(f"POSTGRES_PASSWORD={config['postgres_password']}\nKEYCLOAK_ADMIN_PASSWORD={config['keycloak_admin_password']}\nDATABASE_URL={config['db_app_url']}\n",encoding='utf-8')
(ROOT/'infra/postgres-init.sql').write_text(f"CREATE ROLE bmdl_app LOGIN PASSWORD '{config['app_db_password']}';\nGRANT CONNECT ON DATABASE bmdl TO bmdl_app;\nGRANT USAGE, CREATE ON SCHEMA public TO bmdl_app;\n",encoding='utf-8')
now=datetime.now(timezone.utc)
def make_ca(name):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,name)])
    cert=(x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=365))
          .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
          .add_extension(x509.KeyUsage(digital_signature=True,key_encipherment=False,key_cert_sign=True,crl_sign=True,
               content_commitment=False,data_encipherment=False,key_agreement=False,encipher_only=False,decipher_only=False),critical=True)
          .sign(key,hashes.SHA256()))
    return key,cert
ca_key,ca=make_ca('BMDL local laboratory CA')
(secret/'ca.key').write_bytes(ca_key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
(pki/'ca.crt').write_bytes(ca.public_bytes(serialization.Encoding.PEM))
def issue(name,ca_key,ca,server=False):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    cert=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,name)]))
          .issuer_name(ca.subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=90))
          .add_extension(x509.BasicConstraints(ca=False,path_length=None),True)
          .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH if server else x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH]),False))
    if server:cert=cert.add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'),x509.DNSName('gateway'),x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),False)
    cert=cert.sign(ca_key,hashes.SHA256())
    (pki/f'{name}.key').write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    (pki/f'{name}.crt').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    if not server:(pki/f'{name}.p12').write_bytes(pkcs12.serialize_key_and_certificates(name.encode(),key,cert,[ca],serialization.BestAvailableEncryption(password.encode())))
    return cert
issue('server',ca_key,ca,True)
registry={};users=[]
for username in config['users']:
    role='manager' if username in ['adam','brian'] else 'auditor' if username=='auditor' else 'security_admin' if username=='secadmin' else 'staff'
    dept='A' if username in ['alice','anna','adam'] else 'B' if username in ['bob','bea','brian'] else 'OPS'
    sub=str(uuid.uuid5(uuid.NAMESPACE_DNS,'bmdl:'+username));cert=issue(username,ca_key,ca)
    registry[username]={'serial':format(cert.serial_number,'X'),'subject_id':sub,'role':role,'department':dept}
    users.append({'id':sub,'username':username,'enabled':True,'emailVerified':True,'firstName':username,'lastName':'Lab',
                  'email':username+'@bmdl.test','attributes':{'b0_role':[role],'b0_department':[dept]},
                  'credentials':[{'type':'password','value':password,'temporary':False}]})
issue('rogue',ca_key,ca)
bad_key,bad_ca=make_ca('Untrusted lab test CA');issue('bad',bad_key,bad_ca)
(pki/'registry.json').write_text(json.dumps(registry,indent=2))
for name in ['bao-app-token','proxy-secret']:(runtime/'api-secrets'/name).write_bytes((secret/name).read_bytes())
for name in ['registry.json','ca.crt']:(runtime/'pki-public'/name).write_bytes((pki/name).read_bytes())
mappers=[{'name':'api-audience','protocol':'openid-connect','protocolMapper':'oidc-audience-mapper','config':{'included.custom.audience':'zt-api','access.token.claim':'true','id.token.claim':'false'}}]
for name in ['b0_role','b0_department']:
    mappers.append({'name':name,'protocol':'openid-connect','protocolMapper':'oidc-usermodel-attribute-mapper','config':{'user.attribute':name,'claim.name':name,'jsonType.label':'String','access.token.claim':'true','id.token.claim':'false'}})
realm={'realm':'bmdl','enabled':True,'sslRequired':'none','registrationAllowed':False,'accessTokenLifespan':300,
       'users':users,'clients':[
        {'clientId':'zt-web','enabled':True,'publicClient':True,'standardFlowEnabled':True,'directAccessGrantsEnabled':False,
         'redirectUris':['http://localhost:8088/auth/callback'],'webOrigins':['http://localhost:8088'],
         'attributes':{'pkce.code.challenge.method':'S256'},'protocolMappers':mappers},
        {'clientId':'zt-tests','enabled':True,'publicClient':True,'standardFlowEnabled':False,'directAccessGrantsEnabled':True,'protocolMappers':mappers}]}
(ROOT/'infra/keycloak-realm.json').write_text(json.dumps(realm,indent=2))
nginx='''events { worker_connections 512; }
http {
  server_tokens off;
  resolver 127.0.0.11 valid=1s ipv6=off;
  resolver_timeout 2s;
  upstream api_b1 { zone api_b1 64k; server api:8000 resolve; }
  upstream api_b0 { zone api_b0 64k; server api-baseline:8000 resolve; }
  upstream idp { zone idp 64k; server keycloak:8080 resolve; }
  log_format safe '$time_iso8601 $request_method $uri $status $request_time';
  access_log /var/log/nginx/access.log safe;
  client_max_body_size 2m;
  ssl_certificate /runtime/pki/server.crt;
  ssl_certificate_key /runtime/pki/server.key;
  ssl_protocols TLSv1.2 TLSv1.3;
  server {
    listen 9443 ssl;
    location / {
      proxy_pass http://idp;
      proxy_set_header Host localhost:9443;
      proxy_set_header X-Forwarded-Proto https;
      proxy_set_header X-Forwarded-Port 9443;
      proxy_set_header X-Forwarded-Host localhost:9443;
    }
  }
'''
for port,backend in [(8443,'api_b1'),(8444,'api_b0')]:
    nginx+=f'''  server {{
    listen {port} ssl;
    ssl_client_certificate /runtime/pki/ca.crt;
    ssl_verify_client on;
    ssl_verify_depth 2;
    location /api/ {{
      proxy_pass http://{backend}/;
      proxy_set_header X-Expected-Policy-Mode {'B1' if port==8443 else 'B0'};
      proxy_set_header X-Verified-Serial $ssl_client_serial;
      proxy_set_header X-Verified-TLS $ssl_client_verify;
      proxy_set_header X-Proxy-Secret {config['proxy_secret']};
      proxy_set_header X-Device-ID "";
      proxy_set_header X-Role "";
      proxy_set_header X-Department "";
      proxy_set_header X-Lab-Policy-Mode "";
    }}
  }}
'''
(ROOT/'infra/nginx.conf').write_text(nginx+'}\n')
print('Generated local PKI, realm and service credentials; secrets were not printed.')
