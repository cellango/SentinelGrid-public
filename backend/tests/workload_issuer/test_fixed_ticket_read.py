"""Fixed issuer/read caller through actual ticket router/current IAM RSA.

Issuer and HTTP/key transport are synthetic; no real Keycloak, issuer provisioning,
secret store, SQL, provider, browser delegation or production caller is qualified.
"""

import base64
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
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from pydantic import SecretStr, ValidationError
import pytest

from app.api import tickets
from app.core import database
from sg_core import iam_verification, workload_read_client
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.workload_reads import (
    WorkloadReadBinding,
    WorkloadReadSettings,
    READ_CONTRACT,
    service_audience,
)
from sg_core.workload_read_client import (
    FixedTicketReadSettings,
    FixedTicketReadClient,
    keycloak_client_fragment,
    PATH,
    QUERY,
)

ROOT = Path(__file__).resolve().parents[3]
HTTP_CLIENT = httpx.Client
ISSUER = "https://identity.internal.test/realms/synthetic"
TENANT = "11111111-1111-4111-8111-111111111111"
SUBJECT = "22222222-2222-4222-8222-222222222222"
RESOURCE = "33333333-3333-4333-8333-333333333333"
FOREIGN = "44444444-4444-4444-8444-444444444444"
SECRET = "SYNTHETIC_NOT_A_REAL_CLIENT_SECRET"
BINDING = dict(
    issuer=ISSUER,
    client_id="ticket-reader",
    subject_id=SUBJECT,
    tenant_id=TENANT,
    service_id="ticketing_service",
    permission="ticketing.read",
    contract=READ_CONTRACT,
)

IAM_WORKER = '\nimport json,sys\nfrom types import SimpleNamespace\nfrom app.services import token_validator as m\nfrom app.models.auth import TokenValidationResponse\nvalue=json.load(sys.stdin)\nm.settings=SimpleNamespace(KEYCLOAK_URL="https://identity.internal.test",KEYCLOAK_REALM="synthetic",\n    KEYCLOAK_CLIENT_ID="review-client",KEYCLOAK_ISSUER_BASE_URLS=[],JWKS_CACHE_TTL=60)\nvalidator=m.TokenValidator(None)\n# The fixture\'s owned JWKS replaces key transport. No token-selected key/URL.\nvalidator._get_jwks_for_realm=lambda *args: {"keys":[value["jwk"]]}\nprint(TokenValidationResponse(**validator.validate_token(value["token"])).model_dump_json())\n'


@pytest.fixture(scope="module")
def keys():
    return [
        rsa.generate_private_key(public_exponent=65537, key_size=2048) for _ in range(2)
    ]


@pytest.fixture
def boundary(monkeypatch, keys):
    binding = WorkloadReadBinding(**BINDING)
    config = FixedTicketReadSettings(
        enabled=True, binding=binding, service_origin="https://ticket.internal.test"
    )
    verifier = IAMVerificationSettings(
        _env_file=None,
        ENVIRONMENT="production",
        IAM_AGENT_URL="https://iam.internal.test",
        KEYCLOAK_CLIENT_ID="review-client",
    )
    app = FastAPI()
    app.state.iam_verification_settings = verifier
    app.state.workload_read_settings = WorkloadReadSettings(
        _env_file=None, SERVICE_READ_WORKLOAD_BINDINGS=(binding,)
    )
    app.include_router(tickets.router, prefix="/api/v1/tickets")
    server = TestClient(app)
    db = Mock()
    opened = []

    def session(tenant):
        opened.append(tenant)
        yield db

    monkeypatch.setattr(database, "get_tenant_db", session)
    lookup = Mock(
        return_value=[
            SimpleNamespace(
                id=UUID(RESOURCE),
                tenant_id=UUID(TENANT),
                title="Synthetic ticket",
                status="open",
            )
        ]
    )
    monkeypatch.setattr(tickets.ticket_service, "search_tickets", lookup)
    forbidden = Mock(side_effect=AssertionError("No real SQL, provider or socket"))
    monkeypatch.setattr(database, "SessionLocal", forbidden)
    monkeypatch.setattr("socket.socket.connect", forbidden)
    state = SimpleNamespace(
        config=config,
        verifier=verifier,
        binding=binding,
        app=app,
        db=db,
        opened=opened,
        lookup=lookup,
        requests=[],
        clients=[],
        claims={},
        token_response={},
        token_status=200,
        token_content=None,
        token_headers={},
        data_status=None,
        data_content=None,
        iam_outage=False,
        receipt_mutator=None,
        forged=False,
    )
    fragment = keycloak_client_fragment(config, "review-client")
    jwk = json.loads(RSAAlgorithm.to_jwk(keys[0].public_key()))
    jwk.update(kid="read-key", alg="RS256", use="sig")

    def handler(request):
        state.requests.append(request)
        if str(request.url) == ISSUER + "/protocol/openid-connect/token":
            assert (
                request.method == "POST"
                and request.content == b"grant_type=client_credentials"
            )
            assert (
                request.headers["authorization"]
                == "Basic "
                + base64.b64encode(("ticket-reader:" + SECRET).encode()).decode()
            )
            assert not any(
                n in request.headers
                for n in [
                    "x-tenant-id",
                    "x-realm",
                    "x-user-id",
                    "x-internal-token",
                    "x-internal-service-token",
                ]
            )
            claims = dict(
                iss=ISSUER,
                sub=SUBJECT,
                azp="ticket-reader",
                aud=[],
                typ="Bearer",
                iat=int(time.time()) - 1,
                exp=int(time.time()) + 29,
                jti=str(uuid4()),
            )
            # This fixture interprets proposed mapper data. It is not a Keycloak runtime.
            for mapper in fragment["protocolMappers"]:
                c = mapper["config"]
                if mapper["protocolMapper"] == "oidc-audience-mapper":
                    claims["aud"].append(c["included.custom.audience"])
                else:
                    claims[c["claim.name"]] = (
                        json.loads(c["claim.value"])
                        if c["jsonType.label"] == "JSON"
                        else c["claim.value"]
                    )
            token = jwt.encode(
                {**claims, **state.claims},
                keys[1] if state.forged else keys[0],
                algorithm="RS256",
                headers={"kid": "read-key"},
            )
            if state.token_content is not None:
                return httpx.Response(
                    state.token_status,
                    content=state.token_content,
                    headers={"Content-Type": "application/json"},
                )
            return httpx.Response(
                state.token_status,
                json={
                    "access_token": token,
                    "token_type": "Bearer",
                    "expires_in": 30,
                    **state.token_response,
                },
                headers=state.token_headers,
            )
        if (
            str(request.url)
            == "https://iam.internal.test/internal/iam/auth/validate-token"
        ):
            if state.iam_outage:
                raise httpx.ConnectError("synthetic-private-diagnostic")
            assert request.method == "POST" and set(json.loads(request.content)) == {
                "token"
            }
            assert "authorization" not in request.headers
            env = {
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": os.pathsep.join(
                    [str(ROOT / "backend/libs"), str(ROOT / "backend/agents/iam_agent")]
                ),
            }
            result = subprocess.run(
                [sys.executable, "-B", "-c", IAM_WORKER],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                input=json.dumps(
                    {"token": json.loads(request.content)["token"], "jwk": jwk}
                ),
                timeout=10,
            )
            assert result.returncode == 0, "Current IAM worker failed"
            receipt = json.loads(result.stdout)
            if state.receipt_mutator:
                state.receipt_mutator(receipt)
            return httpx.Response(200, json=receipt)
        assert (
            str(request.url)
            == "https://ticket.internal.test" + PATH + "?" + QUERY.decode()
        )
        assert (
            request.method == "GET"
            and not request.content
            and request.url.query == QUERY
        )
        assert request.headers["authorization"].startswith("Bearer ")
        assert "cookie" not in request.headers
        assert not any(
            n in request.headers
            for n in [
                "x-tenant-id",
                "x-realm",
                "x-user-id",
                "x-internal-token",
                "x-internal-service-token",
            ]
        )
        if state.data_content is not None:
            return httpx.Response(
                state.data_status or 200,
                content=state.data_content,
                headers={"Content-Type": "application/json"},
            )
        if state.data_status is not None:
            return httpx.Response(
                state.data_status, json={"detail": "synthetic-private-diagnostic"}
            )
        response = server.get(
            PATH + "?" + QUERY.decode(),
            headers={"Authorization": request.headers["authorization"]},
        )
        return httpx.Response(response.status_code, json=response.json())

    def factory(**kwargs):
        state.clients.append(kwargs)
        assert kwargs["trust_env"] is False and kwargs["follow_redirects"] is False
        assert kwargs["verify"] is True
        return HTTP_CLIENT(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(httpx, "Client", factory)
    state.caller = FixedTicketReadClient(config, SecretStr(SECRET), verifier)
    yield state
    server.close()
    forbidden.assert_not_called()
    db.add.assert_not_called()
    db.commit.assert_not_called()
    db.delete.assert_not_called()
    assert not app.dependency_overrides


def test_positive_issuer_client_actual_router_and_current_IAM_roundtrip(boundary):
    b = boundary
    result = b.caller.fetch()
    assert result[0]["id"] == RESOURCE and result[0]["tenant_id"] == TENANT
    assert len(b.requests) == 4 and len(b.opened) == 1
    b.lookup.assert_called_once_with(
        db=b.db,
        tenant_id=UUID(TENANT),
        status="open",
        severity=None,
        category=None,
        limit=3,
        offset=0,
    )
    assert SECRET not in repr(b.caller) and SECRET not in repr(b.caller._secret)


def test_genuine_empty_page_is_honest_and_each_read_acquires_a_fresh_token(boundary):
    b = boundary
    b.lookup.return_value = []
    assert b.caller.fetch() == [] and b.caller.fetch() == []
    assert sum(r.url.path.endswith("/token") for r in b.requests) == 2
    assert len(b.opened) == 2


def test_disabled_default_stops_before_token_IAM_or_data_transport(boundary):
    b = boundary
    config = FixedTicketReadSettings(
        binding=b.binding, service_origin="https://ticket.internal.test"
    )
    with pytest.raises(HTTPException):
        FixedTicketReadClient(config, SecretStr(SECRET), b.verifier).fetch()
    assert not b.requests and not b.opened and not b.clients


@pytest.mark.parametrize(
    "updates",
    [
        {"tenant_id": FOREIGN},
        {"sub": FOREIGN},
        {"azp": "foreign"},
        {"sg_principal_type": "user"},
        {"sg_identity_contract": "keycloak-user-v1"},
        {"sg_permissions": ["ticketing.write"]},
        {"aud": ["review-client"]},
        {"aud": ["review-client", service_audience("ticketing_service"), "account"]},
        {"act": {"sub": SUBJECT}},
        {
            "sg_request": {
                "service_id": "ticketing_service",
                "method": "GET",
                "path": "/foreign",
                "query_sha256": hashlib.sha256(QUERY).hexdigest(),
            }
        },
        {"exp": 1},
        {"exp": int(time.time()) + 300},
        {"iat": int(time.time()) - 65},
        {"jti": "not-a-uuid"},
        {"iss": "https://foreign.internal.test/realms/synthetic"},
    ],
)
def test_wrong_signed_claims_never_dispatch_downstream(boundary, updates):
    b = boundary
    b.claims = updates
    with pytest.raises(HTTPException) as exc:
        b.caller.fetch()
    assert exc.value.status_code == 503 and not b.opened
    assert not any(r.url.host == "ticket.internal.test" for r in b.requests)


@pytest.mark.parametrize("kind", ["forged", "iam_outage", "conflicting_receipt"])
def test_current_IAM_signature_receipt_and_outage_gate_data(boundary, kind):
    b = boundary
    b.forged = kind == "forged"
    b.iam_outage = kind == "iam_outage"
    if kind == "conflicting_receipt":
        b.receipt_mutator = lambda r: r.update(tenant_id=FOREIGN)
    with pytest.raises(HTTPException) as exc:
        b.caller.fetch()
    assert (
        exc.value.status_code == 503
        and SECRET not in str(exc.value)
        and "synthetic-private" not in str(exc.value)
    )
    assert not b.opened and not any(
        r.url.host == "ticket.internal.test" for r in b.requests
    )


@pytest.mark.parametrize(
    "change",
    [
        {"token_type": "bearer"},
        {"expires_in": True},
        {"expires_in": 61},
        {"expires_in": 0},
        {"refresh_token": "synthetic"},
        {"id_token": "synthetic"},
        {"scope": "offline_access"},
        {"access_token": "x" * 32769},
    ],
)
def test_unexpected_token_response_rejected_before_IAM(boundary, change):
    b = boundary
    b.token_response = change
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert len(b.requests) == 1 and not b.opened


@pytest.mark.parametrize(
    "content",
    [
        b'{"access_token":"a","access_token":"b"}',
        b'{"x":NaN}',
        b'{"x":1e999}',
        b"x" * 131073,
        b"[]",
    ],
)
def test_malformed_ambiguous_or_oversized_token_JSON_is_unavailable(boundary, content):
    b = boundary
    b.token_content = content
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert len(b.requests) == 1 and not b.opened


@pytest.mark.parametrize("status", [301, 302, 307, 400, 401, 403, 429, 500])
def test_token_failures_and_redirects_do_not_trigger_fallback_or_retry(
    boundary, status
):
    b = boundary
    b.token_status = status
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert len(b.requests) == 1 and not b.opened


@pytest.mark.parametrize("status", [301, 302, 401, 403, 429, 500])
def test_data_errors_are_not_empty_pages_or_success(boundary, status):
    b = boundary
    b.data_status = status
    with pytest.raises(HTTPException) as exc:
        b.caller.fetch()
    assert exc.value.status_code == 503 and "synthetic-private" not in str(exc.value)
    assert not b.opened


@pytest.mark.parametrize(
    "rows",
    [
        [{"id": RESOURCE, "tenant_id": FOREIGN}],
        [{"id": "slug", "tenant_id": TENANT}],
        [{"id": RESOURCE, "tenant_id": TENANT}] * 4,
        {},
        None,
    ],
)
def test_foreign_unbounded_or_malformed_data_page_cannot_succeed(boundary, rows):
    b = boundary
    b.data_content = json.dumps(rows).encode()
    with pytest.raises(HTTPException):
        b.caller.fetch()
    assert not b.opened


@pytest.mark.parametrize(
    "changes",
    [
        {"service_origin": "http://ticket.internal.test"},
        {"service_origin": "https://user:secret@ticket.internal.test"},
        {"service_origin": "https://ticket.internal.test/path"},
        {"service_origin": "https://ticket.internal.test?"},
        {"service_origin": "https://ticket.internal.test#"},
        {"service_origin": "https://ticket.internal.test:0"},
        {"timeout_seconds": 11.0},
        {"timeout_seconds": float("nan")},
        {"ca_bundle": ""},
        {"path": "/foreign"},
        {"query": "limit=100"},
    ],
)
def test_caller_config_cannot_choose_unowned_target_transport_or_body(changes):
    with pytest.raises(ValidationError):
        FixedTicketReadSettings(
            binding=WorkloadReadBinding(**BINDING),
            **{"service_origin": "https://ticket.internal.test", **changes},
        )


def test_no_caller_arguments_or_raw_untyped_secret_are_an_authority_channel(boundary):
    b = boundary
    with pytest.raises(TypeError):
        b.caller.fetch(tenant_id=FOREIGN, path="/foreign", approved=True)
    with pytest.raises(ValueError):
        FixedTicketReadClient(b.config, SECRET, b.verifier)
    assert not b.requests


def test_fragment_is_disabled_deterministic_secret_free_and_issuer_owned():
    c = FixedTicketReadSettings(
        binding=WorkloadReadBinding(**BINDING),
        service_origin="https://ticket.internal.test",
    )
    fragment = keycloak_client_fragment(c, "review-client")
    assert (
        fragment == keycloak_client_fragment(c, "review-client")
        and fragment["enabled"] is False
    )
    assert not any(
        fragment[x]
        for x in [
            "publicClient",
            "standardFlowEnabled",
            "implicitFlowEnabled",
            "directAccessGrantsEnabled",
            "authorizationServicesEnabled",
            "fullScopeAllowed",
        ]
    )
    assert (
        fragment["serviceAccountsEnabled"]
        and not fragment["defaultClientScopes"]
        and not fragment["optionalClientScopes"]
    )
    names = {m["config"].get("claim.name") for m in fragment["protocolMappers"]}
    assert not names.intersection({"sub", "azp", "iss", "iat", "exp", "jti", "roles"})
    assert SECRET not in json.dumps(fragment) and "secret" not in fragment
    mappers = {
        m["config"]["claim.name"]: m["config"]
        for m in fragment["protocolMappers"]
        if "claim.name" in m["config"]
    }
    assert json.loads(mappers["sg_permissions"]["claim.value"]) == ["ticketing.read"]
    target = json.loads(mappers["sg_request"]["claim.value"])
    assert target == {
        "service_id": "ticketing_service",
        "method": "GET",
        "path": PATH,
        "query_sha256": hashlib.sha256(QUERY).hexdigest(),
    }
    assert all(
        m["id.token.claim"] == "false" and m["userinfo.token.claim"] == "false"
        for m in mappers.values()
    )


def test_issuer_parent_domain_cookie_does_not_cross_into_data_request(boundary):
    b = boundary
    b.token_headers = {
        "Set-Cookie": "synthetic=private; Domain=internal.test; Path=/; Secure"
    }
    assert b.caller.fetch()[0]["id"] == RESOURCE
