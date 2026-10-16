"""Focused tenant-isolation coverage for SIEM router webhook."""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import router as router_api


class _FakeResponse:
    status_code = 200
    text = "ok"

    def raise_for_status(self) -> None:
        return None


class _FakeAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return _FakeResponse()


def test_opensearch_router_uses_resolved_tenant_scope():
    """Webhook routing should resolve tenant scope before DB access."""
    calls = {"tenant": 0, "session": 0}
    test_app = FastAPI()
    test_app.include_router(router_api.router, prefix="/api/v1", tags=["router"])

    def override_resolve_opensearch_router_tenant():
        calls["tenant"] += 1
        return "11111111-1111-1111-1111-111111111111"

    def override_get_opensearch_router_session():
        calls["session"] += 1
        yield object()

    test_app.dependency_overrides[router_api.resolve_opensearch_router_tenant] = (
        override_resolve_opensearch_router_tenant
    )
    test_app.dependency_overrides[router_api.get_opensearch_router_session] = (
        override_get_opensearch_router_session
    )

    with patch.object(
        router_api,
        "_get_tenant_destination",
        return_value={"custom_config": {"soar_webhook_url": "https://soar.example/webhook"}},
    ), patch("app.api.router.httpx.AsyncClient", return_value=_FakeAsyncClient()):
        client = TestClient(test_app)
        response = client.post(
            "/api/v1/router/opensearch-webhook",
            json={"tenant_id": "11111111-1111-1111-1111-111111111111", "message": "alert"},
        )

    assert response.status_code == 200
    assert calls == {"tenant": 1, "session": 1}
