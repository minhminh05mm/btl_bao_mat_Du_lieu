"""Idempotent trusted-local installation. Never executed inside resource API."""
import json, os, secrets, sys, time
from pathlib import Path
from datetime import datetime, timedelta, timezone
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from .common import tls_client, IDENTITY_ISSUER

ROOT=Path('/project'); RT=Path('/runtime'); BASE=RT/'federation'

def put(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():path.write_bytes(data if isinstance(data,bytes)else data.encode())
    path.chmod(0o644)

def prepare():
    cfg=json.loads((RT/'secrets/config.json').read_text())
    ca=x509.load_pem_x509_certificate((RT/'pki/ca.crt').read_bytes())
    ca_key=serialization.load_pem_private_key((RT/'secrets/ca.key').read_bytes(),password=None)
    for name in ('partner','coordinator','resource','public'):(BASE/name).mkdir(parents=True,exist_ok=True)
    for owner in ('partner','resource'):
        keyfile=BASE/owner/'signing.key'
        if not keyfile.exists():
            key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
            put(keyfile,key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        key=serialization.load_pem_private_key(keyfile.read_bytes(),password=None)
        put(BASE/'public'/f'{owner}.pub',key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
    for service in ('partner','coordinator'):
        if not (BASE/service/'server.crt').exists():
            key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
            now=datetime.now(timezone.utc)
            cert=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,service)]))
                .issuer_name(ca.subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now-timedelta(minutes=5)).not_valid_after(now+timedelta(days=365))
                .add_extension(x509.SubjectAlternativeName([x509.DNSName(service),x509.DNSName(service+'-restore')]),False)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),False).sign(ca_key,hashes.SHA256()))
            put(BASE/service/'server.key',key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
            put(BASE/service/'server.crt',cert.public_bytes(serialization.Encoding.PEM))
    for name,owners in [('source-read-token',('partner','coordinator')),('api-token',('resource','coordinator')),
                        ('resource-read-token',('resource','coordinator')),('ops-token',('partner',)),('ops-token',('coordinator',))]:
        existing=next((BASE/o/name for o in owners if (BASE/o/name).exists()),None)
        value=existing.read_text()if existing else secrets.token_urlsafe(48)
        for owner in owners:put(BASE/owner/name,value)
    admin=conninfo_to_dict(cfg['db_admin_url'])
    with psycopg.connect(cfg['db_admin_url'],autocommit=True)as conn:
        for owner in ('partner','coordinator'):
            role='bmdl_'+owner; database=role
            passwordfile=BASE/owner/'db-password';put(passwordfile,secrets.token_urlsafe(36));password=passwordfile.read_text()
            if not conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone():
                conn.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)))
            if not conn.execute('SELECT 1 FROM pg_database WHERE datname=%s',(database,)).fetchone():
                conn.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(database),sql.Identifier(role)))
            conn.execute(sql.SQL('REVOKE CONNECT ON DATABASE {} FROM PUBLIC').format(sql.Identifier(database)))
            dsn=make_conninfo(**{**admin,'user':role,'password':password,'dbname':database})
            put(BASE/owner/'database-url',dsn)
        conn.execute('REVOKE CONNECT ON DATABASE bmdl FROM PUBLIC')
        conn.execute('GRANT CONNECT ON DATABASE bmdl TO bmdl_app')
    gateway(cfg['proxy_secret'])
    print('Federation keys, private databases and gateway prepared; no existing data reset.')

def gateway(proxy_secret):
    text='''events { worker_connections 512; }
http {
  resolver 127.0.0.11 valid=5s ipv6=off;
  log_format safe '$time_iso8601 $request_method $uri $status';
  access_log /var/log/nginx/access.log safe;
  server_tokens off;
  client_max_body_size 2m;
  ssl_certificate /runtime/pki/server.crt;
  ssl_certificate_key /runtime/pki/server.key;
  ssl_protocols TLSv1.2 TLSv1.3;
  server {
    listen 9443 ssl;
    location = /federation-resource-state {
      set $resource http://api:8000;
      proxy_pass $resource/internal/federation-state;
      proxy_set_header Authorization $http_authorization;
    }
    location / { set $idp http://keycloak:8080; proxy_pass $idp;
      proxy_set_header Host localhost:9443;
      proxy_set_header X-Forwarded-Proto https;
      proxy_set_header X-Forwarded-Host localhost:9443;
      proxy_set_header X-Forwarded-Port 9443;
    }
  }
'''
    for port,mode in ((8443,'F2'),(8444,'F0'),(8445,'F1')):
        text+=f'''  server {{
    listen {port} ssl;
    ssl_client_certificate /runtime/pki/ca.crt;
    ssl_verify_client on;
    ssl_verify_depth 2;
    location /api/internal/ {{ return 404; }}
    location /api/ {{
      set $resource http://api:8000;
      rewrite ^/api/(.*)$ /$1 break;
      proxy_pass $resource;
      proxy_set_header Authorization $http_authorization;
      proxy_set_header X-Verified-Serial $ssl_client_serial;
      proxy_set_header X-Verified-TLS $ssl_client_verify;
      proxy_set_header X-Verified-Federation-Mode {mode};
      proxy_set_header X-Expected-Policy-Mode B1;
      proxy_set_header X-Proxy-Secret {proxy_secret};
      proxy_read_timeout 25s;
    }}
  }}
'''
    (ROOT/'infra/nginx.conf').write_text(text+'}\n')

def private(service,path,body=None,method='POST'):
    token=(BASE/service/'ops-token').read_text().strip()
    with tls_client()as client:
        r=client.request(method,'https://'+service+':8080'+path,headers={'Authorization':'Bearer '+token},json=body)
    r.raise_for_status();return r.json()

def register(identifier,organization=None):
    from lab import operations as ops
    with ops.db()as conn:
        user=conn.execute('SELECT * FROM principals WHERE id=%s',(identifier,)).fetchone()
        dev=conn.execute('SELECT * FROM devices WHERE principal_id=%s ORDER BY id LIMIT 1',(identifier,)).fetchone()
        org=organization or user['organization']
        conn.execute('UPDATE principals SET organization=%s WHERE id=%s',(org,identifier))
        if org!=user.get('organization'):ops._ledger('principal',identifier,{'organization':org,'updated_at':time.time()})
    if org=='P':
        private('partner','/ops/register',{'id':user['id'],'username':user['username'],'subject_id':user['subject_id'],
            'organization':'P','active':user['active'],'partner_admin':user['role']=='partner_admin',
            'cert_serial':dev['cert_serial'],'device_id':dev['id']})
    private('coordinator','/ops/register',{'principal_id':user['id'],'username':user['username'],
        'subject_id':user['subject_id'],'organization':org})

def seed():
    from lab import management as mg, operations as ops
    for attempt in range(90):
        try:
            with tls_client() as client:
                for name in ('partner','coordinator'):
                    response=client.get('https://'+name+':8080/health')
                    response.raise_for_status()
                    if not response.json().get('ready'):raise RuntimeError('Not ready')
            with ops.db() as conn:conn.execute('SELECT organization FROM principals LIMIT 1')
            from lab.client import LabClient
            probe=LabClient()
            try:probe.token('alice')
            finally:probe.close()
            break
        except Exception:
            if attempt==89:raise RuntimeError('Federation services are not ready') from None
            time.sleep(1)
    fixtures=[('p_alice','Nhân viên đối tác','staff','A','P'),('p_adam','Trưởng phòng đối tác','manager','A','P'),
        ('p_admin','Quản trị đối tác','partner_admin','OPS','P'),('r_bob','Nhân viên kho','staff','B','R'),
        ('r_secadmin','Quản trị kho','security_admin','OPS','R'),('r_auditor','Kiểm toán kho','auditor','OPS','R')]
    known=mg.known_users()
    for username,name,role,department,org in fixtures:
        if username not in known:
            mg.create_employee({'username':username,'display_name':name,'role':role,'department':department,
                'active':True,'password':'Bmdl-'+secrets.token_urlsafe(12)+'7','organization':org})
    for user in ops.rows('principals'):
        org='R'if user['username'].startswith('r_')else user.get('organization','P')
        register(user['id'],org)
    print('Source identities and trusted resource bindings registered; existing users retained.')

if __name__=='__main__':
    os.environ['FEDERATION_CA_FILE']=str(RT/'pki/ca.crt')
    {'prepare':prepare,'seed':seed}[sys.argv[1]]()
