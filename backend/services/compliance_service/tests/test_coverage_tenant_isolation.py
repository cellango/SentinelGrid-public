from pathlib import Path
import os
import sys

import pytest
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

os.environ.setdefault("DB_HOST", "localhost")

from app.main import app
from app.api import coverage as coverage_api
from app.core.database import get_current_tenant, get_db, get_tenant_session


TENANT_ID = "00000000-0000-0000-0000-000000000111"
OTHER_TENANT_ID = "00000000-0000-0000-0000-000000000222"


class FakeDB:
    pass


@pytest.fixture
def coverage_client(monkeypatch):
    fake_db = FakeDB()
    calls = {}

    class FakeWorkflowService:
        async def create_recommendation_and_task(self, db, **kwargs):
            calls.setdefault("agent_recommendations", []).append({"db": db, "kwargs": kwargs})
            return {"id": "rec-1"}

    def override_get_current_tenant():
        return TENANT_ID

    def unexpected_get_db():
        raise AssertionError("Coverage route used get_db instead of get_tenant_session")
        yield  # pragma: no cover

    def override_get_tenant_session():
        yield fake_db

    def fake_load_soc2_reporting_inputs(db, tenant_id):
        assert db is fake_db
        calls.setdefault("loaded_tenants", []).append(tenant_id)
        return {
            "iam_rows": ["iam"],
            "posture_rows": ["posture"],
            "alerts": ["alert"],
            "playbooks": ["playbook"],
            "executions": ["execution"],
        }

    def fake_build_soc2_coverage_payload(**kwargs):
        calls["coverage_payload"] = kwargs
        return {"tenant_id": kwargs["tenant_id"], "coverage": 87}

    def fake_build_compliance_dashboard_payload(coverage):
        calls["dashboard_input"] = coverage
        return {"tenant_id": coverage["tenant_id"], "widgets": 4}

    def fake_build_multi_framework_coverage_payload(db, tenant_id, inputs, limit=100, offset=0):
        calls.setdefault("multi_coverage", []).append(
            {"db": db, "tenant_id": tenant_id, "inputs": inputs, "limit": limit, "offset": offset}
        )
        return {
            "tenant_id": tenant_id,
            "items": [
                {
                    "framework_id": "soc2",
                    "framework_name": "SOC 2",
                    "status": "not_started",
                    "controls": [],
                }
            ],
            "count": 1,
            "limit": limit,
            "offset": offset,
            "source": "test",
        }

    def fake_build_framework_coverage_payload(db, tenant_id, framework_id, inputs, limit=100, offset=0):
        calls["framework_coverage"] = {
            "db": db,
            "tenant_id": tenant_id,
            "framework_id": framework_id,
            "inputs": inputs,
            "limit": limit,
            "offset": offset,
        }
        return {"tenant_id": tenant_id, "framework_id": framework_id, "controls": []}

    def fake_build_control_status_payload(db, tenant_id, control_id, inputs, framework_id=None):
        calls["control_status"] = {
            "db": db,
            "tenant_id": tenant_id,
            "control_id": control_id,
            "inputs": inputs,
            "framework_id": framework_id,
        }
        return {"tenant_id": tenant_id, "control_id": control_id, "framework_id": framework_id, "items": []}

    app.dependency_overrides[get_current_tenant] = override_get_current_tenant
    app.dependency_overrides[get_db] = unexpected_get_db
    app.dependency_overrides[get_tenant_session] = override_get_tenant_session
    app.dependency_overrides[coverage_api.get_compliance_agent_workflow_service] = lambda: FakeWorkflowService()

    monkeypatch.setattr(coverage_api, "_load_soc2_reporting_inputs", fake_load_soc2_reporting_inputs)
    monkeypatch.setattr(coverage_api, "build_soc2_coverage_payload", fake_build_soc2_coverage_payload)
    monkeypatch.setattr(coverage_api, "build_compliance_dashboard_payload", fake_build_compliance_dashboard_payload)
    monkeypatch.setattr(coverage_api, "build_multi_framework_coverage_payload", fake_build_multi_framework_coverage_payload)
    monkeypatch.setattr(coverage_api, "build_framework_coverage_payload", fake_build_framework_coverage_payload)
    monkeypatch.setattr(coverage_api, "build_control_status_payload", fake_build_control_status_payload)

    try:
        with TestClient(app) as test_client:
            yield test_client, calls
    finally:
        app.dependency_overrides.clear()


def test_coverage_routes_use_authenticated_tenant_session(coverage_client):
    client, calls = coverage_client

    coverage_response = client.get(
        "/api/v1/compliance/soc2/coverage",
        headers={"X-Tenant-ID": TENANT_ID, "Authorization": "Bearer test"},
    )
    assert coverage_response.status_code == 200
    assert coverage_response.json() == {"tenant_id": TENANT_ID, "coverage": 87}

    dashboard_response = client.get(
        "/api/v1/compliance/dashboard",
        params={"tenant_id": TENANT_ID},
    )
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["tenant_id"] == TENANT_ID
    assert dashboard_response.json()["widgets"] == 4
    assert dashboard_response.json()["framework_coverage"]["tenant_id"] == TENANT_ID
    assert dashboard_response.json()["selected_frameworks"][0]["framework_id"] == "soc2"

    assert calls["loaded_tenants"] == [TENANT_ID, TENANT_ID]
    assert calls["coverage_payload"]["tenant_id"] == TENANT_ID
    assert calls["dashboard_input"] == {"tenant_id": TENANT_ID, "coverage": 87}
    assert calls["multi_coverage"][0]["limit"] == 50


def test_generalized_coverage_routes_use_authenticated_tenant_session(coverage_client):
    client, calls = coverage_client

    coverage_response = client.get(
        "/api/v1/compliance/coverage",
        headers={"X-Tenant-ID": TENANT_ID},
        params={"limit": 25, "offset": 5},
    )
    assert coverage_response.status_code == 200
    assert calls["multi_coverage"][0]["tenant_id"] == TENANT_ID
    assert calls["multi_coverage"][0]["limit"] == 25
    assert calls["multi_coverage"][0]["offset"] == 5

    framework_response = client.get(
        "/api/v1/compliance/frameworks/hipaa/coverage",
        headers={"X-Tenant-ID": TENANT_ID},
        params={"limit": 10},
    )
    assert framework_response.status_code == 200
    assert calls["framework_coverage"]["framework_id"] == "hipaa"
    assert calls["framework_coverage"]["limit"] == 10

    control_response = client.get(
        "/api/v1/compliance/controls/CC6.1/status",
        headers={"X-Tenant-ID": TENANT_ID},
        params={"framework_id": "soc2"},
    )
    assert control_response.status_code == 200
    assert calls["control_status"]["control_id"] == "CC6.1"
    assert calls["control_status"]["framework_id"] == "soc2"


def test_generalized_coverage_triggers_high_priority_gap_recommendation(monkeypatch, coverage_client):
    client, calls = coverage_client

    def fake_build_multi_framework_coverage_payload(db, tenant_id, inputs, limit=100, offset=0):
        calls.setdefault("multi_coverage", []).append(
            {"db": db, "tenant_id": tenant_id, "inputs": inputs, "limit": limit, "offset": offset}
        )
        return {
            "tenant_id": tenant_id,
            "items": [
                {
                    "framework_id": "soc2",
                    "controls": [
                        {
                            "control_id": "CC6.1",
                            "gaps": [
                                {
                                    "id": "gap-1",
                                    "severity": "high",
                                    "title": "MFA evidence missing",
                                    "remediation_hint": "Collect current MFA enforcement evidence.",
                                },
                                {"id": "gap-low", "severity": "low", "title": "Minor documentation gap"},
                            ],
                        }
                    ],
                }
            ],
            "count": 1,
            "limit": limit,
            "offset": offset,
            "source": "test",
        }

    monkeypatch.setattr(
        coverage_api,
        "build_multi_framework_coverage_payload",
        fake_build_multi_framework_coverage_payload,
    )

    response = client.get(
        "/api/v1/compliance/coverage",
        headers={
            "X-Tenant-ID": TENANT_ID,
            "X-User-ID": "user-123",
            "Authorization": "Bearer user-token",
        },
    )

    assert response.status_code == 200
    recommendations = calls["agent_recommendations"]
    assert len(recommendations) == 1
    recommendation = recommendations[0]["kwargs"]
    assert recommendation["tenant_id"] == TENANT_ID
    assert recommendation["created_by"] == "user-123"
    assert recommendation["authorization"] == "Bearer user-token"
    assert recommendation["trigger_type"] == "high_priority_control_gap_detected"
    assert recommendation["recommendation_type"] == "create_evidence_collection_task"
    assert recommendation["framework_id"] == "soc2"
    assert recommendation["control_id"] == "CC6.1"
    assert recommendation["metadata"]["gap"]["id"] == "gap-1"


def test_coverage_routes_reject_cross_tenant_selectors(coverage_client):
    client, calls = coverage_client

    header_mismatch = client.get(
        "/api/v1/compliance/soc2/coverage",
        headers={"X-Tenant-ID": OTHER_TENANT_ID},
    )
    assert header_mismatch.status_code == 403
    assert header_mismatch.json()["detail"] == "Cross-tenant access denied"

    query_mismatch = client.get(
        "/api/v1/compliance/dashboard",
        params={"tenant_id": OTHER_TENANT_ID},
    )
    assert query_mismatch.status_code == 403
    assert query_mismatch.json()["detail"] == "Cross-tenant access denied"

    generalized_header_mismatch = client.get(
        "/api/v1/compliance/coverage",
        headers={"X-Tenant-ID": OTHER_TENANT_ID},
    )
    assert generalized_header_mismatch.status_code == 403
    assert generalized_header_mismatch.json()["detail"] == "Cross-tenant access denied"

    control_query_mismatch = client.get(
        "/api/v1/compliance/controls/CC6.1/status",
        params={"tenant_id": OTHER_TENANT_ID, "framework_id": "soc2"},
    )
    assert control_query_mismatch.status_code == 403
    assert control_query_mismatch.json()["detail"] == "Cross-tenant access denied"

    assert "loaded_tenants" not in calls
    assert "multi_coverage" not in calls
    assert "control_status" not in calls
