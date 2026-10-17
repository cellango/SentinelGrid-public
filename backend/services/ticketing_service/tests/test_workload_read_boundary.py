"""Actual ticket router/dependency with real IAM validation in another app process.

Only HTTP/JWKS transport, the session factory and domain data reads are replaced.
No auth dependency override, socket, real SQL, provider or service startup is used.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
import pytest

from app.api import tickets
from app.core import database
from sg_core.iam_verification import IAMVerificationSettings
from sg_core import iam_verification
from sg_core.workload_reads import READ_CONTRACT, WorkloadReadBinding, WorkloadReadSettings, service_audience

ROOT = Path(__file__).resolve().parents[4]
HTTP_CLIENT = httpx.Client
ISSUER = "https://identity.internal.test/realms/synthetic"
SERVICE = "ticketing_service"

IAM_WORKER = '''
import json,sys
from types import SimpleNamespace
from app.services import token_validator as m
from app.models.auth import TokenValidationResponse
value=json.load(sys.stdin)
m.settings=SimpleNamespace(KEYCLOAK_URL="https://identity.internal.test",KEYCLOAK_REALM="synthetic",
    KEYCLOAK_CLIENT_ID="review-client",KEYCLOAK_ISSUER_BASE_URLS=[],JWKS_CACHE_TTL=60)
validator=m.TokenValidator(None)
# The fixture's owned JWKS replaces key transport. No token-selected key/URL.
validator._get_jwks_for_realm=lambda *args: {"keys":[value["jwk"]]}
print(TokenValidationResponse(**validator.validate_token(value["token"])).model_dump_json())
'''


@pytest.fixture(scope="module")
def key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def boundary(monkeypatch, key):
    tenant, subject, ticket_id = (str(uuid4()) for _ in range(3))
    config = IAMVerificationSettings(_env_file=None, IAM_AGENT_URL="https://iam.internal.test", KEYCLOAK_CLIENT_ID="review-client")
    binding = WorkloadReadBinding(issuer=ISSUER, client_id="ticket-reader", subject_id=subject,
        tenant_id=tenant, service_id=SERVICE, permission="ticketing.read", contract=READ_CONTRACT)
    app = FastAPI()
    app.state.iam_verification_settings = config
    app.state.workload_read_settings = WorkloadReadSettings(_env_file=None, SERVICE_READ_WORKLOAD_BINDINGS=(binding,))
    app.include_router(tickets.router, prefix="/api/v1/tickets")
    opened, calls = [], []
    db = Mock()

    def tenant_db(tenant_id):
        opened.append(tenant_id)
        yield db

    monkeypatch.setattr(database, "get_tenant_db", tenant_db)
    search = Mock(return_value=[])
    lookup = Mock(return_value=None)
    monkeypatch.setattr(tickets.ticket_service, "search_tickets", search)
    monkeypatch.setattr(tickets.ticket_service, "get_ticket", lookup)
    jwk = json.loads(RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update(kid="read-key", use="sig", alg="RS256")
    state = SimpleNamespace(tenant=tenant, subject=subject, ticket_id=ticket_id, db=db,
                            opened=opened, calls=calls, search=search, lookup=lookup, unavailable=False)

    def sign(path="/api/v1/tickets", query=b"", **updates):
        claims = dict(iss=ISSUER, aud=["review-client", service_audience(SERVICE)], sub=subject, tenant_id=tenant,
            typ="Bearer", azp="ticket-reader", realm_access={"roles": []}, iat=int(time.time())-1,
            exp=int(time.time())+30, jti=str(uuid4()), sg_principal_type="workload",
            sg_identity_contract=READ_CONTRACT, sg_permissions=["ticketing.read"],
            sg_request={"service_id": SERVICE, "method": "GET", "path": path,
                        "query_sha256": hashlib.sha256(query).hexdigest()})
        return jwt.encode({**claims, **updates}, key, algorithm="RS256", headers={"kid": "read-key"})

    def handler(request):
        calls.append(request)
        assert str(request.url) == "https://iam.internal.test/internal/iam/auth/validate-token"
        if state.unavailable:
            raise httpx.ConnectError("synthetic IAM outage")
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH":
            str(ROOT/"backend/libs")+os.pathsep+str(ROOT/"backend/agents/iam_agent")}
        # Real current IAM code runs in its own app namespace; no duplicate JWT
        # verifier and no monkeypatching one service's app package into another.
        result = subprocess.run([sys.executable, "-B", "-c", IAM_WORKER], cwd=ROOT, env=env, text=True,
            input=json.dumps({"token": json.loads(request.content)["token"], "jwk": jwk}),
            capture_output=True, timeout=10)
        assert result.returncode == 0, "Synthetic IAM worker failed"
        return httpx.Response(200, json=json.loads(result.stdout))

    def client(**kwargs):
        return HTTP_CLIENT(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(iam_verification.httpx, "Client", client)
    state.sign = sign
    state.client = TestClient(app)
    yield state
    state.client.close()


def test_actual_search_uses_verified_tenant_and_session_after_real_iam(boundary):
    token = boundary.sign(query=b"status=open&limit=3")
    response = boundary.client.get("/api/v1/tickets?status=open&limit=3", headers={"Authorization": "Bearer "+token})
    assert response.status_code == 200 and response.json() == []
    assert boundary.opened == [boundary.tenant] and len(boundary.calls) == 1
    boundary.search.assert_called_once_with(db=boundary.db, tenant_id=UUID(boundary.tenant),
        status="open", severity=None, category=None, limit=3, offset=0)


def test_actual_single_target_uses_both_target_and_verified_tenant(boundary):
    path = "/api/v1/tickets/"+boundary.ticket_id
    response = boundary.client.get(path, headers={"Authorization": "Bearer "+boundary.sign(path)})
    assert response.status_code == 404
    boundary.lookup.assert_called_once_with(boundary.db, boundary.ticket_id, UUID(boundary.tenant))
    assert boundary.opened == [boundary.tenant]


@pytest.mark.parametrize("kind, status", [("header-only", 401), ("shared", 401), ("foreign", 403),
    ("user", 403), ("audience", 403), ("path", 403), ("permission", 403), ("expired", 401), ("outage", 503)])
def test_actual_route_rejects_before_session_or_domain_read(boundary, kind, status):
    token = boundary.sign()
    headers = {"Authorization": "Bearer "+token}
    if kind == "header-only": headers = {"X-Tenant-ID": boundary.tenant}
    if kind == "shared": headers = {"Authorization": "Bearer synthetic-shared-token", "X-Tenant-ID": boundary.tenant}
    if kind == "foreign": headers = {"Authorization": "Bearer "+boundary.sign(tenant_id=str(uuid4()))}
    if kind == "user": headers = {"Authorization": "Bearer "+boundary.sign(sg_principal_type="user")}
    if kind == "audience": headers = {"Authorization": "Bearer "+boundary.sign(aud=["review-client"])}
    if kind == "path": headers = {"Authorization": "Bearer "+boundary.sign("/api/v1/tickets/"+str(uuid4()))}
    if kind == "permission": headers = {"Authorization": "Bearer "+boundary.sign(sg_permissions=["ticketing.write"])}
    if kind == "expired": headers = {"Authorization": "Bearer "+boundary.sign(exp=1)}
    if kind == "outage": boundary.unavailable = True
    response = boundary.client.get("/api/v1/tickets", headers=headers)
    assert response.status_code == status
    assert boundary.opened == []
    boundary.search.assert_not_called(); boundary.lookup.assert_not_called()


@pytest.mark.parametrize("method,path,body", [
    ("POST", "/api/v1/tickets", {"title": "synthetic", "approved": True}),
    ("PUT", "/api/v1/tickets/synthetic", {"status": "closed"}),
    ("POST", "/api/v1/tickets/synthetic/comments", {"comment": "synthetic"}),
])
def test_no_ticket_writer_or_provider_is_admitted_by_read_contract(boundary, method, path, body):
    response = boundary.client.request(method, path, json=body,
        headers={"Authorization": "Bearer "+boundary.sign(realm_access={"roles": ["PLATFORM_ADMIN"]})})
    assert response.status_code == 503
    assert boundary.opened == [] and boundary.calls == []


def test_actual_single_ticket_returns_only_the_tenant_bound_lookup(boundary):
    boundary.lookup.return_value = SimpleNamespace(id=UUID(boundary.ticket_id), tenant_id=UUID(boundary.tenant),
                                                  title="synthetic", status="open")
    path = "/api/v1/tickets/"+boundary.ticket_id
    response = boundary.client.get(path, headers={"Authorization": "Bearer "+boundary.sign(path)})
    assert response.status_code == 200
    assert response.json()["tenant_id"] == boundary.tenant
    boundary.lookup.assert_called_once_with(boundary.db, boundary.ticket_id, UUID(boundary.tenant))


def test_actual_tab_read_uses_the_same_tenant_scoped_ticket(boundary):
    boundary.lookup.return_value = SimpleNamespace(iam_data={"synthetic": True}, vm_data={}, cmdb_data={},
                                                  network_data={}, timeline_data={})
    path = "/api/v1/tickets/"+boundary.ticket_id+"/tabs/iam"
    response = boundary.client.get(path, headers={"Authorization": "Bearer "+boundary.sign(path)})
    assert response.status_code == 200 and response.json() == {"tab": "iam", "data": {"synthetic": True}}
    boundary.lookup.assert_called_once_with(boundary.db, UUID(boundary.ticket_id), UUID(boundary.tenant))


def test_unreviewed_router_alias_does_not_inherit_read_permission(boundary):
    alias = FastAPI()
    alias.include_router(tickets.router, prefix="/unreviewed/tickets")
    path = "/unreviewed/tickets"
    response = TestClient(alias).get(path, headers={"Authorization": "Bearer "+boundary.sign(path)})
    assert response.status_code == 503
    assert boundary.opened == [] and boundary.calls == []
