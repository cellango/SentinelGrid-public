"""Legacy identity/provider/session overrides cannot establish owned route acceptance."""

import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from app.main import app
from app.core import database


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/v1/wazuh/agents/register"),
        ("GET", "/api/v1/wazuh/agents"),
        ("GET", "/api/v1/wazuh/agents/001"),
        ("DELETE", "/api/v1/wazuh/agents/001"),
        ("POST", "/api/v1/wazuh/agents/001/restart"),
    ],
)
def test_raw_header_cannot_open_storage_or_provider(monkeypatch, method, path):
    forbidden = Mock(side_effect=AssertionError("No SQL"))
    monkeypatch.setattr(database, "SessionLocal", forbidden)
    with TestClient(app) as client:
        response = client.request(
            method,
            path,
            headers={"X-Tenant-ID": "11111111-1111-4111-8111-111111111111"},
            json={},
        )
    assert response.status_code == (401 if path == "/api/v1/wazuh/agents" else 503)
    forbidden.assert_not_called()
