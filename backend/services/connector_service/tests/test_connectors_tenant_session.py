"""Focused tenant-session coverage for connector CRUD and OAuth init routes."""

from importlib import import_module
from uuid import UUID, uuid4
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.api import connectors as connectors_api
from app.main import app
from app.models.connector import ConnectorConfig


@pytest.fixture
def tenant_scoped_client(test_db):
    """Force connector routes to use the tenant-scoped dependency."""
    tenant_id = str(uuid4())

    def override_get_current_tenant():
        return tenant_id

    def unexpected_get_db():
        raise AssertionError("Connector route used get_db instead of get_tenant_session")
        yield  # pragma: no cover

    def override_get_tenant_session():
        yield test_db

    app.dependency_overrides[connectors_api.get_current_tenant] = override_get_current_tenant
    app.dependency_overrides[connectors_api.get_db] = unexpected_get_db
    app.dependency_overrides[connectors_api.get_tenant_session] = override_get_tenant_session

    try:
        yield TestClient(app), test_db, tenant_id
    finally:
        app.dependency_overrides.clear()


def _create_connector(test_db, tenant_id: str, name: str = "Google Workspace") -> ConnectorConfig:
    connector = ConnectorConfig(
        tenant_id=UUID(tenant_id),
        type="google_workspace",
        name=name,
        credentials={"token": "test-token"},
        sync_settings={"mode": "full"},
        status="active",
    )
    test_db.add(connector)
    test_db.commit()
    test_db.refresh(connector)
    return connector


def test_connector_crud_routes_use_tenant_session(tenant_scoped_client):
    client, _test_db, tenant_id = tenant_scoped_client

    create_response = client.post(
        "/api/v1/connectors",
        json={
            "type": "google_workspace",
            "name": "Workspace",
            "credentials": {"token": "abc"},
            "sync_settings": {"mode": "delta"},
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    connector_id = created["id"]
    assert created["tenant_id"] == tenant_id

    list_response = client.get("/api/v1/connectors")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [connector_id]

    get_response = client.get(f"/api/v1/connectors/{connector_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Workspace"

    update_response = client.patch(
        f"/api/v1/connectors/{connector_id}",
        json={"name": "Updated Workspace", "status": "paused"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Workspace"
    assert update_response.json()["status"] == "paused"

    delete_response = client.delete(f"/api/v1/connectors/{connector_id}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/v1/connectors/{connector_id}")
    assert missing_response.status_code == 404


def test_connector_sync_routes_use_tenant_session(tenant_scoped_client):
    client, test_db, tenant_id = tenant_scoped_client
    connector = _create_connector(test_db, tenant_id)

    sync_response = client.post(f"/api/v1/connectors/{connector.id}/sync")
    assert sync_response.status_code == 200
    assert sync_response.json() == {
        "status": "stub",
        "connector_id": str(connector.id),
        "tenant_id": tenant_id,
    }

    sync_all_response = client.post("/api/v1/connectors/sync/all")
    assert sync_all_response.status_code == 200
    assert sync_all_response.json() == {
        "status": "stub",
        "tenant_id": tenant_id,
    }


def test_test_connector_route_uses_tenant_session(tenant_scoped_client):
    client, test_db, tenant_id = tenant_scoped_client
    connector = _create_connector(test_db, tenant_id)

    google_workspace_module = import_module("app.connectors.google_workspace")
    mock_connector = Mock()
    mock_connector.test_connection.return_value = True
    mock_connector.fetch_users.return_value = [{"id": "1"}]

    with patch.object(
        google_workspace_module,
        "GoogleWorkspaceConnector",
        return_value=mock_connector,
    ):
        response = client.post(f"/api/v1/connectors/{connector.id}/test")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["users_count"] == 1


@patch("app.services.oauth_service.OAuthService.init_google_workspace_oauth")
def test_oauth_init_uses_tenant_session_and_rejects_cross_tenant(
    mock_init_google_workspace_oauth,
    tenant_scoped_client,
):
    client, _test_db, tenant_id = tenant_scoped_client
    mock_init_google_workspace_oauth.return_value = {
        "oauth_url": "https://example.com/oauth",
        "state_token": "state-token",
    }

    success_response = client.post(
        "/api/v1/connectors/oauth/init",
        json={
            "provider": "google_workspace",
            "tenant_id": tenant_id,
            "redirect_uri": "http://localhost:3000/callback",
        },
    )
    assert success_response.status_code == 200
    assert success_response.json()["state_token"] == "state-token"

    mismatch_response = client.post(
        "/api/v1/connectors/oauth/init",
        json={
            "provider": "google_workspace",
            "tenant_id": str(uuid4()),
            "redirect_uri": "http://localhost:3000/callback",
        },
    )
    assert mismatch_response.status_code == 403
    assert mismatch_response.json()["detail"] == "Cross-tenant access denied"
    assert mock_init_google_workspace_oauth.call_count == 1
