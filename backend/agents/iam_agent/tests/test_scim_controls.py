"""SCIM client binding, accurate observations and rejected provisioning boundaries."""

import asyncio
import hashlib
from uuid import uuid4
from unittest.mock import Mock
import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError, SecretStr
from app.api import scim
from app.core.config import settings, Settings
from app.core.scim_config import SCIMClientBinding
from app.services import scim_service as service


def binding(tenant, token, **changes):
    return SCIMClientBinding(
        tenant_id=tenant,
        realm="bound-realm",
        credential_digest=hashlib.sha256(token.encode()).hexdigest(),
        permissions=["users.read"],
        **changes,
    )


def user(tenant, **changes):
    return dict(
        id=str(uuid4()),
        username="synthetic-user",
        enabled=True,
        attributes={"tenant_id": [str(tenant)]},
        createdTimestamp=1700000000000,
        email="synthetic@example.test",
        **changes,
    )


@pytest.fixture
def setup(monkeypatch):
    tenant, foreign, client_id = uuid4(), uuid4(), uuid4()
    token = "synthetic-scim-credential-" + uuid4().hex
    b = binding(tenant, token)
    monkeypatch.setattr(settings, "SCIM_CLIENT_BINDINGS", {str(client_id): b})
    monkeypatch.setattr(settings, "SCIM_RATE_LIMIT_PER_MINUTE", 600)
    monkeypatch.setattr(settings, "KEYCLOAK_URL", "https://directory.invalid")
    monkeypatch.setattr(
        "app.services.role_directory_service.resolve_keycloak_admin_runtime_auth",
        lambda: Mock(
            user_realm_name="directory-admin",
            token_payload={"grant_type": "client_credentials"},
        ),
    )
    with service._rate_lock:
        service._rate_limit_state.clear()
    rows, calls = [], []
    db = Mock()
    db.add.side_effect = rows.append
    data = {"users": [user(foreign), user(tenant), user(tenant)], "status": 200}

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/token"):
            return httpx.Response(
                200, json={"access_token": "synthetic-directory-token"}
            )
        assert request.method == "GET" and request.url.path.startswith(
            "/admin/realms/bound-realm/users"
        )
        if data["status"] != 200:
            return httpx.Response(
                data["status"],
                headers={"Location": "https://foreign.invalid"},
                text="private provider message",
            )
        if "payload" in data:
            return httpx.Response(200, json=data["payload"])
        if request.url.path.endswith("/users"):
            start = int(request.url.params["first"])
            return httpx.Response(200, json=data["users"][start : start + 2])
        record = next(
            (
                u
                for u in data["users"]
                if u.get("id") == request.url.path.split("/")[-1]
            ),
            None,
        )
        return httpx.Response(200, json=record) if record else httpx.Response(404)

    directory = service.SCIMDirectoryService(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(service, "SCIMDirectoryService", lambda: directory)
    app = FastAPI()
    app.include_router(scim.router)
    app.dependency_overrides[scim.get_scim_session] = lambda: db
    with TestClient(app) as client:
        yield dict(
            tenant=tenant,
            foreign=foreign,
            client_id=client_id,
            token=token,
            binding=b,
            db=db,
            rows=rows,
            calls=calls,
            data=data,
            client=client,
            app=app,
        )


def request(s, method="get", path="/Users", **kwargs):
    return getattr(s["client"], method)(
        "/api/v1/scim/v2" + path,
        headers={"Authorization": "Bearer " + s["token"], **kwargs.pop("headers", {})},
        **kwargs,
    )


def test_list_filters_tenant_before_pagination_and_reports_actual_totals(setup):
    s = setup
    result = request(
        s,
        path="/Users?startIndex=2&count=1",
        headers={"X-Tenant-ID": str(s["foreign"]), "X-Realm": "foreign-realm"},
    )
    assert result.status_code == 200, result.text
    body = result.json()
    own = sorted(
        u["id"]
        for u in s["data"]["users"]
        if u["attributes"]["tenant_id"] == [str(s["tenant"])]
    )
    assert (
        body["totalResults"] == 2
        and body["itemsPerPage"] == 1
        and body["Resources"][0]["id"] == own[1]
    )
    assert (
        result.headers["content-type"].startswith("application/scim+json")
        and result.headers["cache-control"] == "no-store"
    )
    assert len(s["calls"]) == 4  # token, two short pages, empty page
    row = s["rows"][0]
    assert (
        row.tenant_id == s["tenant"]
        and row.actor_type == "internal_service"
        and row.performed_by is None
    )
    assert (
        row.metadata_json["scim_client_id"] == str(s["client_id"])
        and row.metadata_json["directory_realm"] == "bound-realm"
    )
    assert s["token"] not in str(row.metadata_json) and s[
        "binding"
    ].credential_digest.get_secret_value() not in str(row.metadata_json)
    s["db"].commit.assert_called_once()


@pytest.mark.parametrize(
    "query,total,items,start",
    [
        ("count=0", 2, 0, 1),
        ("count=-1", 2, 0, 1),
        ("startIndex=0&count=1000", 2, 2, 1),
        ("startIndex=99&count=2", 2, 0, 99),
    ],
)
def test_scim_pagination_semantics(setup, query, total, items, start):
    result = request(setup, path="/Users?" + query)
    assert result.status_code == 200, result.text
    body = result.json()
    assert (body["totalResults"], body["itemsPerPage"], body["startIndex"]) == (
        total,
        items,
        start,
    )


def test_get_projects_known_fields_without_fabricated_metadata_or_provider_secrets(
    setup,
):
    s = setup
    own = s["data"]["users"][1]
    own.update(
        credentials=[{"secret": "synthetic-only"}],
        firstName="Synthetic",
        lastName="User",
    )
    result = request(s, path="/Users/" + own["id"])
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["id"] == own["id"] and body["meta"]["created"].endswith("+00:00")
    assert (
        "externalId" not in body
        and "lastModified" not in body["meta"]
        and "attributes" not in body
        and "credentials" not in body
    )
    assert "synthetic-only" not in result.text


@pytest.mark.parametrize("kind", ["foreign", "missing"])
def test_foreign_and_missing_user_are_indistinguishable_not_found(setup, kind):
    s = setup
    identity = s["data"]["users"][0]["id"] if kind == "foreign" else str(uuid4())
    result = request(s, path="/Users/" + identity)
    assert result.status_code == 404 and result.json()["detail"] == "User not found"
    assert s["rows"][0].decision == "deny" and s["rows"][0].changes["status"] == 404


@pytest.mark.parametrize(
    "query",
    [
        "filter=userName%20eq%20%22a%22",
        "filter=",
        "sortBy=userName",
        "tenant_id=slug",
        "realm=foreign",
        "attributes=emails",
        "excludedAttributes=userName",
        "count=one",
        "count=999999999999999999",
        "count=1&count=2",
        "startIndex=1&startIndex=2",
    ],
)
def test_unsupported_and_ambiguous_queries_are_errors_without_provider_access(
    setup, query
):
    s = setup
    result = request(s, path="/Users?" + query)
    assert result.status_code == 400 and result.json()["schemas"] == [
        service.ERROR_SCHEMA
    ]
    if query.startswith("filter"):
        assert result.json()["scimType"] == "invalidFilter"
    assert not s["calls"] and s["rows"][0].decision == "deny"


BLOCKED = [
    ("post", "/Users"),
    ("put", "/Users/{id}"),
    ("patch", "/Users/{id}"),
    ("delete", "/Users/{id}"),
    ("get", "/Groups"),
    ("post", "/Groups"),
    ("get", "/Groups/{id}"),
    ("put", "/Groups/{id}"),
    ("patch", "/Groups/{id}"),
    ("delete", "/Groups/{id}"),
    ("post", "/Bulk"),
    ("post", "/Users/.search"),
    ("post", "/Groups/.search"),
]


@pytest.mark.parametrize("method,path", BLOCKED)
def test_provider_effects_and_unowned_groups_are_explicitly_blocked(
    setup, method, path
):
    s = setup
    url = path.format(id=uuid4())
    result = request(
        s,
        method,
        url,
        **(
            {
                "json": {
                    "tenant_id": str(s["foreign"]),
                    "realm": "foreign",
                    "approved": True,
                    "active": False,
                    "members": [{"value": str(uuid4())}],
                }
            }
            if method in {"post", "put", "patch"}
            else {}
        ),
    )
    assert result.status_code == 501, result.text
    assert (
        s["rows"][0].decision == "deny"
        and s["rows"][0].changes["provider_effects"] == []
    )
    assert not s["calls"]


@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "Basic synthetic",
        "Bearer wrong",
        "Bearer " + "a" * 513,
        "Bearer " + "a" * 31,
        "Bearer " + "a" * 64 + " ",
        "Bearer " + "a" * 32 + "\tvalue",
    ],
)
def test_invalid_auth_never_uses_provider_or_audit_or_populates_rate_cache(
    setup, authorization
):
    s = setup
    headers = {} if authorization is None else {"Authorization": authorization}
    result = s["client"].get("/api/v1/scim/v2/Users", headers=headers)
    assert result.status_code == 401 and result.headers["www-authenticate"] == "Bearer"
    assert not s["calls"] and not s["rows"] and not service._rate_limit_state


def test_duplicate_authentication_headers_are_rejected(setup):
    s = setup
    result = s["client"].get(
        "/api/v1/scim/v2/Users",
        headers=[
            ("Authorization", "Bearer " + s["token"]),
            ("Authorization", "Bearer " + s["token"]),
        ],
    )
    assert result.status_code == 401 and not s["calls"]


def test_rate_limit_keys_are_known_clients_not_credentials(setup, monkeypatch):
    s = setup
    monkeypatch.setattr(settings, "SCIM_RATE_LIMIT_PER_MINUTE", 1)
    assert request(s).status_code == 200
    assert request(s).status_code == 429
    assert set(service._rate_limit_state) == {str(s["client_id"])}
    assert s["token"] not in repr(service._rate_limit_state)


def test_read_permission_is_explicit_not_inferred_from_a_valid_token(
    setup, monkeypatch
):
    s = setup
    monkeypatch.setattr(
        settings,
        "SCIM_CLIENT_BINDINGS",
        {
            str(s["client_id"]): s["binding"].model_copy(
                update={"permissions": frozenset()}
            )
        },
    )
    result = request(s)
    assert result.status_code == 403 and not s["calls"]


def test_legacy_token_map_and_default_realm_never_select_authority(setup, monkeypatch):
    s = setup
    monkeypatch.setattr(settings, "SCIM_CLIENT_BINDINGS", {})
    monkeypatch.setattr(settings, "SCIM_BEARER_TOKEN", s["token"])
    monkeypatch.setattr(settings, "SCIM_DEFAULT_TENANT_ID", str(s["tenant"]))
    result = request(s)
    assert result.status_code == 401 and not s["calls"]


@pytest.mark.parametrize("status", [302, 401, 403, 404, 429, 500])
def test_provider_failures_never_become_empty_success_or_leak_details(setup, status):
    s = setup
    s["data"]["status"] = status
    result = request(s)
    assert result.status_code == 503 and "private provider" not in result.text
    assert s["rows"][0].event_type == "scim_rejected"
    assert all(r.method == "GET" or r.url.path.endswith("/token") for r in s["calls"])


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        [{"id": "bad"}],
        [
            {
                "id": str(uuid4()),
                "enabled": "true",
                "attributes": {"tenant_id": [str(uuid4())]},
            }
        ],
    ],
)
def test_malformed_directory_data_is_an_error_not_empty_success(setup, payload):
    s = setup
    s["data"]["payload"] = payload
    assert request(s).status_code == 503


@pytest.mark.parametrize(
    "change",
    [
        {"attributes": {}},
        {"attributes": {"tenant_id": ["slug"]}},
        {"attributes": {"tenant_id": [str(uuid4()), str(uuid4())]}},
        {"username": ""},
        {"createdTimestamp": True},
    ],
)
def test_unverified_membership_or_resource_fields_block_the_read(setup, change):
    s = setup
    s["data"]["users"][1].update(change)
    assert request(s).status_code == 503


def test_duplicate_and_oversized_inventory_cannot_claim_totals(setup):
    s = setup
    s["data"]["users"] = [s["data"]["users"][1]] * 2
    assert request(s).status_code == 503
    s["data"]["users"] = [user(s["tenant"]) for _ in range(101)]
    result = request(s)
    assert result.status_code == 400 and result.json()["scimType"] == "tooMany"


@pytest.mark.parametrize("failure", ["flush", "commit"])
def test_audit_failure_prevents_successful_read_response(setup, failure):
    s = setup
    getattr(s["db"], failure).side_effect = RuntimeError("private database details")
    result = request(s)
    assert (
        result.status_code == 503
        and "Resources" not in result.json()
        and "private" not in result.text
    )
    s["db"].rollback.assert_called_once()


def test_discovery_advertises_only_current_capabilities_without_auth(setup):
    s = setup
    result = s["client"].get("/api/v1/scim/v2/ServiceProviderConfig")
    assert result.status_code == 200
    for capability in ["patch", "bulk", "filter", "changePassword", "sort", "etag"]:
        assert result.json()[capability]["supported"] is False
    assert not s["calls"] and not s["rows"]


def config(bindings):
    return Settings(
        _env_file=None, ENVIRONMENT="development", SCIM_CLIENT_BINDINGS=bindings
    )


@pytest.mark.parametrize(
    "change",
    [
        {"tenant_id": "slug"},
        {"realm": "../foreign"},
        {"realm": ".."},
        {"credential_digest": "plaintext"},
        {"permissions": ["users.write"]},
        {"extra": "authority"},
    ],
)
def test_binding_configuration_rejects_ambiguous_or_unsupported_authority(change):
    token = "synthetic-scim-credential-" + uuid4().hex
    data = dict(
        tenant_id=str(uuid4()),
        realm="bound",
        credential_digest=hashlib.sha256(token.encode()).hexdigest(),
        permissions=["users.read"],
    )
    data.update(change)
    with pytest.raises(ValidationError):
        config({str(uuid4()): data})


def test_duplicate_credentials_and_conflicting_tenant_realms_are_rejected():
    token = "synthetic-scim-credential-" + uuid4().hex
    tenant = uuid4()
    b = binding(tenant, token)
    with pytest.raises(ValidationError):
        config({str(uuid4()): b, str(uuid4()): b})
    with pytest.raises(ValidationError):
        config(
            {
                str(uuid4()): b,
                str(uuid4()): b.model_copy(
                    update={
                        "realm": "foreign",
                        "credential_digest": SecretStr(
                            hashlib.sha256(b"other-synthetic-token").hexdigest()
                        ),
                    }
                ),
            }
        )


def test_config_secrets_are_hidden_and_no_clients_is_the_default(monkeypatch):
    monkeypatch.delenv("SCIM_CLIENT_BINDINGS", raising=False)
    c = config({})
    assert c.SCIM_CLIENT_BINDINGS == {}
    token = "synthetic-scim-credential-" + uuid4().hex
    b = binding(uuid4(), token)
    c = config({str(uuid4()): b})
    assert (
        b.credential_digest.get_secret_value() not in repr(c)
        and b.credential_digest.get_secret_value() not in c.model_dump_json()
    )


def test_binding_change_during_observation_cannot_return_user_data(setup, monkeypatch):
    s = setup
    context = service.verify_scim_token("Bearer " + s["token"])
    directory = Mock()

    async def read(*args):
        monkeypatch.setattr(settings, "SCIM_CLIENT_BINDINGS", {})
        return [{"id": str(uuid4())}]

    directory.read = read
    with pytest.raises(service.SCIMError) as error:
        asyncio.run(
            service.SCIMService(s["db"], context, directory=directory).handle(
                "list_users"
            )
        )
    assert error.value.status_code == 403 and s["rows"][0].decision == "deny"


@pytest.mark.parametrize("method", ["configure", "test", "list"])
def test_outbound_scim_placeholders_cannot_report_configured_or_connected(method):
    from app.services.protocol_manager import ProtocolManager, ProtocolType

    manager = ProtocolManager.__new__(ProtocolManager)
    with pytest.raises(HTTPException) as error:
        if method == "configure":
            manager.configure_scim_client("https://foreign.invalid", "synthetic-only")
        elif method == "test":
            manager.test_protocol_connection("synthetic", ProtocolType.SCIM2)
        else:
            manager.list_protocol_configurations(ProtocolType.SCIM2)
    assert error.value.status_code == 501


def test_outbound_scim_route_does_not_construct_provider_clients(setup):
    from app.api import protocols
    from app.api.request_context import RequestContext, get_current_request_context

    s = setup
    s["app"].include_router(protocols.router)
    s["app"].dependency_overrides[get_current_request_context] = lambda: RequestContext(
        s["tenant"], str(uuid4()), ("TENANT_ADMIN",)
    )
    s["app"].dependency_overrides[protocols.get_protocol_manager] = lambda: pytest.fail(
        "No provider initialization for unsupported SCIM"
    )
    result = s["client"].post(
        "/internal/iam/protocols/scim",
        json={
            "scim_endpoint": "https://foreign.invalid/scim",
            "bearer_token": "synthetic-only",
        },
    )
    assert result.status_code == 501 and "configured_at" not in result.text
    assert not s["calls"]


@pytest.mark.parametrize("client", ["slug", "00000000000000000000000000000001"])
def test_configuration_requires_canonical_client_uuids(client):
    with pytest.raises(ValidationError):
        config({client: binding(uuid4(), "synthetic-scim-credential-" + uuid4().hex)})


def test_configuration_bounds_number_of_clients():
    bindings = {
        str(uuid4()): binding(uuid4(), "synthetic-scim-credential-" + uuid4().hex)
        for _ in range(65)
    }
    with pytest.raises(ValidationError):
        config(bindings)


def test_authenticated_rate_limit_is_serialized_across_concurrent_calls(
    setup, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace

    s = setup
    monkeypatch.setattr(settings, "SCIM_RATE_LIMIT_PER_MINUTE", 10)
    monkeypatch.setattr(service, "time", SimpleNamespace(monotonic=lambda: 120.0))

    def authenticate(_):
        try:
            return service.verify_scim_token("Bearer " + s["token"])
        except service.SCIMError as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(authenticate, range(20)))
    assert sum(isinstance(row, service.SCIMContext) for row in results) == 10
    assert results.count(429) == 10
    assert set(service._rate_limit_state) == {str(s["client_id"])}


@pytest.mark.parametrize(
    "method,path", [("get", "/Users"), ("patch", "/Users/" + str(uuid4()))]
)
def test_legacy_admin_middleware_does_not_reinterpret_scim_credentials(
    setup, monkeypatch, method, path
):
    from app.middleware.admin_audit import AdminAuditMiddleware
    from app.services import keycloak_client, audit_service

    s = setup
    legacy_client = Mock()
    legacy_audit = Mock()
    monkeypatch.setattr(keycloak_client, "KeycloakClient", legacy_client)
    monkeypatch.setattr(audit_service.AuditService, "log_auth_event", legacy_audit)
    app = FastAPI()
    app.include_router(scim.router)
    app.add_middleware(AdminAuditMiddleware)
    app.dependency_overrides[scim.get_scim_session] = lambda: s["db"]
    with TestClient(app) as client:
        result = getattr(client, method)(
            "/api/v1/scim/v2" + path, headers={"Authorization": "Bearer " + s["token"]}
        )
    assert result.status_code == (200 if method == "get" else 501)
    legacy_client.assert_not_called()
    legacy_audit.assert_not_called()
    assert len(s["rows"]) == 1


def test_existing_case_sensitive_dotenv_loading_is_preserved(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SCIM_RATE_LIMIT_PER_MINUTE", raising=False)
    monkeypatch.setenv("scim_rate_limit_per_minute", "12")
    (tmp_path / ".env").write_text("SCIM_RATE_LIMIT_PER_MINUTE=77\n")
    assert Settings(ENVIRONMENT="development").SCIM_RATE_LIMIT_PER_MINUTE == 77
