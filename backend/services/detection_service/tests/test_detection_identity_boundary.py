"""Actual detection assembly/gate/projector with current IAM RSA and owned doubles.

Runtime state is injected, never an authentication override or real scheduler.
SQL, APScheduler lifecycle, evaluation and provider effects are unqualified.
"""

import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from pydantic import ValidationError
import pytest
from starlette.requests import Request

from app.main import app
import app.main as main
from app.api import rules, scheduler as scheduler_api
from app.core import database, security
from app.core.config import Settings
from app.core.principal_policy import DetectionPrincipalSettings, RuntimeReader
from app.services import scheduler
from sg_core import iam_verification
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.user_principals import UserClientBinding

ROOT = Path(__file__).resolve().parents[4]
HTTP_CLIENT = httpx.Client
TENANT = "11111111-1111-4111-8111-111111111111"
SUBJECT = "22222222-2222-4222-8222-222222222222"
FOREIGN = "44444444-4444-4444-8444-444444444444"
RESOURCE = "33333333-3333-4333-8333-333333333333"
ISSUER = "https://identity.internal.test/realms/synthetic"
STATUS = "/api/v1/scheduler/status"
RULE = "/api/v1/rules/" + RESOURCE
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
    service="detection-service",
    scope="service_runtime",
    permission="detection.read_scheduler_runtime",
)
UNAVAILABLE = [
    ("GET", "/health"),
    ("POST", "/api/v1/rules"),
    ("GET", "/api/v1/rules"),
    ("GET", RULE),
    ("PATCH", RULE),
    ("DELETE", RULE),
    ("POST", RULE + "/evaluate"),
    ("POST", "/api/v1/rules/evaluate/all"),
    ("POST", "/api/v1/rules/enable"),
    *[("POST", "/api/v1/scheduler/" + tail) for tail in ["start", "stop", "trigger"]],
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
    policy = DetectionPrincipalSettings(
        _env_file=None,
        IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
        DETECTION_SCHEDULER_READERS=(RuntimeReader(**READER),),
    )
    monkeypatch.setattr(
        app.state,
        "iam_verification_settings",
        IAMVerificationSettings(
            _env_file=None,
            IAM_AGENT_URL="https://iam.internal.test",
            KEYCLOAK_CLIENT_ID="review-client",
        ),
    )
    monkeypatch.setattr(app.state, "detection_principal_settings", policy)
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
    job = SimpleNamespace(
        id="synthetic-job",
        name="Synthetic bounded job",
        next_run_time=datetime.now(timezone.utc),
    )
    runtime = SimpleNamespace(running=True, get_jobs=Mock(return_value=[job]))
    monkeypatch.setattr(scheduler, "_scheduler", runtime)
    forbidden = Mock(
        side_effect=AssertionError("Unqualified lifecycle, SQL or provider effect")
    )
    monkeypatch.setattr(database, "SessionLocal", forbidden)
    monkeypatch.setattr("sqlalchemy.engine.Engine.connect", forbidden)
    monkeypatch.setattr("sqlalchemy.sql.schema.MetaData.create_all", forbidden)
    monkeypatch.setattr(httpx, "AsyncClient", forbidden)
    state = SimpleNamespace(
        keys=keys,
        claims=claims,
        job=job,
        runtime=runtime,
        policy=policy,
        calls=[],
        forbidden=forbidden,
        unavailable=False,
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
            name in request.headers
            for name in [
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
        assert result.returncode == 0, "Synthetic current IAM worker failed"
        receipt = json.loads(result.stdout)
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
    assert not app.dependency_overrides


def auth(b, **updates):
    return {"Authorization": "Bearer " + b.sign(updates)}


def no_data(b):
    b.runtime.get_jobs.assert_not_called()
    b.forbidden.assert_not_called()


def test_actual_service_wide_reader_projects_initialized_runtime(boundary):
    b = boundary
    r = b.client.get(STATUS, headers=auth(b))
    assert r.status_code == 200 and len(b.calls) == 1
    assert r.json() == {
        "running": True,
        "jobs": [
            {
                "id": "synthetic-job",
                "name": "Synthetic bounded job",
                "next_run_time": b.job.next_run_time.isoformat(),
            }
        ],
    }
    b.runtime.get_jobs.assert_called_once_with()
    assert TENANT not in r.text and SUBJECT not in r.text


def test_matching_hints_do_not_select_a_tenant_scheduler(boundary):
    b = boundary
    r = b.client.get(
        STATUS, headers={**auth(b), "X-Tenant-ID": TENANT, "X-Realm": "synthetic"}
    )
    assert r.status_code == 200 and len(r.json()["jobs"]) == 1


def test_uninitialized_runtime_never_fabricates_stopped_or_empty_success(
    boundary, monkeypatch
):
    b = boundary
    monkeypatch.setattr(scheduler, "_scheduler", None)
    assert b.client.get(STATUS, headers=auth(b)).status_code == 503
    no_data(b)


def test_actual_empty_stopped_runtime_is_distinct_from_unavailable(boundary):
    b = boundary
    b.runtime.running = False
    b.runtime.get_jobs.return_value = []
    assert b.client.get(STATUS, headers=auth(b)).json() == {
        "running": False,
        "jobs": [],
    }


@pytest.mark.parametrize(
    "change",
    [
        "oversized",
        "bad_running",
        "long_name",
        "control_name",
        "naive_time",
        "broken_store",
    ],
)
def test_bad_or_failed_runtime_projection_is_generic_unavailable(boundary, change):
    b = boundary
    if change == "oversized":
        b.runtime.get_jobs.return_value = [b.job] * 101
    elif change == "bad_running":
        b.runtime.running = "false"
    elif change == "long_name":
        b.job.name = "x" * 257
    elif change == "control_name":
        b.job.name = "bad\nname"
    elif change == "naive_time":
        b.job.next_run_time = datetime.now()
    else:
        b.runtime.get_jobs.side_effect = RuntimeError("synthetic-private-diagnostic")
    r = b.client.get(STATUS, headers=auth(b))
    assert r.status_code == 503 and "synthetic-private-diagnostic" not in r.text


@pytest.mark.parametrize("method,path", UNAVAILABLE)
@pytest.mark.parametrize("kind", ["raw_header", "signed_admin", "workload"])
def test_all_unqualified_operations_stop_before_storage_or_lifecycle(
    boundary, method, path, kind
):
    b = boundary
    headers = (
        {"X-Tenant-ID": TENANT, "X-Internal-Token": "synthetic"}
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
            json={"tenant_id": FOREIGN, "create_alerts_flag": True},
        ).status_code
        == 503
    )
    assert not b.calls
    no_data(b)


@pytest.mark.parametrize(
    "kind",
    [
        "none",
        "header",
        "dev",
        "static",
        "basic",
        "cookie",
        "marker",
        "duplicate",
        "conflict",
    ],
)
def test_raw_credentials_cannot_grant_global_runtime_reads(boundary, kind):
    b = boundary
    headers = {}
    if kind == "header":
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
        headers = {**auth(b), "Cookie": "access_token=synthetic-static-token"}
    assert b.client.get(STATUS, headers=headers).status_code == 401
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
def test_signed_identity_is_not_global_operation_permission(boundary, updates):
    b = boundary
    assert b.client.get(STATUS, headers=auth(b, **updates)).status_code in {401, 403}
    no_data(b)


@pytest.mark.parametrize(
    "kind", ["forged", "expired", "audience", "outage", "conflicting_receipt"]
)
def test_actual_signature_receipt_and_verifier_failure_denials(boundary, kind):
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
        STATUS, headers={"Authorization": "Bearer " + token}
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
def test_raw_hints_cannot_override_owned_service_wide_authority(boundary, hints):
    b = boundary
    assert b.client.get(STATUS, headers=[*auth(b).items(), *hints]).status_code == 403
    no_data(b)


@pytest.mark.parametrize(
    "path",
    [
        STATUS + "?tenant_id=" + FOREIGN,
        STATUS + "?format=prometheus",
        STATUS + "?x=" + "a" * 65,
        STATUS + "?scope=service_runtime&scope=service_runtime",
    ],
)
def test_query_cannot_select_or_expand_runtime_scope(boundary, path):
    b = boundary
    assert b.client.get(path, headers=auth(b)).status_code == 400
    no_data(b)


@pytest.mark.parametrize(
    "headers", [{"Content-Length": "1"}, {"Transfer-Encoding": "chunked"}]
)
def test_runtime_read_body_is_rejected(boundary, headers):
    b = boundary
    assert (
        b.client.request(
            "GET", STATUS, headers={**auth(b), **headers}, content=b"x"
        ).status_code
        == 400
    )
    no_data(b)


def test_encoded_and_proxy_root_targets_need_explicit_compatibility(boundary):
    b = boundary
    assert (
        b.client.get("/api/v1/scheduler/%73tatus", headers=auth(b)).status_code == 403
    )
    with TestClient(app, root_path="/proxy") as client:
        assert client.get(STATUS, headers=auth(b)).status_code == 403
    no_data(b)


@pytest.mark.parametrize(
    "kind", ["grants", "registrations", "untyped_policy", "untyped_verifier"]
)
def test_empty_or_untyped_owned_settings_fail_closed(boundary, monkeypatch, kind):
    b = boundary
    value = (
        DetectionPrincipalSettings(
            _env_file=None, IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),)
        )
        if kind == "grants"
        else DetectionPrincipalSettings(_env_file=None)
        if kind == "registrations"
        else {}
    )
    monkeypatch.setattr(
        app.state,
        "iam_verification_settings"
        if kind == "untyped_verifier"
        else "detection_principal_settings",
        value,
    )
    assert b.client.get(
        STATUS, headers=auth(b, realm_access={"roles": ["admin"]})
    ).status_code in {403, 503}
    no_data(b)


@pytest.mark.parametrize("environment", ["development", "test", "production"])
def test_debug_settings_cannot_enable_tenant_or_operator_identity(
    boundary, monkeypatch, environment
):
    b = boundary
    monkeypatch.setattr(main.settings, "ENVIRONMENT", environment)
    monkeypatch.setattr(main.settings, "DEBUG_MODE", True)
    monkeypatch.setenv("DEV_TENANT_ID", TENANT)
    assert (
        b.client.get(STATUS, headers={"Authorization": "Bearer dev-token"}).status_code
        == 401
    )
    assert (
        b.client.get("/api/v1/rules", headers={"X-Tenant-ID": TENANT}).status_code
        == 503
    )
    no_data(b)


def test_source_startup_and_root_never_autostart_scheduler(boundary, monkeypatch):
    b = boundary
    monkeypatch.setattr(scheduler, "start_scheduler", b.forbidden)
    monkeypatch.setattr(scheduler, "stop_scheduler", b.forbidden)
    with TestClient(app) as client:
        assert client.get("/").json() == {
            "status": "ok",
            "service": "detection-service",
        }
    assert not b.calls
    no_data(b)


def test_standalone_routers_and_future_route_cannot_bypass_gate(boundary):
    b = boundary
    isolated = FastAPI()
    isolated.include_router(rules.router, prefix="/api/v1")
    isolated.include_router(scheduler_api.router, prefix="/api/v1")
    with TestClient(isolated) as client:
        for method, path in UNAVAILABLE:
            if path != "/health":
                assert client.request(method, path, json={}).status_code == 503
    routes = list(app.router.routes)
    try:

        @app.get("/synthetic-future")
        def future():
            return {"started": True}

        assert b.client.get("/synthetic-future", headers=auth(b)).status_code == 503
    finally:
        app.router.routes[:] = routes
    no_data(b)


def test_legacy_tenant_sessions_and_token_helper_do_not_grant_authority(boundary):
    b = boundary
    for generator in [
        database.get_db(),
        database.get_tenant_db(TENANT),
        database.get_tenant_session(TENANT),
    ]:
        with pytest.raises(HTTPException) as exc:
            next(generator)
        assert exc.value.status_code == 503
    request = Request({"type": "http", "headers": [(b"x-tenant-id", TENANT.encode())]})
    for coroutine in [
        security.get_current_tenant(request),
        security.verify_token_with_iam_agent("dev-token"),
    ]:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(coroutine)
        assert exc.value.status_code == 503
    no_data(b)


@pytest.mark.parametrize(
    "action", ["start", "stop", "one_time", "job_global", "job_tenant"]
)
def test_direct_lifecycle_cannot_claim_started_or_completed_effects(boundary, action):
    b = boundary
    with pytest.raises(RuntimeError, match="Owned detection scheduler workload"):
        if action == "start":
            scheduler.start_scheduler(TENANT)
        elif action == "stop":
            scheduler.stop_scheduler()
        elif action == "one_time":
            scheduler.add_one_time_job(b.forbidden, datetime.now(timezone.utc))
        else:
            asyncio.run(
                scheduler.evaluate_all_rules_job(
                    None if action == "job_global" else TENANT
                )
            )
    no_data(b)


@pytest.mark.parametrize(
    "change",
    [
        {"subject_id": "*"},
        {"subject_id": "00000000-0000-0000-0000-000000000000"},
        {"tenant_id": FOREIGN},
        {"client_id": "foreign"},
        {"scope": "tenant"},
        {"service": "another-service"},
        {"permission": "detection.evaluate"},
    ],
)
def test_exact_runtime_policy_cannot_expand_registration_scope_or_operation(change):
    with pytest.raises(ValidationError):
        DetectionPrincipalSettings(
            _env_file=None,
            IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
            DETECTION_SCHEDULER_READERS=(RuntimeReader(**{**READER, **change}),),
        )


def test_duplicate_grants_and_empty_defaults_are_explicit():
    with pytest.raises(ValidationError):
        DetectionPrincipalSettings(
            _env_file=None,
            IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
            DETECTION_SCHEDULER_READERS=(
                RuntimeReader(**READER),
                RuntimeReader(**READER),
            ),
        )
    settings = Settings(_env_file=None, ENVIRONMENT="test")
    assert (
        not settings.principal_settings().IAM_USER_CLIENT_BINDINGS
        and not settings.principal_settings().DETECTION_SCHEDULER_READERS
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
def test_owned_production_verifier_config_is_bounded(options):
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


def test_source_boundary_does_not_install_or_replace_APScheduler():
    assert not any(
        name == "apscheduler" or name.startswith("apscheduler.") for name in sys.modules
    )
