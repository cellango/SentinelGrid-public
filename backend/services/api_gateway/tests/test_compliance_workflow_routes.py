from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from sg_core.security import get_current_tenant


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)
        self.headers = {"content-type": "application/json"}
        self.content = str(payload).encode()

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
        self.recorder["method"] = method
        self.recorder["url"] = url
        self.recorder["headers"] = headers or {}
        self.recorder["params"] = params or {}
        self.recorder["json"] = json
        return FakeResponse({"ok": True, "url": url, "payload": json})

    async def get(self, url, headers=None, params=None):
        self.recorder["method"] = "GET"
        self.recorder["url"] = url
        self.recorder["headers"] = headers or {}
        self.recorder["params"] = params or {}
        self.recorder["json"] = None
        return FakeResponse({"ok": True, "url": url})


@pytest.fixture
def workflow_client():
    tenant_id = str(uuid4())

    def _get_tenant():
        return tenant_id

    app.dependency_overrides[get_current_tenant] = _get_tenant

    with TestClient(app) as client:
        yield client, tenant_id

    app.dependency_overrides.clear()


def test_collect_evidence_route_proxies_to_iam_compliance(workflow_client, mocker):
    client, tenant_id = workflow_client
    recorder = {}
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    response = client.post(
        "/api/v1/compliance/evidence/collect",
        headers={"Authorization": "Bearer token-123"},
        json={
            "control_id": "IA-2",
            "evidence_types": ["configuration", "audit_log"],
        },
    )

    assert response.status_code == 200
    assert recorder["url"].endswith("/internal/iam/compliance/evidence/collect")
    assert recorder["headers"]["X-Tenant-ID"] == tenant_id
    assert recorder["headers"]["Authorization"] == "Bearer token-123"
    assert recorder["json"]["tenant_id"] == tenant_id
    assert recorder["json"]["control_id"] == "IA-2"


def test_collect_evidence_rejects_foreign_tenant_override(workflow_client, mocker):
    client, tenant_id = workflow_client
    recorder = {}
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    response = client.post(
        "/api/v1/compliance/evidence/collect",
        headers={"Authorization": "Bearer token-123"},
        json={
            "control_id": "IA-2",
            "evidence_types": ["configuration"],
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant ID mismatch. You can only access your own tenant's data."
    assert recorder == {}


def test_soc2_coverage_route_forwards_authenticated_tenant(workflow_client, mocker):
    client, tenant_id = workflow_client
    recorder = {}
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    response = client.get(
        "/api/v1/compliance/soc2/coverage",
        headers={"Authorization": "Bearer token-123"},
    )

    assert response.status_code == 200
    assert recorder["url"].endswith("/api/v1/compliance/soc2/coverage")
    assert recorder["headers"]["X-Tenant-ID"] == tenant_id
    assert recorder["headers"]["Authorization"] == "Bearer token-123"


def test_compliance_dashboard_route_forwards_authenticated_tenant(workflow_client, mocker):
    client, tenant_id = workflow_client
    recorder = {}
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    response = client.get(
        "/api/v1/compliance/dashboard",
        headers={"Authorization": "Bearer token-123"},
    )

    assert response.status_code == 200
    assert recorder["url"].endswith("/api/v1/compliance/dashboard")
    assert recorder["headers"]["X-Tenant-ID"] == tenant_id
    assert recorder["headers"]["Authorization"] == "Bearer token-123"


def test_compliance_capabilities_route_proxies_runtime_metadata(workflow_client, mocker):
    client, _tenant_id = workflow_client
    recorder = {}

    class CapabilitiesAsyncClient(FakeAsyncClient):
        async def get(self, url, headers=None, params=None):
            self.recorder["method"] = "GET"
            self.recorder["url"] = url
            self.recorder["headers"] = headers or {}
            self.recorder["params"] = params or {}
            self.recorder["json"] = None
            return FakeResponse(
                {
                    "runtime_mode": "soc2_readiness",
                    "capabilities": {"soc2_readiness": True},
                    "truth_labels": {"dashboard_title": "SOC 2 Readiness Dashboard"},
                }
            )

    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: CapabilitiesAsyncClient(recorder))

    response = client.get("/api/v1/compliance/capabilities")

    assert response.status_code == 200
    assert recorder["url"].endswith("/api/v1/compliance/capabilities")
    assert response.json()["runtime_mode"] == "soc2_readiness"
    assert response.json()["truth_labels"]["dashboard_title"] == "SOC 2 Readiness Dashboard"


def test_compliance_capabilities_route_falls_back_to_gateway_flags(workflow_client, mocker):
    client, _tenant_id = workflow_client

    class FailingAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return False

        async def get(self, url, headers=None, params=None):
            raise httpx.ConnectError("compliance service unavailable")

    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", FailingAsyncClient)

    response = client.get("/api/v1/compliance/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime_mode"] == "soc2_readiness"
    assert payload["capabilities"]["multi_framework_selection"] is False
    assert payload["capabilities"]["durable_evidence_repository"] is False
    assert payload["capabilities"]["compliance_agent_workflows"] is False
    assert payload["admin_control_paths"]["settings"] == "/api/v1/compliance/admin/settings"


def test_compliance_launch_readiness_route_proxies_authenticated_tenant(workflow_client, mocker):
    client, tenant_id = workflow_client
    recorder = {}
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    response = client.get(
        "/api/v1/compliance/launch-readiness",
        headers={"Authorization": "Bearer token-123"},
    )

    assert response.status_code == 200
    assert recorder["method"] == "GET"
    assert recorder["url"].endswith("/api/v1/compliance/launch-readiness")
    assert recorder["headers"]["X-Tenant-ID"] == tenant_id
    assert recorder["headers"]["Authorization"] == "Bearer token-123"


def test_compliance_admin_settings_routes_proxy_authenticated_tenant(workflow_client, mocker):
    client, tenant_id = workflow_client
    recorder = {}
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    get_response = client.get(
        "/api/v1/compliance/admin/settings",
        headers={"Authorization": "Bearer token-123"},
    )
    put_response = client.put(
        "/api/v1/compliance/admin/settings",
        headers={"Authorization": "Bearer token-123"},
        json={"multi_framework_selection": False, "compliance_agent_workflows": True},
    )

    assert get_response.status_code == 200
    assert put_response.status_code == 200
    assert recorder["method"] == "PUT"
    assert recorder["url"].endswith("/api/v1/compliance/admin/settings")
    assert recorder["headers"]["X-Tenant-ID"] == tenant_id
    assert recorder["json"] == {"multi_framework_selection": False, "compliance_agent_workflows": True}


def test_compliance_framework_catalog_routes_proxy_to_compliance_service(workflow_client, mocker):
    client, _tenant_id = workflow_client
    recorder = {}
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    list_response = client.get("/api/v1/compliance/frameworks")
    detail_response = client.get("/api/v1/compliance/frameworks/soc2")
    controls_response = client.get("/api/v1/compliance/frameworks/soc2/controls")

    assert list_response.status_code == 200
    assert list_response.json()["url"].endswith("/api/v1/compliance/frameworks")

    assert detail_response.status_code == 200
    assert detail_response.json()["url"].endswith("/api/v1/compliance/frameworks/soc2")

    assert controls_response.status_code == 200
    assert controls_response.json()["url"].endswith("/api/v1/compliance/frameworks/soc2/controls")


def test_compliance_generalized_coverage_routes_proxy_authenticated_tenant(workflow_client, mocker):
    client, tenant_id = workflow_client
    recorder = {}
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    coverage_response = client.get(
        "/api/v1/compliance/coverage?limit=25&offset=5",
        headers={"Authorization": "Bearer token-123"},
    )
    assert coverage_response.status_code == 200
    assert recorder["url"].endswith("/api/v1/compliance/coverage")
    assert recorder["headers"]["X-Tenant-ID"] == tenant_id
    assert recorder["params"] == {"limit": 25, "offset": 5}

    framework_response = client.get(
        "/api/v1/compliance/frameworks/hipaa/coverage?limit=10",
        headers={"Authorization": "Bearer token-123"},
    )
    assert framework_response.status_code == 200
    assert recorder["url"].endswith("/api/v1/compliance/frameworks/hipaa/coverage")
    assert recorder["params"] == {"limit": 10, "offset": 0}

    control_response = client.get(
        "/api/v1/compliance/controls/CC6.1/status?framework_id=soc2",
        headers={"Authorization": "Bearer token-123"},
    )
    assert control_response.status_code == 200
    assert recorder["url"].endswith("/api/v1/compliance/controls/CC6.1/status")
    assert recorder["params"] == {"framework_id": "soc2"}


def test_compliance_framework_selection_routes_proxy_authenticated_tenant(workflow_client, mocker):
    client, tenant_id = workflow_client
    recorder = {}
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    get_response = client.get(
        "/api/v1/compliance/framework-selections",
        headers={"Authorization": "Bearer token-123"},
    )

    assert get_response.status_code == 200
    assert recorder["method"] == "GET"
    assert recorder["url"].endswith("/api/v1/compliance/framework-selections")
    assert recorder["headers"]["X-Tenant-ID"] == tenant_id
    assert recorder["headers"]["Authorization"] == "Bearer token-123"

    put_response = client.put(
        "/api/v1/compliance/framework-selections",
        headers={"Authorization": "Bearer token-123"},
        json={"selections": [{"framework_id": "soc2", "status": "active"}]},
    )

    assert put_response.status_code == 200
    assert recorder["method"] == "PUT"
    assert recorder["url"].endswith("/api/v1/compliance/framework-selections")
    assert recorder["headers"]["X-Tenant-ID"] == tenant_id
    assert recorder["json"]["tenant_id"] == tenant_id
    assert recorder["json"]["selections"][0]["framework_id"] == "soc2"


def test_compliance_framework_selection_route_rejects_foreign_tenant_override(workflow_client, mocker):
    client, _tenant_id = workflow_client
    recorder = {}
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    response = client.put(
        "/api/v1/compliance/framework-selections",
        headers={"Authorization": "Bearer token-123"},
        json={
            "tenant_id": str(uuid4()),
            "selections": [{"framework_id": "soc2"}],
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant ID mismatch. You can only access your own tenant's data."
    assert recorder == {}


def test_compliance_evidence_repository_routes_proxy_authenticated_tenant(workflow_client, mocker):
    client, tenant_id = workflow_client
    recorder = {}
    evidence_id = str(uuid4())
    package_id = str(uuid4())
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    list_response = client.get(
        "/api/v1/compliance/evidence?framework_id=soc2&control_id=CC6.1&limit=25",
        headers={"Authorization": "Bearer token-123"},
    )
    assert list_response.status_code == 200
    assert recorder["method"] == "GET"
    assert recorder["url"].endswith("/api/v1/compliance/evidence")
    assert recorder["headers"]["X-Tenant-ID"] == tenant_id
    assert recorder["params"]["tenant_id"] == tenant_id
    assert recorder["params"]["framework_id"] == "soc2"
    assert recorder["params"]["control_id"] == "CC6.1"

    create_response = client.post(
        "/api/v1/compliance/evidence",
        headers={"Authorization": "Bearer token-123"},
        json={
            "evidence_type": "configuration",
            "title": "MFA configuration export",
            "source_system": "iam_agent",
            "source_resource_id": "tenant-mfa-settings",
            "collector": "iam_agent",
            "collection_method": "api",
            "valid_from": "2026-04-01T00:00:00Z",
            "valid_until": "2026-07-01T00:00:00Z",
            "hash_sha256": "a" * 64,
            "storage_uri": "s3://evidence/tenant/mfa.json",
            "summary": "MFA is enforced for privileged users.",
            "control_links": [{"control_id": "CC6.1", "framework_id": "soc2"}],
        },
    )
    assert create_response.status_code == 200
    assert recorder["method"] == "POST"
    assert recorder["url"].endswith("/api/v1/compliance/evidence")
    assert recorder["json"]["tenant_id"] == tenant_id
    assert recorder["json"]["control_links"][0]["control_id"] == "CC6.1"

    get_response = client.get(
        f"/api/v1/compliance/evidence/{evidence_id}",
        headers={"Authorization": "Bearer token-123"},
    )
    assert get_response.status_code == 200
    assert recorder["url"].endswith(f"/api/v1/compliance/evidence/{evidence_id}")

    review_response = client.post(
        f"/api/v1/compliance/evidence/{evidence_id}/review",
        headers={"Authorization": "Bearer token-123"},
        json={"review_status": "accepted"},
    )
    assert review_response.status_code == 200
    assert recorder["url"].endswith(f"/api/v1/compliance/evidence/{evidence_id}/review")
    assert recorder["json"]["tenant_id"] == tenant_id
    assert recorder["json"]["review_status"] == "accepted"

    package_list_response = client.get(
        "/api/v1/compliance/evidence/packages?framework_id=soc2&status=collecting&limit=25",
        headers={"Authorization": "Bearer token-123"},
    )
    assert package_list_response.status_code == 200
    assert recorder["method"] == "GET"
    assert recorder["url"].endswith("/api/v1/compliance/evidence/packages")
    assert recorder["params"]["tenant_id"] == tenant_id
    assert recorder["params"]["framework_id"] == "soc2"
    assert recorder["params"]["status"] == "collecting"

    package_response = client.post(
        "/api/v1/compliance/evidence/packages",
        headers={"Authorization": "Bearer token-123"},
        json={
            "package_name": "SOC 2 Q2 Evidence",
            "framework_id": "soc2",
            "report_period_start": "2026-04-01",
            "report_period_end": "2026-06-30",
        },
    )
    assert package_response.status_code == 200
    assert recorder["url"].endswith("/api/v1/compliance/evidence/packages")
    assert recorder["json"]["tenant_id"] == tenant_id

    task_list_response = client.get(
        "/api/v1/compliance/evidence/tasks?status=manual_evidence_required&limit=25",
        headers={"Authorization": "Bearer token-123"},
    )
    assert task_list_response.status_code == 200
    assert recorder["method"] == "GET"
    assert recorder["url"].endswith("/api/v1/compliance/evidence/tasks")
    assert recorder["params"]["tenant_id"] == tenant_id
    assert recorder["params"]["status"] == "manual_evidence_required"

    task_response = client.post(
        "/api/v1/compliance/evidence/tasks",
        headers={"Authorization": "Bearer token-123"},
        json={
            "task_name": "Manual IA-2 MFA attestation",
            "task_type": "api_response",
            "status": "manual_evidence_required",
            "idempotency_key": "iam:test:IA-2:api_response:task",
        },
    )
    assert task_response.status_code == 200
    assert recorder["url"].endswith("/api/v1/compliance/evidence/tasks")
    assert recorder["json"]["tenant_id"] == tenant_id
    assert recorder["json"]["status"] == "manual_evidence_required"

    package_detail_response = client.get(
        f"/api/v1/compliance/evidence/packages/{package_id}",
        headers={"Authorization": "Bearer token-123"},
    )
    assert package_detail_response.status_code == 200
    assert recorder["url"].endswith(f"/api/v1/compliance/evidence/packages/{package_id}")

    export_response = client.post(
        f"/api/v1/compliance/evidence/packages/{package_id}/export",
        headers={"Authorization": "Bearer token-123"},
        json={"export_format": "zip"},
    )
    assert export_response.status_code == 200
    assert recorder["url"].endswith(f"/api/v1/compliance/evidence/packages/{package_id}/export")
    assert recorder["json"]["tenant_id"] == tenant_id
    assert recorder["json"]["export_format"] == "zip"


def test_compliance_evidence_repository_routes_reject_foreign_tenant_override(workflow_client, mocker):
    client, _tenant_id = workflow_client
    recorder = {}
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    response = client.post(
        "/api/v1/compliance/evidence/packages",
        headers={"Authorization": "Bearer token-123"},
        json={
            "tenant_id": str(uuid4()),
            "package_name": "Foreign Evidence",
            "report_period_start": "2026-04-01",
            "report_period_end": "2026-06-30",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant ID mismatch. You can only access your own tenant's data."
    assert recorder == {}


def test_compliance_agent_recommendation_routes_proxy_authenticated_tenant(workflow_client, mocker):
    client, tenant_id = workflow_client
    recorder = {}
    mocker.patch("app.api.routes_compliance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    list_response = client.get(
        "/api/v1/compliance/agent/recommendations?state=proposed&source_type=control_gap&limit=25",
        headers={"Authorization": "Bearer token-123"},
    )

    assert list_response.status_code == 200
    assert recorder["method"] == "GET"
    assert recorder["url"].endswith("/api/v1/compliance/agent/recommendations")
    assert recorder["headers"]["X-Tenant-ID"] == tenant_id
    assert recorder["headers"]["Authorization"] == "Bearer token-123"
    assert recorder["params"] == {
        "state": "proposed",
        "source_type": "control_gap",
        "limit": 25,
        "offset": 0,
    }

    decision_response = client.post(
        "/api/v1/compliance/agent/recommendations/rec-1/decision",
        headers={"Authorization": "Bearer token-123"},
        json={"state": "accepted", "decision_notes": "Approved from dashboard."},
    )

    assert decision_response.status_code == 200
    assert recorder["method"] == "POST"
    assert recorder["url"].endswith("/api/v1/compliance/agent/recommendations/rec-1/decision")
    assert recorder["headers"]["X-Tenant-ID"] == tenant_id
    assert recorder["json"] == {
        "state": "accepted",
        "decision_notes": "Approved from dashboard.",
    }


def test_governance_proxy_forwards_campaign_create(workflow_client, mocker):
    client, tenant_id = workflow_client
    recorder = {}
    mocker.patch("app.api.routes_governance.httpx.AsyncClient", lambda *a, **k: FakeAsyncClient(recorder))

    response = client.post(
        "/api/governance/campaigns",
        headers={"Authorization": "Bearer token-456"},
        json={
            "tenant_id": tenant_id,
            "name": "CC6.1 Access Review",
            "start_date": "2026-03-26T00:00:00Z",
            "end_date": "2026-04-09T00:00:00Z",
            "reviewer_type": "admin",
        },
    )

    assert response.status_code == 200
    assert recorder["url"].endswith("/api/v1/governance/campaigns")
    assert recorder["headers"]["X-Tenant-ID"] == tenant_id
    assert recorder["headers"]["Authorization"] == "Bearer token-456"
    assert recorder["json"]["name"] == "CC6.1 Access Review"
