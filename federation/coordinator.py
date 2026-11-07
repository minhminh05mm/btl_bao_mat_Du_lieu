"""Persistent, device-bound resource sessions and cross-domain revocation."""
from __future__ import annotations

import asyncio
import logging
import os
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from psycopg.types.json import Jsonb

from .common import (FederationError, IDENTITY_ISSUER, MODES, PARTNER_ISSUER,
                     RESOURCE_ISSUER, database, identity, install_error_handler,
                     number, read_secret, require_credential, serial, state_reason,
                     tls_client, token_hash, validate_snapshot, verify_proof, version)

SERVICE=Path(os.getenv('SERVICE_SECRET_DIR','/runtime/service'))
PUBLIC=Path(os.getenv('SOURCE_PUBLIC_DIR','/runtime/source-public'))
GENERATION=str(uuid.uuid4())
logger=logging.getLogger('bmdl.coordinator')
ready=False
SCHEMA='''
CREATE TABLE IF NOT EXISTS bindings (
 subject_id text PRIMARY KEY, identity_issuer text NOT NULL, principal_id text UNIQUE NOT NULL,
 username text UNIQUE NOT NULL, organization text NOT NULL CHECK(organization IN ('P','R'))
);
CREATE TABLE IF NOT EXISTS sessions (
 id text PRIMARY KEY, bearer_hash text UNIQUE NOT NULL, subject_id text NOT NULL REFERENCES bindings(subject_id),
 principal_id text NOT NULL, username text NOT NULL, organization text NOT NULL, mode text NOT NULL,
 cert_serial text NOT NULL, device_id text NOT NULL, created_at double precision NOT NULL,
 expires_at double precision NOT NULL, revoked boolean NOT NULL DEFAULT false, reason text,
 snapshot jsonb NOT NULL, verified_at double precision NOT NULL, valid_until double precision NOT NULL,
 generation text NOT NULL, revoked_at double precision, source_changed_at double precision
);
CREATE INDEX IF NOT EXISTS sessions_subject ON sessions(subject_id,mode,revoked);
CREATE TABLE IF NOT EXISTS source_versions (
 source text NOT NULL, subject_id text NOT NULL, entity_kind text NOT NULL, entity_id text NOT NULL,
 last_version bigint NOT NULL, PRIMARY KEY(source,subject_id,entity_kind,entity_id)
);
CREATE TABLE IF NOT EXISTS event_versions (
 source text NOT NULL, subject_id text NOT NULL, entity_kind text NOT NULL, entity_id text NOT NULL,
 last_version bigint NOT NULL, PRIMARY KEY(source,subject_id,entity_kind,entity_id)
);
CREATE TABLE IF NOT EXISTS events (
 event_id text PRIMARY KEY, source text NOT NULL, payload jsonb NOT NULL, received_at double precision NOT NULL,
 applied_at double precision NOT NULL, outcome text NOT NULL, affected integer NOT NULL
);
CREATE TABLE IF NOT EXISTS trace (
 id bigserial PRIMARY KEY, created_at double precision NOT NULL, kind text NOT NULL,
 session_id text, subject_id text, mode text, request_id text, reason text NOT NULL,
 details jsonb NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS settings (key text PRIMARY KEY,value jsonb NOT NULL);
'''


def record(kind,reason,*,session=None,subject=None,mode=None,request_id=None,details=None,conn=None):
    args=(time.time(),kind,session,subject,mode,request_id,reason,Jsonb(details or {}))
    statement='INSERT INTO trace(created_at,kind,session_id,subject_id,mode,request_id,reason,details)VALUES(%s,%s,%s,%s,%s,%s,%s,%s)'
    if conn is not None:
        conn.execute(statement,args)
    else:
        with database()as own:own.execute(statement,args)


def settings():
    result={'cache_seconds':5.0,'poll_seconds':5.0,'session_seconds':900.0,'disable_poll':False,'coordinator_unavailable':False}
    with database()as conn:
        row=conn.execute("SELECT value FROM settings WHERE key='config'").fetchone()
    if row:result.update(row['value'])
    return result


def initialize():
    with database()as conn:
        conn.execute(SCHEMA)
        # A restored DB cannot reactivate bearer sessions from another service boot.
        conn.execute("UPDATE sessions SET revoked=true,reason='SESSION_SERVICE_RESTARTED',revoked_at=%s WHERE revoked=false",(time.time(),))
        record('startup','SESSIONS_INVALIDATED',details={'generation':GENERATION},conn=conn)


def api_auth(request):require_credential(request,SERVICE/'api-token')
def ops_auth(request):require_credential(request,SERVICE/'ops-token')


def binding(subject):
    with database()as conn:
        row=conn.execute('SELECT * FROM bindings WHERE subject_id=%s',(subject,)).fetchone()
    if not row or row['identity_issuer']!=IDENTITY_ISSUER:
        raise FederationError('FEDERATION_SUBJECT_UNREGISTERED',401)
    return row


def remember_snapshot(conn,state):
    for kind,identifier,v in [('principal',state['principal_id'],state['subject_version']),
                              ('device',state['device_id'],state['device_version'])]:
        key=(state['iss'],state['sub'],kind,identifier)
        row=conn.execute('SELECT last_version FROM source_versions WHERE source=%s AND subject_id=%s AND entity_kind=%s AND entity_id=%s FOR UPDATE',key).fetchone()
        if row and v<row['last_version']:
            raise FederationError('SOURCE_VERSION_ROLLBACK',503)
        conn.execute('INSERT INTO source_versions(source,subject_id,entity_kind,entity_id,last_version)VALUES(%s,%s,%s,%s,%s) '
                     'ON CONFLICT(source,subject_id,entity_kind,entity_id)DO UPDATE SET last_version=GREATEST(source_versions.last_version,EXCLUDED.last_version)',(*key,v))


def fetch_state(member,cert_serial):
    nonce=secrets.token_urlsafe(24)
    partner=member['organization']=='P'
    url=os.getenv('PARTNER_URL','https://partner:8080')+'/eligibility' if partner else os.getenv('RESOURCE_STATE_URL','https://gateway:9443/federation-resource-state')
    credential=read_secret(SERVICE/('source-read-token'if partner else'resource-read-token'))
    try:
        with tls_client(timeout=4)as client:
            r=client.post(url,headers={'Authorization':'Bearer '+credential},json={
                'subject':member['subject_id'],'cert_serial':cert_serial,'nonce':nonce})
        if not r.is_success:
            reason=(r.json().get('detail')or{}).get('reason','SOURCE_UNAVAILABLE')
            raise FederationError(reason,r.status_code if r.status_code in {401,403,404}else 503)
        state=verify_proof(r.json()['proof'],PUBLIC/('partner.pub'if partner else'resource.pub'),
                           PARTNER_ISSUER if partner else RESOURCE_ISSUER,kind='state')
        validate_snapshot(state,subject=member['subject_id'],device_serial=cert_serial,
                          organization=member['organization'],nonce=nonce,require_eligible=False)
        if state.get('principal_id')!=member['principal_id'] or state.get('identity_issuer')!=member['identity_issuer']:
            raise FederationError('SOURCE_BINDING_MISMATCH',401)
        with database()as conn:remember_snapshot(conn,state)
        return state
    except FederationError:
        raise
    except Exception:
        raise FederationError('SOURCE_UNAVAILABLE',503)from None


def valid_until(state,config):
    return min(number(state['exp']),number(state['iat'])+config['cache_seconds'],
               number(state['observed_at'])+60,number(state['risk_at'])+60)


def revoke(subject,reason,*,device=None,modes=('F1','F2'),source_at=None,conn=None):
    def apply(c):
        args=[reason,time.time(),source_at,subject,list(modes)]
        tail=''
        if device is not None:tail=' AND device_id=%s';args.append(device)
        rows=c.execute('UPDATE sessions SET revoked=true,reason=%s,revoked_at=%s,source_changed_at=%s '
                       'WHERE subject_id=%s AND mode=ANY(%s) AND revoked=false'+tail+' RETURNING id,mode',args).fetchall()
        for row in rows:
            record('revocation',reason,session=row['id'],subject=subject,mode=row['mode'],
                   details={'source_changed_at':source_at,'device_id':device},conn=c)
        return len(rows)
    if conn is not None:return apply(conn)
    with database()as own:return apply(own)


def refresh_session(row,config,*,origin='request'):
    member=binding(row['subject_id'])
    state=fetch_state(member,row['cert_serial'])
    reason=state_reason(state)
    previous=row['snapshot']
    epoch_changed=(state['subject_epoch']!=previous['subject_epoch']or state['device_epoch']!=previous['device_epoch'])
    if reason or epoch_changed:
        reason=reason or 'SOURCE_STATE_CHANGED'
        # Polling/freshness is a property of F2; it must not repair F1's lost events.
        revoke(row['subject_id'],reason,
               device=None if not state['active']or state['subject_epoch']!=previous['subject_epoch']else state['device_id'],
               modes=('F2',),source_at=state.get('changed_at'))
        raise FederationError(reason)
    until=valid_until(state,config)
    if until<=time.time():raise FederationError('SOURCE_OBSERVATION_STALE')
    now=time.time()
    with database()as conn:
        conn.execute('UPDATE sessions SET snapshot=%s,verified_at=%s,valid_until=%s '
                     'WHERE id=%s AND revoked=false AND generation=%s',
                     (Jsonb(state),now,until,row['id'],GENERATION))
        record('source_refresh','SOURCE_VERIFIED',session=row['id'],subject=row['subject_id'],mode=row['mode'],
               details={'origin':origin,'observed_at':state['observed_at'],'issued_at':state['iat'],
                        'valid_until':until,'subject_version':state['subject_version'],'device_version':state['device_version']},conn=conn)


def public_session(row):
    snapshot=row['snapshot']
    return {k:row[k]for k in ('id','subject_id','principal_id','username','organization','mode','device_id',
            'created_at','expires_at','revoked','reason','verified_at','valid_until','revoked_at','source_changed_at')}|{
            'source':{'issuer':snapshot['iss'],'observed_at':snapshot['observed_at'],'issued_at':snapshot['iat'],
                      'subject_version':snapshot['subject_version'],'device_version':snapshot['device_version'],
                      'subject_epoch':snapshot['subject_epoch'],'device_epoch':snapshot['device_epoch'],
                      'active':snapshot['active'],'compliant':snapshot['compliant'],'risk':snapshot['risk']}}


def create_session(body):
    config=settings()
    if config['coordinator_unavailable']:raise FederationError('COORDINATOR_UNAVAILABLE',503)
    mode=body.get('mode')
    if mode not in MODES:raise FederationError('FEDERATION_MODE_INVALID',422)
    claims=identity(str(body.get('id_token','')))
    member=binding(claims['sub'])
    device_serial=serial(body.get('cert_serial'))
    state=fetch_state(member,device_serial)
    reason=state_reason(state)
    if reason:raise FederationError(reason)
    now=time.time();identifier=str(uuid.uuid4());token='rs_'+secrets.token_urlsafe(40)
    expiry=now+config['session_seconds'];until=valid_until(state,config)
    with database()as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',('event:'+claims['sub'],))
        if mode in {'F1','F2'}:
            events=conn.execute("SELECT payload FROM events WHERE payload->>'sub'=%s AND outcome='applied' ORDER BY applied_at DESC LIMIT 100",(claims['sub'],)).fetchall()
            for entry in events:
                e=entry['payload']
                relevant=e['entity_kind']=='principal'or e.get('device_id')==state['device_id']
                epoch=state['subject_epoch']if e['entity_kind']=='principal'else state['device_epoch']
                if relevant and e['source_epoch']>epoch:raise FederationError('SOURCE_STATE_CHANGED')
        conn.execute('INSERT INTO sessions(id,bearer_hash,subject_id,principal_id,username,organization,mode,cert_serial,'
                     'device_id,created_at,expires_at,snapshot,verified_at,valid_until,generation)'
                     'VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                     (identifier,token_hash(token),member['subject_id'],member['principal_id'],member['username'],member['organization'],
                      mode,device_serial,state['device_id'],now,expiry,Jsonb(state),now,until,GENERATION))
        record('login','RESOURCE_SESSION_CREATED',session=identifier,subject=claims['sub'],mode=mode,
               request_id=body.get('request_id'),details={'organization':member['organization'],'expires_at':expiry,
               'observed_at':state['observed_at'],'source_version':state['subject_version']},conn=conn)
        row=conn.execute('SELECT * FROM sessions WHERE id=%s',(identifier,)).fetchone()
    return {'resource_token':token,'session':public_session(row)}


def introspect(body):
    row=None
    try:
        config=settings()
        if config['coordinator_unavailable']:raise FederationError('COORDINATOR_UNAVAILABLE',503)
        token=str(body.get('resource_token',''))
        if not token.startswith('rs_'):raise FederationError('RESOURCE_SESSION_REQUIRED',401)
        with database()as conn:
            row=conn.execute('SELECT * FROM sessions WHERE bearer_hash=%s',(token_hash(token),)).fetchone()
        if not row:raise FederationError('RESOURCE_SESSION_INVALID',401)
        validate_session_row(row,body)
        if row['mode']=='F2'and time.time()>=row['valid_until']:
            refresh_session(row,config)
        with database()as conn:
            row=conn.execute('SELECT * FROM sessions WHERE id=%s FOR SHARE',(row['id'],)).fetchone()
            validate_session_row(row,body)
            if row['mode']=='F2'and time.time()>=row['valid_until']:
                raise FederationError('SOURCE_CONTEXT_EXPIRED',503)
            record('introspection','SESSION_VALID',session=row['id'],subject=row['subject_id'],mode=row['mode'],
                   request_id=body.get('request_id'),details={'phase':body.get('phase','request'),
                   'source_age_seconds':round(time.time()-row['snapshot']['observed_at'],3)},conn=conn)
        return {'session':public_session(row),'identity':{'sub':row['subject_id'],'iss':IDENTITY_ISSUER},
                'device':{'id':row['device_id'],'principal_id':row['principal_id'],
                          **{k:row['snapshot'][k]for k in ('compliant','revoked','risk','observed_at','risk_at')}}}
    except FederationError as error:
        record('introspection',error.reason,session=row['id']if row else None,
               subject=row['subject_id']if row else None,mode=row['mode']if row else body.get('mode'),
               request_id=body.get('request_id'),details={'phase':body.get('phase','request')})
        raise


def validate_session_row(row,body):
    if row['mode']!=body.get('mode'):raise FederationError('SESSION_MODE_MISMATCH',401)
    if row['cert_serial']!=serial(body.get('cert_serial')):raise FederationError('DEVICE_MISMATCH')
    if row['generation']!=GENERATION:raise FederationError('SESSION_SERVICE_RESTARTED',401)
    if row['revoked']:raise FederationError(row['reason']or'RESOURCE_SESSION_REVOKED')
    if time.time()>=row['expires_at']:raise FederationError('RESOURCE_SESSION_EXPIRED',401)


def apply_event(proof):
    event=verify_proof(proof,PUBLIC/'partner.pub',PARTNER_ISSUER,kind='event')
    required={'event_id','entity_kind','entity_id','state_version','organization','occurred_at','source_epoch'}
    if not required<=event.keys()or event['entity_kind']not in {'principal','device'}or event['organization']!='P':
        raise FederationError('EVENT_SCHEMA_INVALID',422)
    if not all(isinstance(event[k],str)and event[k]for k in ('event_id','entity_id')):
        raise FederationError('EVENT_SCHEMA_INVALID',422)
    if event['entity_kind']=='device' and event.get('device_id')!=event['entity_id']:
        raise FederationError('EVENT_SCHEMA_INVALID',422)
    if event['entity_kind']=='principal' and type(event.get('active'))is not bool:
        raise FederationError('EVENT_SCHEMA_INVALID',422)
    version(event['state_version']);version(event['source_epoch']);number(event['occurred_at'])
    if event['occurred_at']>time.time()+1:raise FederationError('SOURCE_CLOCK_INVALID',422)
    member=binding(event['sub'])
    if member['organization']!='P'or member['principal_id']!=event.get('principal_id')or event.get('identity_issuer')!=IDENTITY_ISSUER:
        raise FederationError('SOURCE_BINDING_MISMATCH',401)
    reason='SOURCE_STATE_CHANGED'
    if event.get('active')is False:reason='SOURCE_ACCOUNT_DISABLED'
    elif event.get('revoked')is True:reason='SOURCE_DEVICE_REVOKED'
    elif event.get('compliant')is False:reason='SOURCE_DEVICE_NONCOMPLIANT'
    elif event.get('risk')=='HIGH':reason='SOURCE_DEVICE_RISK'
    received=time.time()
    key=(event['iss'],event['sub'],event['entity_kind'],event['entity_id'])
    with database()as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',('event:'+event['sub'],))
        duplicate=conn.execute('SELECT outcome FROM events WHERE event_id=%s',(event['event_id'],)).fetchone()
        if duplicate:return {'outcome':'duplicate','affected':0}
        previous=conn.execute('SELECT last_version FROM event_versions WHERE source=%s AND subject_id=%s AND entity_kind=%s AND entity_id=%s',key).fetchone()
        stale=previous and event['state_version']<=previous['last_version']
        affected=0
        if not stale:
            conn.execute('INSERT INTO event_versions(source,subject_id,entity_kind,entity_id,last_version)VALUES(%s,%s,%s,%s,%s)'
                         'ON CONFLICT(source,subject_id,entity_kind,entity_id)DO UPDATE SET last_version=EXCLUDED.last_version',(*key,event['state_version']))
            affected=revoke(event['sub'],reason,device=event.get('device_id')if event['entity_kind']=='device'else None,
                            source_at=event['occurred_at'],conn=conn)
        applied=time.time();outcome='stale'if stale else'applied'
        conn.execute('INSERT INTO events(event_id,source,payload,received_at,applied_at,outcome,affected)VALUES(%s,%s,%s,%s,%s,%s,%s)',
                     (event['event_id'],event['iss'],Jsonb(event),received,applied,outcome,affected))
        record('event',outcome.upper(),subject=event['sub'],details={'event_id':event['event_id'],
               'source_changed_at':event['occurred_at'],'received_at':received,'applied_at':applied,'affected':affected},conn=conn)
    return {'outcome':outcome,'affected':affected,'received_at':received,'applied_at':applied}


async def reconcile():
    while True:
        try:
            config=await asyncio.to_thread(settings)
            if not config['disable_poll']and not config['coordinator_unavailable']:
                with database()as conn:
                    rows=conn.execute("SELECT * FROM sessions WHERE mode='F2'AND revoked=false AND expires_at>%s ORDER BY verified_at LIMIT 100",(time.time(),)).fetchall()
                for row in rows:
                    try:await asyncio.to_thread(refresh_session,row,config,origin='reconciliation')
                    except FederationError as error:
                        await asyncio.to_thread(record,'reconciliation',error.reason,session=row['id'],subject=row['subject_id'],mode='F2')
            delay=config['poll_seconds']
        except Exception:
            logger.warning('Reconciliation unavailable');delay=1
        await asyncio.sleep(delay)


@asynccontextmanager
async def lifespan(app):
    global ready
    for attempt in range(90):
        try:await asyncio.to_thread(initialize);break
        except Exception:
            if attempt==89:raise RuntimeError('Session storage unavailable')from None
            await asyncio.sleep(1)
    ready=True;task=asyncio.create_task(reconcile())
    try:yield
    finally:
        ready=False;task.cancel()
        try:await task
        except asyncio.CancelledError:pass


app=FastAPI(title='Phiên tài nguyên và thu hồi liên miền',lifespan=lifespan,docs_url=None,redoc_url=None)
install_error_handler(app)

@app.get('/health')
def health():return {'ready':ready,'generation':GENERATION}

@app.post('/sessions')
def sessions(request:Request,body:dict):api_auth(request);return create_session(body)

@app.post('/introspect')
def session_check(request:Request,body:dict):api_auth(request);return introspect(body)

@app.post('/events')
def events(body:dict):return apply_event(str(body.get('proof','')))

@app.get('/ops/state')
def ops_state(request:Request):
    ops_auth(request)
    with database()as conn:
        sessions=conn.execute('SELECT * FROM sessions ORDER BY created_at DESC LIMIT 200').fetchall()
        traces=conn.execute('SELECT * FROM trace ORDER BY id DESC LIMIT 300').fetchall()
        events=conn.execute('SELECT * FROM events ORDER BY applied_at DESC LIMIT 100').fetchall()
        members=conn.execute('SELECT * FROM bindings ORDER BY username').fetchall()
    return {'ready':ready,'generation':GENERATION,'config':settings(),'sessions':[public_session(r)for r in sessions],
            'trace':traces,'events':events,'bindings':members,'now':time.time()}

@app.post('/ops/register')
def register(request:Request,body:dict):
    ops_auth(request)
    keys={'subject_id','principal_id','username','organization'}
    if not keys<=body.keys()or any(not isinstance(body[k],str)or not body[k]for k in keys)or body['organization']not in {'P','R'}:
        raise FederationError('BINDING_INVALID',422)
    with database()as conn:
        old=conn.execute('SELECT * FROM bindings WHERE subject_id=%s',(body['subject_id'],)).fetchone()
        if old and any(old[k]!=body[k]for k in keys):raise FederationError('BINDING_CONFLICT',409)
        conn.execute('INSERT INTO bindings(subject_id,identity_issuer,principal_id,username,organization)VALUES(%s,%s,%s,%s,%s)ON CONFLICT(subject_id)DO NOTHING',
                     (body['subject_id'],IDENTITY_ISSUER,body['principal_id'],body['username'],body['organization']))
    return {'registered':True,'subject_id':body['subject_id']}

@app.put('/ops/config')
def set_config(request:Request,body:dict):
    ops_auth(request)
    allowed={'cache_seconds','poll_seconds','session_seconds','disable_poll','coordinator_unavailable'}
    if set(body)-allowed:raise FederationError('CONFIG_UNKNOWN',422)
    bounds={'cache_seconds':(1,10),'poll_seconds':(1,30),'session_seconds':(15,3600)}
    for k,v in body.items():
        if k in bounds:
            if type(v)not in {int,float}or not bounds[k][0]<=v<=bounds[k][1]:raise FederationError('CONFIG_INVALID',422)
        elif type(v)is not bool:raise FederationError('CONFIG_INVALID',422)
    with database()as conn:
        conn.execute("INSERT INTO settings(key,value)VALUES('config',%s)ON CONFLICT(key)DO UPDATE SET value=EXCLUDED.value",(Jsonb(body),))
    return {'config':settings()}

@app.post('/ops/invalidate')
def invalidate(request:Request,body:dict):
    ops_auth(request)
    target=body.get('session_id')
    with database()as conn:
        if target:
            rows=conn.execute("UPDATE sessions SET revoked=true,reason='OPERATOR_SESSION_REVOKED',revoked_at=%s WHERE id=%s AND revoked=false RETURNING id",(time.time(),target)).fetchall()
        else:
            rows=conn.execute("UPDATE sessions SET revoked=true,reason='RECOVERY_REAUTH_REQUIRED',revoked_at=%s WHERE revoked=false RETURNING id",(time.time(),)).fetchall()
        record('invalidation','OPERATOR_INVALIDATION',details={'session_id':target,'affected':len(rows)},conn=conn)
    return {'invalidated':len(rows)}
