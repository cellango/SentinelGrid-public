from fastapi.testclient import TestClient

from app.main import app


def test_health_response_includes_request_trace_headers():
    client = TestClient(app)

    response = client.get(
        "/health",
        headers={
            "X-Request-ID": "req-health-1",
            "X-Correlation-ID": "corr-health-1",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-health-1"
    assert response.headers["X-Correlation-ID"] == "corr-health-1"
