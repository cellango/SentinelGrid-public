"""Actual orchestrator assembly, current IAM RSA validator in an isolated process.

Only keys/HTTP I/O and history storage are doubled. No auth dependency override,
real SQL, provider/model calls, live services or full runtime qualification.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from pydantic import ValidationError
import pytest

from app.main import app
from app.api import dashboard, posture, snapshot, response, phishing
from app.core.config import Settings
from app.core.principal_policy import OrchestratorPrincipalSettings, PostureHistoryReader
from app.core.security import HISTORY_PATH, get_current_tenant
from sg_core import iam_verification
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.user_principals import UserClientBinding

ROOT=Path(__file__).resolve().parents[4]
HTTP_CLIENT=httpx.Client
TEST_TENANT_ID='11111111-1111-4111-8111-111111111111'
TEST_USER_ID='22222222-2222-4222-8222-222222222222'
TEST_FOREIGN_ID='33333333-3333-4333-8333-333333333333'
ISSUER='https://identity.internal.test/realms/synthetic'
PATH=HISTORY_PATH.replace('{tenant_id}',TEST_TENANT_ID)
BINDING=dict(issuer=ISSUER,client_id='owned-browser',tenant_id=TEST_TENANT_ID,
    contract='keycloak-user-v1',service_accounts_enabled=False,token_exchange_enabled=False)
READER=dict(issuer=ISSUER,client_id='owned-browser',tenant_id=TEST_TENANT_ID,
    subject_id=TEST_USER_ID,permission='posture.read_history')
# All other currently mounted operations, including GETs with effects/global data.
UNAVAILABLE=[
 ('GET',f'/api/v1/orchestrator/tenant/{TEST_TENANT_ID}/'+tail) for tail in
 ['security-snapshot','dashboard-snapshot','dashboard-health','recommendations','ai-risk-summary',
  'now-queue','operator-overview','posture-score']
]+[
 ('POST',f'/api/v1/orchestrator/tenant/{TEST_TENANT_ID}/posture-rescore'),
 ('GET','/api/v1/orchestrator/scanner/health'),('GET','/api/v1/orchestrator/scanner/registry'),
 ('POST','/api/v1/orchestrator/analyze-phishing-email'),
 ('POST',f'/api/v1/orchestrator/alerts/{TEST_FOREIGN_ID}/orchestrate'),
 ('POST',f'/api/v1/orchestrator/findings/{TEST_FOREIGN_ID}/orchestrate'),
 ('GET',f'/api/v1/orchestrator/executions/{TEST_FOREIGN_ID}/status'),
 ('GET','/api/v1/orchestrator/reports/executions'),('GET','/ready'),('GET','/metrics'),
 ('GET','/metrics/prometheus'),('POST','/internal/orchestrator/handle_alert')]

IAM_WORKER = '\nimport json,sys\nfrom types import SimpleNamespace\nfrom app.services import token_validator as m\nfrom app.models.auth import TokenValidationResponse\nvalue=json.load(sys.stdin)\nm.settings=SimpleNamespace(KEYCLOAK_URL="https://identity.internal.test",KEYCLOAK_REALM="synthetic",\n    KEYCLOAK_CLIENT_ID="review-client",KEYCLOAK_ISSUER_BASE_URLS=[],JWKS_CACHE_TTL=60)\nvalidator=m.TokenValidator(None)\n# The fixture\'s owned JWKS replaces key transport. No token-selected key/URL.\nvalidator._get_jwks_for_realm=lambda *args: {"keys":[value["jwk"]]}\nprint(TokenValidationResponse(**validator.validate_token(value["token"])).model_dump_json())\n'

@pytest.fixture(scope='module')
def keys():return [rsa.generate_private_key(public_exponent=65537,key_size=2048) for _ in range(2)]

@pytest.fixture
def boundary(monkeypatch,keys):
    assert not app.dependency_overrides
    policy=OrchestratorPrincipalSettings(_env_file=None,IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
        ORCHESTRATOR_POSTURE_HISTORY_READERS=(PostureHistoryReader(**READER),))
    monkeypatch.setattr(app.state,'orchestrator_principal_settings',policy)
    monkeypatch.setattr(app.state,'iam_verification_settings',IAMVerificationSettings(_env_file=None,
        IAM_AGENT_URL='https://iam.internal.test',KEYCLOAK_CLIENT_ID='review-client'))
    claims=dict(iss=ISSUER,aud='review-client',sub=TEST_USER_ID,tenant_id=TEST_TENANT_ID,typ='Bearer',azp='owned-browser',
        sg_principal_type='user',sg_identity_contract='keycloak-user-v1',realm_access={'roles':['SOC_ANALYST']},
        iat=int(time.time())-1,exp=int(time.time())+600)
    opened=[];calls=[];db=Mock();db.execute.return_value.mappings.return_value.all.return_value=[{'overall_score':72}]
    @contextmanager
    def connection():opened.append(True);yield db
    monkeypatch.setattr(posture,'_history_engine',SimpleNamespace(connect=connection))
    forbidden=Mock(side_effect=AssertionError('Unqualified operation must not initialize or execute'))
    for module,name in [(snapshot,'SnapshotService'),(response,'ResponseOrchestrator'),(phishing,'PhishingAnalyzer')]:
        monkeypatch.setattr(module,name,forbidden)
    for instance,name in [(dashboard._posture_scorer,'score_tenant'),(posture._posture_scorer,'score_tenant'),
        (dashboard._ai_risk_summary_service,'build_summary'),(dashboard._now_queue_service,'build_queue')]:
        monkeypatch.setattr(instance,name,forbidden)
    import app.main as main
    monkeypatch.setattr(main,'probe_database_engine_async',forbidden);monkeypatch.setattr(main,'probe_http_dependency',forbidden)
    monkeypatch.setattr(httpx,'AsyncClient',forbidden)
    monkeypatch.setattr('sqlalchemy.engine.Engine.connect',forbidden)
    state=SimpleNamespace(claims=claims,calls=calls,opened=opened,db=db,forbidden=forbidden,
        unavailable=False,rows=db.execute.return_value.mappings.return_value.all)
    jwk=json.loads(RSAAlgorithm.to_jwk(keys[0].public_key()));jwk.update(kid='read-key',use='sig',alg='RS256')
    def sign(updates=None,key=None):
        return jwt.encode({**claims,**(updates or {})},key or keys[0],algorithm='RS256',headers={'kid':'read-key'})
    def handler(request):
        calls.append(request)
        assert str(request.url)=='https://iam.internal.test/internal/iam/auth/validate-token'
        assert set(json.loads(request.content))=={'token'}
        for name in ['authorization','x-tenant-id','x-realm','x-internal-service-token']:assert name not in request.headers
        if state.unavailable:raise httpx.ConnectError('synthetic verifier outage')
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':
            str(ROOT/'backend/libs')+os.pathsep+str(ROOT/'backend/agents/iam_agent')}
        value=subprocess.run([sys.executable,'-B','-c',IAM_WORKER],cwd=ROOT,env=env,text=True,
            input=json.dumps({'token':json.loads(request.content)['token'],'jwk':jwk}),capture_output=True,timeout=10)
        assert value.returncode==0,'Synthetic authoritative IAM process failed'
        return httpx.Response(200,json=json.loads(value.stdout))
    monkeypatch.setattr(iam_verification.httpx,'Client',lambda **kwargs:HTTP_CLIENT(transport=httpx.MockTransport(handler),**kwargs))
    state.sign=sign;state.keys=keys;state.app=app;state.client=TestClient(app)
    yield state
    state.client.close();forbidden.assert_not_called();assert not app.dependency_overrides


def auth(b,**updates):return {'Authorization':'Bearer '+b.sign(updates)}


def test_actual_history_read_binds_verified_tenant_and_bounded_limit(boundary):
    b=boundary;r=b.client.get(PATH+'?limit=7',headers=auth(b))
    assert r.status_code==200 and r.json()=={'items':[{'overall_score':72}]}
    assert b.opened==[True] and len(b.calls)==1
    assert app.openapi()['paths'][HISTORY_PATH]['get']['security']==[{'HTTPBearer':[]}]
    sql,params=b.db.execute.call_args.args
    assert 'FROM public.posture_score_snapshot' in str(sql) and 'WHERE tenant_id = :tenant_id' in str(sql)
    assert params=={'tenant_id':TEST_TENANT_ID,'limit':7}


def test_empty_history_is_true_empty_data(boundary):
    b=boundary;b.rows.return_value=[];r=b.client.get(PATH,headers=auth(b))
    assert r.status_code==200 and r.json()=={'items':[]}


def test_history_store_outage_does_not_become_empty_success(boundary):
    b=boundary;b.db.execute.side_effect=RuntimeError('private store diagnostic')
    r=b.client.get(PATH,headers=auth(b));assert r.status_code==503 and 'private store diagnostic' not in r.text


@pytest.mark.parametrize('method,path',UNAVAILABLE)
@pytest.mark.parametrize('signed',[False,True])
def test_all_unqualified_mounted_operations_stop_before_effects(boundary,method,path,signed):
    b=boundary;headers=auth(b,realm_access={'roles':['PLATFORM_ADMIN']}) if signed else {}
    r=b.client.request(method,path,headers=headers,json={'approved':True,'tenant_id':TEST_TENANT_ID} if method=='POST' else None)
    assert r.status_code==503 and b.opened==[] and b.db.mock_calls==[] and b.calls==[]


@pytest.mark.parametrize('kind',['none','static','cookie','marker','duplicate','conflict','malformed'])
def test_raw_direct_credentials_cannot_create_read_authority(boundary,kind):
    b=boundary;token=b.sign();headers=[]
    if kind=='static':headers=[('Authorization','Bearer disposable-local-only'),('X-Tenant-ID',TEST_TENANT_ID)]
    if kind=='cookie':headers=[('Cookie','access_token='+token)]
    if kind=='marker':headers=[('Authorization','Bearer session-cookie'),('Cookie','access_token='+token)]
    if kind=='duplicate':headers=[('Authorization','Bearer '+token)]*2
    if kind=='conflict':headers=[('Authorization','Bearer '+token),('Cookie','access_token=other')]
    if kind=='malformed':headers=[('Authorization','Basic other'),('Cookie','access_token='+token)]
    r=b.client.get(PATH,headers=headers);assert r.status_code==401 and b.opened==[]


@pytest.mark.parametrize('updates',[
 {'tenant_id':TEST_FOREIGN_ID},{'sub':TEST_FOREIGN_ID},{'azp':'foreign-client'},
 {'sg_principal_type':'workload'},{'sg_principal_type':None},{'sg_identity_contract':'other'},
 {'typ':'ID'},{'act':{'sub':TEST_USER_ID}},{'may_act':{}},{'client_id':'owned-browser'},
])
def test_signed_foreign_or_unclassified_principal_is_not_a_reader(boundary,updates):
    b=boundary;r=b.client.get(PATH,headers=auth(b,**updates));assert r.status_code==403 and b.opened==[]


@pytest.mark.parametrize('kind',['forged','expired','wrong_audience','outage'])
def test_real_RSA_and_unavailable_verifier_reject_before_history(boundary,kind):
    b=boundary;updates={};expected=401
    if kind=='expired':updates={'exp':int(time.time())-1}
    if kind=='wrong_audience':updates={'aud':'foreign'}
    if kind=='outage':b.unavailable=True;expected=503
    token=b.sign(updates,key=b.keys[1] if kind=='forged' else None)
    r=b.client.get(PATH,headers={'Authorization':'Bearer '+token})
    assert r.status_code==expected and b.opened==[] and token not in r.text


@pytest.mark.parametrize('hints',[
 [('X-Tenant-ID',TEST_FOREIGN_ID)],[('X-Tenant-ID',TEST_TENANT_ID)]*2,
 [('X-Realm','foreign')],[('X-Realm','synthetic')]*2,[('X-User-ID',TEST_USER_ID)],
 [('X-Roles','PLATFORM_ADMIN')],[('X-Internal-Service-Token','disposable-local-only')],
 [('X-Internal-Token','disposable-local-only')]])
def test_forwarded_hints_never_override_verified_context(boundary,hints):
    b=boundary;r=b.client.get(PATH,headers=[*auth(b).items(),*hints]);assert r.status_code==403 and b.opened==[]


def test_valid_user_without_explicit_reader_grant_is_denied(boundary,monkeypatch):
    b=boundary;monkeypatch.setattr(app.state,'orchestrator_principal_settings',
        OrchestratorPrincipalSettings(_env_file=None,IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),)))
    r=b.client.get(PATH,headers=auth(b,realm_access={'roles':['PLATFORM_ADMIN']}))
    assert r.status_code==403 and b.opened==[]


def test_empty_policy_fails_closed(boundary,monkeypatch):
    b=boundary;monkeypatch.setattr(app.state,'orchestrator_principal_settings',OrchestratorPrincipalSettings(_env_file=None))
    assert b.client.get(PATH,headers=auth(b)).status_code==503 and b.opened==[]


@pytest.mark.parametrize('target',[
 HISTORY_PATH.replace('{tenant_id}',TEST_FOREIGN_ID),PATH.replace('11111111','%31'+'1111111',1),
])
def test_foreign_or_encoded_tenant_target_is_rejected(boundary,target):
    b=boundary;r=b.client.get(target,headers=auth(b));assert r.status_code==403 and b.opened==[]


@pytest.mark.parametrize('query,status',[('limit=1&limit=2',400),('tenant_id='+TEST_FOREIGN_ID,400),
    ('limit=0',422),('limit=91',422),('limit=invalid',422)])
def test_ambiguous_or_unbounded_query_does_not_open_store(boundary,query,status):
    b=boundary;r=b.client.get(PATH+'?'+query,headers=auth(b));assert r.status_code==status and b.opened==[]


@pytest.mark.parametrize('path',['/','/health'])
def test_only_local_metadata_is_public_without_external_calls(boundary,path):
    b=boundary;r=b.client.get(path);assert r.status_code==200 and b.calls==[] and b.opened==[]


def test_unknown_method_or_alias_cannot_inherit_admission(boundary):
    b=boundary;other=FastAPI()
    other.state.iam_verification_settings=app.state.iam_verification_settings
    other.state.orchestrator_principal_settings=app.state.orchestrator_principal_settings
    other.include_router(posture.router,prefix='/unreviewed')
    with TestClient(other) as client:r=client.get('/unreviewed/tenant/'+TEST_TENANT_ID+'/posture-score/history',headers=auth(b))
    assert r.status_code==503 and b.opened==[] and b.calls==[]
    # A synthetic use of the compatibility tenant helper cannot select an operation.
    @other.get('/other')
    def alias(tenant=Depends(get_current_tenant)):return {'tenant':str(tenant)}
    with TestClient(other) as client:r=client.get('/other',headers=auth(b))
    assert r.status_code==503 and b.opened==[]


@pytest.mark.parametrize('change',[{'subject_id':'00000000-0000-0000-0000-000000000000'},
    {'subject_id':'not-a-uuid'},{'tenant_id':TEST_FOREIGN_ID},{'permission':'all'}])
def test_reader_configuration_cannot_widen_or_cross_registrations(change):
    with pytest.raises(ValidationError):
        OrchestratorPrincipalSettings(_env_file=None,IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
            ORCHESTRATOR_POSTURE_HISTORY_READERS=({**READER,**change},))


def test_duplicate_reader_grants_fail_closed():
    reader=PostureHistoryReader(**READER)
    with pytest.raises(ValidationError):
        OrchestratorPrincipalSettings(_env_file=None,IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
            ORCHESTRATOR_POSTURE_HISTORY_READERS=(reader,reader))


def test_verifier_snapshot_uses_only_owned_orchestrator_settings():
    settings=Settings(_env_file=None,IAM_AGENT_URL='https://owned-iam.internal.test',KEYCLOAK_CLIENT_ID='owned-audience')
    verified=settings.verification_settings();assert verified.IAM_AGENT_URL=='https://owned-iam.internal.test'
    assert verified.KEYCLOAK_CLIENT_ID=='owned-audience' and settings.principal_settings().ORCHESTRATOR_POSTURE_HISTORY_READERS==()
