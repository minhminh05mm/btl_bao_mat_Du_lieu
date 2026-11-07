import time,uuid
import jwt,pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from federation.common import (verify_proof,validate_snapshot,state_reason,FederationError,
    PARTNER_ISSUER,STATE_AUDIENCE,mint_proof)

@pytest.fixture
def keys(tmp_path):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    private=tmp_path/'private';public=tmp_path/'public'
    private.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    public.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
    return private,public

def payload():
    now=time.time()
    return {'kind':'state','sub':'subject','organization':'P','principal_id':'member','device_id':'dev-member',
        'nonce':'testnonce-0123456789','cert_serial':'AB','active':True,'compliant':True,'revoked':False,'risk':'NORMAL',
        'subject_version':2,'device_version':3,'subject_epoch':1,'device_epoch':1,'observed_at':now,'risk_at':now}

def test_valid_signed_source(keys):
    private,public=keys;s=payload();proof=mint_proof(s,private,PARTNER_ISSUER)
    verified=verify_proof(proof,public,PARTNER_ISSUER,kind='state')
    assert validate_snapshot(verified,subject='subject',device_serial='ab',organization='P',nonce=s['nonce'])['active']

@pytest.mark.parametrize('changes',[{'iss':'another-source'},{'aud':'another-resource'},{'exp':0},{'iat':time.time()+60},
    {'sub':''},{'jti':''},{'kind':'event'},{'exp':time.time()+1000}])
def test_signed_invalid_claims_rejected(keys,changes):
    private,public=keys;now=time.time();s={**payload(),'iss':PARTNER_ISSUER,'aud':STATE_AUDIENCE,'iat':now,'exp':now+15,'jti':str(uuid.uuid4()),**changes}
    proof=jwt.encode(s,private.read_bytes(),algorithm='RS256')
    with pytest.raises(FederationError):verify_proof(proof,public,PARTNER_ISSUER,kind='state')

def test_signature_and_algorithm_are_pinned(keys):
    private,public=keys;proof=mint_proof(payload(),private,PARTNER_ISSUER);a,b,z=proof.split('.')
    for value in (a+'.'+b+'.'+('A'if z[0]!='A'else'B')+z[1:],jwt.encode(payload(),'x'*40,algorithm='HS256')):
        with pytest.raises(FederationError):verify_proof(value,public,PARTNER_ISSUER,kind='state')

@pytest.mark.parametrize('patch',[{'active':'true'},{'compliant':None},{'revoked':0},{'subject_epoch':True},
    {'device_version':0},{'observed_at':float('nan')},{'risk_at':float('inf')},{'risk':'UNKNOWN'}])
def test_malformed_eligibility_is_never_accepted(patch):
    with pytest.raises(FederationError):state_reason({**payload(),**patch})

def test_issued_at_does_not_launder_old_observation(keys):
    private,public=keys;s={**payload(),'observed_at':time.time()-70}
    value=verify_proof(mint_proof(s,private,PARTNER_ISSUER),public,PARTNER_ISSUER,kind='state')
    assert state_reason(value)=='SOURCE_OBSERVATION_STALE'

@pytest.mark.parametrize('changes',[{'nonce':'wrong'},{'subject':'wrong'},{'organization':'R'},{'device_serial':'AC'}])
def test_exact_source_binding(changes):
    args={'subject':'subject','device_serial':'AB','organization':'P','nonce':'testnonce-0123456789',**changes}
    with pytest.raises(FederationError):validate_snapshot(payload(),**args)
