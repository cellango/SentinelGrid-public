"""Actual connector assembly/reader and current IAM RSA with key/HTTP/SQL doubles.

No identity override, provider SDK replacement, live SQL/provider or startup DDL.
"""

import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone
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
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from pydantic import ValidationError
import pytest
from sqlalchemy.dialects import postgresql

from app.main import app
import app.main as main
from app.api import connectors
from app.core import database, security
from app.core.config import Settings
from app.core.principal_policy import ConnectorPrincipalSettings, ConnectorReader
from app.services.ingestion_service import send_to_ingestion
from sg_core import iam_verification
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.user_principals import UserClientBinding

ROOT = Path(__file__).resolve().parents[4]
HTTP_CLIENT = httpx.Client
TENANT = "11111111-1111-4111-8111-111111111111"
SUBJECT = "22222222-2222-4222-8222-222222222222"
RESOURCE = "33333333-3333-4333-8333-333333333333"
FOREIGN = "44444444-4444-4444-8444-444444444444"
ISSUER = "https://identity.internal.test/realms/synthetic"
BINDING = dict(
    issuer=ISSUER,
    client_id="owned-browser",
    tenant_id=TENANT,
    contract="keycloak-user-v1",
    service_accounts_enabled=False,
    token_exchange_enabled=False,
)
READER = dict(
    issuer=ISSUER,
    client_id="owned-browser",
    tenant_id=TENANT,
    subject_id=SUBJECT,
    permission="connector.read_owned",
)
LIST = "/api/v1/connectors"
DETAIL = LIST + "/" + RESOURCE
UNAVAILABLE = [
    ("POST", LIST),
    ("PATCH", DETAIL),
    ("DELETE", DETAIL),
    ("POST", DETAIL + "/sync"),
    ("POST", LIST + "/sync/all"),
    ("POST", DETAIL + "/test"),
    ("POST", LIST + "/oauth/init"),
    ("POST", LIST + "/oauth/callback"),
]
IAM_WORKER = '\nimport json,sys\nfrom types import SimpleNamespace\nfrom app.services import token_validator as m\nfrom app.models.auth import TokenValidationResponse\nvalue=json.load(sys.stdin)\nm.settings=SimpleNamespace(KEYCLOAK_URL="https://identity.internal.test",KEYCLOAK_REALM="synthetic",\n    KEYCLOAK_CLIENT_ID="review-client",KEYCLOAK_ISSUER_BASE_URLS=[],JWKS_CACHE_TTL=60)\nvalidator=m.TokenValidator(None)\n# The fixture\'s owned JWKS replaces key transport. No token-selected key/URL.\nvalidator._get_jwks_for_realm=lambda *args: {"keys":[value["jwk"]]}\nprint(TokenValidationResponse(**validator.validate_token(value["token"])).model_dump_json())\n'


@pytest.fixture(scope="module")
def keys():
    return [
        rsa.generate_private_key(public_exponent=65537, key_size=2048) for _ in range(2)
    ]


@pytest.fixture
def boundary(monkeypatch, keys):
    assert not app.dependency_overrides
    monkeypatch.setattr(
        app.state,
        "iam_verification_settings",
        IAMVerificationSettings(
            _env_file=None,
            IAM_AGENT_URL="https://iam.internal.test",
            KEYCLOAK_CLIENT_ID="review-client",
        ),
    )
    policy = ConnectorPrincipalSettings(
        _env_file=None,
        IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
        CONNECTOR_METADATA_READERS=(ConnectorReader(**READER),),
    )
    monkeypatch.setattr(app.state, "connector_principal_settings", policy)
    claims = dict(
        iss=ISSUER,
        aud="review-client",
        sub=SUBJECT,
        tenant_id=TENANT,
        typ="Bearer",
        azp="owned-browser",
        sg_principal_type="user",
        sg_identity_contract="keycloak-user-v1",
        realm_access={"roles": ["SOC_ANALYST"]},
        iat=int(time.time()) - 1,
        exp=int(time.time()) + 600,
    )
    row = dict(
        id=UUID(RESOURCE),
        tenant_id=UUID(TENANT),
        type="google_workspace",
        name="Synthetic Workspace",
        status="active",
        last_sync_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        credentials={"token": "SYNTHETIC_NOT_A_CREDENTIAL"},
        sync_settings={"synthetic_private": "setting"},
        error_message="synthetic-private-provider-diagnostic",
    )
    db = Mock()
    db.execute.return_value.mappings.return_value.all.return_value = [row]
    db.execute.return_value.mappings.return_value.one_or_none.return_value = row
    opened = []

    @contextmanager
    def session(factory, tenant):
        opened.append((factory, tenant))
        yield db

    monkeypatch.setattr(database, "tenant_session", session)
    forbidden = Mock(side_effect=AssertionError("No provider, unqualified SQL or DDL"))
    monkeypatch.setattr(database, "SessionLocal", forbidden)
    monkeypatch.setattr("sqlalchemy.engine.Engine.connect", forbidden)
    monkeypatch.setattr("sqlalchemy.sql.schema.MetaData.create_all", forbidden)
    monkeypatch.setattr(httpx, "AsyncClient", forbidden)
    state = SimpleNamespace(
        claims=claims,
        keys=keys,
        row=row,
        db=db,
        opened=opened,
        calls=[],
        unavailable=False,
        policy=policy,
        forbidden=forbidden,
        receipt_mutator=None,
    )
    jwk = json.loads(RSAAlgorithm.to_jwk(keys[0].public_key()))
    jwk.update(kid="read-key", use="sig", alg="RS256")

    def sign(updates=None, key=None):
        return jwt.encode(
            {**claims, **(updates or {})},
            key or keys[0],
            algorithm="RS256",
            headers={"kid": "read-key"},
        )

    def handler(request):
        state.calls.append(request)
        assert (
            str(request.url)
            == "https://iam.internal.test/internal/iam/auth/validate-token"
        )
        assert set(json.loads(request.content)) == {"token"}
        assert not any(
            n in request.headers
            for n in [
                "authorization",
                "x-tenant-id",
                "x-realm",
                "x-user-id",
                "x-api-key",
                "x-internal-service-token",
            ]
        )
        if state.unavailable:
            raise httpx.ConnectError("synthetic verifier outage")
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ROOT / "backend/libs")
            + os.pathsep
            + str(ROOT / "backend/agents/iam_agent"),
        }
        r = subprocess.run(
            [sys.executable, "-B", "-c", IAM_WORKER],
            cwd=ROOT,
            env=env,
            text=True,
            input=json.dumps(
                {"token": json.loads(request.content)["token"], "jwk": jwk}
            ),
            capture_output=True,
            timeout=10,
        )
        assert r.returncode == 0, "Current IAM fixture failed"
        receipt = json.loads(r.stdout)
        if state.receipt_mutator:
            state.receipt_mutator(receipt)
        return httpx.Response(200, json=receipt)

    monkeypatch.setattr(
        iam_verification.httpx,
        "Client",
        lambda **kwargs: HTTP_CLIENT(transport=httpx.MockTransport(handler), **kwargs),
    )
    state.sign = sign
    state.client = TestClient(app)
    yield state
    state.client.close()
    forbidden.assert_not_called()
    db.add.assert_not_called()
    db.commit.assert_not_called()
    db.delete.assert_not_called()
    assert not app.dependency_overrides


def auth(b, **updates):
    return {"Authorization": "Bearer " + b.sign(updates)}


def no_data(b):
    assert not b.opened and not b.db.execute.called


def test_actual_owned_list_selects_only_bounded_metadata_columns(boundary):
    b = boundary
    r = b.client.get(LIST + "?skip=2&limit=7", headers=auth(b))
    assert r.status_code == 200 and len(b.calls) == 1 and len(b.opened) == 1
    result = r.json()[0]
    assert (
        result["id"] == RESOURCE
        and result["tenant_id"] == TENANT
        and result["error_message"] is None
    )
    assert not any(
        value in r.text
        for value in [
            "SYNTHETIC_NOT_A_CREDENTIAL",
            "synthetic_private",
            "synthetic-private-provider-diagnostic",
        ]
    )
    statement = b.db.execute.call_args.args[0]
    assert {c.name for c in statement.selected_columns} == {
        "id",
        "tenant_id",
        "type",
        "name",
        "status",
        "last_sync_at",
        "created_at",
        "updated_at",
    }
    compiled = statement.compile(dialect=postgresql.dialect())
    assert "connector_configs.tenant_id =" in str(
        compiled
    ) and "ORDER BY connector_configs.id" in str(compiled)
    assert (
        UUID(TENANT) in compiled.params.values()
        and 2 in compiled.params.values()
        and 7 in compiled.params.values()
    )
    assert (
        b.row["credentials"]["token"] == "SYNTHETIC_NOT_A_CREDENTIAL"
        and b.row["error_message"] == "synthetic-private-provider-diagnostic"
    )


def test_actual_owned_detail_binds_both_resource_and_tenant(boundary):
    b = boundary
    r = b.client.get(DETAIL, headers=auth(b))
    assert r.status_code == 200 and r.json()["name"] == "Synthetic Workspace"
    compiled = b.db.execute.call_args.args[0].compile(dialect=postgresql.dialect())
    assert "connector_configs.id =" in str(
        compiled
    ) and "connector_configs.tenant_id =" in str(compiled)
    assert (
        UUID(RESOURCE) in compiled.params.values()
        and UUID(TENANT) in compiled.params.values()
    )


def test_missing_owned_detail_and_real_empty_list_keep_honest_results(boundary):
    b = boundary
    b.db.execute.return_value.mappings.return_value.one_or_none.return_value = None
    assert b.client.get(DETAIL, headers=auth(b)).status_code == 404
    b.db.execute.return_value.mappings.return_value.all.return_value = []
    assert b.client.get(LIST, headers=auth(b)).json() == []


@pytest.mark.parametrize("path", [LIST, DETAIL])
def test_foreign_rows_and_store_errors_cannot_be_success(boundary, path):
    b = boundary
    b.row["tenant_id"] = UUID(FOREIGN)
    assert b.client.get(path, headers=auth(b)).status_code == 503
    b.db.execute.side_effect = RuntimeError("synthetic-private-diagnostic")
    response = b.client.get(path, headers=auth(b))
    assert (
        response.status_code == 503
        and "synthetic-private-diagnostic" not in response.text
    )


def test_contradictory_detail_target_is_not_returned(boundary):
    b = boundary
    b.row["id"] = UUID(FOREIGN)
    assert b.client.get(DETAIL, headers=auth(b)).status_code == 503


@pytest.mark.parametrize("when", ["enter", "exit"])
def test_session_failure_finishes_before_success(boundary, monkeypatch, when):
    b = boundary

    @contextmanager
    def broken(factory, tenant):
        if when == "enter":
            raise RuntimeError("synthetic session unavailable")
        yield b.db
        raise RuntimeError("synthetic session cleanup unavailable")

    monkeypatch.setattr(database, "tenant_session", broken)
    assert b.client.get(LIST, headers=auth(b)).status_code == 503


@pytest.mark.parametrize("method,path", UNAVAILABLE)
@pytest.mark.parametrize("kind", ["raw_header", "signed_admin", "workload"])
def test_writes_sync_tests_and_oauth_deny_before_dependencies(
    boundary, method, path, kind
):
    b = boundary
    headers = (
        {"X-Tenant-ID": TENANT, "X-Internal-Service-Token": "synthetic"}
        if kind == "raw_header"
        else auth(b, sg_principal_type="workload")
        if kind == "workload"
        else auth(b, realm_access={"roles": ["admin"]})
    )
    assert (
        b.client.request(
            method,
            path,
            headers=headers,
            json={"state": "synthetic", "code": "synthetic", "tenant_id": FOREIGN},
        ).status_code
        == 503
    )
    assert not b.calls
    no_data(b)


@pytest.mark.parametrize(
    "kind",
    [
        "none",
        "tenant_header",
        "dev",
        "static",
        "basic",
        "cookie",
        "marker",
        "duplicate",
        "conflict",
    ],
)
def test_raw_credentials_cannot_establish_owned_reader(boundary, kind):
    b = boundary
    headers = {}
    if kind == "tenant_header":
        headers = {"X-Tenant-ID": TENANT}
    elif kind in {"dev", "static"}:
        headers = {
            "Authorization": "Bearer "
            + ("dev-token" if kind == "dev" else "synthetic-static-token")
        }
    elif kind == "basic":
        headers = {"Authorization": "Basic synthetic"}
    elif kind == "cookie":
        headers = {"Cookie": "access_token=" + b.sign()}
    elif kind == "marker":
        headers = {
            "Authorization": "Bearer session-cookie",
            "Cookie": "access_token=" + b.sign(),
        }
    elif kind == "duplicate":
        headers = [
            ("Authorization", "Bearer " + b.sign()),
            ("Authorization", "Bearer " + b.sign()),
        ]
    elif kind == "conflict":
        headers = {**auth(b), "Cookie": "access_token=synthetic"}
    assert b.client.get(LIST, headers=headers).status_code == 401
    assert not b.calls
    no_data(b)


@pytest.mark.parametrize(
    "updates",
    [
        {"sub": FOREIGN},
        {"tenant_id": FOREIGN},
        {"azp": "foreign"},
        {"iss": "https://identity.internal.test/realms/foreign"},
        {"sg_principal_type": "workload"},
        {"sg_identity_contract": "foreign"},
        {"act": {"sub": SUBJECT}},
        {"client_id": "owned-browser"},
    ],
)
def test_signed_user_or_workload_is_not_owned_read_permission(boundary, updates):
    b = boundary
    assert b.client.get(LIST, headers=auth(b, **updates)).status_code in {401, 403}
    no_data(b)


@pytest.mark.parametrize(
    "kind", ["forged", "expired", "audience", "outage", "conflicting_receipt"]
)
def test_current_IAM_signature_receipt_and_unavailability_denials(boundary, kind):
    b = boundary
    token = (
        b.sign(key=b.keys[1])
        if kind == "forged"
        else b.sign({"iat": int(time.time()) - 100, "exp": int(time.time()) - 1})
        if kind == "expired"
        else b.sign({"aud": "foreign"})
        if kind == "audience"
        else b.sign()
    )
    b.unavailable = kind == "outage"
    if kind == "conflicting_receipt":
        b.receipt_mutator = lambda result: result.update(tenant_id=FOREIGN)
    assert b.client.get(
        LIST, headers={"Authorization": "Bearer " + token}
    ).status_code == (503 if kind in {"outage", "conflicting_receipt"} else 401)
    no_data(b)


@pytest.mark.parametrize(
    "hints",
    [
        [("X-Tenant-ID", FOREIGN)],
        [("X-Tenant-ID", TENANT), ("X-Tenant-ID", TENANT)],
        [("X-Realm", "foreign")],
        [("X-Realm", "synthetic"), ("X-Realm", "synthetic")],
        [("X-User-ID", SUBJECT)],
        [("X-Roles", "admin")],
        [("X-Internal-Token", "synthetic")],
        [("X-Internal-Service-Token", "synthetic")],
        [("X-API-Key", "synthetic")],
    ],
)
def test_forwarded_hints_cannot_override_owned_context(boundary, hints):
    b = boundary
    assert b.client.get(LIST, headers=[*auth(b).items(), *hints]).status_code == 403
    no_data(b)


@pytest.mark.parametrize(
    "path,status",
    [
        (LIST + "?limit=0", 422),
        (LIST + "?limit=101", 422),
        (LIST + "?skip=-1", 422),
        (LIST + "?skip=10001", 422),
        (LIST + "?limit=1&limit=1", 400),
        (LIST + "?tenant_id=" + FOREIGN, 400),
        (DETAIL + "?limit=1", 400),
        (LIST + "?x=" + "a" * 65, 400),
        (LIST + "/00000000-0000-0000-0000-000000000000", 403),
        (LIST + "/slug", 403),
        ("/api/v1/%63onnectors", 403),
    ],
)
def test_target_query_bounds_before_session(boundary, path, status):
    b = boundary
    assert b.client.get(path, headers=auth(b)).status_code == status
    no_data(b)


@pytest.mark.parametrize(
    "headers", [{"Content-Length": "1"}, {"Transfer-Encoding": "chunked"}]
)
def test_metadata_read_does_not_accept_body(boundary, headers):
    b = boundary
    assert (
        b.client.request(
            "GET", LIST, headers={**auth(b), **headers}, content=b"x"
        ).status_code
        == 400
    )
    no_data(b)


@pytest.mark.parametrize(
    "kind", ["empty_grants", "empty_registration", "untyped_policy", "untyped_verifier"]
)
def test_empty_or_wrong_config_fails_closed(boundary, monkeypatch, kind):
    b = boundary
    value = (
        ConnectorPrincipalSettings(
            _env_file=None, IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),)
        )
        if kind == "empty_grants"
        else ConnectorPrincipalSettings(_env_file=None)
        if kind == "empty_registration"
        else {}
    )
    monkeypatch.setattr(
        app.state,
        "iam_verification_settings"
        if kind == "untyped_verifier"
        else "connector_principal_settings",
        value,
    )
    assert b.client.get(
        LIST, headers=auth(b, realm_access={"roles": ["admin"]})
    ).status_code in {403, 503}
    no_data(b)


@pytest.mark.parametrize("path", ["/", "/health"])
def test_only_local_metadata_is_public(boundary, path):
    b = boundary
    assert b.client.get(path).status_code == 200
    assert not b.calls
    no_data(b)


@pytest.mark.parametrize("environment", ["development", "test", "production"])
def test_debug_cannot_supply_a_development_identity(boundary, monkeypatch, environment):
    b = boundary
    monkeypatch.setattr(main.settings, "ENVIRONMENT", environment)
    monkeypatch.setattr(main.settings, "DEBUG_MODE", True)
    monkeypatch.setenv("DEV_TENANT_ID", TENANT)
    assert b.client.get(LIST).status_code == 401
    assert (
        b.client.get(LIST, headers={"Authorization": "Bearer dev-token"}).status_code
        == 401
    )
    no_data(b)


def test_standalone_routers_and_future_alias_are_gated(boundary):
    b = boundary
    isolated = FastAPI()
    isolated.include_router(connectors.router, prefix="/api/v1")
    isolated.include_router(connectors.oauth_router, prefix="/api/v1")
    with TestClient(isolated) as client:
        for method, path in UNAVAILABLE:
            assert client.request(method, path, json={}).status_code == 503
    routes = list(app.router.routes)
    try:

        @app.get("/synthetic-future")
        def future():
            return {"success": True}

        assert b.client.get("/synthetic-future", headers=auth(b)).status_code == 503
    finally:
        app.router.routes[:] = routes
    no_data(b)


def test_legacy_helpers_and_delivery_cannot_create_authority_or_success(boundary):
    b = boundary
    for generator in [
        database.get_db(),
        database.get_tenant_db(TENANT),
        connectors.get_oauth_callback_tenant_session(),
    ]:
        with pytest.raises(HTTPException) as exc:
            next(generator)
        assert exc.value.status_code == 503
    with pytest.raises(HTTPException) as exc:
        asyncio.run(security.verify_token_with_iam_agent("dev-token"))
    assert exc.value.status_code == 503
    with pytest.raises(HTTPException) as exc:
        connectors.resolve_oauth_callback_tenant(
            connectors.OAuthCallbackRequest(
                provider="google_workspace", code="synthetic", state="synthetic"
            )
        )
    assert exc.value.status_code == 503
    with pytest.raises(RuntimeError, match="Owned ingestion workload"):
        send_to_ingestion(TENANT, [{"tenant_id": FOREIGN}])
    assert not b.calls
    no_data(b)


@pytest.mark.parametrize(
    "change",
    [
        {"subject_id": "*"},
        {"tenant_id": FOREIGN},
        {"client_id": "foreign"},
        {"subject_id": "00000000-0000-0000-0000-000000000000"},
        {"permission": "connector.sync"},
        {"issuer": "https://identity.internal.test/realms/foreign"},
    ],
)
def test_reader_policy_cannot_expand_owned_registration(change):
    with pytest.raises(ValidationError):
        ConnectorPrincipalSettings(
            _env_file=None,
            IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
            CONNECTOR_METADATA_READERS=(ConnectorReader(**{**READER, **change}),),
        )


def test_duplicate_grants_and_empty_defaults_are_explicit():
    with pytest.raises(ValidationError):
        ConnectorPrincipalSettings(
            _env_file=None,
            IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
            CONNECTOR_METADATA_READERS=(
                ConnectorReader(**READER),
                ConnectorReader(**READER),
            ),
        )
    settings = Settings(_env_file=None, ENVIRONMENT="test")
    assert (
        not settings.principal_settings().IAM_USER_CLIENT_BINDINGS
        and not settings.principal_settings().CONNECTOR_METADATA_READERS
    )
    assert isinstance(app.state.iam_verification_settings, IAMVerificationSettings)


@pytest.mark.parametrize(
    "options",
    [
        {"IAM_AGENT_URL": "http://iam.internal.test"},
        {"IAM_AGENT_URL": "https://iam.internal.test/path"},
        {"IAM_TOKEN_VALIDATION_TIMEOUT": 11},
        {"IAM_TOKEN_VALIDATION_TIMEOUT": float("nan")},
    ],
)
def test_production_verifier_configuration_is_owned_and_bounded(options):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            **{
                "ENVIRONMENT": "production",
                "INTERNAL_SERVICE_TOKEN": "synthetic-owned-token",
                "IAM_AGENT_URL": "https://iam.internal.test",
                **options,
            },
        )


def test_actual_source_assembly_does_not_import_provider_services_or_SDKs():
    assert not any(
        n in sys.modules
        for n in [
            "app.services.oauth_service",
            "app.services.sync_service",
            "google_auth_oauthlib",
            "googleapiclient",
            "boto3",
        ]
    )
