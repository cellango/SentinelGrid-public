from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import security as siem_security
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

    monkeypatch.setattr(siem_security.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(siem_security.settings, "UPSTREAM_TLS_VERIFY", True, raising=False)
    monkeypatch.setattr(siem_security, "IAM_AGENT_URL", "https://iam.example.test")

    app = FastAPI()
    app.add_middleware(RequestTracingMiddleware, service_name="siem-agent")

    @app.get("/validate")
    async def validate():
        return await siem_security.verify_token_with_iam_agent("jwt-123")

    client = TestClient(app)
    response = client.get(
        "/validate",
        headers={
            "X-Request-ID": "req-siem-auth-1",
            "X-Correlation-ID": "corr-siem-auth-1",
        },
    )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "tenant-123"
    assert calls[0]["client_kwargs"]["verify"] is True
    assert calls[1]["url"] == "https://iam.example.test/internal/iam/auth/validate-token"
    assert calls[1]["headers"]["X-Request-ID"] == "req-siem-auth-1"
    assert calls[1]["headers"]["X-Correlation-ID"] == "corr-siem-auth-1"
    assert calls[1]["json"] == {"token": "jwt-123"}
