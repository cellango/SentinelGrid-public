"""Every rule capability remains required behind explicit source unavailability."""

from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import database

ID = "33333333-3333-4333-8333-333333333333"


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/v1/rules"),
        ("GET", "/api/v1/rules"),
        ("GET", "/api/v1/rules/" + ID),
        ("PATCH", "/api/v1/rules/" + ID),
        ("DELETE", "/api/v1/rules/" + ID),
        ("POST", "/api/v1/rules/" + ID + "/evaluate"),
        ("POST", "/api/v1/rules/evaluate/all"),
        ("POST", "/api/v1/rules/enable"),
    ],
)
def test_raw_tenant_cannot_open_rule_storage(method, path, monkeypatch):
    forbidden = Mock(side_effect=AssertionError("No SQL or evaluation"))
    monkeypatch.setattr(database, "SessionLocal", forbidden)
    with TestClient(app) as client:
        response = client.request(
            method,
            path,
            headers={"X-Tenant-ID": "11111111-1111-4111-8111-111111111111"},
            json={},
        )
    assert response.status_code == 503
    forbidden.assert_not_called()
