"""Partner-owned account/device authority and durable signed event outbox."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from psycopg import sql
from psycopg.types.json import Jsonb

from .common import (FederationError, PARTNER_ISSUER, bearer, database, identity,
                     install_error_handler, mint_proof, require_credential, serial, tls_client)

SERVICE = Path(os.getenv('SERVICE_SECRET_DIR', '/runtime/service'))
SCHEMA = '''
CREATE TABLE IF NOT EXISTS identities (
 id text PRIMARY KEY, subject_id text UNIQUE NOT NULL, username text UNIQUE NOT NULL,
 organization text NOT NULL CHECK(organization='P'), active boolean NOT NULL,
 partner_admin boolean NOT NULL DEFAULT false, version bigint NOT NULL DEFAULT 1, epoch bigint NOT NULL DEFAULT 1,
 changed_at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS devices (
 id text PRIMARY KEY, principal_id text NOT NULL REFERENCES identities(id),
 cert_serial text UNIQUE NOT NULL, compliant boolean NOT NULL, revoked boolean NOT NULL,
 risk text NOT NULL, observed_at double precision NOT NULL, risk_at double precision NOT NULL,
 auto_refresh boolean NOT NULL DEFAULT true, version bigint NOT NULL DEFAULT 1, epoch bigint NOT NULL DEFAULT 1,
 changed_at double precision NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
 event_id text PRIMARY KEY, payload jsonb NOT NULL, created_at double precision NOT NULL,
 status text NOT NULL DEFAULT 'pending', delivered_at double precision, last_status integer
);
CREATE TABLE IF NOT EXISTS settings (key text PRIMARY KEY, value jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS changes (
 id bigserial PRIMARY KEY, actor text NOT NULL, kind text NOT NULL, target text NOT NULL,
 patch jsonb NOT NULL, created_at double precision NOT NULL, event_id text
);
'''
logger = logging.getLogger('bmdl.partner')
ready = False


def initialize():
    with database() as conn:
        conn.execute(SCHEMA)


def faults():
    with database() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='faults'").fetchone()
    return row['value'] if row else {}


def require_ops(request):
    require_credential(request, SERVICE/'ops-token')


def require_admin(request):
    claims = identity(bearer(request))
    with database() as conn:
        user = conn.execute('SELECT * FROM identities WHERE subject_id=%s', (claims['sub'],)).fetchone()
    if not user or not user['active'] or not user['partner_admin']:
        raise FederationError('PARTNER_ADMIN_REQUIRED')
    return user['id']


def snapshot(subject, device_serial, nonce):
    if not isinstance(nonce, str) or not 16 <= len(nonce) <= 128:
        raise FederationError('SOURCE_NONCE_REQUIRED', 422)
    with database() as conn:
        user = conn.execute('SELECT * FROM identities WHERE subject_id=%s', (subject,)).fetchone()
        if not user:
            raise FederationError('SOURCE_SUBJECT_UNKNOWN', 403)
        device = conn.execute('SELECT * FROM devices WHERE cert_serial=%s AND principal_id=%s',
                              (serial(device_serial), user['id'])).fetchone()
        if not device:
            raise FederationError('DEVICE_MISMATCH')
    return {'kind': 'state', 'sub': user['subject_id'], 'identity_issuer': os.getenv('OIDC_ISSUER', 'https://localhost:9443/realms/bmdl'),
            'organization': 'P', 'principal_id': user['id'], 'username': user['username'],
            'active': user['active'], 'subject_version': user['version'], 'subject_epoch': user['epoch'],
            'device_id': device['id'], 'cert_serial': device['cert_serial'],
            'compliant': device['compliant'], 'revoked': device['revoked'], 'risk': device['risk'],
            'observed_at': device['observed_at'], 'risk_at': device['risk_at'],
            'device_version': device['version'], 'device_epoch': device['epoch'], 'nonce': nonce,
            'changed_at': max(user['changed_at'],device['changed_at'])}


def event(conn, user, *, kind, device=None):
    now = time.time()
    identifier = str(uuid.uuid4())
    entity = device if kind == 'device' else user
    payload = {'kind': 'event', 'event_id': identifier, 'sub': user['subject_id'],
               'organization': 'P', 'identity_issuer': os.getenv('OIDC_ISSUER', 'https://localhost:9443/realms/bmdl'),
               'principal_id': user['id'], 'entity_kind': kind, 'entity_id': entity['id'],
               'state_version': entity['version'], 'source_epoch': entity['epoch'], 'occurred_at': now,
               'active': user['active']}
    if device:
        payload.update({k: device[k] for k in ('compliant','revoked','risk','observed_at','risk_at')})
        payload['device_id'] = device['id']
    conn.execute('INSERT INTO outbox(event_id,payload,created_at) VALUES (%s,%s,%s)',
                 (identifier, Jsonb(payload), now))
    return identifier


def change(kind, target, patch, actor, *, operator=False):
    allowed = {'active'} if kind == 'principal' else {'compliant','revoked','risk','auto_refresh'}
    if operator and kind == 'device':
        allowed |= {'observed_at','risk_at'}
    if not isinstance(patch, dict) or not patch or set(patch)-allowed:
        raise FederationError('SOURCE_PATCH_INVALID', 422)
    for key, value in patch.items():
        if key in {'active','compliant','revoked','auto_refresh'} and type(value) is not bool:
            raise FederationError('SOURCE_PATCH_INVALID', 422)
        if key == 'risk' and value not in {'NORMAL','HIGH'}:
            raise FederationError('SOURCE_PATCH_INVALID', 422)
        if key in {'observed_at','risk_at'} and (type(value) not in {int,float} or not 0 <= value <= time.time()+1):
            raise FederationError('SOURCE_PATCH_INVALID', 422)
    if not operator and kind=='principal'and target==actor and patch.get('active')is False:
        raise FederationError('SOURCE_SELF_LOCK_FORBIDDEN',409)
    table = 'identities' if kind == 'principal' else 'devices'
    now = time.time()
    with database() as conn:
        row = conn.execute(sql.SQL('SELECT * FROM {} WHERE id=%s FOR UPDATE').format(sql.Identifier(table)), (target,)).fetchone()
        if not row:
            # R identities are deliberately absent from this authority.
            raise FederationError('PARTNER_OBJECT_NOT_FOUND', 404)
        user = row if kind == 'principal' else conn.execute('SELECT * FROM identities WHERE id=%s FOR SHARE', (row['principal_id'],)).fetchone()
        values = {**patch, 'changed_at': now}
        if kind == 'device' and not operator:
            values.update({'observed_at': now, 'risk_at': now})
        assignments = [sql.SQL('{}=%s').format(sql.Identifier(k)) for k in values]
        conn.execute(sql.SQL('UPDATE {} SET {},version=version+1,epoch=epoch+1 WHERE id=%s').format(
            sql.Identifier(table), sql.SQL(',').join(assignments)), (*values.values(), target))
        updated = conn.execute(sql.SQL('SELECT * FROM {} WHERE id=%s').format(sql.Identifier(table)), (target,)).fetchone()
        if kind == 'principal':
            user = updated
        event_id = event(conn, user, kind=kind, device=updated if kind=='device' else None)
        conn.execute('INSERT INTO changes(actor,kind,target,patch,created_at,event_id) VALUES (%s,%s,%s,%s,%s,%s)',
                     (actor,kind,target,Jsonb(patch),now,event_id))
    return {'object': updated, 'event_id': event_id, 'source_changed_at': now}


def refresh_observations():
    now = time.time()
    with database() as conn:
        conn.execute('UPDATE devices SET observed_at=%s,risk_at=%s,version=version+1 '
                     'WHERE auto_refresh=true', (now,now))


def deliver_once():
    config = faults()
    if config.get('source_unavailable') or config.get('pause_events'):
        return
    with database() as conn:
        pending = conn.execute("SELECT * FROM outbox WHERE status='pending' ORDER BY created_at LIMIT 30 FOR UPDATE SKIP LOCKED").fetchall()
        for row in pending:
            if config.get('drop_events'):
                conn.execute("UPDATE outbox SET status='dropped',last_status=0 WHERE event_id=%s", (row['event_id'],))
                continue
            if time.time() < row['created_at'] + float(config.get('event_delay_seconds',0)):
                continue
            proof = mint_proof(row['payload'], SERVICE/'signing.key', PARTNER_ISSUER, lifetime=300)
            if config.get('tamper_events'):
                a,b,c=proof.split('.');proof=a+'.'+b+'.'+('A' if c[0]!='A' else 'B')+c[1:]
            try:
                with tls_client(timeout=3) as client:
                    r = client.post(os.getenv('COORDINATOR_URL','https://coordinator:8080')+'/events', json={'proof':proof})
                code = r.status_code
            except Exception:
                code = 503
            if code == 200:
                conn.execute("UPDATE outbox SET status='delivered',delivered_at=%s,last_status=%s WHERE event_id=%s",
                             (time.time(),code,row['event_id']))
            else:
                conn.execute('UPDATE outbox SET last_status=%s WHERE event_id=%s', (code,row['event_id']))


async def background():
    refresh_at = 0.0
    while True:
        try:
            if time.monotonic() >= refresh_at:
                await asyncio.to_thread(refresh_observations)
                refresh_at = time.monotonic()+20
            await asyncio.to_thread(deliver_once)
        except Exception:
            logger.warning('Partner background task unavailable')
        await asyncio.sleep(.25)


@asynccontextmanager
async def lifespan(app):
    global ready
    for attempt in range(90):
        try:
            await asyncio.to_thread(initialize)
            break
        except Exception:
            if attempt == 89:
                raise RuntimeError('Partner storage unavailable') from None
            await asyncio.sleep(1)
    ready=True
    task=asyncio.create_task(background())
    try:
        yield
    finally:
        ready=False;task.cancel()
        try:await task
        except asyncio.CancelledError:pass


app=FastAPI(title='Danh tính và thiết bị đối tác',lifespan=lifespan,docs_url=None,redoc_url=None)
install_error_handler(app)


@app.get('/health')
def health():
    return {'ready':ready,'authority':'P','issuer':PARTNER_ISSUER}


@app.post('/eligibility')
def eligibility(request:Request,body:dict):
    require_credential(request,SERVICE/'source-read-token')
    config=faults()
    if config.get('source_unavailable'):
        raise FederationError('SOURCE_UNAVAILABLE',503)
    value=snapshot(str(body.get('subject','')),body.get('cert_serial'),body.get('nonce'))
    proof=mint_proof(value,SERVICE/'signing.key',PARTNER_ISSUER)
    if config.get('tamper_state'):
        a,b,c=proof.split('.');proof=a+'.'+b+'.'+('A'if c[0]!='A'else'B')+c[1:]
    return {'proof':proof}


def public_state():
    with database()as conn:
        users=conn.execute('SELECT * FROM identities ORDER BY username').fetchall()
        devices=conn.execute('SELECT * FROM devices ORDER BY id').fetchall()
        events=conn.execute('SELECT event_id,payload,created_at,status,delivered_at,last_status FROM outbox ORDER BY created_at DESC LIMIT 100').fetchall()
        changes=conn.execute('SELECT * FROM changes ORDER BY id DESC LIMIT 100').fetchall()
    return {'authority':'P','identities':users,'devices':devices,'events':events,'changes':changes,'faults':faults()}


@app.get('/admin/state')
def admin_state(request:Request):
    require_admin(request)
    return public_state()


@app.patch('/admin/principals/{identifier}')
def admin_principal(identifier:str,request:Request,body:dict):
    return change('principal',identifier,body,require_admin(request))


@app.patch('/admin/devices/{identifier}')
def admin_device(identifier:str,request:Request,body:dict):
    return change('device',identifier,body,require_admin(request))


@app.get('/ops/state')
def ops_state(request:Request):
    require_ops(request)
    return public_state()


@app.post('/ops/register')
def register(request:Request,body:dict):
    require_ops(request)
    required={'id','subject_id','username','cert_serial','device_id'}
    if not required<=body.keys() or any(not isinstance(body[k],str) or not body[k] for k in required):
        raise FederationError('SOURCE_REGISTRATION_INVALID',422)
    if body.get('organization')!='P':raise FederationError('PARTNER_SCOPE_REQUIRED',422)
    now=time.time()
    with database()as conn:
        existing=conn.execute('SELECT * FROM identities WHERE id=%s',(body['id'],)).fetchone()
        if existing:
            if existing['subject_id']!=body['subject_id'] or existing['username']!=body['username']:
                raise FederationError('SOURCE_BINDING_CONFLICT',409)
        else:
            conn.execute('INSERT INTO identities(id,subject_id,username,organization,active,partner_admin,changed_at) '
                         'VALUES (%s,%s,%s,\'P\',%s,%s,%s)',
                         (body['id'],body['subject_id'],body['username'],bool(body.get('active',True)),bool(body.get('partner_admin',False)),now))
        old_device=conn.execute('SELECT * FROM devices WHERE id=%s',(body['device_id'],)).fetchone()
        if old_device and (old_device['principal_id']!=body['id']or old_device['cert_serial']!=serial(body['cert_serial'])):
            raise FederationError('SOURCE_DEVICE_BINDING_CONFLICT',409)
        conn.execute('INSERT INTO devices(id,principal_id,cert_serial,compliant,revoked,risk,observed_at,risk_at,changed_at) '
                     'VALUES (%s,%s,%s,true,false,\'NORMAL\',%s,%s,%s) ON CONFLICT(id) DO NOTHING',
                     (body['device_id'],body['id'],serial(body['cert_serial']),now,now,now))
    return {'registered':True,'id':body['id'],'organization':'P'}


@app.patch('/ops/principals/{identifier}')
def ops_principal(identifier:str,request:Request,body:dict):
    require_ops(request)
    return change('principal',identifier,body,'trusted-test-operator',operator=True)


@app.patch('/ops/devices/{identifier}')
def ops_device(identifier:str,request:Request,body:dict):
    require_ops(request)
    return change('device',identifier,body,'trusted-test-operator',operator=True)


@app.put('/ops/faults')
def set_faults(request:Request,body:dict):
    require_ops(request)
    allowed={'source_unavailable','pause_events','drop_events','tamper_events','tamper_state','event_delay_seconds'}
    if set(body)-allowed:raise FederationError('FAULT_UNKNOWN',422)
    for k,v in body.items():
        if k=='event_delay_seconds':
            if type(v)not in {int,float}or not 0<=v<=60:raise FederationError('FAULT_INVALID',422)
        elif type(v)is not bool:raise FederationError('FAULT_INVALID',422)
    with database()as conn:
        conn.execute("INSERT INTO settings(key,value)VALUES('faults',%s)ON CONFLICT(key)DO UPDATE SET value=EXCLUDED.value",(Jsonb(body),))
    return {'faults':body}


@app.get('/ops/events/{identifier}/proof')
def event_proof(identifier:str,request:Request):
    require_ops(request)
    with database()as conn:
        row=conn.execute('SELECT payload FROM outbox WHERE event_id=%s',(identifier,)).fetchone()
    if not row:raise FederationError('EVENT_NOT_FOUND',404)
    return {'proof':mint_proof(row['payload'],SERVICE/'signing.key',PARTNER_ISSUER,lifetime=300)}
