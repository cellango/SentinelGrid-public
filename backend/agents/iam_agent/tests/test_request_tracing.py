from fastapi import FastAPI
from fastapi.testclient import TestClient

from sg_core.request_tracing import RequestTracingMiddleware


def _client():
    app = FastAPI()
    app.add_middleware(RequestTracingMiddleware, service_name="iam-agent")

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    return TestClient(app)


def test_request_tracing_generates_response_headers():
    client = _client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Correlation-ID"] == response.headers["X-Request-ID"]


def test_request_tracing_preserves_incoming_headers():
    client = _client()

    response = client.get(
        "/health",
        headers={
            "X-Request-ID": "req-iam-1",
            "X-Correlation-ID": "corr-iam-1",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-iam-1"
    assert response.headers["X-Correlation-ID"] == "corr-iam-1"
