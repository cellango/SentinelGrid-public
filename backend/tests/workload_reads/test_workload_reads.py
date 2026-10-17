"""Real IAM/RSA receipts plus the actual shared workload read dependency."""

import asyncio
import hashlib
import time
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

# Reuse the established real IAM validator/model fixture, not another JWT verifier.
from backend.tests.gateway_identity.test_verifier_boundary import boundary, keys  # noqa: F401
from sg_core.dependencies import get_current_tenant, service_tenant_dependency
from sg_core.workload_reads import (
    READ_CONTRACT, READ_OPERATIONS, WorkloadReadBinding, WorkloadReadSettings,
    service_audience,
)


@pytest.fixture
def read_client(boundary):
    boundary.claims.update(typ="Bearer", azp="review-worker", sg_principal_type="workload",
                           sg_identity_contract=READ_CONTRACT, exp=int(time.time())+30,
                           aud=["review-client", service_audience("ticketing_service")],
                           jti=str(uuid4()), sg_permissions=["ticketing.read"])
    binding = WorkloadReadBinding(issuer=boundary.claims["iss"], client_id="review-worker",
        subject_id=boundary.claims["sub"], tenant_id=boundary.claims["tenant_id"],
        service_id="ticketing_service", permission="ticketing.read", contract=READ_CONTRACT)
    app = FastAPI()
    app.state.iam_verification_settings = boundary.config
    app.state.workload_read_settings = WorkloadReadSettings(_env_file=None, SERVICE_READ_WORKLOAD_BINDINGS=(binding,))
    reached = []
    tenant = service_tenant_dependency("ticketing_service")

    @app.get("/api/v1/tickets")
    def tickets(tenant_id: UUID = Depends(tenant)):
        reached.append(tenant_id)
        return {"tenant_id": str(tenant_id)}

    @app.get("/api/v1/tickets/{ticket_id}")
    def ticket(ticket_id: str, tenant_id: UUID = Depends(tenant)):
        reached.append(tenant_id)
        return {"tenant_id": str(tenant_id), "ticket_id": ticket_id}

    @app.post("/api/v1/tickets")
    def create(tenant_id: UUID = Depends(tenant)):
        pytest.fail("Read identity admitted mutation")

    def token(path="/api/v1/tickets", query=b"", **updates):
        claims = {**boundary.claims, "sg_request": {
            "service_id": "ticketing_service", "method": "GET", "path": path,
            "query_sha256": hashlib.sha256(query).hexdigest()}, **updates}
        return boundary.sign(claims)

    return app, TestClient(app), reached, token, binding


def test_real_iam_signed_read_reaches_only_registered_tenant(boundary, read_client):
    _, client, reached, token, _ = read_client
    response = client.get("/api/v1/tickets?status=open", headers={"Authorization": "Bearer " + token(query=b"status=open")})
    assert response.status_code == 200
    assert reached == [UUID(boundary.claims["tenant_id"])]
    assert len(boundary.calls) == 1


def test_concrete_target_and_query_are_signed_not_selected_by_body(boundary, read_client):
    _, client, reached, token, _ = read_client
    target = str(uuid4())
    credential = token("/api/v1/tickets/" + target)
    assert client.get("/api/v1/tickets/" + target, headers={"Authorization": "Bearer " + credential}).status_code == 200
    reached.clear()
    for path in ("/api/v1/tickets/"+str(uuid4()), "/api/v1/tickets/"+target+"?scope=all"):
        assert client.get(path, headers={"Authorization": "Bearer " + credential}).status_code == 403
    assert reached == []


@pytest.mark.parametrize("updates", [
    {"sg_principal_type": "user"}, {"sg_principal_type": None}, {"sg_identity_contract": "keycloak-user-v1"},
    {"typ": "Refresh"}, {"typ": "ID"}, {"act": {}}, {"may_act": {}}, {"sg_actor": str(uuid4())},
    {"azp": "other-worker"}, {"sub": str(uuid4())}, {"tenant_id": str(uuid4())},
    {"sg_permissions": ["ticketing.write"]}, {"sg_permissions": ["ticketing.read", "ticketing.write"]},
    {"sg_permissions": "ticketing.read"}, {"aud": ["review-client"]},
    {"aud": ["review-client", service_audience("scanner_orchestrator")]},
    {"aud": ["review-client", service_audience("ticketing_service"), "other"]},
    {"aud": ["review-client", service_audience("ticketing_service"), "review-client"]},
    {"client_id": "other-worker"},
])
def test_verified_wrong_kind_caller_tenant_or_permission_is_denied(read_client, updates):
    _, client, reached, token, _ = read_client
    response = client.get("/api/v1/tickets", headers={"Authorization": "Bearer " + token(**updates)})
    assert response.status_code == 403 and reached == []


@pytest.mark.parametrize("headers", [
    {}, {"X-Tenant-ID": str(uuid4())}, {"Authorization": "Bearer synthetic-shared-token", "X-Tenant-ID": str(uuid4())},
    [("Authorization", "Bearer one"), ("Authorization", "Bearer two")],
    {"Authorization": "Basic one", "Cookie": "access_token=two"},
])
def test_missing_header_only_shared_or_conflicting_credentials_do_not_reach_iam(boundary, read_client, headers):
    _, client, reached, _, _ = read_client
    response = client.get("/api/v1/tickets", headers=headers)
    assert response.status_code == 401
    assert reached == [] and boundary.calls == []


@pytest.mark.parametrize("headers", [
    {"X-Tenant-ID": str(uuid4())}, {"X-Realm": "foreign"}, {"X-User-ID": str(uuid4())},
    {"X-Roles": "PLATFORM_ADMIN"}, {"X-Internal-Service-Token": "synthetic-shared-token"},
    {"X-Internal-Token": "synthetic-shared-token"},
])
def test_hints_cannot_override_authenticated_workload(read_client, headers):
    _, client, reached, token, _ = read_client
    response = client.get("/api/v1/tickets", headers={"Authorization": "Bearer " + token(), **headers})
    assert response.status_code == 403 and reached == []


def test_duplicates_of_matching_tenant_hint_are_not_authority(boundary, read_client):
    _, client, reached, token, _ = read_client
    response = client.get("/api/v1/tickets", headers=[("Authorization", "Bearer "+token()),
        ("X-Tenant-ID", boundary.claims["tenant_id"]), ("X-Tenant-ID", boundary.claims["tenant_id"])])
    assert response.status_code == 403 and reached == []


def test_signed_administrator_roles_cannot_turn_read_into_mutation(boundary, read_client):
    _, client, reached, token, _ = read_client
    response = client.post("/api/v1/tickets", headers={"Authorization": "Bearer " + token(
        realm_access={"roles": ["PLATFORM_ADMIN", "INTERNAL_SERVICE"]})},
        json={"tenant_id": str(uuid4()), "approved": True, "sg_principal_type": "user"})
    assert response.status_code == 503 and reached == [] and boundary.calls == []


@pytest.mark.parametrize("updates", [
    {"exp": 1}, {"exp": int(time.time())+300}, {"iat": int(time.time())-65},
])
def test_expired_or_overlong_workload_token_is_not_admitted(read_client, updates):
    _, client, reached, token, _ = read_client
    response = client.get("/api/v1/tickets", headers={"Authorization": "Bearer " + token(**updates)})
    assert response.status_code == 401 and reached == []


def test_forgery_and_iam_outage_never_fall_back_to_tenant_hint(boundary, read_client):
    _, client, reached, token, _ = read_client
    credential = token()
    parts = credential.split(".")
    forged = ".".join(parts[:2] + [parts[2][:-5]+"aaaaa"])
    assert client.get("/api/v1/tickets", headers={"Authorization": "Bearer "+forged}).status_code == 401
    import httpx
    boundary.error = httpx.ConnectError("synthetic outage")
    assert client.get("/api/v1/tickets", headers={"Authorization": "Bearer "+credential}).status_code == 503
    assert reached == []


@pytest.mark.parametrize("query", ["x=1&x=2", "x=2&x=1", "status=closed", "status=%6fpen"])
def test_query_bytes_cannot_be_reordered_or_reencoded(read_client, query):
    _, client, reached, token, _ = read_client
    response = client.get("/api/v1/tickets?"+query, headers={"Authorization": "Bearer "+token(query=b"status=open")})
    assert response.status_code == 403 and reached == []


def test_get_body_is_not_a_delegation_channel(read_client):
    _, client, reached, token, _ = read_client
    response = client.request("GET", "/api/v1/tickets", headers={"Authorization": "Bearer "+token()},
                              json={"tenant_id": str(uuid4()), "approved": True})
    assert response.status_code == 403 and reached == []


def test_same_bound_read_can_repeat_until_expiry_and_is_not_one_time(read_client):
    _, client, reached, token, _ = read_client
    headers = {"Authorization": "Bearer "+token()}
    for _ in range(2): assert client.get("/api/v1/tickets", headers=headers).status_code == 200
    assert len(reached) == 2


def test_empty_or_malformed_registration_fails_closed(read_client):
    app, client, reached, token, _ = read_client
    for config in (WorkloadReadSettings(_env_file=None), {"tenant_id": "forged"}):
        app.state.workload_read_settings = config
        assert client.get("/api/v1/tickets", headers={"Authorization": "Bearer "+token()}).status_code == 503
    assert reached == []


@pytest.mark.parametrize("changes", [
    {"tenant_id": "demo"}, {"subject_id": "service-account-worker"}, {"client_id": "*"},
    {"issuer": "https://user:password@identity.test/realms/synthetic"}, {"issuer": "https://identity.test/realms/synthetic?"},
    {"issuer": "https://identity.test:invalid/realms/synthetic"},
    {"permission": "ticketing.write"}, {"permission": "scan.read_results"},
    {"service_id": "unknown"}, {"contract": "keycloak-user-v1"},
])
def test_unsafe_or_mixed_registration_is_rejected(read_client, changes):
    *_, binding = read_client
    with pytest.raises(ValidationError): WorkloadReadBinding(**{**binding.model_dump(), **changes})


def test_duplicate_and_non_https_production_registrations_fail(read_client):
    *_, binding = read_client
    with pytest.raises(ValidationError):
        WorkloadReadSettings(_env_file=None, SERVICE_READ_WORKLOAD_BINDINGS=(binding, binding))
    with pytest.raises(ValidationError):
        WorkloadReadSettings(_env_file=None, ENVIRONMENT="production", SERVICE_READ_WORKLOAD_BINDINGS=(
            WorkloadReadBinding(**{**binding.model_dump(), "issuer": "http://identity.test/realms/synthetic"}),))


def test_unscoped_legacy_dependency_and_unknown_service_never_authenticate():
    with pytest.raises(HTTPException) as error: asyncio.run(get_current_tenant())
    assert error.value.status_code == 503
    with pytest.raises(ValueError): service_tenant_dependency("model-selected-service")
    assert service_tenant_dependency("ticketing_service") is service_tenant_dependency("ticketing_service")


@pytest.mark.parametrize("service, path", list(READ_OPERATIONS))
def test_every_selected_read_adapter_binds_its_own_service(boundary, service, path):
    # Exercise dependency dispatch for each owned route declaration. This is not
    # qualification of those handlers' provider/SQL/runtime behavior.
    permission = READ_OPERATIONS[(service, path)]
    app = FastAPI()
    app.state.iam_verification_settings = boundary.config
    binding = WorkloadReadBinding(issuer=boundary.claims["iss"], client_id="review-worker",
        subject_id=boundary.claims["sub"], tenant_id=boundary.claims["tenant_id"], service_id=service,
        permission=permission, contract=READ_CONTRACT)
    app.state.workload_read_settings = WorkloadReadSettings(_env_file=None, SERVICE_READ_WORKLOAD_BINDINGS=(binding,))
    dependency = service_tenant_dependency(service)

    @app.get(path)
    def endpoint(tenant: UUID = Depends(dependency)):
        return {"tenant": str(tenant)}

    concrete = path
    for variable in ("ticket_id", "tab_name", "scan_id"):
        concrete = concrete.replace("{" + variable + "}", str(uuid4()))
    claims = {**boundary.claims, "exp": int(time.time())+30, "typ": "Bearer", "azp": "review-worker",
        "aud": ["review-client", service_audience(service)], "jti": str(uuid4()),
        "sg_principal_type": "workload", "sg_identity_contract": READ_CONTRACT, "sg_permissions": [permission],
        "sg_request": {"service_id": service, "method": "GET", "path": concrete,
                       "query_sha256": hashlib.sha256(b"").hexdigest()}}
    response = TestClient(app).get(concrete, headers={"Authorization": "Bearer "+boundary.sign(claims)})
    assert response.status_code == 200 and response.json() == {"tenant": boundary.claims["tenant_id"]}


@pytest.mark.parametrize("service, path", [("scanner_orchestrator", "/scans"), ("soar_service", "/soar/ootb")])
def test_unqualified_domain_reads_remain_unavailable_before_iam(boundary, service, path):
    app = FastAPI()
    dependency = service_tenant_dependency(service)

    @app.get(path)
    def unqualified(tenant: UUID = Depends(dependency)):
        pytest.fail("Unqualified domain read admitted")

    response = TestClient(app).get(path, headers={"Authorization": "Bearer "+boundary.sign()})
    assert response.status_code == 503 and boundary.calls == []


@pytest.mark.parametrize("request_id", [None, "not-a-uuid", "00000000-0000-0000-0000-000000000000"])
def test_invalid_signed_request_ids_do_not_authenticate(read_client, request_id):
    _, client, reached, token, _ = read_client
    assert client.get("/api/v1/tickets", headers={"Authorization": "Bearer "+token(jti=request_id)}).status_code == (401 if request_id is None else 403)
    assert reached == []
