from pathlib import Path
p=Path(__file__).resolve().parent.parent/'infra/nginx.conf'
t=p.read_text()
if 'upstream api_b1' not in t:
    t=t.replace('server_tokens off;', '''server_tokens off;
  resolver 127.0.0.11 valid=1s ipv6=off;
  resolver_timeout 2s;
  upstream api_b1 { zone api_b1 64k; server api:8000 resolve; }
  upstream api_b0 { zone api_b0 64k; server api-baseline:8000 resolve; }
  upstream idp { zone idp 64k; server keycloak:8080 resolve; }''')
    t=t.replace('proxy_pass http://keycloak:8080;','proxy_pass http://idp;')
    t=t.replace('proxy_pass http://api:8000/;','proxy_pass http://api_b1/;\n      proxy_set_header X-Expected-Policy-Mode B1;')
    t=t.replace('proxy_pass http://api-baseline:8000/;','proxy_pass http://api_b0/;\n      proxy_set_header X-Expected-Policy-Mode B0;')
    p.write_text(t)
print('Gateway DNS and policy-mode binding updated; no credentials printed.')
