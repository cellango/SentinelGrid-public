"""Actual IAM context/router with current RSA validator and key/storage spies.

No identity override, self-RPC, full app startup, provider or real SQL. The existing
IAM unit harness provides its declared Redis double; it is not runtime evidence.
"""
import asyncio
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
import time
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request

from app.api import access_requests, auth, iam_portal, policies, request_context as ctx
from app.core.source_admission import include_source_router
from app.services import keycloak_client
from sg_core import iam_verification
from sg_core.user_principals import UserClientBinding, UserPrincipalSettings
from backend.agents.iam_agent.tests.test_token_validator import keys, setup

TEST_TENANT_ID='11111111-1111-4111-8111-111111111111'
TEST_USER_ID='22222222-2222-4222-8222-222222222222'
TEST_FOREIGN_ID='33333333-3333-4333-8333-333333333333'

@pytest.fixture
def boundary(setup,monkeypatch):
    setup.claims.update(tenant_id=TEST_TENANT_ID,sub=TEST_USER_ID,typ='Bearer',
        sg_principal_type='user',sg_identity_contract='keycloak-user-v1',azp='owned-browser')
    binding=UserClientBinding(issuer=setup.claims['iss'],client_id='owned-browser',tenant_id=TEST_TENANT_ID,
        contract='keycloak-user-v1',service_accounts_enabled=False,token_exchange_enabled=False)
    config=UserPrincipalSettings(_env_file=None,IAM_USER_CLIENT_BINDINGS=(binding,))
    monkeypatch.setattr(ctx,'settings',SimpleNamespace(KEYCLOAK_CLIENT_ID=setup.config.KEYCLOAK_CLIENT_ID))
    rpc=Mock(side_effect=AssertionError('No IAM self RPC'));monkeypatch.setattr(iam_verification,'verify_iam_token',rpc)
    provider=Mock(side_effect=AssertionError('No provider admin constructor'))
    monkeypatch.setattr(keycloak_client,'KeycloakClient',provider)
    monkeypatch.setattr(iam_portal,'KeycloakClient',provider)
    entries=[];db=Mock();query=db.query.return_value
    query.filter.return_value=query;query.order_by.return_value=query
    query.offset.return_value=query;query.limit.return_value=query;query.all.return_value=[]
    @contextmanager
    def session(factory,tenant):
        entries.append((factory,tenant));yield db
    monkeypatch.setattr(ctx,'tenant_session',session)
    service=Mock();service.list_policies.return_value=[]
    constructor=Mock(return_value=service);monkeypatch.setattr(policies,'PolicyService',constructor)
    validate=Mock(wraps=setup.validator.validate_token);monkeypatch.setattr(setup.validator,'validate_token',validate)
    app=FastAPI();app.state.user_principal_settings=config
    app.dependency_overrides[auth.get_token_validator]=lambda:setup.validator
    include_source_router(app,'iam_policies.router',policies.router)
    include_source_router(app,'access_requests.router',access_requests.router)
    @app.get('/context')
    async def context(context=Depends(ctx.get_current_request_context),info=Depends(ctx.get_current_user_info)):
        return {'tenant_id':str(context.tenant_id),'user_id':context.user_id,'roles':context.roles,'info':info}
    state=SimpleNamespace(**vars(setup),app=app,policy=config,entries=entries,db=db,constructor=constructor,
        validate=validate,provider=provider,rpc=rpc)
    with TestClient(app) as client:
        state.client=client;yield state
    rpc.assert_not_called();provider.assert_not_called()

def header(b):return {'Authorization':'Bearer '+b.sign()}

def test_policy_route_shares_identity_for_SQL_and_service(boundary):
    b=boundary;r=b.client.get('/api/iam-portal/policies',headers=header(b))
    assert r.status_code==200 and r.json()==[]
    assert b.entries==[(ctx.SessionLocal,UUID(TEST_TENANT_ID))]
    b.constructor.assert_called_once_with(b.db,UUID(TEST_TENANT_ID),'tenant-a')
    assert b.validate.call_count==1 and b.fetch.call_count==1
    assert policies.get_current_user_info is ctx.get_current_user_info is iam_portal.get_current_user_info

def test_access_request_route_filters_verified_tenant_and_user(boundary):
    b=boundary;r=b.client.get('/api/v1/access-requests',headers=header(b))
    assert r.status_code==200 and r.json()==[] and b.validate.call_count==1
    assert b.entries==[(ctx.IAMSessionLocal,UUID(TEST_TENANT_ID))]
    filters=b.db.query.return_value.filter.call_args_list
    assert filters[0].args[0].right.value==UUID(TEST_TENANT_ID)
    assert {c.right.value for c in filters[1].args[0].clauses}=={UUID(TEST_USER_ID)}

def test_context_projects_signed_metadata_and_roles(boundary):
    b=boundary;r=b.client.get('/context',headers=header(b));assert r.status_code==200
    info=r.json()['info'];assert info['user_id']==TEST_USER_ID and info['tenant_id']==TEST_TENANT_ID
    assert info['roles']==['SOC_ANALYST'] and info['realm_name']=='tenant-a'
    assert info['email']=='user@example.test' and info['username']=='review-user' and b.validate.call_count==1

@pytest.mark.parametrize('kind',['missing','header_only','static_with_tenant','static_no_tenant',
    'cookie_only','marker_cookie','duplicate_authorization','conflicting_cookie','malformed_header_cookie'])
def test_legacy_ambiguous_credentials_reject_before_SQL(boundary,kind):
    b=boundary;token=b.sign();h=[]
    if kind=='header_only':h=[('X-Tenant-ID',TEST_TENANT_ID)]
    if kind=='static_with_tenant':h=[('Authorization','Bearer disposable-local-only'),('X-Tenant-ID',TEST_TENANT_ID)]
    if kind=='static_no_tenant':h=[('Authorization','Bearer disposable-local-only')]
    if kind=='cookie_only':h=[('Cookie','access_token='+token)]
    if kind=='marker_cookie':h=[('Authorization','Bearer session-cookie'),('Cookie','access_token='+token)]
    if kind=='duplicate_authorization':h=[('Authorization','Bearer '+token)]*2
    if kind=='conflicting_cookie':h=[('Authorization','Bearer '+token),('Cookie','access_token=other')]
    if kind=='malformed_header_cookie':h=[('Authorization','Basic other'),('Cookie','access_token='+token)]
    r=b.client.get('/api/iam-portal/policies',headers=h)
    assert r.status_code==401 and b.entries==[] and b.constructor.mock_calls==[]

@pytest.mark.parametrize('update',[
    {'sg_principal_type':'workload'},{'sg_principal_type':None},{'sg_identity_contract':'other'},
    {'typ':'ID'},{'azp':'foreign-client'},{'tenant_id':TEST_FOREIGN_ID},
    {'act':{'sub':TEST_USER_ID}},{'may_act':{}},{'client_id':'owned-browser'},
    {'sub':'not-a-user-uuid'},{'sub':'00000000-0000-0000-0000-000000000000'},
    {'tenant_id':'00000000-0000-0000-0000-000000000000'},
    {'realm_access':{'roles':['SOC_ANALYST','SOC_ANALYST']}}])
def test_signed_identity_outside_owned_contract_rejects_before_SQL(boundary,update):
    b=boundary;b.claims.update(update);r=b.client.get('/api/iam-portal/policies',headers=header(b))
    assert r.status_code in {403,503} and b.entries==[] and b.constructor.mock_calls==[]

@pytest.mark.parametrize('kind',['forged','expired','future','wrong_issuer','wrong_audience','keys_unavailable'])
def test_actual_signature_issuer_time_and_key_failures_reject_before_SQL(boundary,kind):
    b=boundary
    if kind=='expired':b.claims['exp']=int(time.time())-1
    if kind=='future':b.claims['iat']=int(time.time())+60
    if kind=='wrong_issuer':b.claims['iss']='https://foreign.internal.test/realms/tenant-a'
    if kind=='wrong_audience':b.claims['aud']='foreign-audience'
    if kind=='keys_unavailable':b.fetch.return_value=None
    token=b.sign(key=b.keys[1] if kind=='forged' else None)
    r=b.client.get('/api/iam-portal/policies',headers={'Authorization':'Bearer '+token})
    assert r.status_code==401 and b.entries==[] and b.constructor.mock_calls==[]
    assert 'Trusted signing keys' not in r.text and token not in r.text

@pytest.mark.parametrize('extra',[
    [('X-Tenant-ID',TEST_FOREIGN_ID)],[('X-Tenant-ID',TEST_TENANT_ID)]*2,
    [('X-Realm','foreign')],[('X-Realm','tenant-a')]*2,[('X-User-ID',TEST_USER_ID)],
    [('X-Roles','PLATFORM_ADMIN')],[('X-Internal-Token','disposable-local-only')],
    [('X-Internal-Service-Token','disposable-local-only')]])
def test_forwarded_hints_cannot_override_verified_user(boundary,extra):
    b=boundary;r=b.client.get('/api/iam-portal/policies',headers=[*header(b).items(),*extra])
    assert r.status_code==403 and b.entries==[] and b.constructor.mock_calls==[]

def test_matching_bearer_cookie_and_hints_are_unambiguous(boundary):
    b=boundary;token=b.sign();r=b.client.get('/context',headers={'Authorization':'Bearer '+token,
        'Cookie':'access_token='+token,'X-Tenant-ID':TEST_TENANT_ID,'X-Realm':'tenant-a'})
    assert r.status_code==200 and b.validate.call_count==1

@pytest.mark.parametrize('config',[None,{},'not-a-policy'])
def test_missing_or_invalid_owned_policy_is_unavailable(boundary,monkeypatch,config):
    b=boundary;b.app.state.user_principal_settings=UserPrincipalSettings(_env_file=None) if config is None else config
    import sg_core.user_principals as user_policy
    # A falsey wrong type must not silently fall back to a valid ambient policy.
    monkeypatch.setattr(user_policy,'get_user_principal_settings',lambda:b.policy)
    r=b.client.get('/api/iam-portal/policies',headers=header(b))
    assert r.status_code==503 and b.entries==[]

@pytest.mark.parametrize('change',['tenant','roles','payload','valid','expiry','error','exception'])
def test_contradictory_or_failed_validator_results_are_unavailable(boundary,change):
    b=boundary;original=b.validator.validate_token
    def altered(token):
        if change=='exception':raise RuntimeError('private-validator-diagnostic')
        result=original(token)
        if change=='tenant':result['tenant_id']=TEST_FOREIGN_ID
        if change=='roles':result['roles']=['PLATFORM_ADMIN']
        if change=='payload':result['payload']={**result['payload'],'sub':TEST_FOREIGN_ID}
        if change=='valid':result['valid']=1
        if change=='expiry':result['expires_at']=None
        if change=='error':result['error']='private-validator-diagnostic'
        return result
    b.validator.validate_token=altered;r=b.client.get('/api/iam-portal/policies',headers=header(b))
    assert r.status_code==503 and b.entries==[] and 'private-validator-diagnostic' not in r.text

def test_immutable_context_ignores_public_state_and_rejects_credential_change(boundary):
    b=boundary;token=b.sign();scope={'type':'http','method':'GET','path':'/context',
        'headers':[(b'authorization',('Bearer '+token).encode())],'app':b.app}
    request=Request(scope);request.state.request_context=ctx.RequestContext(UUID(TEST_FOREIGN_ID),'forged',('PLATFORM_ADMIN',))
    first=asyncio.run(ctx.get_current_request_context(request,b.validator));assert first.tenant_id==UUID(TEST_TENANT_ID)
    with pytest.raises(FrozenInstanceError):first.user_id='forged'
    assert asyncio.run(ctx.get_current_request_context(request,b.validator)) is first
    b.claims['sub']=TEST_FOREIGN_ID;scope['headers']=[(b'authorization',('Bearer '+b.sign()).encode())]
    with pytest.raises(HTTPException) as error:asyncio.run(ctx.get_current_request_context(request,b.validator))
    assert error.value.status_code==401 and b.validate.call_count==1

def test_user_identity_cannot_enable_unreviewed_handler(boundary):
    b=boundary;router=APIRouter();effect=Mock()
    @router.post('/unreviewed-effect')
    def effect_handler():effect();return {'executed':True}
    include_source_router(b.app,'legacy.router',router)
    r=b.client.post('/unreviewed-effect',headers=header(b),json={'approved':True,'tenant_id':TEST_TENANT_ID})
    assert r.status_code==501 and b.entries==[];effect.assert_not_called()


@pytest.mark.parametrize('path',['/api/v1/access-requests','/api/iam-portal/policies'])
@pytest.mark.parametrize('kind',['static','workload'])
def test_mutation_body_and_roles_cannot_promote_callers(boundary,path,kind):
    b=boundary;b.claims.update(sg_principal_type='workload',realm_access={'roles':['PLATFORM_ADMIN']})
    token='disposable-local-only' if kind=='static' else b.sign()
    r=b.client.post(path,headers={'Authorization':'Bearer '+token},json={
        'approved':True,'tenant_id':TEST_TENANT_ID,'user_id':TEST_USER_ID,'roles':['PLATFORM_ADMIN']})
    assert r.status_code==(401 if kind=='static' else 403)
    assert b.entries==[] and b.constructor.mock_calls==[] and b.db.mock_calls==[]


def test_cached_identity_still_rejects_changed_context_hints(boundary):
    b=boundary;scope={'type':'http','method':'GET','path':'/context','app':b.app,
        'headers':[(b'authorization',('Bearer '+b.sign()).encode())]};request=Request(scope)
    asyncio.run(ctx.get_current_request_context(request,b.validator))
    scope['headers'].append((b'x-tenant-id',TEST_FOREIGN_ID.encode()))
    with pytest.raises(HTTPException) as error:asyncio.run(ctx.get_current_request_context(request,b.validator))
    assert error.value.status_code==403 and b.validate.call_count==1


def test_policy_OpenAPI_retains_explicit_bearer_security(boundary):
    schema=boundary.app.openapi()
    assert schema['paths']['/api/iam-portal/policies']['get']['security']==[{'HTTPBearer':[]}]
    assert schema['components']['securitySchemes']['HTTPBearer']=={'type':'http','scheme':'bearer'}
