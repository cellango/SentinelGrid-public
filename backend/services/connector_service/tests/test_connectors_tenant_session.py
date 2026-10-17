"""Legacy CRUD/sync/test acceptance stays required behind the source gate."""

from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import database

ID = "33333333-3333-4333-8333-333333333333"


@pytest.mark.parametrize(
    "method,path,status",
    [
        ("POST", "/api/v1/connectors", 503),
        ("GET", "/api/v1/connectors", 401),
        ("GET", "/api/v1/connectors/" + ID, 401),
        ("PATCH", "/api/v1/connectors/" + ID, 503),
        ("DELETE", "/api/v1/connectors/" + ID, 503),
        ("POST", "/api/v1/connectors/" + ID + "/sync", 503),
        ("POST", "/api/v1/connectors/sync/all", 503),
        ("POST", "/api/v1/connectors/" + ID + "/test", 503),
    ],
)
def test_raw_header_cannot_open_tenant_session(method, path, status, monkeypatch):
    forbidden = Mock(side_effect=AssertionError("No SQL from a forwarded tenant"))
    monkeypatch.setattr(database, "SessionLocal", forbidden)
    with TestClient(app) as client:
        response = client.request(
            method,
            path,
            headers={"X-Tenant-ID": "11111111-1111-4111-8111-111111111111"},
            json={},
        )
    assert response.status_code == status
    forbidden.assert_not_called()
