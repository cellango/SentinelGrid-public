from fastapi.testclient import TestClient

from app.main import app
from sg_core.request_tracing import RequestTracingMiddleware


def test_model_gateway_app_registers_request_tracing_middleware():
    assert any(
        middleware.cls is RequestTracingMiddleware
        for middleware in app.user_middleware
    )


def test_request_tracing_generates_response_headers():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Correlation-ID"] == response.headers["X-Request-ID"]


def test_request_tracing_preserves_incoming_headers():
    client = TestClient(app)

    response = client.get(
        "/health",
        headers={
            "X-Request-ID": "req-model-1",
            "X-Correlation-ID": "corr-model-1",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-model-1"
    assert response.headers["X-Correlation-ID"] == "corr-model-1"
