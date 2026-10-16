import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import gateway, state


class _FakeResponse:
    def __init__(self, *, status_code=200, json_data=None, text="", headers=None, is_redirect=False):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.headers = headers or {}
        self.is_redirect = is_redirect

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self._json_data


class _FakeAsyncClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.post_calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, data=None, headers=None):
        self.post_calls.append({"url": url, "data": data, "headers": headers})
        if not self._responses:
            raise AssertionError("No fake response configured")
        return self._responses.pop(0)


@pytest.fixture(autouse=True)
def clear_gateway_state_cache():
    gateway._state_cache.clear()
    yield
    gateway._state_cache.clear()


@pytest.fixture
def auth_gateway_app():
    app = FastAPI()
    app.include_router(state.router)
    app.include_router(gateway.router)
    return app


@pytest.fixture
def auth_gateway_client(auth_gateway_app):
    return TestClient(auth_gateway_app)


def _configure_successful_oidc(monkeypatch, fake_client, ensure_calls, token_responses=None):
    if token_responses is None:
        token_responses = {
            "access-token": {
                "valid": True,
                "email": "admin@example.com",
                "payload": {
                    "iss": f"{gateway.settings.KEYCLOAK_URL.rstrip('/')}/realms/{gateway.settings.KEYCLOAK_REALM}",
                    "aud": gateway.settings.KEYCLOAK_CLIENT_ID,
                    "exp": 4102444800,
                    "email": "admin@example.com",
                },
            },
            "id-token": {
                "valid": True,
                "payload": {"nonce": "nonce-123"},
            },
        }

    class _FakeTokenValidator:
        def __init__(self, _client):
            pass

        def validate_token(self, token):
            return token_responses[token]

    async def _fake_fetch_idp_config(_alias: str):
        return {"allowedDomains": "example.com", "defaultRole": "viewer"}

    async def _fake_ensure_user_in_keycloak(email, tenant_id, default_role):
        ensure_calls.append(
            {
                "email": email,
                "tenant_id": tenant_id,
                "default_role": default_role,
            }
        )

    monkeypatch.setattr(gateway.httpx, "AsyncClient", lambda *args, **kwargs: fake_client)
    monkeypatch.setattr(gateway, "TokenValidator", _FakeTokenValidator)
    monkeypatch.setattr(gateway, "KeycloakClient", lambda: object())
    monkeypatch.setattr(gateway, "_fetch_idp_config", _fake_fetch_idp_config)
    monkeypatch.setattr(gateway, "_ensure_user_in_keycloak", _fake_ensure_user_in_keycloak)


def test_oidc_state_route_mints_server_side_binding(auth_gateway_client):
    response = auth_gateway_client.get(
        "/auth/oidc/state",
        params={
            "tenant_id": "tenant-a",
            "idp": "demo-idp",
            "redirect_to": "https://app.example/post-login",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"]
    assert body["nonce"]

    stored = gateway._consume_state(body["state"])
    assert stored["tenant_id"] == "tenant-a"
    assert stored["idp"] == "demo-idp"
    assert stored["redirect_to"] == "https://app.example/post-login"
    assert stored["nonce"] == body["nonce"]


def test_oidc_callback_rejects_query_tenant_mismatch(auth_gateway_client):
    state_value = gateway._store_state(
        {
            "tenant_id": "tenant-a",
            "idp": "demo-idp",
            "redirect_to": "https://app.example/post-login",
            "nonce": "nonce-123",
        }
    )["state"]

    response = auth_gateway_client.get(
        "/auth/oidc/callback",
        params={
            "code": "code-1",
            "state": state_value,
            "tenant_id": "tenant-b",
            "idp": "demo-idp",
            "redirect_to": "https://app.example/post-login",
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "State mismatch"}


def test_oidc_callback_uses_state_bound_tenant_for_token_exchange(auth_gateway_client, monkeypatch):
    state_value = gateway._store_state(
        {
            "tenant_id": "tenant-a",
            "idp": "demo-idp",
            "redirect_to": "https://app.example/post-login",
            "nonce": "nonce-123",
        }
    )["state"]
    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                json_data={
                    "access_token": "access-token",
                    "id_token": "id-token",
                    "refresh_token": "refresh-token",
                }
            )
        ]
    )
    ensure_calls = []
    _configure_successful_oidc(monkeypatch, fake_client, ensure_calls)

    response = auth_gateway_client.get(
        "/auth/oidc/callback",
        params={"code": "code-1", "state": state_value},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "https://app.example/post-login"
    assert ensure_calls == [
        {
            "email": "admin@example.com",
            "tenant_id": "tenant-a",
            "default_role": "viewer",
        }
    ]
    assert fake_client.post_calls[0]["data"]["redirect_uri"].endswith(
        "/auth/oidc/callback?tenant_id=tenant-a"
    )


def test_oidc_callback_rejects_invalid_id_token_nonce(auth_gateway_client, monkeypatch):
    state_value = gateway._store_state(
        {
            "tenant_id": "tenant-a",
            "idp": "demo-idp",
            "redirect_to": "https://app.example/post-login",
            "nonce": "nonce-123",
        }
    )["state"]
    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                json_data={
                    "access_token": "access-token",
                    "id_token": "id-token",
                    "refresh_token": "refresh-token",
                }
            )
        ]
    )
    ensure_calls = []
    _configure_successful_oidc(
        monkeypatch,
        fake_client,
        ensure_calls,
        token_responses={
            "access-token": {
                "valid": True,
                "email": "admin@example.com",
                "payload": {
                    "iss": f"{gateway.settings.KEYCLOAK_URL.rstrip('/')}/realms/{gateway.settings.KEYCLOAK_REALM}",
                    "aud": gateway.settings.KEYCLOAK_CLIENT_ID,
                    "exp": 4102444800,
                    "email": "admin@example.com",
                },
            },
            "id-token": {
                "valid": True,
                "payload": {"nonce": "wrong-nonce"},
            },
        },
    )

    response = auth_gateway_client.get(
        "/auth/oidc/callback",
        params={"code": "code-1", "state": state_value},
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid nonce"}
    assert ensure_calls == []


def test_oidc_callback_rejects_invalid_token_audience(auth_gateway_client, monkeypatch):
    state_value = gateway._store_state(
        {
            "tenant_id": "tenant-a",
            "idp": "demo-idp",
            "redirect_to": "https://app.example/post-login",
            "nonce": "nonce-123",
        }
    )["state"]
    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                json_data={
                    "access_token": "access-token",
                    "id_token": "id-token",
                    "refresh_token": "refresh-token",
                }
            )
        ]
    )
    ensure_calls = []
    _configure_successful_oidc(
        monkeypatch,
        fake_client,
        ensure_calls,
        token_responses={
            "access-token": {
                "valid": True,
                "email": "admin@example.com",
                "payload": {
                    "iss": f"{gateway.settings.KEYCLOAK_URL.rstrip('/')}/realms/{gateway.settings.KEYCLOAK_REALM}",
                    "aud": "unexpected-client",
                    "exp": 4102444800,
                    "email": "admin@example.com",
                },
            },
            "id-token": {
                "valid": True,
                "payload": {"nonce": "nonce-123"},
            },
        },
    )

    response = auth_gateway_client.get(
        "/auth/oidc/callback",
        params={"code": "code-1", "state": state_value},
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token audience"}
    assert ensure_calls == []


def test_saml_acs_rejects_query_tenant_mismatch_against_preissued_relay_state(auth_gateway_client):
    relay_state = gateway._store_state(
        {
            "tenant_id": "tenant-a",
            "idp": "demo-idp",
            "redirect_to": "https://app.example/post-login",
            "nonce": "",
        }
    )["state"]

    response = auth_gateway_client.post(
        "/auth/saml/acs",
        params={"tenant_id": "tenant-b", "idp": "demo-idp"},
        data={"SAMLResponse": "assertion", "RelayState": relay_state},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "State mismatch"}


def test_saml_acs_seeds_callback_binding_for_legacy_relay_state(auth_gateway_client, monkeypatch):
    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                status_code=302,
                is_redirect=True,
                headers={"Location": "https://auth.example/callback?code=code-1"},
            ),
            _FakeResponse(
                json_data={
                    "access_token": "access-token",
                    "id_token": "id-token",
                    "refresh_token": "refresh-token",
                }
            ),
        ]
    )
    ensure_calls = []
    _configure_successful_oidc(monkeypatch, fake_client, ensure_calls)

    response = auth_gateway_client.post(
        "/auth/saml/acs",
        params={
            "tenant_id": "tenant-a",
            "idp": "demo-idp",
            "redirect_to": "https://app.example/post-login",
        },
        data={"SAMLResponse": "assertion", "RelayState": "relay-1"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"] == "https://app.example/post-login"
    assert ensure_calls == [
        {
            "email": "admin@example.com",
            "tenant_id": "tenant-a",
            "default_role": "viewer",
        }
    ]
    assert fake_client.post_calls[0]["url"].endswith("/broker/demo-idp/endpoint")
    assert fake_client.post_calls[1]["data"]["redirect_uri"].endswith(
        "/auth/oidc/callback?tenant_id=tenant-a"
    )
