"""Tests for app catalog API endpoints."""

from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from app.api import app_catalog


class _FakeResult:
    def __init__(self, *, rows=None, row=None):
        self._rows = rows or []
        self._row = row

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._row

    def first(self):
        return self._row


class FakeDB:
    def __init__(self):
        self.executed = []
        self.commits = 0

    def execute(self, statement, params=None):
        sql = str(statement)
        self.executed.append((sql, params or {}))

        if "SELECT protocol FROM app_catalog" in sql:
            return _FakeResult(row=("saml",))
        if "SELECT slug FROM tenants" in sql:
            return _FakeResult(row=("demo-tenant",))
        if "SELECT setup_guide FROM app_catalog" in sql:
            return _FakeResult(row=None)
        if "FROM app_catalog" in sql:
            return _FakeResult(rows=[], row=None)

        return _FakeResult()

    def commit(self):
        self.commits += 1


@pytest.fixture
def fake_db():
    return FakeDB()


@pytest.fixture
def client(fake_db):
    """Create test client."""
    app = FastAPI()
    app.include_router(app_catalog.router)
    app.include_router(app_catalog.portal_router)

    def _get_tenant_session_override():
        yield fake_db

    app.dependency_overrides[app_catalog.get_tenant_session] = _get_tenant_session_override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(app_catalog.get_tenant_session, None)


@pytest.fixture
def mock_token_data():
    """Mock token data with tenant_id."""
    return {
        "valid": True,
        "tenant_id": "test-tenant-123",
        "user_id": "user-123",
        "roles": ["TENANT_ADMIN"],
        "realm_name": "demo",
    }


@patch('app.api.app_catalog.get_token_data')
def test_list_app_catalog(mock_get_token, client, mock_token_data, fake_db):
    """Test list app catalog endpoint."""
    mock_get_token.return_value = mock_token_data
    
    response = client.get(
        "/api/v1/apps/catalog",
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    # Should have prebuilt apps
    assert len(data["items"]) > 0
    assert any("FROM app_catalog" in sql for sql, _ in fake_db.executed)


@patch('app.api.app_catalog.get_token_data')
def test_list_app_catalog_with_category_filter(mock_get_token, client, mock_token_data, fake_db):
    """Test list app catalog with category filter."""
    mock_get_token.return_value = mock_token_data
    
    response = client.get(
        "/api/v1/apps/catalog?category=Productivity",
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    # All returned apps should be in Productivity category
    for app in data["items"]:
        assert app.get("category") == "Productivity"
    assert any("FROM app_catalog" in sql for sql, _ in fake_db.executed)


@patch('app.api.app_catalog.get_token_data')
@patch('app.api.app_catalog.KeycloakAdminClient')
def test_connect_app(mock_kc_class, mock_get_token, client, mock_token_data, fake_db):
    """Test connect app endpoint."""
    mock_get_token.return_value = mock_token_data
    
    mock_kc = AsyncMock()
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.headers = {"Location": "/realms/test/clients/client-123"}
    mock_kc._make_request = AsyncMock(return_value=mock_response)
    mock_kc.__aenter__ = AsyncMock(return_value=mock_kc)
    mock_kc.__aexit__ = AsyncMock(return_value=None)
    mock_kc_class.return_value = mock_kc
    
    response = client.post(
        "/api/v1/apps/catalog/microsoft_365/connect",
        json={
            "catalog_app_id": "microsoft_365",
            "config": {
                "redirect_uri": "https://login.microsoftonline.com/saml",
                "entity_id": "https://sts.windows.net/tenant-id/"
            }
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "app_id" in data
    assert any("SELECT slug FROM tenants" in sql for sql, _ in fake_db.executed)
    assert any("INSERT INTO apps" in sql for sql, _ in fake_db.executed)


@patch('app.api.app_catalog.get_token_data')
def test_get_app_catalog_item_defaults(mock_get_token, client, mock_token_data, fake_db):
    """Test catalog item retrieval (fallback defaults)."""
    mock_get_token.return_value = mock_token_data

    resp = client.get(
        "/api/v1/apps/catalog/gitlab",
        headers={"Authorization": "Bearer test-token"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "gitlab"
    assert any("FROM app_catalog" in sql for sql, _ in fake_db.executed)


@patch('app.api.app_catalog.get_token_data')
def test_get_setup_guide_defaults(mock_get_token, client, mock_token_data, fake_db):
    mock_get_token.return_value = mock_token_data

    resp = client.get(
        "/api/v1/apps/catalog/gitlab/setup-guide",
        headers={"Authorization": "Bearer test-token"}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["app_id"] == "gitlab"
    assert any("SELECT setup_guide FROM app_catalog" in sql for sql, _ in fake_db.executed)


@patch('app.api.app_catalog.get_token_data')
def test_list_app_catalog_portal_uses_tenant_scoped_session(mock_get_token, client, mock_token_data, fake_db):
    mock_get_token.return_value = mock_token_data

    resp = client.get(
        "/api/iam-portal/catalog/apps",
        headers={"Authorization": "Bearer test-token"}
    )

    assert resp.status_code == 200
    assert any("FROM app_catalog" in sql for sql, _ in fake_db.executed)


@patch('app.api.app_catalog.get_token_data')
@patch('app.api.app_catalog.KeycloakAdminClient')
def test_connect_app_portal_uses_tenant_scoped_session(mock_kc_class, mock_get_token, client, mock_token_data, fake_db):
    mock_get_token.return_value = mock_token_data

    mock_kc = AsyncMock()
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.headers = {"Location": "/realms/test/clients/client-456"}
    mock_kc._make_request = AsyncMock(return_value=mock_response)
    mock_kc.__aenter__ = AsyncMock(return_value=mock_kc)
    mock_kc.__aexit__ = AsyncMock(return_value=None)
    mock_kc_class.return_value = mock_kc

    resp = client.post(
        "/api/iam-portal/catalog/apps/microsoft_365/connect",
        json={
            "catalog_app_id": "microsoft_365",
            "config": {
                "redirect_uri": "https://login.microsoftonline.com/saml",
                "entity_id": "https://sts.windows.net/tenant-id/"
            }
        },
        headers={"Authorization": "Bearer test-token"}
    )

    assert resp.status_code == 200
    assert any("SELECT slug FROM tenants" in sql for sql, _ in fake_db.executed)
