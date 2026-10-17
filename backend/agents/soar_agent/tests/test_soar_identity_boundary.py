"""Actual SOAR assembly and owned reader with current IAM RSA in another process.

Keys/HTTP and session/database results are doubled; no identity overrides, existing
SQL/provider/model/worker/engine startup or supported runtime is qualified.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import time
from unittest.mock import Mock
from uuid import UUID

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from pydantic import ValidationError
import pytest

from app.main import app
import app.main as main
from app.api import (
    detection_events,
    enrichment,
    ootb_playbooks,
    phishing_containment,
    webhooks,
)
from app.core import database
from app.core.config import Settings
from app.core.principal_policy import PlaybookReader, SOARPrincipalSettings
from app.core.security import LIST_PATH, DETAIL_PATH, require_soar_request
from app.database import PlaybookDB
from app.services.playbook_service import PlaybookService
from sg_core import iam_verification
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.user_principals import UserClientBinding

ROOT = Path(__file__).resolve().parents[4]
HTTP_CLIENT = httpx.Client
TEST_TENANT_ID = "11111111-1111-4111-8111-111111111111"
TEST_USER_ID = "22222222-2222-4222-8222-222222222222"
TEST_PLAYBOOK_ID = "33333333-3333-4333-8333-333333333333"
TEST_FOREIGN_ID = "44444444-4444-4444-8444-444444444444"
ISSUER = "https://identity.internal.test/realms/synthetic"
BINDING = dict(
    issuer=ISSUER,
    client_id="owned-browser",
    tenant_id=TEST_TENANT_ID,
    contract="keycloak-user-v1",
    service_accounts_enabled=False,
    token_exchange_enabled=False,
)
READER = dict(
    issuer=ISSUER,
    client_id="owned-browser",
    tenant_id=TEST_TENANT_ID,
    subject_id=TEST_USER_ID,
    permission="playbook.read_owned",
)
DETAIL = DETAIL_PATH.replace("{playbook_id}", TEST_PLAYBOOK_ID)
UNAVAILABLE = [
    ("POST", "/soar/playbooks"),
    ("PUT", DETAIL),
    ("DELETE", DETAIL),
    *[
        ("POST", DETAIL + "/" + tail)
        for tail in ["copy", "approve", "reject", "preview", "validate", "execute"]
    ],
    ("GET", "/soar/executions/" + TEST_PLAYBOOK_ID),
    ("GET", "/soar/observables/types"),
    ("GET", "/soar/analyzers"),
    ("GET", "/soar/analyzers/synthetic"),
    ("POST", "/soar/observables"),
    ("POST", "/soar/analyzers/synthetic/run"),
    ("POST", "/api/v1/thehive/case/update"),
    ("POST", "/api/v1/thehive/observable/update"),
    ("POST", "/api/v1/playbooks/phishing-containment/execute"),
    ("GET", "/soar/ootb"),
    ("POST", "/soar/ootb/synthetic/clone"),
    ("POST", "/soar/ootb/seed"),
    ("POST", "/api/v1/detection-events/ingest"),
    ("GET", "/api/v1/detection-events/health"),
    ("POST", "/api/v1/enrichment/ticket/" + TEST_PLAYBOOK_ID),
    ("GET", "/api/v1/enrichment/ticket/" + TEST_PLAYBOOK_ID),
    ("POST", "/internal/soar/playbooks/" + TEST_PLAYBOOK_ID + "/execute"),
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
    policy = SOARPrincipalSettings(
        _env_file=None,
        IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
        SOAR_PLAYBOOK_READERS=(PlaybookReader(**READER),),
    )
    monkeypatch.setattr(app.state, "soar_principal_settings", policy)
    claims = dict(
        iss=ISSUER,
        aud="review-client",
        sub=TEST_USER_ID,
        tenant_id=TEST_TENANT_ID,
        typ="Bearer",
        azp="owned-browser",
        sg_principal_type="user",
        sg_identity_contract="keycloak-user-v1",
        realm_access={"roles": ["SOC_ANALYST"]},
        iat=int(time.time()) - 1,
        exp=int(time.time()) + 600,
    )
    row = PlaybookDB(
        id=UUID(TEST_PLAYBOOK_ID),
        tenant_id=UUID(TEST_TENANT_ID),
        name="Synthetic owned definition",
        description="Synthetic",
        category="phishing",
        version="1.0.0",
        workflow={"nodes": [], "edges": []},
        timeout_seconds=300,
        on_failure="fail",
        is_template=False,
        requires_approval=True,
        is_builtin=False,
        auto_trigger_enabled=False,
        trigger_priority=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        n8n_webhook_url="https://hooks.internal.test/synthetic-installed-hook",
    )
    db = Mock()
    db.execute.return_value.scalars.return_value.all.return_value = [row]
    db.execute.return_value.scalar_one_or_none.return_value = row
    opened = []
    calls = []

    @contextmanager
    def session(factory, tenant):
        opened.append((factory, tenant))
        yield db

    monkeypatch.setattr(database, "tenant_session", session)
    forbidden = Mock(
        side_effect=AssertionError("Unqualified factory or effect must not run")
    )
    monkeypatch.setattr(main, "PlaybookService", forbidden)
    monkeypatch.setattr(PlaybookService, "_get_sg_admin_tenant_id", forbidden)
    for module, name in [
        (enrichment, "EnrichmentService"),
        (phishing_containment, "PhishingContainmentPlaybook"),
        (detection_events, "IncidentCreator"),
    ]:
        monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(httpx, "AsyncClient", forbidden)
    monkeypatch.setattr("sqlalchemy.engine.Engine.connect", forbidden)
    state = SimpleNamespace(
        db=db,
        row=row,
        claims=claims,
        opened=opened,
        calls=calls,
        forbidden=forbidden,
        unavailable=False,
        policy=policy,
        keys=keys,
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
        calls.append(request)
        assert (
            str(request.url)
            == "https://iam.internal.test/internal/iam/auth/validate-token"
        )
        assert set(json.loads(request.content)) == {"token"}
        for n in [
            "authorization",
            "x-tenant-id",
            "x-user-id",
            "x-api-key",
            "x-internal-service-token",
        ]:
            assert n not in request.headers
        if state.unavailable:
            raise httpx.ConnectError("synthetic verifier outage")
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(ROOT / "backend/libs")
            + os.pathsep
            + str(ROOT / "backend/agents/iam_agent"),
        }
        result = subprocess.run(
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
        assert result.returncode == 0, "Synthetic IAM worker failed"
        return httpx.Response(200, json=json.loads(result.stdout))

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
    assert not app.dependency_overrides


def auth(b, **updates):
    return {"Authorization": "Bearer " + b.sign(updates)}


def test_actual_owned_list_preserves_definition_with_exact_tenant_and_bounds(boundary):
    b = boundary
    r = b.client.get(
        LIST_PATH + "?limit=7&skip=2&category=phishing&is_template=false",
        headers=auth(b),
    )
    assert (
        r.status_code == 200
        and r.json()[0]["id"] == TEST_PLAYBOOK_ID
        and r.json()[0]["tenant_id"] == TEST_TENANT_ID
    )
    assert r.json()[0]["n8n_webhook_url"] is None and b.row.n8n_webhook_url is not None
    assert (
        b.opened == [(database.SessionLocal, UUID(TEST_TENANT_ID))]
        and len(b.calls) == 1
    )
    statement = b.db.execute.call_args.args[0]
    params = statement.compile().params
    assert (
        params["tenant_id_1"] == UUID(TEST_TENANT_ID)
        and params["category_1"] == "phishing"
    )
    assert params["param_1"] == 7 and params["param_2"] == 2
    assert " OR " not in str(statement) and "tenants" not in str(statement)
    b.db.commit.assert_not_called()
    b.db.add.assert_not_called()
    assert app.openapi()["paths"][LIST_PATH]["get"]["security"] == [{"HTTPBearer": []}]


def test_actual_owned_detail_matches_both_id_and_tenant(boundary):
    b = boundary
    r = b.client.get(DETAIL, headers=auth(b))
    assert r.status_code == 200 and r.json()["id"] == TEST_PLAYBOOK_ID
    params = b.db.execute.call_args.args[0].compile().params
    assert (
        params == {"id_1": UUID(TEST_PLAYBOOK_ID), "tenant_id_1": UUID(TEST_TENANT_ID)}
        and len(b.calls) == 1
    )


def test_missing_or_foreign_detail_is_not_found_in_verified_scope(boundary):
    b = boundary
    b.db.execute.return_value.scalar_one_or_none.return_value = None
    r = b.client.get(DETAIL, headers=auth(b))
    assert r.status_code == 404
    assert b.opened == [(database.SessionLocal, UUID(TEST_TENANT_ID))]


@pytest.mark.parametrize("path", [LIST_PATH, DETAIL])
def test_contradictory_foreign_builtin_row_never_becomes_shared_visibility(
    boundary, path
):
    b = boundary
    b.row.tenant_id = UUID(TEST_FOREIGN_ID)
    b.row.is_builtin = True
    r = b.client.get(path, headers=auth(b))
    assert r.status_code == 503 and TEST_FOREIGN_ID not in r.text


@pytest.mark.parametrize("path", [LIST_PATH, DETAIL])
def test_store_failure_is_not_empty_success(boundary, path):
    b = boundary
    b.db.execute.side_effect = RuntimeError("private store diagnostic")
    r = b.client.get(path, headers=auth(b))
    assert r.status_code == 503 and "private store diagnostic" not in r.text


def test_actual_empty_list_remains_true_empty_data(boundary):
    b = boundary
    b.db.execute.return_value.scalars.return_value.all.return_value = []
    r = b.client.get(LIST_PATH, headers=auth(b))
    assert r.status_code == 200 and r.json() == []


@pytest.mark.parametrize("method,path", UNAVAILABLE)
@pytest.mark.parametrize("signed", [False, True])
def test_all_unqualified_operations_reject_before_dependencies(
    boundary, method, path, signed
):
    b = boundary
    headers = auth(b, realm_access={"roles": ["PLATFORM_ADMIN"]}) if signed else {}
    r = b.client.request(
        method,
        path,
        headers=headers,
        json={"approved": True, "tenant_id": TEST_TENANT_ID}
        if method in {"POST", "PUT"}
        else None,
    )
    assert (
        r.status_code == 503
        and b.opened == []
        and b.db.mock_calls == []
        and b.calls == []
    )


@pytest.mark.parametrize(
    "kind",
    [
        "none",
        "header_only",
        "static",
        "cookie",
        "marker",
        "duplicate",
        "conflict",
        "malformed",
    ],
)
def test_raw_credentials_do_not_establish_SOAR_tenant(boundary, kind):
    b = boundary
    token = b.sign()
    headers = []
    if kind == "header_only":
        headers = [("X-Tenant-ID", TEST_TENANT_ID)]
    if kind == "static":
        headers = [
            ("Authorization", "Bearer disposable-local-only"),
            ("X-Tenant-ID", TEST_TENANT_ID),
        ]
    if kind == "cookie":
        headers = [("Cookie", "access_token=" + token)]
    if kind == "marker":
        headers = [
            ("Authorization", "Bearer session-cookie"),
            ("Cookie", "access_token=" + token),
        ]
    if kind == "duplicate":
        headers = [("Authorization", "Bearer " + token)] * 2
    if kind == "conflict":
        headers = [
            ("Authorization", "Bearer " + token),
            ("Cookie", "access_token=other"),
        ]
    if kind == "malformed":
        headers = [
            ("Authorization", "Basic other"),
            ("Cookie", "access_token=" + token),
        ]
    r = b.client.get(LIST_PATH, headers=headers)
    assert r.status_code == 401 and b.opened == []


@pytest.mark.parametrize(
    "updates",
    [
        {"tenant_id": TEST_FOREIGN_ID},
        {"sub": TEST_FOREIGN_ID},
        {"azp": "foreign"},
        {"sg_principal_type": "workload"},
        {"sg_principal_type": None},
        {"sg_identity_contract": "other"},
        {"typ": "ID"},
        {"act": {}},
        {"may_act": {}},
        {"client_id": "owned-browser"},
    ],
)
def test_signed_foreign_or_workload_identity_is_not_an_owned_reader(boundary, updates):
    b = boundary
    r = b.client.get(LIST_PATH, headers=auth(b, **updates))
    assert r.status_code == 403 and b.opened == []


@pytest.mark.parametrize("kind", ["forged", "expired", "wrong_audience", "outage"])
def test_actual_signature_time_and_verifier_failures_reject_before_SQL(boundary, kind):
    b = boundary
    updates = {}
    expected = 401
    if kind == "expired":
        updates = {"exp": int(time.time()) - 1}
    if kind == "wrong_audience":
        updates = {"aud": "foreign"}
    if kind == "outage":
        b.unavailable = True
        expected = 503
    token = b.sign(updates, key=b.keys[1] if kind == "forged" else None)
    r = b.client.get(LIST_PATH, headers={"Authorization": "Bearer " + token})
    assert r.status_code == expected and b.opened == [] and token not in r.text


@pytest.mark.parametrize(
    "hints",
    [
        [("X-Tenant-ID", TEST_FOREIGN_ID)],
        [("X-Tenant-ID", TEST_TENANT_ID)] * 2,
        [("X-Realm", "foreign")],
        [("X-Realm", "synthetic")] * 2,
        [("X-User-ID", TEST_USER_ID)],
        [("X-Roles", "PLATFORM_ADMIN")],
        [("X-Internal-Token", "disposable-local-only")],
        [("X-Internal-Service-Token", "disposable-local-only")],
        [("X-API-Key", "synthetic")],
    ],
)
def test_identity_hints_and_API_keys_cannot_override_context(boundary, hints):
    b = boundary
    r = b.client.get(LIST_PATH, headers=[*auth(b).items(), *hints])
    assert r.status_code == 403 and b.opened == []


@pytest.mark.parametrize(
    "query,status",
    [
        ("tenant_id=" + TEST_FOREIGN_ID, 400),
        ("limit=1&limit=2", 400),
        ("limit=0", 422),
        ("limit=101", 422),
        ("skip=-1", 422),
        ("skip=10001", 422),
        ("is_template=invalid", 422),
        ("category=" + "x" * 51, 422),
    ],
)
def test_bad_query_is_rejected_before_session_creation(boundary, query, status):
    b = boundary
    r = b.client.get(LIST_PATH + "?" + query, headers=auth(b))
    assert r.status_code == status and b.opened == []


def test_user_and_admin_role_without_exact_reader_grant_have_no_read_authority(
    boundary, monkeypatch
):
    b = boundary
    monkeypatch.setattr(
        app.state,
        "soar_principal_settings",
        SOARPrincipalSettings(
            _env_file=None, IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),)
        ),
    )
    assert (
        b.client.get(
            LIST_PATH, headers=auth(b, realm_access={"roles": ["PLATFORM_ADMIN"]})
        ).status_code
        == 403
    )
    assert b.opened == []


def test_empty_policy_fails_closed(boundary, monkeypatch):
    b = boundary
    monkeypatch.setattr(
        app.state, "soar_principal_settings", SOARPrincipalSettings(_env_file=None)
    )
    assert (
        b.client.get(LIST_PATH, headers=auth(b)).status_code == 503 and b.opened == []
    )


@pytest.mark.parametrize("path", ["/", "/health"])
def test_only_local_metadata_remains_public(boundary, path):
    b = boundary
    assert b.client.get(path).status_code == 200 and b.calls == [] and b.opened == []


def test_standalone_router_and_future_alias_cannot_admit_effects(boundary):
    b = boundary
    other = FastAPI()
    other.include_router(webhooks.router)
    with TestClient(other) as client:
        r = client.post(
            "/thehive/case/update", headers={"X-Tenant-ID": TEST_TENANT_ID}, json={}
        )
    assert r.status_code == 503 and b.opened == []
    alias = FastAPI(dependencies=[Depends(require_soar_request)])
    effect = Mock()

    @alias.get("/unreviewed")
    def renamed():
        effect()
        return {"ok": True}

    with TestClient(alias) as client:
        r = client.get("/unreviewed", headers=auth(b))
    assert r.status_code == 503
    effect.assert_not_called()


@pytest.mark.parametrize(
    "helper",
    [
        webhooks.validate_thehive_webhook_auth,
        detection_events.validate_webhook_auth,
        enrichment.get_query_tenant_session,
        phishing_containment.get_query_tenant_session,
    ],
)
def test_legacy_webhook_and_query_helpers_are_unavailable_without_effects(helper):
    import asyncio, inspect

    with pytest.raises(HTTPException) as error:
        value = helper()
        if inspect.isawaitable(value):
            asyncio.run(value)
        elif inspect.isgenerator(value):
            next(value)
    assert error.value.status_code == 503


def test_raw_UUID_session_and_runtime_DDL_launcher_are_unavailable(boundary):
    with pytest.raises(HTTPException) as error:
        next(database.get_tenant_db(TEST_TENANT_ID))
    assert error.value.status_code == 503
    with pytest.raises(RuntimeError, match="Flyway"):
        database.init_db()
    assert boundary.opened == []


@pytest.mark.parametrize(
    "change",
    [
        {"subject_id": "not-a-uuid"},
        {"subject_id": "00000000-0000-0000-0000-000000000000"},
        {"tenant_id": TEST_FOREIGN_ID},
        {"permission": "all"},
    ],
)
def test_reader_policy_cannot_cross_registration_or_expand_permission(change):
    with pytest.raises(ValidationError):
        SOARPrincipalSettings(
            _env_file=None,
            IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
            SOAR_PLAYBOOK_READERS=({**READER, **change},),
        )


def test_duplicate_reader_grants_fail_closed():
    reader = PlaybookReader(**READER)
    with pytest.raises(ValidationError):
        SOARPrincipalSettings(
            _env_file=None,
            IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
            SOAR_PLAYBOOK_READERS=(reader, reader),
        )


def test_owned_verifier_and_empty_grants_are_bound_from_SOAR_settings():
    config = Settings(
        _env_file=None,
        IAM_AGENT_URL="https://owned-iam.internal.test",
        KEYCLOAK_CLIENT_ID="owned-audience",
    )
    assert (
        config.verification_settings().IAM_AGENT_URL
        == "https://owned-iam.internal.test"
    )
    assert (
        config.verification_settings().KEYCLOAK_CLIENT_ID == "owned-audience"
        and config.principal_settings().SOAR_PLAYBOOK_READERS == ()
    )


@pytest.mark.parametrize("when", ["enter", "exit"])
def test_session_failure_cannot_report_a_successful_read(boundary, monkeypatch, when):
    b = boundary

    @contextmanager
    def failed(factory, tenant):
        if when == "enter":
            raise RuntimeError("private session diagnostic")
        yield b.db
        raise RuntimeError("private session diagnostic")

    monkeypatch.setattr(database, "tenant_session", failed)
    r = b.client.get(LIST_PATH, headers=auth(b))
    assert r.status_code == 503 and "private session diagnostic" not in r.text
