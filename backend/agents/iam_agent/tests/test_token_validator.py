"""Offline token-boundary tests with real RSA signatures and mocked key transport."""

import json
import time
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import rsa
import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
import pytest

from app.services import token_validator as module


@pytest.fixture(scope="module")
def keys():
    return [rsa.generate_private_key(public_exponent=65537, key_size=2048) for _ in range(2)]


@pytest.fixture
def setup(monkeypatch, keys):
    config = SimpleNamespace(KEYCLOAK_REALM="tenant-a", KEYCLOAK_URL="https://keycloak.internal.test",
                             KEYCLOAK_CLIENT_ID="review-client", KEYCLOAK_ISSUER_BASE_URLS=[],
                             JWKS_CACHE_TTL=60, TOKEN_VALIDATION_TIMEOUT=3, KEYCLOAK_VERIFY_TLS=True)
    monkeypatch.setattr(module, "settings", config)
    client = SimpleNamespace(introspect_token=Mock(return_value=None))
    validator = module.TokenValidator(client)
    jwk = json.loads(RSAAlgorithm.to_jwk(keys[0].public_key()))
    jwk.update(kid="key-1", alg="RS256", use="sig")
    claims = dict(sub=str(uuid4()), tenant_id=str(uuid4()),
                  iss=config.KEYCLOAK_URL + "/realms/tenant-a", aud=config.KEYCLOAK_CLIENT_ID,
                  exp=int(time.time()) + 600, iat=int(time.time()) - 1,
                  preferred_username="review-user", email="user@example.test",
                  realm_access={"roles": ["SOC_ANALYST"]})
    fetch = Mock(return_value={"keys": [jwk]})
    monkeypatch.setattr(validator, "_get_jwks_for_realm", fetch)

    def sign(payload=None, key=None, headers=None):
        return jwt.encode(claims if payload is None else payload, key or keys[0], algorithm="RS256",
                          headers={"kid": "key-1", **(headers or {})})
    return SimpleNamespace(validator=validator, client=client, config=config, claims=claims,
                           jwk=jwk, fetch=fetch, sign=sign, keys=keys)


def assert_invalid(result):
    assert result["valid"] is False
    assert result["payload"] is None and result["tenant_id"] is None
    assert result["user_id"] is None and result["roles"] == []


def test_valid_signed_token_preserves_claims_without_email_or_realm_remapping(setup):
    setup.claims["email"] = "synthetic@demo.sentinelgrid.ai"
    result = setup.validator.validate_token(setup.sign())
    assert result["valid"] is True
    assert result["tenant_id"] == setup.claims["tenant_id"]
    assert result["user_id"] == setup.claims["sub"]
    assert result["roles"] == ["SOC_ANALYST"]
    assert result["expires_at"].tzinfo is not None


@pytest.mark.parametrize("claim", ["exp", "iat", "iss", "aud", "sub", "tenant_id"])
def test_missing_required_claim_is_rejected(setup, claim):
    del setup.claims[claim]
    assert_invalid(setup.validator.validate_token(setup.sign()))


@pytest.mark.parametrize("update", [
    {"exp": 1}, {"exp": int(time.time())}, {"iat": int(time.time()) + 3600},
    {"nbf": int(time.time()) + 3600}, {"aud": "another-client"}, {"aud": ["account"]},
    {"tenant_id": "demo"}, {"tenant_id": None}, {"tenant_id": 1}, {"tenant_id": []},
    {"sub": ""}, {"sub": 1}, {"realm_access": {"roles": "PLATFORM_ADMIN"}},
    {"exp": "9999999999"}, {"iat": True}, {"nbf": "1"},
])
def test_invalid_identity_time_and_audience_claims_are_rejected(setup, update):
    setup.claims.update(update)
    assert_invalid(setup.validator.validate_token(setup.sign()))


@pytest.mark.parametrize("issuer", [
    "https://attacker.example.test/realms/tenant-a", "https://keycloak.internal.test.evil.test/realms/tenant-a",
    "https://keycloak.internal.test/realms/tenant-a/extra", "https://keycloak.internal.test/realms/../tenant-a",
    "https://keycloak.internal.test/realms/%2e%2e", "https://keycloak.internal.test/realms/tenant-a?x=y",
    "https://keycloak.internal.test/realms/tenant-a#suffix", "https://user@keycloak.internal.test/realms/tenant-a",
    "https://keycloak.internal.test/realms/", "https://keycloak.internal.test/realms/tenant-a/",
])
def test_untrusted_issuer_and_realm_never_fetch_keys(setup, issuer):
    setup.claims["iss"] = issuer
    assert_invalid(setup.validator.validate_token(setup.sign()))
    setup.fetch.assert_not_called()


def test_explicit_public_issuer_is_verified_without_becoming_a_key_destination(setup):
    setup.config.KEYCLOAK_ISSUER_BASE_URLS = ["https://identity.example.test"]
    setup.claims["iss"] = "https://identity.example.test/realms/tenant-a"
    assert setup.validator.validate_token(setup.sign())["valid"] is True
    setup.fetch.assert_called_once_with("tenant-a", setup.claims["iss"])


def test_forged_signature_is_rejected(setup):
    assert_invalid(setup.validator.validate_token(setup.sign(key=setup.keys[1])))


@pytest.mark.parametrize("algorithm", ["HS256", "none"])
def test_untrusted_algorithm_is_rejected_even_with_valid_claims(setup, algorithm):
    key = "synthetic-hmac-key-only-for-negative-tests" if algorithm == "HS256" else None
    token = jwt.encode(setup.claims, key, algorithm=algorithm, headers={"kid": "key-1"})
    assert_invalid(setup.validator.validate_token(token))


@pytest.mark.parametrize("headers", [{"kid": "unknown"}, {"kid": ""}, {"jku": "https://attacker.example.test/jwks"},
                                     {"x5u": "https://attacker.example.test/cert"}, {"jwk": {}}, {"crit": ["custom"]}])
def test_key_and_header_constraints_are_enforced(setup, headers):
    assert_invalid(setup.validator.validate_token(setup.sign(headers=headers)))


@pytest.mark.parametrize("key_change", [{"use": "enc"}, {"alg": "HS256"}, {"kty": "oct"}, {"key_ops": ["sign"]}, {"key_ops": "verify"}])
def test_incompatible_jwk_is_rejected(setup, key_change):
    setup.jwk.update(key_change)
    assert_invalid(setup.validator.validate_token(setup.sign()))


def test_ambiguous_key_id_and_unavailable_jwks_fail_closed(setup):
    setup.fetch.return_value = {"keys": [setup.jwk, setup.jwk]}
    assert_invalid(setup.validator.validate_token(setup.sign()))
    setup.fetch.return_value = None
    assert_invalid(setup.validator.validate_token(setup.sign()))


@pytest.mark.parametrize("token", ["", "not-a-token", "a.b.c", "a.b.c.d", "x" * 32769])
def test_malformed_tokens_fail_without_authenticated_payload(setup, token):
    assert_invalid(setup.validator.validate_token(token))


def test_introspection_cannot_authenticate_a_forged_token_or_remap_identity(setup):
    setup.client.introspect_token.return_value = {"active": True, "tenant_id": str(uuid4()), "sub": "someone-else"}
    assert setup.validator.introspect_token(setup.sign(key=setup.keys[1]))["active"] is False
    setup.client.introspect_token.assert_not_called()
    result = setup.validator.introspect_token(setup.sign())
    assert result["active"] is True and result["tenant_id"] == setup.claims["tenant_id"]
    assert result["sub"] == setup.claims["sub"]


def test_explicit_inactive_introspection_is_not_replaced_by_local_acceptance(setup):
    setup.client.introspect_token.return_value = {"active": False}
    result = setup.validator.introspect_token(setup.sign())
    assert result["active"] is False and result["tenant_id"] is None


def test_unavailable_introspection_preserves_signed_token_fallback(setup):
    setup.client.introspect_token.side_effect = httpx.ConnectError("synthetic outage")
    assert setup.validator.introspect_token(setup.sign())["active"] is True


def test_key_transport_uses_configured_origin_tls_no_redirects_and_cache(setup, monkeypatch):
    # Exercise real transport selection, replacing only HTTP with a local mock.
    validator = module.TokenValidator(setup.client)
    response = Mock()
    response.json.return_value = {"keys": [setup.jwk]}
    transport = Mock()
    transport.__enter__ = Mock(return_value=transport)
    transport.__exit__ = Mock(return_value=False)
    transport.get.return_value = response
    factory = Mock(return_value=transport)
    monkeypatch.setattr(module.httpx, "Client", factory)
    first = validator._get_jwks_for_realm("tenant-a", "https://attacker.example.test")
    assert first == validator._get_jwks_for_realm("tenant-a")
    assert transport.get.call_count == 1
    transport.get.assert_called_with("https://keycloak.internal.test/realms/tenant-a/protocol/openid-connect/certs")
    factory.assert_called_with(timeout=3, verify=True, follow_redirects=False)
    validator.jwks_cache["tenant-a"]["timestamp"] -= 61
    assert validator._get_jwks_for_realm("tenant-a") == first
    assert transport.get.call_count == 2


def test_key_transport_failure_and_malformed_keys_are_not_cached(setup, monkeypatch):
    validator = module.TokenValidator(setup.client)
    def unavailable(*args, **kwargs):
        raise httpx.ConnectError("synthetic key-service outage")
    monkeypatch.setattr(module.httpx, "Client", unavailable)
    assert validator._get_jwks_for_realm("tenant-a") is None
    assert not validator.jwks_cache
    assert validator._get_jwks_for_realm("../other") is None
