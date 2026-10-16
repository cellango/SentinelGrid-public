"""Tests for privileged access API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user_token():
    """Mock token data for regular user."""
    return {
        "valid": True,
        "tenant_id": "test-tenant-123",
        "user_id": "user-123",
        "email": "user@example.com",
        "roles": ["SOC_ANALYST"]
    }


@pytest.fixture
def mock_admin_token():
    """Mock token data for admin user."""
    return {
        "valid": True,
        "tenant_id": "test-tenant-123",
        "user_id": "admin-123",
        "email": "admin@example.com",
        "roles": ["TENANT_ADMIN"]
    }


@patch('app.api.privileged_access.get_token_data')
def test_request_privileged_access(mock_get_token, client, mock_user_token):
    """Test request privileged access endpoint."""
    mock_get_token.return_value = mock_user_token
    
    response = client.post(
        "/api/v1/privileged-access/request",
        json={
            "resource_type": "role",
            "resource_id": "ADMIN_ROLE",
            "resource_name": "Administrator Role",
            "reason": "Need to perform system maintenance tasks",
            "duration_hours": 2
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["resource_type"] == "role"
    assert data["duration_hours"] == 2


@patch('app.api.privileged_access.get_token_data')
def test_approve_privileged_access(mock_get_token, client, mock_admin_token):
    """Test approve privileged access endpoint."""
    mock_get_token.return_value = mock_admin_token
    
    response = client.post(
        "/api/v1/privileged-access/requests/req-123/approve",
        json={"comments": "Approved for maintenance"},
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@patch('app.api.privileged_access.get_token_data')
def test_approve_requires_admin_role(mock_get_token, client, mock_user_token):
    """Test that approval requires admin role."""
    mock_get_token.return_value = mock_user_token
    
    response = client.post(
        "/api/v1/privileged-access/requests/req-123/approve",
        json={"comments": "Approved"},
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 403
    assert "Approver role required" in response.json()["detail"]


@patch('app.api.privileged_access.get_token_data')
def test_reject_privileged_access(mock_get_token, client, mock_admin_token):
    """Test reject privileged access endpoint."""
    mock_get_token.return_value = mock_admin_token
    
    response = client.post(
        "/api/v1/privileged-access/requests/req-123/reject",
        json={"rejection_reason": "Insufficient justification"},
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

