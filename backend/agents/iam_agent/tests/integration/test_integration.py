"""Integration tests for IAM Agent."""

import pytest
import httpx
import time
import os

# These tests require the services to be running
IAM_AGENT_URL = os.getenv("IAM_AGENT_URL", "http://localhost:8005")
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8081")


@pytest.mark.integration
def test_health_endpoint():
    """Test health endpoint with real service."""
    response = httpx.get(f"{IAM_AGENT_URL}/health", timeout=5.0)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data


@pytest.mark.integration
def test_keycloak_connectivity():
    """Test that Keycloak is accessible."""
    try:
        response = httpx.get(f"{KEYCLOAK_URL}/health", timeout=5.0)
        # Keycloak may return 404 for /health, that's okay
        # Just check it's responding
        assert response.status_code in [200, 404]
    except httpx.ConnectError:
        pytest.skip("Keycloak not available for integration testing")


@pytest.mark.integration
def test_validate_token_with_invalid_token():
    """Test token validation with invalid token."""
    response = httpx.post(
        f"{IAM_AGENT_URL}/internal/iam/auth/validate-token",
        json={"token": "invalid-token-12345"},
        timeout=5.0
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "error" in data


@pytest.mark.integration
def test_introspect_with_invalid_token():
    """Test token introspection with invalid token."""
    response = httpx.post(
        f"{IAM_AGENT_URL}/internal/iam/auth/introspect",
        json={"token": "invalid-token-12345"},
        timeout=5.0
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active"] is False

