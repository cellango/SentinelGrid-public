from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.request_identity import require_gateway_identity
from sg_core.db import get_tenant_session
from sg_core.security import get_current_tenant


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)
        self.content = str(payload).encode()
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.text)


class FakeAsyncClient:
    def __init__(self, recorder):
        self.recorder = recorder

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def request(self, method, url, headers=None, params=None, json=None):
        self.recorder.setdefault("calls", []).append(
            {
                "method": method,
                "url": url,
                "headers": headers or {},
                "params": params or {},
                "json": json,
            }
        )
        if url.endswith("/api/v1/reports/"):
            return FakeResponse(
                [
                    {
                        "id": "report-1",
                        "name": "SOC 2 Evidence Summary",
                        "status": "completed",
                        "generated_at": "2026-04-27T10:00:00Z",
                        "metadata": {"template_key": "soc2_evidence_summary"},
                    },
                    {
                        "id": "report-2",
                        "name": "SOC 2 Coverage",
                        "status": "pending",
                        "created_at": "2026-04-27T11:00:00Z",
                        "metadata": {"template_key": "soc2_coverage"},
                    },
                ]
            )
        if url.endswith("/api/v1/audit/logs"):
            return FakeResponse(
                {
                    "logs": [
                        {
                            "id": "audit-1",
                            "tenant_id": self.recorder["tenant_id"],
                            "timestamp": "2026-04-27T12:00:00Z",
                            "action": "report_generation_requested",
                            "action_category": "compliance",
                            "actor_user_id": "user-1",
                            "actor_email": "owner@example.com",
                            "resource_type": "report",
                            "resource_id": "report-1",
                            "resource_name": "SOC 2 Evidence Summary",
                            "success": True,
                            "metadata": {"template_key": "soc2_evidence_summary"},
                        }
                    ],
                    "count": 1,
                    "limit": params.get("limit", 50) if params else 50,
                    "offset": params.get("offset", 0) if params else 0,
                }
            )
        if url.endswith("/api/v1/entitlements"):
            return FakeResponse(
                [
                    {
                        "id": "ent-orphaned",
                        "tenant_id": self.recorder["tenant_id"],
                        "resource_type": "app",
                        "resource_id": "crm",
                        "action": "admin",
                        "granted_to_type": "user",
                        "granted_to_id": "user-missing",
                        "status": "active",
                    },
                    {
                        "id": "ent-active",
                        "tenant_id": self.recorder["tenant_id"],
                        "resource_type": "app",
                        "resource_id": "email",
                        "action": "read",
                        "granted_to_type": "user",
                        "granted_to_id": "user-active",
                        "status": "active",
                    },
                    {
                        "id": "ent-revoked",
                        "tenant_id": self.recorder["tenant_id"],
                        "resource_type": "app",
                        "resource_id": "billing",
                        "action": "write",
                        "granted_to_type": "user",
                        "granted_to_id": "user-disabled",
                        "status": "revoked",
                    },
                ]
            )
        if url.endswith("/api/iam-portal/users"):
            return FakeResponse(
                [
                    {"user_id": "user-active", "enabled": True},
                    {"user_id": "user-disabled", "enabled": False},
                ]
            )
        return FakeResponse({"ok": True, "url": url})


@pytest.fixture
def compliance_client(mock_db_session):
    tenant_id = str(uuid4())

    def _get_tenant():
        return tenant_id

    def _get_db():
        yield mock_db_session

    app.dependency_overrides[get_current_tenant] = _get_tenant
    # Route-unit fixture; real gateway admission has its own no-override suite.
    app.dependency_overrides[require_gateway_identity] = lambda: None
    app.dependency_overrides[get_tenant_session] = _get_db

    with TestClient(app) as client:
        yield client, tenant_id

    app.dependency_overrides.clear()


def test_compliance_report_route_uses_reporting_service_and_marks_legacy_contract(compliance_client, mocker):
    client, tenant_id = compliance_client
    recorder = {"tenant_id": tenant_id}
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    response = client.get(
        f"/api/v1/compliance/report?tenant_id={tenant_id}",
        headers={"Authorization": "Bearer token-123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == tenant_id
    assert payload["deprecated"] is True
    assert payload["replacement_endpoint"] == "/api/v1/reports"
    assert payload["source"] == "reporting_service"
    assert payload["report_count"] == 2
    assert payload["active_entitlements"] == 1
    assert payload["pending_review"] == 1
    assert recorder["calls"][0]["url"].endswith("/api/v1/reports/")
    assert recorder["calls"][0]["headers"]["X-Tenant-ID"] == tenant_id


def test_compliance_audit_trail_route_uses_audit_service_compliance_events(compliance_client, mocker):
    client, tenant_id = compliance_client
    recorder = {"tenant_id": tenant_id}
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    response = client.get(
        f"/api/v1/compliance/audit-trail?tenant_id={tenant_id}&realm_name=acme&limit=10&offset=5",
        headers={"Authorization": "Bearer token-123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["limit"] == 10
    assert payload["offset"] == 5
    assert payload["source"] == "audit_service"
    assert payload["results"][0]["resource_type"] == "report"
    assert payload["results"][0]["action"] == "report_generation_requested"
    audit_call = recorder["calls"][0]
    assert audit_call["url"].endswith("/api/v1/audit/logs")
    assert audit_call["params"]["tenant_id"] == tenant_id
    assert audit_call["params"]["realm_name"] == "acme"
    assert audit_call["params"]["action_category"] == "compliance"


def test_orphaned_entitlements_route_uses_iam_entitlement_data(compliance_client, mocker):
    client, tenant_id = compliance_client
    recorder = {"tenant_id": tenant_id}
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    response = client.get(
        f"/api/v1/compliance/orphaned-entitlements?tenant_id={tenant_id}",
        headers={"Authorization": "Bearer token-123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == tenant_id
    assert payload["source"] == "iam_agent"
    assert payload["evaluated_entitlements"] == 3
    assert payload["active_user_count"] == 1
    assert payload["orphaned_count"] == 1
    assert payload["entitlements"][0]["id"] == "ent-orphaned"
    assert [call["url"] for call in recorder["calls"]] == [
        "http://iam_agent:8000/api/v1/entitlements",
        "http://iam_agent:8000/api/iam-portal/users",
    ]
