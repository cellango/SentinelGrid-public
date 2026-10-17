"""Real RSA/IAM validation through the shared client, with only HTTP replaced.

No app.main, database, Redis stub, provider or live service is involved. The
synthetic route exercises the existing tenant dependency, not gateway coverage.
"""

import base64
from copy import deepcopy
from datetime import datetime, timezone
import json
import time
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from pydantic import ValidationError
import pytest

from app.models.auth import TokenValidationResponse
from app.services import token_validator as iam
from sg_core import iam_verification as verifier
from sg_core.security import get_current_tenant, verify_token

_REAL_CLIENT = httpx.Client


@pytest.fixture(scope="module")
def keys():
    return [rsa.generate_private_key(public_exponent=65537, key_size=2048) for _ in range(2)]


@pytest.fixture
def boundary(monkeypatch, keys):
    config = verifier.IAMVerificationSettings(
        _env_file=None, IAM_AGENT_URL="https://iam.internal.test", KEYCLOAK_CLIENT_ID="review-client",
    )
    monkeypatch.setattr(verifier, "get_verification_settings", lambda: config)
    monkeypatch.setattr(iam, "settings", SimpleNamespace(
        KEYCLOAK_URL="https://identity.internal.test", KEYCLOAK_REALM="synthetic",
        KEYCLOAK_CLIENT_ID="review-client", KEYCLOAK_ISSUER_BASE_URLS=[], JWKS_CACHE_TTL=60,
    ))
    jwk = json.loads(RSAAlgorithm.to_jwk(keys[0].public_key()))
    jwk.update(kid="test-key", use="sig", alg="RS256")
    validator = iam.TokenValidator(None)
    fetch = Mock(return_value={"keys": [jwk]})
    monkeypatch.setattr(validator, "_get_jwks_for_realm", fetch)
    claims = dict(sub=str(uuid4()), tenant_id=str(uuid4()),
                  iss="https://identity.internal.test/realms/synthetic", aud="review-client",
                  exp=int(time.time()) + 600, iat=int(time.time()) - 5,
                  realm_access={"roles": ["SOC_ANALYST"]})
    calls, options, receipts = [], [], []
    state = SimpleNamespace(config=config, claims=claims, validator=validator, keys=keys,
                            fetch=fetch, calls=calls, options=options, receipts=receipts,
                            change=None, response=None, error=None)

    def sign(payload=None, key=None, **kwargs):
        return jwt.encode(claims if payload is None else payload, key or keys[0],
                          algorithm="RS256", headers={"kid": "test-key", **kwargs})

    state.sign = sign

    def handler(request):
        calls.append(request)
        assert str(request.url) == "https://iam.internal.test/internal/iam/auth/validate-token"
        assert request.method == "POST"
        assert set(json.loads(request.content)) == {"token"}
        # No caller, tenant, role or service credential can be promoted via headers.
        for name in ("authorization", "x-tenant-id", "x-user-id", "x-internal-service-token"):
            assert name not in request.headers
        if state.error:
            raise state.error
        if state.response is not None:
            return state.response
        result = TokenValidationResponse(**validator.validate_token(json.loads(request.content)["token"]))
        receipt = result.model_dump(mode="json")
        receipts.append(deepcopy(receipt))
        if state.change:
            state.change(receipt)
        return httpx.Response(200, json=receipt)

    def factory(**kwargs):
        options.append(kwargs)
        return _REAL_CLIENT(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(verifier.httpx, "Client", factory)
    return state


def assert_denied(boundary, status=401, token=None):
    with pytest.raises(Exception) as caught:
        verify_token(boundary.sign() if token is None else token)
    assert isinstance(caught.value, verifier.HTTPException)
    assert caught.value.status_code == status
    assert caught.value.detail in {"Invalid token", "Missing token", "Token verification service unavailable"}
    return caught.value


def test_real_signed_identity_round_trip_does_not_enrich_or_mutate(boundary):
    boundary.claims["tenant_id"] = boundary.claims["tenant_id"].upper()
    boundary.claims["email"] = "review@example.test"
    boundary.claims["plan_tier"] = "synthetic"
    before = deepcopy(boundary.claims)
    token = boundary.sign()
    actual = verify_token(token)
    assert actual["tenant_id"] == before["tenant_id"].lower()
    assert actual["sub"] == actual["user_id"] == before["sub"]
    assert actual["roles"] == ["SOC_ANALYST"]
    assert actual["plan_tier"] == "synthetic"
    assert boundary.claims == before
    assert boundary.receipts[0]["payload"] == before
    assert json.loads(boundary.calls[0].content) == {"token": token}
    assert boundary.options[0]["verify"] is True
    assert boundary.options[0]["trust_env"] is False
    assert boundary.options[0]["follow_redirects"] is False
    assert boundary.calls[0].extensions["timeout"] == {"connect": 5.0, "read": 5.0, "write": 5.0, "pool": 1.0}


def test_tenant_dependency_binds_only_verified_identity_before_handler(boundary):
    reached = []
    app = FastAPI()

    @app.post("/tenant-data")
    def data(request: Request, tenant: str = Depends(get_current_tenant)):
        reached.append(tenant)
        return {"tenant_id": tenant}

    client = TestClient(app)
    foreign = str(uuid4())
    response = client.post("/tenant-data?tenant_id=" + foreign,
                           headers={"Authorization": "Bearer " + boundary.sign(), "X-Tenant-ID": foreign,
                                    "X-User-ID": foreign, "X-Roles": "PLATFORM_ADMIN", "X-Realm": "foreign"},
                           json={"tenant_id": foreign, "user_id": foreign, "roles": ["PLATFORM_ADMIN"]})
    assert response.status_code == 200
    assert reached == [boundary.claims["tenant_id"]]
    assert response.json() == {"tenant_id": boundary.claims["tenant_id"]}
    reached.clear()
    response = client.post("/tenant-data", headers={"Authorization": "Bearer " + boundary.sign(key=boundary.keys[1]),
                                                   "X-Tenant-ID": foreign})
    assert response.status_code == 401 and reached == []


@pytest.mark.parametrize("update", [
    {"exp": 1}, {"iat": int(time.time()) + 3600}, {"nbf": int(time.time()) + 3600},
    {"iss": "https://attacker.example.test/realms/synthetic"}, {"aud": "other-client"},
    {"tenant_id": "demo"}, {"tenant_id": None}, {"sub": "not-a-uuid"},
    {"sub": "00000000-0000-0000-0000-000000000000"},
    {"tenant_id": "00000000-0000-0000-0000-000000000000"},
    {"realm_access": {"roles": "PLATFORM_ADMIN"}},
])
def test_invalid_signed_identity_never_becomes_authority(boundary, update):
    boundary.claims.update(update)
    # IAM itself rejects all but non-UUID/nil subjects and nil UUID tenants.
    status = 503 if update.get("sub") in {"not-a-uuid", "00000000-0000-0000-0000-000000000000"} or update.get("tenant_id") == "00000000-0000-0000-0000-000000000000" else 401
    assert_denied(boundary, status)


def test_forgery_and_unavailable_signing_keys_never_use_local_claims(boundary):
    assert_denied(boundary, token=boundary.sign(key=boundary.keys[1]))
    boundary.fetch.return_value = None
    assert_denied(boundary)


@pytest.mark.parametrize("token", [None, "", "shared-service-token", "a.b.c", "a..c", "x" * 32769], ids=["none", "empty", "shared", "bad-base64", "empty-segment", "oversize"])
def test_missing_malformed_and_shared_tokens_are_not_forwarded(boundary, token):
    with pytest.raises(verifier.HTTPException) as error:
        verify_token(token)
    assert error.value.status_code == 401
    assert boundary.calls == []


@pytest.mark.parametrize("headers", [{"jku": "https://attacker.example.test/jwks"}, {"x5u": "https://attacker.example.test/cert"}, {"jwk": {}}, {"crit": ["other"]}])
def test_external_key_hints_never_select_verification_destination(boundary, headers):
    assert_denied(boundary, token=boundary.sign(**headers))
    assert boundary.calls == []


def test_wrong_algorithm_does_not_call_iam(boundary):
    token = jwt.encode(boundary.claims, None, algorithm="none", headers={"kid": "test-key"})
    assert_denied(boundary, token=token)
    assert boundary.calls == []


def change(field, value):
    return lambda receipt: receipt.__setitem__(field, value)


@pytest.mark.parametrize("mutate", [
    change("valid", "true"), change("valid", 1), change("valid", None),
    change("error", "sensitive upstream diagnostic"), change("payload", None), change("payload", []),
    change("tenant_id", str(uuid4())), change("tenant_id", "demo"), change("user_id", str(uuid4())),
    change("roles", ["PLATFORM_ADMIN"]), change("roles", "SOC_ANALYST"), change("roles", [1]),
    change("plan_tier", "enterprise"), change("expires_at", "tomorrow"),
    change("expires_at", "2030-01-01T00:00:00"), change("expires_at", "2030-01-01T00:00:00Z"),
    lambda r: r["payload"].update(tenant_id=str(uuid4())),
    lambda r: r["payload"].update(sub=str(uuid4())),
    lambda r: r["payload"]["realm_access"].update(roles=["PLATFORM_ADMIN"]),
])
def test_malformed_or_conflicting_receipt_never_overrides_signed_identity(boundary, mutate):
    boundary.change = mutate
    assert_denied(boundary, 503)


def test_well_formed_receipt_from_another_valid_token_is_rejected(boundary):
    other = {**boundary.claims, "sub": str(uuid4()), "tenant_id": str(uuid4())}
    receipt = TokenValidationResponse(**boundary.validator.validate_token(boundary.sign(other))).model_dump(mode="json")
    boundary.response = httpx.Response(200, json=receipt)
    assert_denied(boundary, 503)


@pytest.mark.parametrize("update", [
    {"roles": ["PLATFORM_ADMIN"]}, {"realm_roles": ["PLATFORM_ADMIN"]}, {"user_id": str(uuid4())},
    {"realm_access": {"roles": [""]}}, {"realm_access": {"roles": [" ADMIN "]}},
    {"realm_access": {"roles": ["ADMIN", "ADMIN"]}}, {"realm_access": {"roles": ["A"] * 129}},
])
def test_conflicting_signed_aliases_or_unbounded_roles_are_rejected(boundary, update):
    boundary.claims.update(update)
    assert_denied(boundary, 503)


@pytest.mark.parametrize("status, expected", [(301, 503), (302, 503), (307, 503), (308, 503), (204, 503), (400, 503), (401, 401), (403, 401), (429, 503), (500, 503)])
def test_redirects_and_error_bodies_are_not_followed_or_disclosed(boundary, status, expected):
    boundary.response = httpx.Response(status, headers={"Location": "https://attacker.example.test"}, text="private upstream response")
    assert_denied(boundary, expected)
    assert len(boundary.calls) == 1


@pytest.mark.parametrize("body, content_type", [
    (b"[]", "application/json"), (b"null", "application/json"), (b"not JSON", "application/json"),
    (b'{"valid":true,"valid":false}', "application/json"),
    (b'{"valid":true,"x":NaN}', "application/json"),
    (b"{}", "text/html"), (b"x" * 131073, "application/json"),
])
def test_malformed_duplicate_or_oversized_response_is_unavailable(boundary, body, content_type):
    boundary.response = httpx.Response(200, content=body, headers={"Content-Type": content_type})
    assert_denied(boundary, 503)


@pytest.mark.parametrize("error", [httpx.ConnectError("secret destination"), httpx.ReadTimeout("secret token"), httpx.RemoteProtocolError("secret response")])
def test_transport_failures_expose_only_generic_unavailability(boundary, error, caplog):
    token = boundary.sign()
    boundary.error = error
    assert_denied(boundary, 503, token)
    assert token not in caplog.text and "secret destination" not in caplog.text


def test_ambient_proxy_and_trust_variables_cannot_override_transport(boundary, monkeypatch):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "SSL_CERT_FILE", "SSL_CERT_DIR"):
        monkeypatch.setenv(name, "/nonexistent-untrusted-destination")
    assert verify_token(boundary.sign())["tenant_id"] == boundary.claims["tenant_id"]
    assert boundary.options[0]["trust_env"] is False and boundary.options[0]["verify"] is True


@pytest.mark.parametrize("url", [
    "https://u:p@iam.example.test", "https://u@iam.example.test", "https://iam.example.test/path",
    "https://iam.example.test?x=y", "https://iam.example.test#x", "https://iam.example.test?",
    "https://iam.example.test#", "https://iam.example.test\\@attacker.example.test", " https://iam.example.test",
    "https://iam.example.test\n", "file:///tmp/iam", "ftp://iam.example.test", "http://remote.example.test",
    "https://iam.example.test:0", "https://iam.example.test:65536", "https://iam.example.test:invalid",
    "https://iam%2eexample.test", "https://", "http://iam_agent.evil.test:8000",
])
def test_invalid_owned_destinations_fail_configuration(url):
    with pytest.raises((ValidationError, ValueError)):
        verifier.IAMVerificationSettings(_env_file=None, IAM_AGENT_URL=url)


@pytest.mark.parametrize("environment", ["production", "staging", "unknown"])
@pytest.mark.parametrize("url", ["http://iam_agent:8000", "http://localhost:8005", "https://iam_agent:8000"])
def test_only_local_development_can_use_local_placeholders(environment, url):
    with pytest.raises(ValidationError):
        verifier.IAMVerificationSettings(_env_file=None, ENVIRONMENT=environment, IAM_AGENT_URL=url)


@pytest.mark.parametrize("url", ["http://iam_agent:8000", "http://127.0.0.1:8005", "http://[::1]:8005", "https://iam.internal.test/"])
def test_owned_local_development_and_https_origins_are_accepted(url):
    assert verifier.IAMVerificationSettings(_env_file=None, IAM_AGENT_URL=url).IAM_AGENT_URL == url


@pytest.mark.parametrize("value", [0, -1, 11, float("inf"), float("nan")])
def test_timeout_is_finite_positive_and_bounded(value):
    with pytest.raises(ValidationError):
        verifier.IAMVerificationSettings(_env_file=None, IAM_TOKEN_VALIDATION_TIMEOUT=value)


def test_invalid_configuration_or_ca_fails_without_outbound_call(boundary, monkeypatch):
    def invalid():
        raise ValueError("private invalid configuration")
    monkeypatch.setattr(verifier, "get_verification_settings", invalid)
    assert_denied(boundary, 503)
    assert boundary.calls == []
    monkeypatch.setattr(verifier, "get_verification_settings", lambda: verifier.IAMVerificationSettings(
        _env_file=None, IAM_AGENT_URL="https://iam.internal.test", IAM_VERIFIER_CA_BUNDLE="/nonexistent-ca.pem"))
    assert_denied(boundary, 503)
    assert boundary.calls == []


def test_duplicate_input_claims_are_not_sent_to_verifier(boundary):
    token = boundary.sign()
    header, _, signature = token.split(".")
    body = base64.urlsafe_b64encode(b'{"sub":"a","sub":"b"}').decode().rstrip("=")
    assert_denied(boundary, token=".".join((header, body, signature)))
    assert boundary.calls == []


def test_receipt_cannot_make_an_expired_submitted_token_current(boundary):
    # Simulate an available verifier incorrectly claiming a valid expired token.
    boundary.claims["exp"] = int(time.time()) - 1
    boundary.claims["iat"] -= 600
    boundary.response = httpx.Response(200, json=dict(
        valid=True, payload=boundary.claims, tenant_id=boundary.claims["tenant_id"],
        user_id=boundary.claims["sub"], roles=["SOC_ANALYST"],
        expires_at=datetime.fromtimestamp(boundary.claims["exp"], timezone.utc).isoformat()))
    assert_denied(boundary)


def test_existing_metrics_names_record_both_outcomes(boundary):
    from sg_core.service_metrics import get_service_metrics
    metrics = get_service_metrics()
    metrics.reset()
    verify_token(boundary.sign())
    assert_denied(boundary, token=boundary.sign(key=boundary.keys[1]))
    counters = metrics.snapshot()["counters"]
    assert counters["token_validation_success_total"]["total"] == 1
    assert counters["auth_failures_total"]["total"] == 1
    assert counters["token_validation_failures_total"]["total"] == 1


@pytest.mark.parametrize("failure, expected", [("unavailable", 503), ("conflicting", 503), ("shared-token", 401)])
def test_rejected_verification_never_reaches_scoped_handler(boundary, failure, expected):
    reached = Mock()
    app = FastAPI()

    @app.get("/protected")
    def protected(tenant: str = Depends(get_current_tenant)):
        reached(tenant)
        return {"tenant_id": tenant}

    token = boundary.sign()
    if failure == "unavailable":
        boundary.error = httpx.ReadTimeout("synthetic timeout")
    elif failure == "conflicting":
        boundary.change = change("tenant_id", str(uuid4()))
    else:
        token = "synthetic-shared-token"
    response = TestClient(app).get("/protected", headers={"Authorization": "Bearer " + token,
                                                        "X-Tenant-ID": str(uuid4())})
    assert response.status_code == expected
    reached.assert_not_called()


def test_verification_receipt_preserves_json_types(boundary):
    boundary.claims["custom_flag"] = True
    boundary.change = lambda r: r["payload"].update(custom_flag=1)
    assert_denied(boundary, 503)


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_non_finite_response_numbers_cannot_enter_identity(boundary, number):
    boundary.response = httpx.Response(200, content=('{"valid":true,"custom":' + number + '}').encode(),
                                      headers={"Content-Type": "application/json"})
    assert_denied(boundary, 503)
