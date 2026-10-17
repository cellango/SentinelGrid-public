"""NHI authority, disabled defaults, bounded input and secret response boundaries."""

from datetime import datetime, timezone
import hashlib
from uuid import UUID, uuid4
from unittest.mock import Mock
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app.api import nhi, api_keys
from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    get_entitlement_session,
)
from app.api.auth import get_token_validator
from app.core.config import Settings, settings
from app.models.service_account import ServiceAccount
from app.services.nhi_service import NHIService
from app.services.token_validator import TokenValidator


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setattr(settings, "IAM_ENABLE_SERVICE_ACCOUNTS", True)
    caller = RequestContext(uuid4(), str(uuid4()), ("TENANT_ADMIN",))
    db = Mock()
    rows = []
    db.add.side_effect = rows.append

    def flush():
        for row in rows:
            if isinstance(row, ServiceAccount):
                row.created_at = row.updated_at = datetime.now(timezone.utc)

    db.flush.side_effect = flush
    app = FastAPI()
    app.include_router(nhi.router)
    app.include_router(api_keys.router)
    app.dependency_overrides[get_current_request_context] = lambda: caller
    app.dependency_overrides[get_entitlement_session] = lambda: db
    with TestClient(app) as client:
        yield caller, db, rows, app, client


OPERATIONS = [
    ("post", "", {"name": "synthetic"}),
    ("get", "", None),
    ("get", "/expiring", None),
    ("get", "/{id}", None),
    ("post", "/{id}/rotate", {"expected_version": 1}),
    ("post", "/{id}/deactivate", {"expected_version": 1}),
    ("post", "/{id}/activate", {"expected_version": 1}),
    ("delete", "/{id}", {"expected_version": 1}),
]


@pytest.mark.parametrize("method,path,payload", OPERATIONS)
def test_all_routes_require_admin_before_storage(setup, method, path, payload):
    caller, db, _, app, client = setup
    app.dependency_overrides[get_current_request_context] = lambda: RequestContext(
        caller.tenant_id, caller.user_id, ()
    )
    result = client.request(
        method,
        "/api/v1/nhi/service-accounts" + path.format(id=uuid4()),
        **({"json": payload} if payload else {}),
    )
    assert result.status_code == 403
    db.query.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.parametrize("method,path,payload", OPERATIONS)
def test_disabled_feature_never_touches_storage(
    setup, monkeypatch, method, path, payload
):
    _, db, _, _, client = setup
    monkeypatch.setattr(settings, "IAM_ENABLE_SERVICE_ACCOUNTS", False)
    result = client.request(
        method,
        "/api/v1/nhi/service-accounts" + path.format(id=uuid4()),
        **({"json": payload} if payload else {}),
    )
    assert result.status_code == 501
    db.query.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.parametrize(
    "value",
    [
        {"tenant_id": str(uuid4())},
        {"owner_user_id": str(uuid4())},
        {"created_by": str(uuid4())},
        {"roles": ["PLATFORM_ADMIN"]},
        {"metadata": {"provider": "keycloak"}},
        {"rotation_days": True},
        {"rotation_days": 0},
        {"rotation_days": 366},
        {"name": "   "},
        {"name": "x\nforged-log"},
        {"description": "x" * 4097},
    ],
)
def test_create_input_cannot_assign_authority_or_unbounded_policy(setup, value):
    _, db, _, _, client = setup
    result = client.post(
        "/api/v1/nhi/service-accounts", json={"name": "synthetic", **value}
    )
    assert result.status_code == 422
    db.add.assert_not_called()


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"expected_version": True},
        {"expected_version": 0},
        {"expected_version": "1"},
        {"expected_version": 1, "approved": True},
        {"expected_version": 1, "tenant_id": str(uuid4())},
        {"expected_version": 1, "reason": "x" * 1001},
    ],
)
def test_transition_requires_exact_bounded_version_contract(setup, value):
    _, db, _, _, client = setup
    result = client.post(
        "/api/v1/nhi/service-accounts/" + str(uuid4()) + "/rotate", json=value
    )
    assert result.status_code == 422
    db.query.assert_not_called()


def test_committed_creation_returns_secret_once_with_no_store_headers(setup, caplog):
    caller, db, rows, _, client = setup
    result = client.post("/api/v1/nhi/service-accounts", json={"name": "synthetic"})
    assert result.status_code == 201, result.text
    payload = result.json()
    secret = payload["client_secret"]
    row = rows[0]
    assert (
        result.headers["cache-control"] == "no-store"
        and result.headers["pragma"] == "no-cache"
    )
    assert payload["owner_user_id"] == caller.user_id == payload["created_by"]
    assert row.secret_hash == hashlib.sha256(secret.encode()).hexdigest()
    assert secret not in repr(rows) and secret not in caplog.text
    assert (
        payload["credential_scope"] == "local_registry_only"
        and payload["provider_status"] == "not_integrated"
    )
    assert "secret_hash" not in payload
    event = rows[1]
    assert event.performed_by == UUID(caller.user_id) and event.subject_id == row.id
    assert secret not in str(event.changes) and row.secret_hash not in str(
        event.changes
    )
    db.commit.assert_called_once()
    # Existing read shapes never include either the digest or plaintext.
    db.query.return_value.filter.return_value.filter.return_value.first.return_value = (
        row
    )
    read = client.get("/api/v1/nhi/service-accounts/" + payload["id"])
    assert (
        read.status_code == 200
        and "client_secret" not in read.json()
        and "secret_hash" not in read.json()
    )


@pytest.mark.parametrize("failure", ["flush", "commit"])
def test_mutation_cannot_return_credentials_if_audit_or_commit_fails(setup, failure):
    _, db, _, _, client = setup
    getattr(db, failure).side_effect = RuntimeError(
        "Sensitive provider/database details"
    )
    result = client.post("/api/v1/nhi/service-accounts", json={"name": "synthetic"})
    assert result.status_code == 503
    assert "client_secret" not in result.text and "Sensitive" not in result.text
    db.rollback.assert_called_once()


def test_read_outage_is_not_an_empty_inventory(setup):
    _, db, _, _, client = setup
    db.query.side_effect = RuntimeError("Sensitive database details")
    result = client.get("/api/v1/nhi/service-accounts")
    assert result.status_code == 503 and result.json().get("count") is None


@pytest.mark.parametrize(
    "path",
    [
        "?status=unknown",
        "/expiring?within_days=-1",
        "/expiring?within_days=366",
        "/not-a-uuid",
    ],
)
def test_query_bounds_and_uuid_paths_are_enforced(setup, path):
    _, db, _, _, client = setup
    assert client.get("/api/v1/nhi/service-accounts" + path).status_code == 422
    db.query.assert_not_called()


@pytest.mark.parametrize("operation", ["create", "read", "list", "transition", "check"])
def test_service_boundary_rejects_non_admin_callers(setup, operation):
    caller, db, _, _, _ = setup
    service = NHIService(db, RequestContext(caller.tenant_id, caller.user_id, ()))
    calls = {
        "create": lambda: service.create_service_account({"name": "synthetic"}),
        "read": lambda: service.get_service_account(uuid4()),
        "list": service.list_service_accounts,
        "transition": lambda: service.transition(
            uuid4(), "activate", {"expected_version": 1}
        ),
        "check": lambda: service.check_credentials("synthetic", "synthetic"),
    }
    with pytest.raises(HTTPException) as error:
        calls[operation]()
    assert error.value.status_code == 403
    db.query.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.parametrize(
    "roles,user", [(("INTERNAL_SERVICE",), None), (("TENANT_ADMIN",), "invalid")]
)
def test_missing_actual_user_actor_is_denied(setup, roles, user):
    caller, db, _, _, _ = setup
    with pytest.raises(HTTPException) as error:
        NHIService(
            db, RequestContext(caller.tenant_id, user, roles)
        ).list_service_accounts()
    assert error.value.status_code == 401
    db.query.assert_not_called()


def test_routes_require_auth_and_internal_token_cannot_create(setup, monkeypatch):
    caller, db, _, app, client = setup
    app.dependency_overrides.pop(get_current_request_context)
    validator = Mock()
    app.dependency_overrides[get_token_validator] = lambda: validator
    assert (
        client.post(
            "/api/v1/nhi/service-accounts", json={"name": "synthetic"}
        ).status_code
        == 401
    )
    monkeypatch.setattr(settings, "INTERNAL_SERVICE_TOKEN", "synthetic-internal-test")
    result = client.post(
        "/api/v1/nhi/service-accounts",
        headers={
            "Authorization": "Bearer synthetic-internal-test",
            "X-Tenant-ID": str(caller.tenant_id),
        },
        json={"name": "synthetic"},
    )
    assert result.status_code == 401
    db.add.assert_not_called()


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("post", "", {"name": "synthetic"}),
        ("get", "", None),
        ("delete", "/synthetic", None),
        ("post", "/synthetic/rotate", None),
    ],
)
def test_placeholder_api_key_routes_cannot_claim_credential_effects(
    setup, monkeypatch, method, path, payload
):
    _, db, _, _, client = setup
    monkeypatch.setenv("IAM_ENABLE_API_KEYS", "true")
    result = client.request(
        method, "/api/v1/api-keys" + path, **({"json": payload} if payload else {})
    )
    assert result.status_code == 503 and "new_key" not in result.text
    db.add.assert_not_called()


def test_feature_default_is_disabled(monkeypatch):
    monkeypatch.delenv("IAM_ENABLE_SERVICE_ACCOUNTS", raising=False)
    assert (
        Settings(_env_file=None, ENVIRONMENT="development").IAM_ENABLE_SERVICE_ACCOUNTS
        is False
    )


def test_local_secret_is_not_accepted_as_a_jwt(setup):
    _, _, _, _, client = setup
    secret = client.post(
        "/api/v1/nhi/service-accounts", json={"name": "synthetic"}
    ).json()["client_secret"]
    result = TokenValidator(Mock()).validate_token(secret)
    assert result["valid"] is False and result.get("tenant_id") is None


@pytest.mark.parametrize("tenant", [None, "slug", str(uuid4())])
def test_programmatic_tenant_context_must_be_a_uuid(setup, tenant):
    caller, db, _, _, _ = setup
    with pytest.raises(HTTPException) as error:
        NHIService(
            db, RequestContext(tenant, caller.user_id, caller.roles)
        ).list_service_accounts()
    assert error.value.status_code == 401
    db.query.assert_not_called()
