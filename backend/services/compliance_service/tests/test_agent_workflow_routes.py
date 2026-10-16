from pathlib import Path
import os
import sys

from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

os.environ.setdefault("DB_HOST", "localhost")

from app.main import app
from app.api import agent_workflow
from sg_core.service_metrics import get_service_metrics, reset_service_metrics


TENANT_ID = "00000000-0000-0000-0000-000000000111"


class FakeRepository:
    def __init__(self):
        self.list_call = None
        self.decision_call = None

    def list_recommendations(self, db, tenant_id, **filters):
        self.list_call = {"db": db, "tenant_id": tenant_id, "filters": filters}
        return {
            "tenant_id": tenant_id,
            "items": [{"id": "rec-1", "state": "proposed", "trigger_type": "framework_selected"}],
            "count": 1,
            "limit": filters["limit"],
            "offset": filters["offset"],
        }

    def record_decision(self, db, **kwargs):
        self.decision_call = {"db": db, "kwargs": kwargs}
        return {
            "id": kwargs["recommendation_id"],
            "tenant_id": kwargs["tenant_id"],
            "state": kwargs["state"],
            "trigger_type": "control_gap",
            "decided_by": kwargs["decided_by"],
            "decision_notes": kwargs["decision_notes"],
        }


def test_agent_recommendation_routes_list_and_record_decisions():
    fake_db = object()
    repository = FakeRepository()

    def override_tenant_session():
        yield fake_db

    app.dependency_overrides[agent_workflow.get_current_tenant] = lambda: TENANT_ID
    app.dependency_overrides[agent_workflow.get_current_payload] = lambda: {
        "tenant_id": TENANT_ID,
        "user_id": "user-123",
        "roles": ["compliance_officer"],
    }
    app.dependency_overrides[agent_workflow.get_tenant_session] = override_tenant_session
    app.dependency_overrides[agent_workflow.get_recommendation_repository] = lambda: repository

    try:
        with TestClient(app) as client:
            list_response = client.get(
                "/api/v1/compliance/agent/recommendations",
                params={"state": "proposed", "limit": 25},
            )
            decision_response = client.post(
                "/api/v1/compliance/agent/recommendations/rec-1/decision",
                json={"state": "accepted", "decision_notes": "Approved for follow-up."},
            )
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == "rec-1"
    assert repository.list_call["tenant_id"] == TENANT_ID
    assert repository.list_call["filters"]["state"] == "proposed"
    assert repository.list_call["filters"]["limit"] == 25

    assert decision_response.status_code == 200
    assert decision_response.json()["state"] == "accepted"
    assert repository.decision_call["kwargs"]["tenant_id"] == TENANT_ID
    assert repository.decision_call["kwargs"]["decided_by"] == "user-123"
    assert repository.decision_call["kwargs"]["decision_notes"] == "Approved for follow-up."


def test_agent_recommendation_decision_role_matrix():
    reset_service_metrics("compliance-service")
    fake_db = object()
    repository = FakeRepository()

    def override_tenant_session():
        yield fake_db

    app.dependency_overrides[agent_workflow.get_current_tenant] = lambda: TENANT_ID
    app.dependency_overrides[agent_workflow.get_tenant_session] = override_tenant_session
    app.dependency_overrides[agent_workflow.get_recommendation_repository] = lambda: repository

    try:
        with TestClient(app) as client:
            for role, expected_status in [
                ("compliance_viewer", 403),
                ("compliance_manager", 200),
                ("evidence_reviewer", 200),
                ("admin", 200),
            ]:
                repository.decision_call = None
                app.dependency_overrides[agent_workflow.get_current_payload] = lambda role=role: {
                    "tenant_id": TENANT_ID,
                    "user_id": f"{role}-user",
                    "roles": [role],
                }
                response = client.post(
                    f"/api/v1/compliance/agent/recommendations/rec-{role}/decision",
                    json={"state": "accepted", "decision_notes": f"decision by {role}"},
                )

                assert response.status_code == expected_status
                if expected_status == 200:
                    assert repository.decision_call["kwargs"]["tenant_id"] == TENANT_ID
                    assert repository.decision_call["kwargs"]["decided_by"] == f"{role}-user"
                else:
                    assert repository.decision_call is None
    finally:
        app.dependency_overrides.clear()

    metrics = get_service_metrics("compliance-service").snapshot()
    assert metrics["counters"]["compliance_agent_recommendation_decisions_total"]["series"][
        "state=accepted,trigger_type=control_gap"
    ] == 3
