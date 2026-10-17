"""Legacy header/session-substitution expectations require owned admission now."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import database
from unittest.mock import Mock

ID = "33333333-3333-4333-8333-333333333333"


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/observables"),
        ("POST", "/observables/bulk"),
        ("GET", "/observables/" + ID),
        ("POST", "/observables/search"),
        ("POST", "/observables/" + ID + "/enrich"),
        ("GET", "/observables/" + ID + "/analyzers"),
        ("PATCH", "/observables/" + ID),
    ],
)
def test_legacy_header_and_static_token_cannot_open_storage(monkeypatch, method, path):
    forbidden = Mock(side_effect=AssertionError("No SQL"))
    monkeypatch.setattr(database, "SessionLocal", forbidden)
    with TestClient(app) as client:
        response = client.request(
            method,
            path,
            headers={
                "X-Tenant-ID": "11111111-1111-4111-8111-111111111111",
                "Authorization": "Bearer synthetic-static-token",
            },
            json={},
        )
    assert response.status_code == (
        401 if method == "GET" and not path.endswith("/analyzers") else 503
    )
    forbidden.assert_not_called()
