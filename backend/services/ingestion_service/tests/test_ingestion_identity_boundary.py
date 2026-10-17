"""Actual ingestion assembly with current IAM RSA and transport/key doubles.

Metrics rendering is real. Event/provider/queue effects are forbidden, not doubled
into successful ingestion. Direct service tests separately check tenant invariants.
"""

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
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from pydantic import ValidationError
import pytest

from app.main import app
import app.main as main
from app.api import ingest
from app.core.config import Settings
from app.core.principal_policy import IngestionPrincipalSettings, RuntimeReader
from app.core.security import require_ingestion_request
from app.models.event import IngestBatchRequest, RawEvent
from app.services.ingestion_service import IngestionService
from sg_core import iam_verification
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.user_principals import UserClientBinding

ROOT = Path(__file__).resolve().parents[4]
HTTP_CLIENT = httpx.Client
TENANT = "11111111-1111-4111-8111-111111111111"
SUBJECT = "22222222-2222-4222-8222-222222222222"
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
    service="ingestion-service",
    scope="service_runtime",
    permission="ingestion.read_runtime",
)
UNAVAILABLE = [
    ("POST", "/ingest/events"),
    ("POST", "/ingest/events/flush"),
    ("GET", "/health"),
    ("GET", "/ready"),
]
# Current IAM runs separately to avoid monorepo app-package collisions.
IAM_WORKER = '\nimport json,sys\nfrom types import SimpleNamespace\nfrom app.services import token_validator as m\nfrom app.models.auth import TokenValidationResponse\nvalue=json.load(sys.stdin)\nm.settings=SimpleNamespace(KEYCLOAK_URL="https://identity.internal.test",KEYCLOAK_REALM="synthetic",\n    KEYCLOAK_CLIENT_ID="review-client",KEYCLOAK_ISSUER_BASE_URLS=[],JWKS_CACHE_TTL=60)\nvalidator=m.TokenValidator(None)\n# The fixture\'s owned JWKS replaces key transport. No token-selected key/URL.\nvalidator._get_jwks_for_realm=lambda *args: {"keys":[value["jwk"]]}\nprint(TokenValidationResponse(**validator.validate_token(value["token"])).model_dump_json())\n'


@pytest.fixture(scope="module")
def keys():
    return [
        rsa.generate_private_key(public_exponent=65537, key_size=2048) for _ in range(2)
    ]


@pytest.fixture
def boundary(monkeypatch, keys):
    assert not app.dependency_overrides
    policy = IngestionPrincipalSettings(
        _env_file=None,
        IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
        INGESTION_RUNTIME_READERS=(RuntimeReader(**READER),),
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
    monkeypatch.setattr(app.state, "ingestion_principal_settings", policy)
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
    forbidden = Mock(
        side_effect=AssertionError("Unqualified ingestion/queue/provider effect")
    )
    monkeypatch.setattr(main, "get_batch_processor", forbidden)
    monkeypatch.setattr(main, "probe_http_dependency", forbidden)
    monkeypatch.setattr(IngestionService, "__init__", forbidden)
    monkeypatch.setattr(httpx, "AsyncClient", forbidden)
    main.runtime_metrics.reset()
    main.runtime_metrics.increment_counter(
        "ingestion_batches_received_total", amount=4, outcome="success"
    )
    main.runtime_metrics.set_gauge("ingestion_pending_events", 7)
    snapshot = Mock(wraps=main.runtime_metrics.snapshot)
    prometheus = Mock(wraps=main.runtime_metrics.prometheus_text)
    monkeypatch.setattr(main.runtime_metrics, "snapshot", snapshot)
    monkeypatch.setattr(main.runtime_metrics, "prometheus_text", prometheus)
    state = SimpleNamespace(
        claims=claims,
        keys=keys,
        policy=policy,
        calls=[],
        unavailable=False,
        snapshot=snapshot,
        prometheus=prometheus,
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
    b.snapshot.assert_not_called()
    b.prometheus.assert_not_called()
    b.forbidden.assert_not_called()


@pytest.mark.parametrize(
    "path", ["/metrics", "/metrics/prometheus", "/metrics?format=prometheus"]
)
def test_exact_service_wide_reader_uses_actual_metrics(boundary, path):
    b = boundary
    r = b.client.get(path, headers=auth(b))
    assert r.status_code == 200 and len(b.calls) == 1
    if path == "/metrics":
        assert r.json()["gauges"]["ingestion_pending_events"] == {"__base__": 7}
        assert r.json()["counters"]["ingestion_batches_received_total"]["total"] == 4
        assert b.snapshot.call_count == 1
    else:
        assert r.headers["content-type"].startswith("text/plain")
        assert 'ingestion_pending_events{service="ingestion-service"} 7' in r.text
        assert 'outcome="success"' in r.text and b.prometheus.call_count == 1
    assert TENANT not in r.text and SUBJECT not in r.text


def test_matching_identity_hints_do_not_select_tenant_metrics(boundary):
    b = boundary
    r = b.client.get(
        "/metrics", headers={**auth(b), "X-Tenant-ID": TENANT, "X-Realm": "synthetic"}
    )
    assert (
        r.status_code == 200
        and r.json()["gauges"]["ingestion_pending_events"]["__base__"] == 7
    )


@pytest.mark.parametrize("method,path", UNAVAILABLE)
@pytest.mark.parametrize(
    "kind", ["missing", "raw_header", "static", "signed_admin", "workload"]
)
def test_all_unqualified_routes_reject_before_factories_or_probes(
    boundary, method, path, kind
):
    b = boundary
    headers = (
        {}
        if kind == "missing"
        else {"X-Tenant-ID": TENANT}
        if kind == "raw_header"
        else {"Authorization": "Bearer synthetic-static-token", "X-Tenant-ID": TENANT}
        if kind == "static"
        else auth(b, sg_principal_type="workload")
        if kind == "workload"
        else auth(b, realm_access={"roles": ["admin"]})
    )
    r = b.client.request(
        method, path, headers=headers, json={"tenant_id": FOREIGN, "events": []}
    )
    assert r.status_code == 503
    assert not b.calls
    no_data(b)


@pytest.mark.parametrize(
    "kind",
    [
        "none",
        "header",
        "static",
        "dev",
        "basic",
        "cookie",
        "marker",
        "duplicate",
        "conflicting_cookie",
    ],
)
def test_raw_credentials_never_establish_operator_authority(boundary, kind):
    b = boundary
    headers = {}
    if kind == "header":
        headers = {"X-Tenant-ID": TENANT}
    elif kind in {"static", "dev"}:
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
    elif kind == "conflicting_cookie":
        headers = {**auth(b), "Cookie": "access_token=synthetic-static-token"}
    r = b.client.get("/metrics", headers=headers)
    assert r.status_code == 401 and not b.calls
    no_data(b)


@pytest.mark.parametrize(
    "updates",
    [
        {"tenant_id": FOREIGN},
        {"sub": FOREIGN},
        {"iss": "https://identity.internal.test/realms/foreign"},
        {"azp": "unowned"},
        {"sg_principal_type": "workload"},
        {"sg_identity_contract": "different"},
        {"act": {"sub": SUBJECT}},
        {"client_id": "owned-browser"},
        {"sg_principal_type": None},
    ],
)
def test_signed_identity_is_not_service_wide_permission(boundary, updates):
    b = boundary
    r = b.client.get("/metrics", headers=auth(b, **updates))
    assert r.status_code in {401, 403}
    no_data(b)


@pytest.mark.parametrize(
    "kind", ["forged", "expired", "audience", "outage", "conflicting_receipt"]
)
def test_real_signature_receipt_and_outage_denials_before_metrics(boundary, kind):
    b = boundary
    if kind == "forged":
        token = b.sign(key=b.keys[1])
    elif kind == "expired":
        token = b.sign({"iat": int(time.time()) - 100, "exp": int(time.time()) - 1})
    elif kind == "audience":
        token = b.sign({"aud": "foreign"})
    else:
        token = b.sign()
    b.unavailable = kind == "outage"
    if kind == "conflicting_receipt":
        b.receipt_mutator = lambda result: result.update(tenant_id=FOREIGN)
    r = b.client.get("/metrics", headers={"Authorization": "Bearer " + token})
    assert r.status_code == (503 if kind in {"outage", "conflicting_receipt"} else 401)
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
def test_forwarded_actor_tenant_and_internal_headers_cannot_override_reader(
    boundary, hints
):
    b = boundary
    r = b.client.get("/metrics", headers=[*auth(b).items(), *hints])
    assert r.status_code == 403
    no_data(b)


@pytest.mark.parametrize(
    "path",
    [
        "/metrics?tenant_id=" + FOREIGN,
        "/metrics?format=json",
        "/metrics?format=prometheus&format=prometheus",
        "/metrics?format=prometheus&scope=service_runtime",
        "/metrics/prometheus?format=prometheus",
        "/metrics?x=" + "a" * 65,
    ],
)
def test_unknown_duplicate_or_oversized_query_is_not_a_selector(boundary, path):
    b = boundary
    r = b.client.get(path, headers=auth(b))
    assert r.status_code == 400
    no_data(b)


@pytest.mark.parametrize(
    "headers", [{"Content-Length": "1"}, {"Transfer-Encoding": "chunked"}]
)
def test_runtime_read_cannot_carry_a_body(boundary, headers):
    b = boundary
    r = b.client.request(
        "GET", "/metrics", headers={**auth(b), **headers}, content=b"x"
    )
    assert r.status_code == 400
    no_data(b)


@pytest.mark.parametrize("path", ["/%6detrics", "/metrics%2fprometheus"])
def test_encoded_runtime_target_is_rejected(boundary, path):
    b = boundary
    r = b.client.get(path, headers=auth(b))
    assert r.status_code == 403
    no_data(b)


@pytest.mark.parametrize("which", ["snapshot", "prometheus"])
def test_runtime_store_failures_are_not_success_or_private_diagnostics(boundary, which):
    b = boundary
    getattr(b, which).side_effect = RuntimeError("synthetic private diagnostic")
    r = b.client.get(
        "/metrics" if which == "snapshot" else "/metrics/prometheus", headers=auth(b)
    )
    assert r.status_code == 503 and "synthetic private diagnostic" not in r.text


@pytest.mark.parametrize(
    "empty", ["grants", "registrations", "untyped_policy", "untyped_verifier"]
)
def test_empty_or_untyped_owned_configuration_fails_closed(
    boundary, monkeypatch, empty
):
    b = boundary
    if empty == "grants":
        value = IngestionPrincipalSettings(
            _env_file=None, IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),)
        )
    elif empty == "registrations":
        value = IngestionPrincipalSettings(_env_file=None)
    else:
        value = {}
    monkeypatch.setattr(
        app.state,
        "iam_verification_settings"
        if empty == "untyped_verifier"
        else "ingestion_principal_settings",
        value,
    )
    r = b.client.get("/metrics", headers=auth(b, realm_access={"roles": ["admin"]}))
    assert r.status_code in {403, 503}
    no_data(b)


def test_only_root_local_metadata_remains_public(boundary):
    b = boundary
    r = b.client.get("/")
    assert r.status_code == 200 and r.json() == {
        "status": "ok",
        "service": "ingestion-service",
    }
    assert not b.calls
    no_data(b)


@pytest.mark.parametrize("environment", ["development", "test", "production"])
def test_debug_mode_and_development_tenant_never_restore_authority(
    boundary, monkeypatch, environment
):
    b = boundary
    monkeypatch.setattr(main.settings, "ENVIRONMENT", environment)
    monkeypatch.setattr(main.settings, "DEBUG_MODE", True)
    monkeypatch.setenv("DEV_TENANT_ID", TENANT)
    assert (
        b.client.get(
            "/metrics", headers={"Authorization": "Bearer dev-token"}
        ).status_code
        == 401
    )
    assert (
        b.client.post(
            "/ingest/events", json={"events": [], "tenant_id": TENANT}
        ).status_code
        == 503
    )
    assert not b.calls
    no_data(b)


def test_proxy_root_path_requires_explicit_compatibility_before_runtime_read(boundary):
    b = boundary
    with TestClient(app, root_path="/proxy") as client:
        response = client.get("/metrics", headers=auth(b))
    assert response.status_code == 403
    no_data(b)


def test_standalone_ingest_router_and_future_route_fail_closed(boundary):
    b = boundary
    isolated = FastAPI()
    isolated.include_router(ingest.router)
    with TestClient(isolated) as client:
        r = client.post(
            "/ingest/events",
            json={"events": [], "tenant_id": FOREIGN},
            headers={"X-Tenant-ID": TENANT},
        )
    assert r.status_code == 503
    # The application-wide gate applies to subsequently added handlers too.
    prior = list(app.router.routes)
    try:

        @app.get("/synthetic-future", dependencies=[Depends(b.forbidden)])
        def future():
            return {"success": True}

        assert b.client.get("/synthetic-future", headers=auth(b)).status_code == 503
    finally:
        app.router.routes[:] = prior
    no_data(b)


@pytest.mark.parametrize(
    "change",
    [
        {"tenant_id": FOREIGN},
        {"client_id": "foreign"},
        {"subject_id": "*"},
        {"subject_id": "00000000-0000-0000-0000-000000000000"},
        {"scope": "tenant"},
        {"service": "another-service"},
        {"permission": "ingestion.enqueue"},
        {"issuer": "https://identity.internal.test/realms/foreign"},
    ],
)
def test_runtime_grant_requires_exact_registration_service_scope_and_permission(change):
    with pytest.raises(ValidationError):
        IngestionPrincipalSettings(
            _env_file=None,
            IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
            INGESTION_RUNTIME_READERS=(RuntimeReader(**{**READER, **change}),),
        )


def test_duplicate_runtime_grants_are_not_ambiguous():
    with pytest.raises(ValidationError):
        IngestionPrincipalSettings(
            _env_file=None,
            IAM_USER_CLIENT_BINDINGS=(UserClientBinding(**BINDING),),
            INGESTION_RUNTIME_READERS=(
                RuntimeReader(**READER),
                RuntimeReader(**READER),
            ),
        )


@pytest.mark.parametrize(
    "options",
    [
        {"IAM_AGENT_URL": "http://iam.internal.test"},
        {"IAM_AGENT_URL": "https://iam.internal.test/unowned"},
        {"IAM_TOKEN_VALIDATION_TIMEOUT": 11},
        {"IAM_TOKEN_VALIDATION_TIMEOUT": float("nan")},
        {"IAM_AGENT_URL": "https://user:synthetic@iam.internal.test"},
    ],
)
def test_owned_verifier_rejects_unsafe_production_config(options):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            **dict(
                ENVIRONMENT="production",
                INTERNAL_SERVICE_TOKEN="synthetic-owned-token",
                **{"IAM_AGENT_URL": "https://iam.internal.test", **options},
            ),
        )


def test_settings_bind_owned_snapshots_and_default_to_no_runtime_grants():
    s = Settings(
        _env_file=None, ENVIRONMENT="test", IAM_AGENT_URL="http://iam_agent:8000"
    )
    assert not s.principal_settings().IAM_USER_CLIENT_BINDINGS
    assert not s.principal_settings().INGESTION_RUNTIME_READERS
    assert s.verification_settings().IAM_AGENT_URL == "http://iam_agent:8000"
    assert isinstance(app.state.iam_verification_settings, IAMVerificationSettings)
    assert isinstance(
        app.state.ingestion_principal_settings, IngestionPrincipalSettings
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("hint", [FOREIGN, "", "tenant-slug"])
async def test_body_tenant_cannot_replace_canonical_internal_context(monkeypatch, hint):
    service = IngestionService()
    effect = Mock(
        side_effect=AssertionError("Must reject before normalization or queue")
    )
    monkeypatch.setattr(service.normalizer, "normalize", effect)
    monkeypatch.setattr(service.batch_processor, "add_event", effect)
    request = IngestBatchRequest(
        tenant_id=hint,
        events=[
            RawEvent(
                event_type="process",
                source="openedr",
                timestamp=datetime.now(timezone.utc),
                raw_data={"tenant_id": FOREIGN},
            )
        ],
    )
    with pytest.raises(ValueError, match="batch and auth context"):
        await service.ingest_batch(request, TENANT)
    effect.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tenant",
    [
        "tenant-slug",
        "",
        "00000000-0000-0000-0000-000000000000",
        TENANT.upper().replace("11111111", "AAAAAAAA"),
    ],
)
async def test_internal_helpers_cannot_select_noncanonical_tenant(monkeypatch, tenant):
    service = IngestionService()
    effect = Mock(
        side_effect=AssertionError("No queue authority from an invalid tenant")
    )
    monkeypatch.setattr(service.batch_processor, "_flush_batch", effect)
    with pytest.raises(ValueError, match="canonical non-nil"):
        await service.ingest_batch(IngestBatchRequest(events=[]), tenant)
    with pytest.raises(ValueError, match="canonical non-nil"):
        await service.flush_tenant_batch(tenant)
    effect.assert_not_called()


@pytest.mark.asyncio
async def test_matching_body_hint_keeps_the_internal_context_and_raw_tenant_inert(
    monkeypatch,
):
    service = IngestionService()
    queued = []

    async def add_event(tenant, event):
        queued.append((tenant, event))

    monkeypatch.setattr(service.batch_processor, "add_event", add_event)
    request = IngestBatchRequest(
        tenant_id=TENANT,
        events=[
            RawEvent(
                event_type="process",
                source="openedr",
                tenant_id=TENANT,
                timestamp=datetime.now(timezone.utc),
                raw_data={"tenant_id": FOREIGN},
            )
        ],
    )
    response = await service.ingest_batch(request, TENANT)
    assert response.ingested_count == 1 and not response.failed_count
    assert queued[0][0] == TENANT and queued[0][1].ecs_fields.tenant_id == TENANT
    assert queued[0][1].raw_data["tenant_id"] == FOREIGN
