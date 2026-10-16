"""
Pytest configuration for authentication tests.
"""

import pytest
import os
from unittest.mock import Mock, patch


@pytest.fixture(scope="session")
def test_config():
    """Test configuration."""
    return {
        "IAM_AGENT_URL": os.getenv("IAM_AGENT_URL", "http://localhost:8005"),
        "WEBSITE_URL": os.getenv("WEBSITE_URL", "http://localhost:3000"),
        "KEYCLOAK_URL": os.getenv("KEYCLOAK_URL", "http://localhost:8081"),
        "KEYCLOAK_REALM": os.getenv("KEYCLOAK_REALM", "sentinelgrid"),
        "TEST_USER_EMAIL": os.getenv("TEST_USER_EMAIL", "admin@sentinelgrid.ai"),
        "TEST_USER_PASSWORD": os.getenv("TEST_USER_PASSWORD", "admin123"),
    }


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks before each test."""
    yield
    # Cleanup if needed


@pytest.fixture
def mock_keycloak_admin():
    """Mock KeycloakAdmin instance."""
    with patch('backend.services.iam_agent.app.services.keycloak_client.KeycloakAdmin') as mock:
        admin_instance = Mock()
        mock.return_value = admin_instance
        yield admin_instance

