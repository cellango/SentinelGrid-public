from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import automation
from app.api.request_context import RequestContext, get_current_request_context


class AutomatedResponseServiceSpy:
    def __init__(self):
        self.risk_calls = []
        self.revoke_calls = []

    def process_risk_response(self, *args):
        self.risk_calls.append(args)
        return {
            "user_id": args[0],
            "tenant_id": args[4],
            "risk_score": args[1],
            "risk_level": args[2],
            "actions_taken": [],
            "anomalies_count": len(args[3]),
            "critical_anomalies_count": 0,
            "processed_at": datetime.now(timezone.utc),
            "auto_remediated": args[5],
        }

    def auto_revoke_suspicious_access(self, *args):
        self.revoke_calls.append(args)
        return {
            "user_id": args[0],
            "tenant_id": args[2],
            "action": "revoke_access",
            "dry_run": args[3],
            "revoked_roles": 0,
            "revoked_entitlements": 0,
            "results": [],
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }


class RemediationServiceSpy:
    def __init__(self):
        self.policy_calls = []
        self.stale_calls = []
        self.compliance_calls = []

    def remediate_policy_violations(self, *args):
        self.policy_calls.append(args)
        return {
            "tenant_id": args[1],
            "total_violations": len(args[0]),
            "remediated": 0,
            "failed": 0,
            "dry_run": args[2],
            "results": [],
            "processed_at": datetime.now(timezone.utc),
        }

    def cleanup_stale_access(self, *args):
        self.stale_calls.append(args)
        return {
            "tenant_id": args[1],
            "total_violations": 0,
            "remediated": 0,
            "failed": 0,
            "dry_run": args[2],
            "results": [],
            "processed_at": datetime.now(timezone.utc),
        }

    def remediate_compliance_issues(self, *args):
        self.compliance_calls.append(args)
        return {
            "tenant_id": args[1],
            "total_violations": len(args[0]),
            "remediated": 0,
            "failed": 0,
            "dry_run": args[2],
            "results": [],
            "processed_at": datetime.now(timezone.utc),
        }


class PredictiveServiceSpy:
    def __init__(self):
        self.calls = []

    def predict_access_patterns(self, *args):
        self.calls.append(("access_patterns", args))
        return {
            "confidence": 0.9,
            "generated_at": datetime.now(timezone.utc),
            "patterns": [],
        }


class WorkflowServiceSpy:
    def __init__(self):
        self.trigger_calls = []
        self.status_calls = []

    def trigger_soar_playbook(self, *args):
        self.trigger_calls.append(("soar_playbook", args))
        return {
            "execution_id": "exec-1",
            "status": "triggered",
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }

    def create_automated_approval_workflow(self, *args):
        self.trigger_calls.append(("approval_workflow", args))
        return {
            "execution_id": "exec-2",
            "status": "triggered",
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }

    def execute_remediation_workflow(self, *args):
        self.trigger_calls.append(("remediation_workflow", args))
        return {
            "execution_id": "exec-3",
            "status": "triggered",
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }

    def create_risk_response_playbook(self, *args):
        self.trigger_calls.append(("risk_response", args))
        return {
            "execution_id": "exec-4",
            "status": "triggered",
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_workflow_status(self, execution_id):
        self.status_calls.append(execution_id)
        return {"execution_id": execution_id, "status": "running"}


@pytest.fixture
def request_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id=str(uuid4()),
    )


@pytest.fixture
def automation_test_app(request_context):
    app = FastAPI()
    app.include_router(automation.router)
    app.dependency_overrides[get_current_request_context] = lambda: request_context
    return app


@pytest.fixture
def automation_client(automation_test_app):
    return TestClient(automation_test_app)


def _override_dependency(app, dependency, value):
    app.dependency_overrides[dependency] = lambda: value


def test_risk_response_rejects_foreign_body_tenant(
    automation_test_app,
    automation_client,
):
    service = AutomatedResponseServiceSpy()
    _override_dependency(
        automation_test_app,
        automation.get_automated_response_service,
        service,
    )

    response = automation_client.post(
        "/internal/iam/automation/risk-response",
        headers={"authorization": "Bearer test-token"},
        json={
            "user_id": "user-1",
            "risk_score": 90,
            "risk_level": "high",
            "anomalies": [],
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert service.risk_calls == []


def test_revoke_suspicious_access_rejects_foreign_query_tenant(
    automation_test_app,
    automation_client,
):
    service = AutomatedResponseServiceSpy()
    _override_dependency(
        automation_test_app,
        automation.get_automated_response_service,
        service,
    )

    response = automation_client.request(
        "POST",
        "/internal/iam/automation/revoke-suspicious-access",
        headers={"authorization": "Bearer test-token"},
        params={
            "user_id": "user-1",
            "tenant_id": str(uuid4()),
        },
        json=[{"type": "privilege_escalation"}],
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert service.revoke_calls == []


def test_remediate_rejects_foreign_body_tenant(
    automation_test_app,
    automation_client,
):
    service = RemediationServiceSpy()
    _override_dependency(
        automation_test_app,
        automation.get_remediation_service,
        service,
    )

    response = automation_client.post(
        "/internal/iam/automation/remediate",
        headers={"authorization": "Bearer test-token"},
        json={
            "violation_type": "policy_violations",
            "violations": [],
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert service.policy_calls == []


def test_predict_rejects_foreign_body_tenant(
    automation_test_app,
    automation_client,
):
    service = PredictiveServiceSpy()
    _override_dependency(
        automation_test_app,
        automation.get_predictive_service,
        service,
    )

    response = automation_client.post(
        "/internal/iam/automation/predict",
        headers={"authorization": "Bearer test-token"},
        json={
            "prediction_type": "access_patterns",
            "user_id": "user-1",
            "tenant_id": str(uuid4()),
            "data": {"access_history": []},
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert service.calls == []


def test_trigger_workflow_uses_authenticated_tenant_when_body_omits_one(
    automation_test_app,
    automation_client,
    request_context,
):
    service = WorkflowServiceSpy()
    _override_dependency(
        automation_test_app,
        automation.get_workflow_service,
        service,
    )

    response = automation_client.post(
        "/internal/iam/automation/workflow/trigger",
        headers={"authorization": "Bearer test-token"},
        json={
            "workflow_type": "soar_playbook",
            "workflow_id": "playbook-1",
            "data": {"severity": "high"},
        },
    )

    assert response.status_code == 200
    assert service.trigger_calls[0][1][2] == str(request_context.tenant_id)
    assert response.json()["execution_id"] == "exec-1"


def test_workflow_status_requires_authenticated_boundary(
    automation_test_app,
    automation_client,
):
    service = WorkflowServiceSpy()
    _override_dependency(
        automation_test_app,
        automation.get_workflow_service,
        service,
    )

    response = automation_client.get(
        "/internal/iam/automation/workflow/exec-1/status",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"execution_id": "exec-1", "status": "running"}
    assert service.status_calls == ["exec-1"]
