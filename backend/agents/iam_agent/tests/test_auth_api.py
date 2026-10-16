"""Tests for authentication API endpoints."""

from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.api import auth as auth_api


def test_removed_direct_reset_never_accesses_keycloak(monkeypatch):
    """An anonymous HTTP request cannot change another account's credentials."""
    from fastapi import FastAPI

    admin_client = Mock(side_effect=AssertionError("Must not access Keycloak"))
    monkeypatch.setattr(auth_api, "KeycloakAdminClient", admin_client)
    app = FastAPI()
    app.include_router(auth_api.public_router)
    with TestClient(app) as client:
        for body in [
            {"email": "reviewer@example.com", "new_password": "synthetic-reset-canary"},
            {"email": "reviewer@example.com", "new_password": "synthetic-reset-canary",
             "realm": "another-realm", "tenant_slug": "another-tenant"},
            {},
        ]:
            response = client.post("/api/v1/auth/reset-password-direct", json=body)
            assert response.status_code == 410
            assert "removed" in response.json()["detail"]
    admin_client.assert_not_called()


def _install_token_validator(monkeypatch, responses_by_token):
    class _FakeTokenValidator:
        def __init__(self, _client):
            pass

        def validate_token(self, token):
            return responses_by_token[token]

    monkeypatch.setattr(auth_api, "TokenValidator", _FakeTokenValidator)
    monkeypatch.setattr(auth_api, "KeycloakClient", lambda: object())


class _FakeHTTPResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self):
        return self._json_data


class _FakeAsyncClient:
    def __init__(self, response):
        self._response = response
        self.post_calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        self.post_calls.append({"args": args, "kwargs": kwargs})
        return self._response


def test_root_endpoint(iam_test_client):
    """Test root endpoint."""
    response = iam_test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "iam-agent"
    assert "version" in data


def test_validate_token_endpoint_no_token(iam_test_client):
    """Test validate token endpoint with no token."""
    response = iam_test_client.post(
        "/internal/iam/auth/validate-token",
        json={}
    )
    assert response.status_code == 422


def test_validate_token_endpoint_invalid_token(iam_test_app, iam_test_client):
    """Test validate token endpoint with invalid token."""
    mock_validator = Mock()
    mock_validator.validate_token.return_value = {
        "valid": False,
        "error": "Invalid token",
        "payload": None,
        "tenant_id": None,
        "user_id": None,
        "username": None,
        "email": None,
        "roles": [],
        "expires_at": None,
    }
    iam_test_app.dependency_overrides[auth_api.get_token_validator] = lambda: mock_validator

    try:
        response = iam_test_client.post(
            "/internal/iam/auth/validate-token",
            json={"token": "invalid-token"}
        )
    finally:
        iam_test_app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["error"] == "Invalid token"


def test_validate_token_endpoint_valid_token(iam_test_app, iam_test_client):
    """Test validate token endpoint with valid token."""
    from datetime import datetime, timedelta

    mock_validator = Mock()
    mock_validator.validate_token.return_value = {
        "valid": True,
        "payload": {"sub": "user-123"},
        "tenant_id": "tenant-456",
        "user_id": "user-123",
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["SOC_ANALYST"],
        "expires_at": datetime.now() + timedelta(hours=1),
        "error": None,
    }
    iam_test_app.dependency_overrides[auth_api.get_token_validator] = lambda: mock_validator

    try:
        response = iam_test_client.post(
            "/internal/iam/auth/validate-token",
            json={"token": "valid-token"}
        )
    finally:
        iam_test_app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["tenant_id"] == "tenant-456"
    assert data["user_id"] == "user-123"
    assert "SOC_ANALYST" in data["roles"]


def test_introspect_endpoint(iam_test_app, iam_test_client):
    """Test token introspection endpoint."""
    mock_validator = Mock()
    mock_validator.introspect_token.return_value = {
        "active": True,
        "sub": "user-123",
        "tenant_id": "tenant-456",
        "username": "testuser",
        "email": "test@example.com",
        "realm_access": {"roles": ["SOC_ANALYST"]},
        "roles": ["SOC_ANALYST"],
        "exp": 1234567890,
        "iat": 1234567890,
        "error": None,
    }
    iam_test_app.dependency_overrides[auth_api.get_token_validator] = lambda: mock_validator

    try:
        response = iam_test_client.post(
            "/internal/iam/auth/introspect",
            json={"token": "test-token"}
        )
    finally:
        iam_test_app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["active"] is True
    assert data["sub"] == "user-123"
    assert data["tenant_id"] == "tenant-456"


def test_auth_health_endpoint(iam_test_app, iam_test_client):
    """Test auth health endpoint."""
    mock_client = Mock()
    mock_client.get_public_key.return_value = "http://keycloak/realms/test/certs"
    mock_client.server_url = "http://keycloak:8080"
    mock_client.realm = "test"
    iam_test_app.dependency_overrides[auth_api.get_keycloak_client] = lambda: mock_client

    try:
        response = iam_test_client.get("/internal/iam/auth/health")
    finally:
        iam_test_app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "keycloak_connected" in data


def test_public_me_accepts_bearer_token(iam_test_app, monkeypatch):
    iam_test_app.include_router(auth_api.public_router)
    client = TestClient(iam_test_app)
    _install_token_validator(
        monkeypatch,
        {
            "bearer-token": {
                "valid": True,
                "payload": {
                    "iss": "http://keycloak/realms/sentinelgrid",
                    "tenant_id": "forged-tenant",
                },
                "tenant_id": "tenant-456",
                "plan_tier": "protect",
                "user_id": "user-123",
                "email": "analyst@example.com",
                "roles": ["SOC_ANALYST"],
            }
        },
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer bearer-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "user-123",
        "email": "analyst@example.com",
        "tenant_id": "tenant-456",
        "roles": ["SOC_ANALYST"],
        "plan_tier": "protect",
        "realm": "sentinelgrid",
    }


def test_public_me_rejects_invalid_bearer_token(iam_test_app, monkeypatch):
    iam_test_app.include_router(auth_api.public_router)
    client = TestClient(iam_test_app)
    _install_token_validator(
        monkeypatch,
        {
            "forged-token": {
                "valid": False,
                "payload": None,
                "error": "signature verification failed",
            }
        },
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer forged-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_public_me_accepts_access_token_cookie(iam_test_app, monkeypatch):
    iam_test_app.include_router(auth_api.public_router)
    client = TestClient(iam_test_app)
    _install_token_validator(
        monkeypatch,
        {
            "cookie-token": {
                "valid": True,
                "payload": {"iss": "http://keycloak/realms/customer-a"},
                "tenant_id": "tenant-999",
                "plan_tier": None,
                "user_id": "user-789",
                "email": "lead@example.com",
                "roles": ["TENANT_ADMIN"],
            }
        },
    )

    response = client.get(
        "/api/v1/auth/me",
        cookies={"access_token": "cookie-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "user-789",
        "email": "lead@example.com",
        "tenant_id": "tenant-999",
        "roles": ["TENANT_ADMIN"],
        "plan_tier": None,
        "realm": "customer-a",
    }


def test_logout_uses_validated_refresh_token_claims(iam_test_app, monkeypatch):
    iam_test_app.include_router(auth_api.public_router)
    client = TestClient(iam_test_app)
    fake_http_client = _FakeAsyncClient(_FakeHTTPResponse())
    _install_token_validator(
        monkeypatch,
        {
            "refresh-token": {
                "valid": True,
                "payload": {"iss": "http://keycloak/realms/customer-a"},
                "tenant_id": "tenant-999",
                "plan_tier": "defend",
                "user_id": "user-789",
                "email": "lead@example.com",
                "roles": ["TENANT_ADMIN"],
            }
        },
    )
    monkeypatch.setattr(auth_api.httpx, "AsyncClient", lambda *args, **kwargs: fake_http_client)
    monkeypatch.setattr(auth_api.SecurityService, "extract_client_info", lambda _request: {})
    monkeypatch.setattr(auth_api.AuditService, "log_auth_event", lambda **kwargs: None)

    response = client.post(
        "/api/v1/auth/logout",
        params={"refresh_token": "refresh-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "Logged out successfully"}
    assert fake_http_client.post_calls == [
        {
            "args": (
                f"{auth_api.settings.KEYCLOAK_URL}/realms/customer-a/protocol/openid-connect/logout",
            ),
            "kwargs": {
                "data": {
                    "client_id": "sentinelgrid-web",
                    "refresh_token": "refresh-token",
                },
                "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            },
        }
    ]


def test_refresh_validates_refresh_and_returned_access_token(iam_test_app, monkeypatch):
    iam_test_app.include_router(auth_api.public_router)
    client = TestClient(iam_test_app)
    _install_token_validator(
        monkeypatch,
        {
            "refresh-token": {
                "valid": True,
                "payload": {"iss": "http://keycloak/realms/customer-a"},
                "tenant_id": "tenant-999",
                "plan_tier": "defend",
                "user_id": "user-789",
                "email": "lead@example.com",
                "roles": ["TENANT_ADMIN"],
            },
            "new-access-token": {
                "valid": True,
                "payload": {"iss": "http://keycloak/realms/customer-a"},
                "tenant_id": "tenant-999",
                "plan_tier": "defend",
                "user_id": "user-789",
                "email": "lead@example.com",
                "roles": ["TENANT_ADMIN"],
            },
        },
    )
    monkeypatch.setattr(
        auth_api.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeAsyncClient(
            _FakeHTTPResponse(
                json_data={
                    "access_token": "new-access-token",
                    "refresh_token": "rotated-refresh-token",
                    "expires_in": 7200,
                }
            )
        ),
    )
    monkeypatch.setattr(auth_api.SecurityService, "extract_client_info", lambda _request: {})
    monkeypatch.setattr(auth_api.AuditService, "log_auth_event", lambda **kwargs: None)

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "refresh-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "new-access-token",
        "refresh_token": "rotated-refresh-token",
        "expires_in": 7200,
        "token_type": "Bearer",
        "user": {
            "id": "user-789",
            "email": "lead@example.com",
            "tenant_id": "tenant-999",
            "roles": ["TENANT_ADMIN"],
        },
        "signup_completed": True,
        "password_reset_required": False,
    }


def test_refresh_rejects_invalid_access_token_returned_by_idp(iam_test_app, monkeypatch):
    iam_test_app.include_router(auth_api.public_router)
    client = TestClient(iam_test_app)
    _install_token_validator(
        monkeypatch,
        {
            "refresh-token": {
                "valid": True,
                "payload": {"iss": "http://keycloak/realms/customer-a"},
                "tenant_id": "tenant-999",
                "plan_tier": "defend",
                "user_id": "user-789",
                "email": "lead@example.com",
                "roles": ["TENANT_ADMIN"],
            },
            "bad-access-token": {
                "valid": False,
                "payload": None,
                "error": "signature verification failed",
            },
        },
    )
    monkeypatch.setattr(
        auth_api.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _FakeAsyncClient(
            _FakeHTTPResponse(
                json_data={
                    "access_token": "bad-access-token",
                    "refresh_token": "rotated-refresh-token",
                    "expires_in": 7200,
                }
            )
        ),
    )
    monkeypatch.setattr(auth_api.SecurityService, "extract_client_info", lambda _request: {})
    monkeypatch.setattr(auth_api.AuditService, "log_auth_event", lambda **kwargs: None)

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "refresh-token"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Invalid token returned by identity provider"}


def test_introspect_endpoint_returns_inactive_payload_for_invalid_token(iam_test_app, iam_test_client):
    mock_validator = Mock()
    mock_validator.introspect_token.return_value = {
        "active": False,
        "tenant_id": None,
        "roles": [],
        "error": "Invalid token",
    }
    iam_test_app.dependency_overrides[auth_api.get_token_validator] = lambda: mock_validator

    try:
        response = iam_test_client.post(
            "/internal/iam/auth/introspect",
            json={"token": "invalid-token"},
        )
    finally:
        iam_test_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["active"] is False
