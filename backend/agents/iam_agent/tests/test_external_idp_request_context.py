from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import external_idp
from app.api.request_context import RequestContext, get_current_request_context


def _request_context(*roles: str) -> RequestContext:
    return RequestContext(
        tenant_id="00000000-0000-0000-0000-000000000001",
        user_id="user-123",
        roles=tuple(roles),
    )


class _FakeResponse:
    def __init__(self, *, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self._json_data


class _FakeAsyncClient:
    def __init__(self, responses):
        self._responses = list(responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, _url):
        if not self._responses:
            raise AssertionError("No fake response configured")
        return self._responses.pop(0)

    async def post(self, _url, data=None, headers=None):
        if not self._responses:
            raise AssertionError("No fake response configured")
        return self._responses.pop(0)


def test_oidc_discovery_requires_authenticated_context():
    app = FastAPI()
    app.include_router(external_idp.router)
    client = TestClient(app)

    response = client.post(
        "/api/v1/idp/test/oidc",
        json={"discovery_url": "https://idp.example/.well-known/openid-configuration"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing or invalid authorization header"}


def test_oidc_discovery_rejects_non_admin():
    app = FastAPI()
    app.include_router(external_idp.router)
    app.dependency_overrides[get_current_request_context] = lambda: _request_context("VIEW_ONLY")
    client = TestClient(app)

    response = client.post(
        "/api/v1/idp/test/oidc",
        headers={"authorization": "Bearer test-token"},
        json={"discovery_url": "https://idp.example/.well-known/openid-configuration"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Missing required role"}


def test_oidc_discovery_allows_tenant_admin(monkeypatch):
    app = FastAPI()
    app.include_router(external_idp.router)
    app.dependency_overrides[get_current_request_context] = lambda: _request_context("TENANT_ADMIN")
    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                json_data={
                    "issuer": "https://idp.example",
                    "authorization_endpoint": "https://idp.example/auth",
                    "token_endpoint": "https://idp.example/token",
                }
            ),
            _FakeResponse(status_code=200, json_data={"access_token": "token"}),
        ]
    )
    monkeypatch.setattr(external_idp.httpx, "AsyncClient", lambda *args, **kwargs: fake_client)
    client = TestClient(app)

    response = client.post(
        "/api/v1/idp/test/oidc",
        headers={"authorization": "Bearer test-token"},
        json={
            "discovery_url": "https://idp.example/.well-known/openid-configuration",
            "client_id": "client-id",
            "client_secret": "client-secret",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "discovery_ok": True,
        "token_ok": True,
        "issuer": "https://idp.example",
        "auth_endpoint": "https://idp.example/auth",
        "token_endpoint": "https://idp.example/token",
        "error": None,
    }


def test_saml_metadata_allows_platform_admin(monkeypatch):
    app = FastAPI()
    app.include_router(external_idp.router)
    app.dependency_overrides[get_current_request_context] = lambda: _request_context("PLATFORM_ADMIN")
    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                text='<EntityDescriptor entityID="https://idp.example/entity"></EntityDescriptor>'
            )
        ]
    )
    monkeypatch.setattr(external_idp.httpx, "AsyncClient", lambda *args, **kwargs: fake_client)
    client = TestClient(app)

    response = client.post(
        "/api/v1/idp/test/saml",
        headers={"authorization": "Bearer test-token"},
        json={"metadata_url": "https://idp.example/metadata"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "metadata_ok": True,
        "entity_id": "https://idp.example/entity",
        "error": None,
    }
