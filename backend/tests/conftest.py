"""
Pytest configuration and shared fixtures.
"""

import pytest
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# Add tests directory to path for shared utils
sys.path.insert(0, os.path.dirname(__file__))


@pytest.fixture(scope="session")
def api_base_url():
    """Base URL for API endpoints."""
    return os.getenv("API_URL", "https://localhost:3443/api/v1")


@pytest.fixture(scope="session")
def website_url():
    """Base URL for website."""
    # Default to frontend app (3443) where full dashboard lives
    return os.getenv("WEBSITE_URL", "https://localhost:3443")


@pytest.fixture(scope="session")
def test_credentials():
    """Test user credentials."""
    return {
        "email": os.getenv("TEST_EMAIL", "test@example.com"),
        "password": os.getenv("TEST_PASSWORD", "TestPassword123!"),
    }


@pytest.fixture(scope="function")
def authenticated_headers(api_base_url, test_credentials):
    """Get authenticated headers for API requests."""
    # TODO: Implement actual authentication
    # For now, return empty headers
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('TEST_TOKEN', '')}",
    }
