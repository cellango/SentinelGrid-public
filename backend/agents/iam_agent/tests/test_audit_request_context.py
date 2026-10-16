from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import audit
from app.api.request_context import RequestContext, get_current_request_context


class AuditServiceSpy:
    def __init__(self):
        self.log_calls = []
        self.log_query_calls = []
        self.review_calls = []
        self.complete_calls = []
        self.analysis_calls = []
        self.statistics_calls = []
        self.export_calls = []

    def log_audit_event(self, **kwargs):
        self.log_calls.append(kwargs)
        return {
            "event_id": "evt-1",
            "event_type": kwargs["event_type"],
            "timestamp": datetime.now(timezone.utc),
            "actor": {"actor_id": kwargs["actor_id"]},
            "action": kwargs["action"],
            "outcome": kwargs["outcome"],
            "severity": kwargs["severity"],
        }

    def get_audit_logs(self, **kwargs):
        self.log_query_calls.append(kwargs)
        return {
            "logs": [],
            "total": 0,
            "limit": kwargs["limit"],
            "offset": kwargs["offset"],
            "filters": {"tenant_id": kwargs["tenant_id"]},
        }

    def create_audit_review(self, **kwargs):
        self.review_calls.append(kwargs)
        return {
            "review_id": "rev-1",
            "review_name": kwargs["review_name"],
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "due_date": None,
        }

    def perform_audit_review(self, **kwargs):
        self.complete_calls.append(kwargs)
        return {
            "review_id": kwargs["review_id"],
            "reviewer_id": kwargs["reviewer_id"],
            "status": "completed",
        }

    def analyze_audit_patterns(self, **kwargs):
        self.analysis_calls.append(kwargs)
        return {
            "tenant_id": kwargs["tenant_id"],
            "analysis_period": {"start": "", "end": ""},
            "total_events": 0,
            "patterns": {},
            "generated_at": datetime.now(timezone.utc),
        }

    def get_audit_statistics(self, **kwargs):
        self.statistics_calls.append(kwargs)
        return {
            "tenant_id": kwargs["tenant_id"],
            "total_events": 0,
            "time_window_days": kwargs["time_window_days"],
        }

    def export_audit_logs(self, **kwargs):
        self.export_calls.append(kwargs)
        return {
            "tenant_id": kwargs["tenant_id"],
            "export_format": kwargs["export_format"],
            "status": "queued",
        }


@pytest.fixture
def request_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id="authenticated-reviewer",
    )


@pytest.fixture
def audit_test_app(request_context):
    app = FastAPI()
    app.include_router(audit.router)
    app.dependency_overrides[get_current_request_context] = lambda: request_context
    return app


@pytest.fixture
def audit_client(audit_test_app):
    return TestClient(audit_test_app)


def _override_audit_service(app, audit_service):
    app.dependency_overrides[audit.get_audit_service] = lambda: audit_service


def test_log_event_rejects_foreign_body_tenant(
    audit_test_app,
    audit_client,
):
    audit_service = AuditServiceSpy()
    _override_audit_service(audit_test_app, audit_service)

    response = audit_client.post(
        "/internal/iam/audit/events",
        headers={"authorization": "Bearer test-token"},
        json={
            "event_type": "authentication",
            "actor_id": "user-1",
            "action": "login",
            "severity": "medium",
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert audit_service.log_calls == []


def test_get_audit_logs_defaults_to_authenticated_tenant(
    audit_test_app,
    audit_client,
    request_context,
):
    audit_service = AuditServiceSpy()
    _override_audit_service(audit_test_app, audit_service)

    response = audit_client.get(
        "/internal/iam/audit/logs",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert audit_service.log_query_calls[0]["tenant_id"] == str(request_context.tenant_id)
    assert response.json()["filters"]["tenant_id"] == str(request_context.tenant_id)


def test_create_review_rejects_foreign_body_tenant(
    audit_test_app,
    audit_client,
):
    audit_service = AuditServiceSpy()
    _override_audit_service(audit_test_app, audit_service)

    response = audit_client.post(
        "/internal/iam/audit/reviews",
        headers={"authorization": "Bearer test-token"},
        json={
            "review_name": "Quarterly IAM Review",
            "scope": {"type": "quarterly"},
            "reviewer_id": "reviewer-1",
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert audit_service.review_calls == []


def test_complete_review_uses_authenticated_request_user(
    audit_test_app,
    audit_client,
):
    audit_service = AuditServiceSpy()
    _override_audit_service(audit_test_app, audit_service)

    response = audit_client.post(
        "/internal/iam/audit/reviews/rev-1/complete",
        headers={"authorization": "Bearer test-token"},
        params={
            "reviewer_id": "caller-supplied-reviewer",
            "conclusion": "approved",
        },
        json=[{"finding_id": "f-1"}],
    )

    assert response.status_code == 200
    assert audit_service.complete_calls[0]["reviewer_id"] == "authenticated-reviewer"
    assert response.json()["reviewer_id"] == "authenticated-reviewer"


def test_analysis_rejects_foreign_query_tenant(
    audit_test_app,
    audit_client,
):
    audit_service = AuditServiceSpy()
    _override_audit_service(audit_test_app, audit_service)

    response = audit_client.get(
        f"/internal/iam/audit/analysis?tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert audit_service.analysis_calls == []


def test_statistics_defaults_to_authenticated_tenant(
    audit_test_app,
    audit_client,
    request_context,
):
    audit_service = AuditServiceSpy()
    _override_audit_service(audit_test_app, audit_service)

    response = audit_client.get(
        "/internal/iam/audit/statistics",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert audit_service.statistics_calls[0]["tenant_id"] == str(request_context.tenant_id)
    assert response.json()["tenant_id"] == str(request_context.tenant_id)


def test_export_rejects_foreign_query_tenant(
    audit_test_app,
    audit_client,
):
    audit_service = AuditServiceSpy()
    _override_audit_service(audit_test_app, audit_service)

    response = audit_client.post(
        f"/internal/iam/audit/export?tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert audit_service.export_calls == []
