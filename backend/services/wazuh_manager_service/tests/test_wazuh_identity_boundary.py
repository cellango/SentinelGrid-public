"""Actual Wazuh assembly/stored inventory and current IAM RSA with key/HTTP/SQL doubles.

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
from app.api import agents, health
from app.core import database, security
from app.core.config import Settings
from app.core.principal_policy import WazuhPrincipalSettings, WazuhInventoryReader
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
    permission="wazuh.read_owned_inventory",
)
LIST = "/api/v1/wazuh/agents"
UNAVAILABLE = [
    ("POST", LIST + "/register"),
    ("GET", LIST + "/001"),
    ("DELETE", LIST + "/001"),
    ("POST", LIST + "/001/restart"),
    ("GET", "/health"),
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
    policy = WazuhPrincipalSettings(
        _env_file=None,
        IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
        WAZUH_INVENTORY_READERS=(WazuhInventoryReader(**READER),),
    )
    monkeypatch.setattr(app.state, "wazuh_principal_settings", policy)
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
    now = datetime.now(timezone.utc)
    row = dict(
        id=UUID(RESOURCE),
        tenant_id=UUID(TENANT),
        wazuh_agent_id="001",
        agent_name="Synthetic Endpoint",
        ip_address="192.0.2.1",
        os_platform="linux",
        os_version="synthetic",
        status="pending",
        last_keepalive=None,
        registration_date=now,
        agent_version="4.8.0",
        metadata={"synthetic_private": "SYNTHETIC_NOT_AN_ENROLLMENT_KEY"},
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
    db.query.assert_not_called()
    assert not app.dependency_overrides


def auth(b, **updates):
    return {"Authorization": "Bearer " + b.sign(updates)}


def no_data(b):
    assert not b.opened and not b.db.execute.called


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
        WazuhPrincipalSettings(
            _env_file=None, IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),)
        )
        if kind == "empty_grants"
        else WazuhPrincipalSettings(_env_file=None)
        if kind == "empty_registration"
        else {}
    )
    monkeypatch.setattr(
        app.state,
        "iam_verification_settings"
        if kind == "untyped_verifier"
        else "wazuh_principal_settings",
        value,
    )
    assert b.client.get(
        LIST, headers=auth(b, realm_access={"roles": ["admin"]})
    ).status_code in {403, 503}
    no_data(b)


@pytest.mark.parametrize("path", ["/"])
def test_only_local_metadata_is_public(boundary, path):
    b = boundary
    assert b.client.get(path).status_code == 200
    assert not b.calls
    no_data(b)


@pytest.mark.parametrize("environment", ["development", "test", "production"])
def test_debug_cannot_supply_a_development_identity(boundary, monkeypatch, environment):
    b = boundary
    monkeypatch.setattr(main.settings, "ENVIRONMENT", environment)
    monkeypatch.setenv("DEBUG_MODE", "true")
    monkeypatch.setenv("DEV_TENANT_ID", TENANT)
    assert b.client.get(LIST).status_code == 401
    assert (
        b.client.get(LIST, headers={"Authorization": "Bearer dev-token"}).status_code
        == 401
    )
    no_data(b)


@pytest.mark.parametrize(
    "change",
    [
        {"subject_id": "*"},
        {"tenant_id": FOREIGN},
        {"client_id": "foreign"},
        {"subject_id": "00000000-0000-0000-0000-000000000000"},
        {"permission": "wazuh.enroll"},
        {"issuer": "https://identity.internal.test/realms/foreign"},
    ],
)
def test_reader_policy_cannot_expand_owned_registration(change):
    with pytest.raises(ValidationError):
        WazuhPrincipalSettings(
            _env_file=None,
            IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
            WAZUH_INVENTORY_READERS=(WazuhInventoryReader(**{**READER, **change}),),
        )


def test_duplicate_grants_and_empty_defaults_are_explicit():
    with pytest.raises(ValidationError):
        WazuhPrincipalSettings(
            _env_file=None,
            IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
            WAZUH_INVENTORY_READERS=(
                WazuhInventoryReader(**READER),
                WazuhInventoryReader(**READER),
            ),
        )
    settings = Settings(_env_file=None, ENVIRONMENT="test")
    assert (
        not settings.principal_settings().IAM_USER_CLIENT_BINDINGS
        and not settings.principal_settings().WAZUH_INVENTORY_READERS
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


def test_owned_stored_inventory_selects_only_exact_tenant_columns(boundary):
    b = boundary
    response = b.client.get(LIST + "?skip=2&limit=7", headers=auth(b))
    assert response.status_code == 200 and len(b.calls) == 1 and len(b.opened) == 1
    payload = response.json()
    assert payload["count"] == 1
    row = payload["agents"][0]
    assert (
        row["id"] == RESOURCE
        and row["wazuh_agent_id"] == "001"
        and row["status"] == "pending"
    )
    assert row["last_seen"] is None and row["version"] == "4.8.0"
    assert (
        "synthetic_private" not in response.text
        and "SYNTHETIC_NOT_AN_ENROLLMENT_KEY" not in response.text
    )
    statement, params = b.db.execute.call_args.args
    sql = str(statement).lower()
    assert (
        "from public.endpoint_agents" in sql and "where tenant_id = :tenant_id" in sql
    )
    assert (
        "order by registration_date desc, id" in sql
        and "limit :limit offset :skip" in sql
    )
    assert "metadata" not in sql and "*" not in sql
    assert params == {"tenant_id": UUID(TENANT), "skip": 2, "limit": 7}
    assert b.row["metadata"]


def test_real_empty_inventory_retains_empty_while_SQL_errors_are_unavailable(boundary):
    b = boundary
    b.db.execute.return_value.mappings.return_value.all.return_value = []
    assert b.client.get(LIST, headers=auth(b)).json() == {"agents": [], "count": 0}
    b.db.execute.side_effect = RuntimeError("synthetic-private-diagnostic")
    response = b.client.get(LIST, headers=auth(b))
    assert (
        response.status_code == 503
        and "synthetic-private-diagnostic" not in response.text
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("tenant_id", UUID(FOREIGN)),
        ("id", UUID(int=0)),
        ("wazuh_agent_id", "000"),
        ("wazuh_agent_id", "../global"),
        ("agent_name", "x" * 256),
        ("status", "invented"),
        ("registration_date", datetime(2026, 1, 1)),
        ("ip_address", "invalid"),
    ],
)
def test_invalid_foreign_or_unbounded_stored_rows_are_not_success(
    boundary, field, value
):
    b = boundary
    b.row[field] = value
    assert b.client.get(LIST, headers=auth(b)).status_code == 503


def test_result_cannot_exceed_requested_bound(boundary):
    b = boundary
    b.db.execute.return_value.mappings.return_value.all.return_value = [b.row, b.row]
    assert b.client.get(LIST + "?limit=1", headers=auth(b)).status_code == 503


@pytest.mark.parametrize("when", ["enter", "exit"])
def test_session_cleanup_must_finish_before_HTTP_success(boundary, monkeypatch, when):
    b = boundary

    @contextmanager
    def broken(factory, tenant):
        if when == "enter":
            raise RuntimeError("synthetic session unavailable")
        yield b.db
        raise RuntimeError("synthetic cleanup unavailable")

    monkeypatch.setattr(database, "tenant_session", broken)
    assert b.client.get(LIST, headers=auth(b)).status_code == 503


@pytest.mark.parametrize("method,path", UNAVAILABLE)
@pytest.mark.parametrize("kind", ["raw_header", "signed_admin", "workload"])
def test_unqualified_lifecycle_detail_health_deny_before_dependencies(
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
            method, path, headers=headers, json={"tenant_id": FOREIGN}
        ).status_code
        == 503
    )
    assert not b.calls
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
        (LIST + "?x=" + "a" * 65, 400),
        ("/api/v1/%77azuh/agents", 403),
    ],
)
def test_inventory_query_and_target_are_bounded_before_SQL(boundary, path, status):
    b = boundary
    assert b.client.get(path, headers=auth(b)).status_code == status
    no_data(b)


def test_both_standalone_routers_enforce_source_contract(boundary):
    b = boundary
    isolated = FastAPI()
    isolated.include_router(agents.router, prefix="/api/v1/wazuh")
    isolated.include_router(health.router)
    isolated.state.iam_verification_settings = app.state.iam_verification_settings
    isolated.state.wazuh_principal_settings = b.policy
    with TestClient(isolated) as client:
        assert client.get(LIST).status_code == 401
        assert client.get(LIST, headers=auth(b)).status_code == 200
        for method, path in UNAVAILABLE:
            assert (
                client.request(method, path, headers=auth(b), json={}).status_code
                == 503
            )


def test_future_alias_cannot_reuse_owned_inventory_authority(boundary):
    b = boundary
    routes = list(app.router.routes)
    try:
        app.add_api_route("/synthetic-future", agents.list_agents, methods=["GET"])
        assert b.client.get("/synthetic-future", headers=auth(b)).status_code == 503
    finally:
        app.router.routes[:] = routes
    no_data(b)


@pytest.mark.parametrize(
    "helper",
    [
        "unscoped",
        "raw_tenant",
        "raw_dependency",
        "client_factory",
        "service_factory",
        "health",
    ],
)
def test_direct_legacy_factories_and_raw_UUIDs_deny(boundary, helper):
    b = boundary
    with pytest.raises(HTTPException) as exc:
        if helper == "unscoped":
            next(database.get_db())
        elif helper == "raw_tenant":
            next(database.get_tenant_db(TENANT))
        elif helper == "raw_dependency":
            next(database.get_tenant_session(TENANT))
        elif helper == "client_factory":
            agents.get_wazuh_client()
        elif helper == "service_factory":
            agents.get_agent_service(b.db, Mock())
        else:
            asyncio.run(health.health_check())
    assert exc.value.status_code == 503
    no_data(b)


@pytest.mark.parametrize(
    "method,args",
    [
        ("register_agent", (UUID(TENANT), "synthetic")),
        ("list_agents", (UUID(TENANT),)),
        ("get_agent_details", (UUID(TENANT), "001")),
        ("delete_agent", (UUID(TENANT), "001")),
        ("restart_agent", (UUID(TENANT), "001")),
    ],
)
def test_direct_agent_service_never_uses_raw_tenant_as_authority(
    boundary, method, args
):
    from app.services.agent_service import AgentService

    b = boundary
    provider = Mock()
    service = AgentService(b.db, provider)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(getattr(service, method)(*args))
    assert exc.value.status_code == 503
    assert not provider.mock_calls
    no_data(b)


@pytest.mark.parametrize(
    "method,args",
    [
        ("_get_token", ()),
        ("_request", ("GET", "/agents")),
        ("create_agent", ("synthetic",)),
        ("update_agent_labels", ("001", {"tenant_id": FOREIGN})),
        ("get_agent", ("001",)),
        ("get_agent_key", ("001",)),
        ("delete_agent", ("001",)),
        ("list_agents", ()),
        ("restart_agent", ("001",)),
        ("get_agent_config", ("001",)),
        ("upgrade_agent", ("001",)),
    ],
)
def test_direct_provider_helpers_deny_even_with_cached_credentials(
    boundary, method, args
):
    from app.services.wazuh_api_client import WazuhAPIClient

    b = boundary
    provider = WazuhAPIClient(
        "https://manager.internal.test", "synthetic", "synthetic", True
    )
    provider.token = "SYNTHETIC_NOT_A_CREDENTIAL"
    with pytest.raises(HTTPException) as exc:
        asyncio.run(getattr(provider, method)(*args))
    assert exc.value.status_code == 503
    no_data(b)


def test_fresh_actual_assembly_lifespan_and_root_do_not_load_provider_modules():
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.pathsep.join(
            [
                str(ROOT / "backend/libs"),
                str(ROOT / "backend/services/wazuh_manager_service"),
            ]
        ),
    }
    code = """import sys
from unittest.mock import Mock
import sqlalchemy.engine,sqlalchemy.sql.schema,httpx
forbidden=Mock(side_effect=AssertionError('No SQL/provider/DDL'))
sqlalchemy.engine.Engine.connect=forbidden
sqlalchemy.sql.schema.MetaData.create_all=forbidden
httpx.AsyncClient=forbidden
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    assert client.get('/').status_code==200
    assert client.get('/health').status_code==503
assert not any(n in sys.modules for n in ['app.services.agent_service','app.services.wazuh_api_client'])
forbidden.assert_not_called()
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
