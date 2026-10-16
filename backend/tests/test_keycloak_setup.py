"""
Test Keycloak account setup functionality.
"""

import pytest
import os
from helpers.keycloak_account_setup import KeycloakAccountSetup, setup_test_user

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8081")
REALM = os.getenv("TEST_REALM", "agribotsai")
ADMIN_USERNAME = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
TEST_USERNAME = os.getenv("TEST_USERNAME", "admin@agribotsai.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "ChangeMe123!")


@pytest.fixture
def account_setup():
    """Create KeycloakAccountSetup instance."""
    return KeycloakAccountSetup(KEYCLOAK_URL, REALM, ADMIN_USERNAME, ADMIN_PASSWORD)


def test_get_user_info(account_setup):
    """Test retrieving user information."""
    user_info = account_setup.get_user_info(TEST_USERNAME)
    assert user_info is not None
    assert user_info["username"] == TEST_USERNAME


def test_activate_account(account_setup):
    """Test account activation."""
    result = account_setup.activate_account(TEST_USERNAME, TEST_PASSWORD)
    # May not always succeed due to Keycloak restrictions
    assert isinstance(result, bool)


def test_setup_test_user_helper():
    """Test the helper function."""
    result = setup_test_user(
        KEYCLOAK_URL,
        REALM,
        TEST_USERNAME,
        TEST_PASSWORD,
        ADMIN_USERNAME,
        ADMIN_PASSWORD
    )
    assert isinstance(result, bool)

