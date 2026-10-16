from fastapi.testclient import TestClient

import app.main as ingestion_main


def test_request_tracing_generates_response_headers():
    client = TestClient(ingestion_main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Correlation-ID"] == response.headers["X-Request-ID"]


def test_request_tracing_preserves_incoming_headers():
    client = TestClient(ingestion_main.app)

    response = client.get(
        "/health",
        headers={
            "X-Request-ID": "req-ingestion-1",
            "X-Correlation-ID": "corr-ingestion-1",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-ingestion-1"
    assert response.headers["X-Correlation-ID"] == "corr-ingestion-1"
