"""Provider OAuth authority is required; raw header/state/code cannot enable it."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.mark.parametrize(
    "tail,provider",
    [
        ("init", "google_workspace"),
        ("init", "unsupported_provider"),
        ("callback", "google_workspace"),
        ("callback", "invalid_provider"),
    ],
)
def test_unqualified_oauth_request_stays_unavailable(tail, provider):
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/connectors/oauth/" + tail,
            json={
                "provider": provider,
                "state": "synthetic-state",
                "code": "synthetic-code",
            },
        )
    assert response.status_code == 503
