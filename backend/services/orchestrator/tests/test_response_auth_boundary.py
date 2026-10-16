import os
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

from app.api import response
from app.core import security
from app.core.config import settings
from app.services.metrics import metrics_tracker


TENANT_ID = UUID("00000000-0000-0000-0000-000000000111")
OTHER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000222")
INTERNAL_TOKEN = "internal-test-token"


@pytest.fixture
def client(monkeypatch):
    metrics_tracker.reset()
    monkeypatch.setattr(settings, "INTERNAL_SERVICE_TOKEN", INTERNAL_TOKEN)

    app = FastAPI()
    app.include_router(response.router)
    calls = []

    class DummyResponseOrchestrator:
        async def orchestrate_alert_response(self, alert_id, tenant_id, response_type):
            calls.append(
                {
                    "method": "orchestrate_alert_response",
                    "tenant_id": str(tenant_id),
                    "alert_id": str(alert_id),
                }
            )
            return {
                "alert_id": str(alert_id),
                "status": "orchestrated",
                "playbooks_triggered": 1,
                "playbooks": [{"playbook_id": "pb-1", "status": "pending"}],
                "tenant_id": str(tenant_id),
                "response_type": str(response_type),
            }

        async def orchestrate_finding_remediation(self, finding_id, finding_type, tenant_id, playbook_id=None):
            calls.append(
                {
                    "method": "orchestrate_finding_remediation",
                    "tenant_id": str(tenant_id),
                    "finding_id": str(finding_id),
                }
            )
            return {
                "finding_id": str(finding_id),
                "finding_type": finding_type,
                "status": "orchestrated",
                "remediation_id": "rem-1",
                "execution_id": "exec-1",
                "tenant_id": str(tenant_id),
                "playbook_id": str(playbook_id) if playbook_id else None,
            }

        async def get_execution_status(self, execution_id, tenant_id, execution_type="playbook"):
            calls.append(
                {
                    "method": "get_execution_status",
                    "tenant_id": str(tenant_id),
                    "execution_id": str(execution_id),
                }
            )
            return {
                "execution_id": str(execution_id),
                "execution_type": execution_type,
                "status": "running",
                "tenant_id": str(tenant_id),
            }

        async def generate_execution_report(self, tenant_id, start_date=None, end_date=None):
            calls.append(
                {
                    "method": "generate_execution_report",
                    "tenant_id": str(tenant_id),
                }
            )
            return {
                "tenant_id": str(tenant_id),
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None,
                },
                "summary": {"total_orchestrations": 1},
            }

    monkeypatch.setattr(response, "ResponseOrchestrator", DummyResponseOrchestrator)
    app.state.calls = calls

    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("post", f"/api/v1/orchestrator/alerts/{uuid4()}/orchestrate", {"json": {"response_type": "automated_response"}}),
        ("post", f"/api/v1/orchestrator/findings/{uuid4()}/orchestrate?finding_type=iam_finding", {"json": {"playbook_id": str(uuid4())}}),
        ("get", f"/api/v1/orchestrator/executions/{uuid4()}/status", {}),
        ("get", "/api/v1/orchestrator/reports/executions", {}),
    ],
)
def test_response_routes_require_real_auth_and_reject_placeholder_tenant(client, method, path, kwargs):
    response_obj = getattr(client, method)(
        path,
        headers={
            "Authorization": f"Bearer {INTERNAL_TOKEN}",
            "X-Tenant-ID": "default",
        },
        **kwargs,
    )

    assert response_obj.status_code == 400
    assert "X-Tenant-ID" in response_obj.json()["detail"]
    assert client.app.state.calls == []


@pytest.mark.parametrize(
    ("method", "path", "kwargs", "expected_key", "expected_call"),
    [
        ("post", f"/api/v1/orchestrator/alerts/{uuid4()}/orchestrate", {"json": {"response_type": "automated_response"}}, "alert_id", "orchestrate_alert_response"),
        ("post", f"/api/v1/orchestrator/findings/{uuid4()}/orchestrate?finding_type=iam_finding", {"json": {"playbook_id": str(uuid4())}}, "finding_id", "orchestrate_finding_remediation"),
        ("get", f"/api/v1/orchestrator/executions/{uuid4()}/status", {}, "execution_id", "get_execution_status"),
        ("get", "/api/v1/orchestrator/reports/executions", {}, "tenant_id", "generate_execution_report"),
    ],
)
def test_response_routes_accept_internal_service_token_with_tenant_header(
    client,
    method,
    path,
    kwargs,
    expected_key,
    expected_call,
):
    response_obj = getattr(client, method)(
        path,
        headers={
            "Authorization": f"Bearer {INTERNAL_TOKEN}",
            "X-Tenant-ID": str(TENANT_ID),
        },
        **kwargs,
    )

    assert response_obj.status_code == 200
    payload = response_obj.json()
    assert expected_key in payload
    assert client.app.state.calls[-1]["method"] == expected_call
    assert client.app.state.calls[-1]["tenant_id"] == str(TENANT_ID)
    if "tenant_id" in payload:
        assert payload["tenant_id"] == str(TENANT_ID)


def test_response_routes_accept_validated_user_token_without_tenant_header(client, monkeypatch):
    monkeypatch.setattr(
        security,
        "verify_token_with_iam",
        lambda _token: {"tenant_id": str(TENANT_ID), "user_id": "user-1"},
    )

    response_obj = client.get(
        "/api/v1/orchestrator/reports/executions",
        headers={"Authorization": "Bearer valid-user-token"},
    )

    assert response_obj.status_code == 200
    assert response_obj.json()["tenant_id"] == str(TENANT_ID)
    assert client.app.state.calls[-1]["tenant_id"] == str(TENANT_ID)


def test_response_routes_reject_user_token_with_mismatched_tenant_header(client, monkeypatch):
    monkeypatch.setattr(
        security,
        "verify_token_with_iam",
        lambda _token: {"tenant_id": str(TENANT_ID), "user_id": "user-1"},
    )

    response_obj = client.get(
        "/api/v1/orchestrator/reports/executions",
        headers={
            "Authorization": "Bearer valid-user-token",
            "X-Tenant-ID": str(OTHER_TENANT_ID),
        },
    )

    assert response_obj.status_code == 403
    assert "Tenant mismatch" in response_obj.json()["detail"]
    assert client.app.state.calls == []


def test_security_dependency_rejects_missing_authentication():
    app = FastAPI()

    @app.get("/tenant")
    def _route(tenant_id: UUID = Depends(security.get_current_tenant)):
        return {"tenant_id": str(tenant_id)}

    with TestClient(app) as client:
        response_obj = client.get("/tenant")

    assert response_obj.status_code == 401
    assert "validated bearer token" in response_obj.json()["detail"]
