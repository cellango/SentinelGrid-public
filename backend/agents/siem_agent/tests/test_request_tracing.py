import sys
import types

from fastapi import FastAPI
from fastapi.testclient import TestClient

opensearchpy_module = types.ModuleType("opensearchpy")
opensearchpy_module.OpenSearch = object
opensearchpy_module.Search = object
opensearchpy_module.Q = object
opensearchpy_module.RequestsHttpConnection = object
opensearchpy_module.exceptions = types.SimpleNamespace(OpenSearchException=Exception, NotFoundError=Exception)
opensearchpy_exceptions_module = types.ModuleType("opensearchpy.exceptions")
opensearchpy_exceptions_module.OpenSearchException = Exception
opensearchpy_exceptions_module.NotFoundError = Exception
sys.modules.setdefault("opensearchpy", opensearchpy_module)
sys.modules.setdefault("opensearchpy.exceptions", opensearchpy_exceptions_module)

redis_stub = types.ModuleType("redis")


class _DummyRedisConnection:
    def ping(self):
        return True


def _from_url(*args, **kwargs):
    return _DummyRedisConnection()


redis_stub.from_url = _from_url
sys.modules.setdefault("redis", redis_stub)

import app.main as siem_main
from sg_core.request_tracing import RequestTracingMiddleware


def _client():
    app = FastAPI()
    app.add_middleware(RequestTracingMiddleware, service_name="siem-agent")

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    return TestClient(app)


def test_siem_app_registers_request_tracing_middleware():
    assert any(
        middleware.cls is RequestTracingMiddleware
        for middleware in siem_main.app.user_middleware
    )


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
            "X-Request-ID": "req-siem-1",
            "X-Correlation-ID": "corr-siem-1",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-siem-1"
    assert response.headers["X-Correlation-ID"] == "corr-siem-1"
