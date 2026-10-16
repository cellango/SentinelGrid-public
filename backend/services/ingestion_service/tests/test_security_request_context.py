from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import security as ingestion_security
from sg_core.request_tracing import RequestTracingMiddleware


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_verify_token_forwards_trace_headers_to_iam_agent(monkeypatch):
    calls = []

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            calls.append({"client_kwargs": kwargs})

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None, headers=None):
            calls.append(
                {
                    "url": url,
                    "json": json,
                    "headers": headers or {},
                }
            )
            return FakeResponse(
                {
                    "valid": True,
                    "payload": {"sub": "user-1", "tenant_id": "tenant-123"},
                    "tenant_id": "tenant-123",
                    "roles": ["admin"],
                    "user_id": "user-1",
                }
            )

    monkeypatch.setattr(ingestion_security.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        ingestion_security.settings,
        "IAM_AGENT_URL",
        "https://iam.example.test",
        raising=False,
    )
    monkeypatch.setattr(
        ingestion_security.settings,
        "UPSTREAM_TLS_VERIFY",
        True,
        raising=False,
    )

    app = FastAPI()
    app.add_middleware(RequestTracingMiddleware, service_name="ingestion-service")

    @app.get("/validate")
    async def validate():
        return await ingestion_security.verify_token_with_iam_agent("jwt-123")

    client = TestClient(app)
    response = client.get(
        "/validate",
        headers={
            "X-Request-ID": "req-ingestion-auth-1",
            "X-Correlation-ID": "corr-ingestion-auth-1",
        },
    )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "tenant-123"
    assert calls[0]["client_kwargs"]["verify"] is True
    assert calls[1]["url"] == "https://iam.example.test/internal/iam/auth/validate-token"
    assert calls[1]["headers"]["X-Request-ID"] == "req-ingestion-auth-1"
    assert calls[1]["headers"]["X-Correlation-ID"] == "corr-ingestion-auth-1"
    assert calls[1]["json"] == {"token": "jwt-123"}
