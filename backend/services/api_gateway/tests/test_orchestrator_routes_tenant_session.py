from contextlib import contextmanager
import json
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_orchestrator
from sg_core.db import get_tenant_session
from sg_core.request_tracing import RequestTracingMiddleware
from sg_core.security import get_current_tenant


class _ProxyResponse:
    def __init__(self, *, status_code=200, payload=None, text=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text if text is not None else json.dumps(self._payload)

    def json(self):
        return self._payload


@contextmanager
def _orchestrator_client(fake_db, tenant_id: str):
    app = FastAPI()
    app.add_middleware(RequestTracingMiddleware, service_name="api-gateway-test")
    app.include_router(routes_orchestrator.router, prefix="/api/v1/orchestrator")

    def _get_tenant():
        return tenant_id

    def _get_db():
        yield fake_db

    app.dependency_overrides[get_current_tenant] = _get_tenant
    app.dependency_overrides[get_tenant_session] = _get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def _patch_async_client(monkeypatch, responses):
    calls = []
    queued = list(responses)

    def _next_response():
        if not queued:
            raise AssertionError("No queued proxy response available")
        return queued.pop(0)

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers=None, params=None):
            calls.append(
                {
                    "method": "GET",
                    "url": str(url),
                    "headers": headers or {},
                    "params": params,
                }
            )
            return _next_response()

        async def post(self, url, headers=None, json=None, params=None, content=None):
            calls.append(
                {
                    "method": "POST",
                    "url": str(url),
                    "headers": headers or {},
                    "json": json,
                    "params": params,
                    "content": content,
                }
            )
            return _next_response()

        async def request(self, method, url, headers=None, params=None, json=None):
            calls.append(
                {
                    "method": method,
                    "url": str(url),
                    "headers": headers or {},
                    "params": params,
                    "json": json,
                }
            )
            return _next_response()

    monkeypatch.setattr(routes_orchestrator.httpx, "AsyncClient", _FakeAsyncClient)
    return calls


def test_enqueue_scan_uses_tenant_scoped_dependency_and_forwards_authenticated_tenant(monkeypatch):
    tenant_id = str(uuid4())
    calls = _patch_async_client(monkeypatch, [_ProxyResponse(payload={"scan_id": "scan-123"})])

    with _orchestrator_client(fake_db=object(), tenant_id=tenant_id) as client:
        response = client.post(
            "/api/v1/orchestrator/scans",
            json={"scanner_id": "baseline", "target_ref": "asset-1"},
            headers={"X-Realm": "realm-123"},
        )

    assert response.status_code == 200
    assert response.json() == {"scan_id": "scan-123"}
    assert calls[0]["headers"]["X-Tenant-ID"] == tenant_id
    assert calls[0]["headers"]["X-Realm"] == "realm-123"
    assert calls[0]["json"] == {"scanner_id": "baseline", "target_ref": "asset-1"}
    assert calls[0]["url"].endswith("/scans")


def test_create_scan_ticket_forwards_authorization_and_tenant_query(monkeypatch):
    tenant_id = str(uuid4())
    calls = _patch_async_client(monkeypatch, [_ProxyResponse(payload={"ticket_id": "ticket-123"})])

    with _orchestrator_client(fake_db=object(), tenant_id=tenant_id) as client:
        response = client.post(
            "/api/v1/orchestrator/scans/scan-123/tickets",
            json={"group_id": "fix-group-1"},
            headers={
                "Authorization": "Bearer gateway-token",
                "X-Request-ID": "req-123",
                "X-Correlation-ID": "corr-123",
                "X-Realm": "realm-123",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ticket_id": "ticket-123"}
    assert calls[0]["headers"]["X-Tenant-ID"] == tenant_id
    assert calls[0]["headers"]["Authorization"] == "Bearer gateway-token"
    assert calls[0]["headers"]["X-Request-ID"] == "req-123"
    assert calls[0]["headers"]["X-Correlation-ID"] == "corr-123"
    assert calls[0]["params"] == {"tenant_id": tenant_id}
    assert calls[0]["url"].endswith("/scans/scan-123/tickets")


def test_security_snapshot_uses_tenant_scoped_session_and_authenticated_tenant(monkeypatch):
    tenant_id = str(uuid4())
    calls = _patch_async_client(monkeypatch, [_ProxyResponse(payload={
            "tenant_id": tenant_id,
            "summary": {"alerts_count": 7},
            "alerts_by_severity": {"critical": 2, "high": 3, "medium": 1, "low": 1},
            "alerts_by_status": {"open": 4, "investigating": 2, "resolved": 1},
            "top_findings": [{"title": "Critical finding", "severity": "critical"}],
        })])

    with _orchestrator_client(fake_db=object(), tenant_id=tenant_id) as client:
        response = client.get(f"/api/v1/orchestrator/tenant/{tenant_id}/security-snapshot")

    assert response.status_code == 200
    assert response.json()["tenant_id"] == tenant_id
    assert response.json()["summary"]["alerts_count"] == 7
    assert response.json()["top_findings"][0]["title"] == "Critical finding"
    assert response.json()["top_findings"][0]["severity"] == "critical"
    assert calls[0]["headers"]["X-Tenant-ID"] == tenant_id
    assert calls[0]["url"].endswith(f"/api/v1/orchestrator/tenant/{tenant_id}/security-snapshot")


def test_security_snapshot_rejects_mismatched_path_tenant():
    tenant_id = str(uuid4())

    with _orchestrator_client(fake_db=object(), tenant_id=tenant_id) as client:
        response = client.get(f"/api/v1/orchestrator/tenant/{uuid4()}/security-snapshot")

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant ID mismatch. You can only access your own tenant's data."


def test_scan_status_forwards_filters_with_authenticated_tenant(monkeypatch):
    tenant_id = str(uuid4())
    calls = _patch_async_client(monkeypatch, [_ProxyResponse(payload={"results": []})])

    with _orchestrator_client(fake_db=object(), tenant_id=tenant_id) as client:
        response = client.get(
            "/api/v1/orchestrator/scans/status"
            "?limit=25&offset=5&scanner=nessus,qualys&status=queued,running&q=prod",
            headers={"X-Realm": "realm-123"},
        )

    assert response.status_code == 200
    assert response.json() == {"results": []}
    assert calls[0]["headers"]["X-Tenant-ID"] == tenant_id
    assert calls[0]["params"] == {
        "limit": 25,
        "offset": 5,
        "scanner": "nessus,qualys",
        "status": "queued,running",
        "q": "prod",
    }
    assert calls[0]["url"].endswith("/scans/status")


def test_scan_detail_uses_tenant_scoped_dependency(monkeypatch):
    tenant_id = str(uuid4())
    calls = _patch_async_client(monkeypatch, [_ProxyResponse(payload={"scan_id": "scan-123"})])

    with _orchestrator_client(fake_db=object(), tenant_id=tenant_id) as client:
        response = client.get("/api/v1/orchestrator/scans/scan-123", headers={"X-Realm": "realm-123"})

    assert response.status_code == 200
    assert response.json() == {"scan_id": "scan-123"}
    assert calls[0]["headers"]["X-Tenant-ID"] == tenant_id
    assert calls[0]["url"].endswith("/scans/scan-123")


def test_rescore_after_scan_uses_tenant_scoped_dependency(monkeypatch):
    tenant_id = str(uuid4())
    calls = _patch_async_client(monkeypatch, [_ProxyResponse(payload={"accepted": True})])

    with _orchestrator_client(fake_db=object(), tenant_id=tenant_id) as client:
        response = client.post("/api/v1/orchestrator/scans/scan-123/rescore")

    assert response.status_code == 200
    assert response.json() == {"accepted": True}
    assert calls[0]["headers"]["X-Tenant-ID"] == tenant_id
    assert calls[0]["url"].endswith(f"/api/v1/orchestrator/tenant/{tenant_id}/posture-rescore")


def test_scan_fix_groups_uses_tenant_scoped_dependency(monkeypatch):
    tenant_id = str(uuid4())
    calls = _patch_async_client(monkeypatch, [_ProxyResponse(payload={"groups": []})])

    with _orchestrator_client(fake_db=object(), tenant_id=tenant_id) as client:
        response = client.get("/api/v1/orchestrator/scans/scan-123/fix-groups", headers={"X-Realm": "realm-123"})

    assert response.status_code == 200
    assert response.json() == {"groups": []}
    assert calls[0]["headers"]["X-Tenant-ID"] == tenant_id
    assert calls[0]["headers"]["X-Realm"] == "realm-123"
    assert calls[0]["url"].endswith("/scans/scan-123/fix-groups")


def test_dashboard_snapshot_rejects_mismatched_path_tenant(monkeypatch):
    tenant_id = str(uuid4())
    calls = _patch_async_client(monkeypatch, [])

    with _orchestrator_client(fake_db=object(), tenant_id=tenant_id) as client:
        response = client.get(f"/api/v1/orchestrator/tenant/{uuid4()}/dashboard-snapshot")

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant ID mismatch. You can only access your own tenant's data."
    assert calls == []


def test_dashboard_snapshot_forwards_authenticated_tenant(monkeypatch):
    tenant_id = str(uuid4())
    calls = _patch_async_client(monkeypatch, [_ProxyResponse(payload={"snapshot": "ok"})])

    with _orchestrator_client(fake_db=object(), tenant_id=tenant_id) as client:
        response = client.get(
            f"/api/v1/orchestrator/tenant/{tenant_id}/dashboard-snapshot",
            headers={
                "X-Request-ID": "req-tenant-1",
                "X-Correlation-ID": "corr-tenant-1",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"snapshot": "ok"}
    assert calls[0]["headers"]["X-Tenant-ID"] == tenant_id
    assert calls[0]["headers"]["X-Request-ID"] == "req-tenant-1"
    assert calls[0]["headers"]["X-Correlation-ID"] == "corr-tenant-1"
    assert calls[0]["url"].endswith(f"/api/v1/orchestrator/tenant/{tenant_id}/dashboard-snapshot")
