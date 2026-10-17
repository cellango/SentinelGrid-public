"""Actual gateway assembly, real RSA signatures and mocked IAM HTTP only.

No identity dependency overrides. The two data operations used for positive
checks are replaced with spies; no database/provider/model is contacted.
"""

from datetime import datetime, timezone
import json
import re
import time
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
import httpx
import jwt
from pydantic import ValidationError
import pytest

from app.main import app
from app.api import routes_alerts
from app.core.config import Settings
from app.core.request_identity import _BLOCKED, _PUBLIC
from sg_core import iam_verification as verifier
from sg_core.db import get_tenant_session
from sg_core.request_credentials import AuthCookieMiddleware, resolve_credentials
from sg_core.security import get_current_payload, get_current_tenant, get_verified_request_identity
from sg_core.user_principals import UserClientBinding, UserPrincipalSettings

_HTTP_CLIENT = httpx.Client
TENANT = "e53ae16f-4381-4da5-9992-8d8d85b1d0eb"
USER = "238699f6-5d17-48a0-935f-539c6d3594cf"
ISSUER = "https://identity.internal.test/realms/synthetic"
BINDING = dict(issuer=ISSUER, client_id="review-browser", tenant_id=TENANT,
               contract="keycloak-user-v1", service_accounts_enabled=False, token_exchange_enabled=False)


@pytest.fixture(scope="module")
def keys():
    return [rsa.generate_private_key(public_exponent=65537, key_size=2048) for _ in range(2)]


@pytest.fixture
def gateway(monkeypatch, keys):
    assert not app.dependency_overrides
    calls, opened = [], []
    claims = dict(sub=USER, tenant_id=TENANT, iss=ISSUER, aud="review-audience", azp="review-browser",
                  typ="Bearer", sg_principal_type="user", sg_identity_contract="keycloak-user-v1",
                  realm_access={"roles": ["SOC_ANALYST"]}, exp=int(time.time())+600, iat=int(time.time())-1)
    config = verifier.IAMVerificationSettings(_env_file=None, IAM_AGENT_URL="https://iam.internal.test",
                                             KEYCLOAK_CLIENT_ID="review-audience")
    policy = UserPrincipalSettings(_env_file=None, IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),))
    monkeypatch.setattr(app.state, "iam_verification_settings", config)
    monkeypatch.setattr(app.state, "user_principal_settings", policy)
    db = Mock()
    service = Mock()
    service.list_alerts.return_value = ([], 0)
    factory = Mock(return_value=service)
    monkeypatch.setattr(routes_alerts, "AlertService", factory)

    def session():
        opened.append(True)
        yield db

    app.dependency_overrides[get_tenant_session] = session
    state = SimpleNamespace(claims=claims, calls=calls, opened=opened, db=db, factory=factory,
                            policy=policy, config=config, unavailable=False)

    def sign(update=None, key=None):
        return jwt.encode({**claims, **(update or {})}, key or keys[0], algorithm="RS256", headers={"kid": "review-key"})

    state.sign = sign

    def iam_transport(request):
        calls.append(request)
        assert str(request.url) == "https://iam.internal.test/internal/iam/auth/validate-token"
        assert set(json.loads(request.content)) == {"token"}
        if state.unavailable:
            raise httpx.ConnectError("synthetic IAM outage")
        try:
            payload = jwt.decode(json.loads(request.content)["token"], keys[0].public_key(),
                                 algorithms=["RS256"], issuer=ISSUER, audience="review-audience")
        except jwt.PyJWTError:
            return httpx.Response(200, json={"valid": False, "error": "synthetic invalid token"})
        return httpx.Response(200, json=dict(valid=True, payload=payload, tenant_id=payload["tenant_id"],
                                            user_id=payload["sub"], roles=payload["realm_access"]["roles"],
                                            expires_at=datetime.fromtimestamp(payload["exp"], timezone.utc).isoformat()))

    def client(**kwargs):
        return _HTTP_CLIENT(transport=httpx.MockTransport(iam_transport), **kwargs)

    monkeypatch.setattr(verifier.httpx, "Client", client)
    state.client = TestClient(app)  # No lifespan/startup hooks or live services.
    yield state
    state.client.close()
    app.dependency_overrides.clear()


@pytest.mark.parametrize("form", ["bearer", "cookie", "marker", "same-bearer-and-cookie"])
def test_verified_user_reaches_actual_alert_route_once(gateway, form):
    token = gateway.sign()
    headers = {"Authorization": "Bearer " + token}
    if form != "bearer":
        headers["Cookie"] = "access_token=" + token
    if form == "cookie":
        del headers["Authorization"]
    if form == "marker":
        headers["Authorization"] = "Bearer session-cookie"
    headers.update({"X-Tenant-ID": TENANT, "X-Realm": "synthetic"})
    response = gateway.client.get("/api/v1/alerts/", headers=headers)
    assert response.status_code == 200 and response.json() == {"items": [], "total": 0}
    gateway.factory.assert_called_once_with(gateway.db, TENANT)
    assert len(gateway.calls) == 1 and gateway.opened == [True]


@pytest.mark.parametrize("extra", [
    {"tenant_id": str(uuid4())}, {"azp": "machine-client"}, {"sg_principal_type": "workload"},
    {"sg_principal_type": None}, {"sg_identity_contract": "other"}, {"typ": "ID"}, {"typ": "Refresh"},
    {"act": {"sub": str(uuid4())}}, {"may_act": {}}, {"client_id": "review-browser"},
])
def test_signed_workload_unknown_or_foreign_context_cannot_be_user(gateway, extra):
    response = gateway.client.get("/api/v1/alerts/", headers={"Authorization": "Bearer " + gateway.sign(extra)})
    assert response.status_code == 403
    assert gateway.opened == []
    gateway.factory.assert_not_called()


@pytest.mark.parametrize("headers", [
    [("Authorization", "Bearer one"), ("Authorization", "Bearer two")],
    [("Authorization", "Bearer one"), ("authorization", "Bearer one")],
    [("Authorization", "Basic one"), ("Cookie", "access_token=two")],
    [("Authorization", "Bearer one two"), ("Cookie", "access_token=two")],
    [("Authorization", "Bearer one,two")], [("Authorization", "")],
    [("Authorization", "Bearer session-cookie")],
    [("Cookie", "access_token=one; access_token=two")],
    [("Cookie", "access_token=one"), ("Cookie", "access_token=one")],
    [("Cookie", 'access_token="one"')], [("Cookie", "access_token=")],
    [("Cookie", "access_token")], [("Cookie", "access_token=session-cookie")],
    [("Authorization", "Bearer one"), ("Cookie", "access_token=two")],
])
def test_ambiguous_credentials_never_reach_iam_or_data(gateway, headers):
    response = gateway.client.get("/api/v1/alerts/", headers=headers)
    assert response.status_code == 401
    assert gateway.calls == [] and gateway.opened == []
    gateway.factory.assert_not_called()


@pytest.mark.parametrize("hints", [
    {"X-Tenant-ID": str(uuid4())}, {"X-Realm": "foreign"}, {"X-User-ID": str(uuid4())},
    {"X-Roles": "PLATFORM_ADMIN"}, {"X-Actor-ID": USER},
    {"X-Internal-Service-Token": "synthetic-service-token"}, {"X-Internal-Token": "synthetic-service-token"},
])
def test_valid_user_cannot_mix_forwarded_identity_or_workload_authority(gateway, hints):
    response = gateway.client.get("/api/v1/alerts/", headers={"Authorization": "Bearer " + gateway.sign(), **hints})
    assert response.status_code == 403 and gateway.opened == []


def test_administrator_role_never_bypasses_exact_tenant_binding(gateway):
    token = gateway.sign({"tenant_id": str(uuid4()), "realm_access": {"roles": ["PLATFORM_ADMIN", "TENANT_ADMIN"]}})
    response = gateway.client.get("/api/v1/alerts/", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 403 and gateway.opened == []


@pytest.mark.parametrize("failure, status", [("forged", 401), ("expired", 401), ("unavailable", 503), ("shared", 401), ("unconfigured", 503)])
def test_verifier_and_registration_fail_closed_before_actual_data(gateway, keys, monkeypatch, failure, status):
    token = gateway.sign()
    if failure == "forged": token = gateway.sign(key=keys[1])
    if failure == "expired": token = gateway.sign({"exp": 1})
    if failure == "unavailable": gateway.unavailable = True
    if failure == "shared": token = "synthetic-shared-token"
    if failure == "unconfigured": monkeypatch.setattr(app.state, "user_principal_settings", UserPrincipalSettings(_env_file=None))
    response = gateway.client.get("/api/v1/alerts/", headers={"Authorization": "Bearer " + token})
    assert response.status_code == status and gateway.opened == []
    gateway.factory.assert_not_called()


def test_legacy_versions_uses_verified_uuid_not_dashboard_tenant(gateway, monkeypatch):
    from app.api import routes_agents
    versions = Mock(return_value=(None, {}))
    monkeypatch.setattr(routes_agents, "_fetch_iam_agent_versions", versions)
    response = gateway.client.get("/api/agents/versions", headers={"Authorization": "Bearer " + gateway.sign()})
    assert response.status_code == 200
    versions.assert_called_once_with(TENANT)


def test_every_openapi_business_method_rejects_before_unconfigured_upstreams(gateway):
    checked = []
    for path, methods in app.openapi()["paths"].items():
        for method in methods:
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
                continue
            operation = (method.upper(), path)
            if operation in _PUBLIC or operation in _BLOCKED:
                continue
            concrete = re.sub(r"\{[^}]+\}", str(uuid4()), path)
            response = gateway.client.request(method, concrete)
            assert response.status_code == 401, (method, path, response.status_code)
            checked.append(operation)
    assert len(checked) >= 200
    assert gateway.opened == [] and gateway.calls == []


@pytest.mark.parametrize("method, path", sorted(_BLOCKED))
def test_workload_and_global_diagnostics_have_no_raw_token_bypass(gateway, method, path):
    response = gateway.client.request(method, path, headers={"Authorization": "Bearer " + gateway.sign()})
    assert response.status_code == 503 and gateway.opened == [] and gateway.calls == []


def test_exact_public_routes_keep_health_and_preauth_contracts(gateway, monkeypatch):
    assert gateway.client.get("/health").status_code == 200
    assert gateway.client.get("/").status_code == 200
    from app.api import routes_auth
    reached = []

    async def preauth(request, path, error_message):
        reached.append(path)
        return {"test": True}

    monkeypatch.setattr(routes_auth, "_proxy_pre_auth", preauth)
    for path in ("/api/v1/auth/login", "/api/v1/auth/refresh"):
        assert gateway.client.post(path, json={}).status_code == 200
    assert len(reached) == 2 and gateway.calls == []
    assert gateway.client.post("/api/v1/auth/login/other", json={}).status_code == 404


def test_payload_cookie_and_tenant_share_immutable_request_snapshot(gateway):
    small = FastAPI()
    small.state.iam_verification_settings = gateway.config
    small.add_middleware(AuthCookieMiddleware)

    @small.get("/identity")
    def identity(request: Request, payload: dict = Depends(get_current_payload), tenant: str = Depends(get_current_tenant)):
        payload["tenant_id"] = str(uuid4())
        payload["roles"].append("PLATFORM_ADMIN")
        verified = get_verified_request_identity(request)
        return {"tenant": tenant, "again": verified.payload(), "roles": verified.roles}

    client = TestClient(small)
    response = client.get("/identity", headers={"Cookie": "access_token=" + gateway.sign()})
    assert response.status_code == 200
    assert response.json()["tenant"] == response.json()["again"]["tenant_id"] == TENANT
    assert response.json()["roles"] == ["SOC_ANALYST"]
    assert len(gateway.calls) == 1
    assert client.get("/identity").status_code == 401


def test_mid_request_credential_replacement_cannot_reuse_identity(gateway):
    small = FastAPI()
    small.state.iam_verification_settings = gateway.config

    @small.get("/swap")
    def swap(request: Request):
        get_verified_request_identity(request)
        request.scope["headers"] = [(b"authorization", b"Bearer different-token")]
        get_verified_request_identity(request)
        pytest.fail("Changed credential reused previous identity")

    response = TestClient(small).get("/swap", headers={"Authorization": "Bearer " + gateway.sign()})
    assert response.status_code == 401 and len(gateway.calls) == 1


@pytest.mark.parametrize("update", [
    {"service_accounts_enabled": True}, {"service_accounts_enabled": 0}, {"token_exchange_enabled": True},
    {"token_exchange_enabled": 0}, {"tenant_id": "demo"}, {"tenant_id": str(uuid4()).upper()},
    {"issuer": ISSUER+"/"}, {"issuer": ISSUER+"?"}, {"contract": "other"}, {"client_id": "* "},
])
def test_ambiguous_or_unsafe_user_registration_is_rejected(update):
    with pytest.raises(ValidationError):
        UserClientBinding(**{**BINDING, **update})


def test_duplicate_exact_client_binding_is_rejected():
    with pytest.raises(ValidationError):
        UserPrincipalSettings(_env_file=None, IAM_USER_CLIENT_BINDINGS=(
            UserClientBinding(**BINDING), UserClientBinding(**BINDING)))


def test_gateway_configuration_owns_verifier_and_policy():
    config = Settings(_env_file=None, IAM_AGENT_URL="https://iam.other.internal.test",
                      KEYCLOAK_CLIENT_ID="owned-audience", IAM_TOKEN_VALIDATION_TIMEOUT=2,
                      IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),))
    assert config.verification_settings().IAM_AGENT_URL == config.IAM_AGENT_URL
    assert config.verification_settings().KEYCLOAK_CLIENT_ID == config.KEYCLOAK_CLIENT_ID
    assert config.verification_settings().IAM_TOKEN_VALIDATION_TIMEOUT == 2
    assert config.user_principal_settings().IAM_USER_CLIENT_BINDINGS[0].tenant_id == TENANT
    with pytest.raises(ValidationError):
        Settings(_env_file=None, IAM_AGENT_URL="https://user:password@iam.internal.test")


def test_shared_realm_can_register_two_exact_tenants_without_wildcards():
    config = UserPrincipalSettings(_env_file=None, IAM_USER_CLIENT_BINDINGS=(
        UserClientBinding(**BINDING), UserClientBinding(**{**BINDING, "tenant_id": str(uuid4())})))
    assert len(config.IAM_USER_CLIENT_BINDINGS) == 2


def test_credential_errors_have_configured_browser_cors_headers(gateway):
    response = gateway.client.get("/api/v1/alerts/", headers={"Origin": "http://localhost:3000", "Authorization": "Basic bad"})
    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert gateway.calls == [] and gateway.opened == []


def test_provider_fragment_uses_admin_owned_access_token_claims_and_no_machine_grants():
    from pathlib import Path
    fragment = json.loads((Path(__file__).resolve().parents[4]/"infra/keycloak/user-principal-contract.example.json").read_text())
    assert fragment["serviceAccountsEnabled"] is False
    assert fragment["attributes"]["standard.token.exchange.enabled"] == "false"
    mappers = fragment["protocolMappers"]
    assert {m["config"]["claim.name"]: m["config"]["claim.value"] for m in mappers} == {
        "sg_principal_type": "user", "sg_identity_contract": "keycloak-user-v1"}
    assert all(m["protocolMapper"] == "oidc-hardcoded-claim-mapper" and m["config"]["id.token.claim"] == "false" for m in mappers)


def test_username_and_session_id_are_not_user_classification(gateway):
    token = gateway.sign({"sg_principal_type": None, "preferred_username": "human-looking-user", "sid": str(uuid4())})
    response = gateway.client.get("/api/v1/alerts/", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 403 and gateway.opened == []


def test_typed_identity_in_request_state_does_not_authenticate(gateway):
    from sg_core.security import VerifiedRequestIdentity
    small = FastAPI()

    @small.get("/forged-state")
    def forged(request: Request):
        request.state.identity = VerifiedRequestIdentity(TENANT, USER, ("PLATFORM_ADMIN",), json.dumps(gateway.claims))
        return get_verified_request_identity(request).payload()

    response = TestClient(small).get("/forged-state", headers={"X-Tenant-ID": TENANT})
    assert response.status_code == 401 and gateway.calls == []


def test_production_registration_rejects_cleartext_issuer():
    with pytest.raises(ValidationError):
        UserPrincipalSettings(_env_file=None, ENVIRONMENT="production", IAM_USER_CLIENT_BINDINGS=(
            UserClientBinding(**{**BINDING, "issuer": "http://identity.internal.test/realms/synthetic"}),))
