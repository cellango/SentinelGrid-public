from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import compliance
from app.api.request_context import RequestContext, get_current_request_context


class NistServiceSpy:
    def __init__(self):
        self.categories = []
        self.control_ids = []

    def get_iam_controls(self, category=None):
        self.categories.append(category)
        return [{"control_id": "AC-1", "title": "Access Control Policy"}]

    def get_control(self, control_id):
        self.control_ids.append(control_id)
        return {"control_id": control_id, "title": "Control"}


class ComplianceServiceSpy:
    def __init__(self):
        self.status_calls = []
        self.gap_calls = []
        self.report_calls = []
        self.record_calls = []

    def track_compliance_status(self, tenant_id, control_ids=None):
        self.status_calls.append((tenant_id, control_ids))
        return {
            "tenant_id": tenant_id,
            "overall_compliance_score": 82.5,
            "total_controls": 1,
            "status_breakdown": {"compliant": 1},
            "compliant_count": 1,
            "partially_compliant_count": 0,
            "non_compliant_count": 0,
            "not_assessed_count": 0,
            "controls": [{"control_id": "AC-1", "status": "compliant"}],
            "assessed_at": datetime.now(timezone.utc),
        }

    def get_compliance_gaps(self, tenant_id, category=None):
        self.gap_calls.append((tenant_id, category))
        return [{"control_id": "AC-2", "priority": "high"}]

    def generate_compliance_report(
        self,
        tenant_id,
        report_type,
        category=None,
        start_date=None,
        end_date=None,
    ):
        self.report_calls.append((tenant_id, report_type, category, start_date, end_date))
        return {
            "tenant_id": tenant_id,
            "report_period": {"start": "", "end": ""},
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {"score": 82.5},
        }

    def record_evidence(self, control_id, evidence, tenant_id):
        self.record_calls.append((control_id, evidence, tenant_id))
        return {
            "control_id": control_id,
            "assessment": {"status": "recorded"},
            "evidence_recorded_at": datetime.now(timezone.utc),
            "tenant_id": tenant_id,
        }


class EvidenceServiceSpy:
    def __init__(self):
        self.calls = []

    def collect_control_evidence(self, control_id, evidence_types, tenant_id, repository_client=None, actor_id=None):
        self.calls.append((control_id, evidence_types, tenant_id, repository_client, actor_id))
        return {
            "control_id": control_id,
            "tenant_id": tenant_id,
            "evidence": {"count": len(evidence_types)},
            "repository": {"status": "completed"},
            "collected_at": datetime.now(timezone.utc),
        }


@pytest.fixture
def request_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id=str(uuid4()),
    )


@pytest.fixture
def compliance_test_app(request_context):
    app = FastAPI()
    app.include_router(compliance.router)
    app.dependency_overrides[get_current_request_context] = lambda: request_context
    return app


@pytest.fixture
def compliance_client(compliance_test_app):
    return TestClient(compliance_test_app)


def _override_dependency(app, dependency, value):
    app.dependency_overrides[dependency] = lambda: value


def test_controls_route_uses_request_context_dependency(
    compliance_test_app,
    compliance_client,
):
    nist_service = NistServiceSpy()
    _override_dependency(compliance_test_app, compliance.get_nist_service, nist_service)

    response = compliance_client.get(
        "/internal/iam/compliance/controls",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json()["total_count"] == 1
    assert nist_service.categories == [None]


def test_status_rejects_foreign_query_tenant(
    compliance_test_app,
    compliance_client,
):
    compliance_service = ComplianceServiceSpy()
    _override_dependency(
        compliance_test_app, compliance.get_compliance_service, compliance_service
    )

    response = compliance_client.get(
        f"/internal/iam/compliance/status?tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert compliance_service.status_calls == []


def test_status_defaults_to_authenticated_tenant(
    compliance_test_app,
    compliance_client,
    request_context,
):
    compliance_service = ComplianceServiceSpy()
    _override_dependency(
        compliance_test_app, compliance.get_compliance_service, compliance_service
    )

    response = compliance_client.get(
        "/internal/iam/compliance/status",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert compliance_service.status_calls == [(str(request_context.tenant_id), None)]
    assert response.json()["tenant_id"] == str(request_context.tenant_id)


def test_generate_report_rejects_foreign_body_tenant(
    compliance_test_app,
    compliance_client,
):
    compliance_service = ComplianceServiceSpy()
    _override_dependency(
        compliance_test_app, compliance.get_compliance_service, compliance_service
    )

    response = compliance_client.post(
        "/internal/iam/compliance/reports",
        headers={"authorization": "Bearer test-token"},
        json={
            "tenant_id": str(uuid4()),
            "report_type": "summary",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert compliance_service.report_calls == []


def test_collect_evidence_uses_authenticated_tenant_when_body_omits_one(
    compliance_test_app,
    compliance_client,
    request_context,
):
    evidence_service = EvidenceServiceSpy()
    _override_dependency(compliance_test_app, compliance.get_evidence_service, evidence_service)

    response = compliance_client.post(
        "/internal/iam/compliance/evidence/collect",
        headers={"authorization": "Bearer test-token"},
        json={
            "control_id": "AC-1",
            "evidence_types": ["configuration", "audit_log"],
        },
    )

    assert response.status_code == 200
    assert evidence_service.calls
    assert evidence_service.calls[0][2] == str(request_context.tenant_id)
    assert evidence_service.calls[0][3].tenant_id == str(request_context.tenant_id)
    assert evidence_service.calls[0][4] == request_context.user_id
    assert response.json()["tenant_id"] == str(request_context.tenant_id)
    assert response.json()["repository"]["status"] == "completed"


def test_get_control_evidence_rejects_foreign_query_tenant(
    compliance_test_app,
    compliance_client,
):
    evidence_service = EvidenceServiceSpy()
    _override_dependency(compliance_test_app, compliance.get_evidence_service, evidence_service)

    response = compliance_client.get(
        f"/internal/iam/compliance/evidence/AC-1?tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert evidence_service.calls == []
