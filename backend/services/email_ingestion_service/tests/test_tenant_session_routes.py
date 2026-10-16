"""Focused tenant-session coverage for email-ingestion routes."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import main as email_main
from app.api import containment as containment_api
from app.api import phishing as phishing_api
from app.core import database as email_database


class FakeDB:
    """Minimal DB stub for route tests."""

    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


def _make_report(tenant_id: str, report_id: str | None = None):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4() if report_id is None else report_id,
        tenant_id=tenant_id,
        message_id=f"<{uuid4()}@example.com>",
        subject="Urgent: Verify Your Account",
        from_address="attacker@example.com",
        to_address="victim@example.com",
        reply_to=None,
        received_date=now,
        reported_by="analyst@example.com",
        raw_email="raw email",
        html_body="<p>body</p>",
        text_body="body",
        attachments={},
        classification=None,
        classification_confidence=None,
        classified_by=None,
        classified_at=None,
        ai_analysis=None,
        ai_summary=None,
        ai_recommended_actions=None,
        mitre_tactics=[],
        mitre_techniques=[],
        nist_controls=[],
        status="new",
        severity=None,
        assigned_to=None,
        ticket_id=None,
        incident_id=None,
        similar_emails=[],
        timeline_data=[],
        created_at=now,
        updated_at=now,
    )


def _make_observable(tenant_id: str, report_id):
    return SimpleNamespace(
        id=uuid4(),
        tenant_id=tenant_id,
        phishing_report_id=report_id,
        observable_type="domain",
        observable_value="example.com",
        observable_context="Email content",
        threat_intel=None,
        reputation_score=None,
        is_malicious=False,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def tenant_scoped_client(monkeypatch):
    """Create a client that requires query-tenant session usage."""
    fake_db = FakeDB()

    def unexpected_get_db():
        raise AssertionError("Route used get_db instead of get_query_tenant_session")
        yield  # pragma: no cover

    def override_get_query_tenant_session():
        yield fake_db

    monkeypatch.setattr(email_main, "init_db", lambda: None)
    email_main.app.dependency_overrides[email_database.get_db] = unexpected_get_db
    email_main.app.dependency_overrides[email_database.get_query_tenant_session] = (
        override_get_query_tenant_session
    )

    try:
        with TestClient(email_main.app) as client:
            yield client, fake_db
    finally:
        email_main.app.dependency_overrides.clear()


def test_phishing_routes_use_query_tenant_session(monkeypatch, tenant_scoped_client):
    client, fake_db = tenant_scoped_client
    tenant_id = str(uuid4())
    report = _make_report(tenant_id)
    observable = _make_observable(tenant_id, report.id)

    class FakeParser:
        def parse(self, raw_email):
            return {
                "message_id": report.message_id,
                "subject": report.subject,
                "from_address": report.from_address,
                "to_address": report.to_address,
                "reply_to": report.reply_to,
                "received_date": report.received_date,
                "reported_by": report.reported_by,
                "html_body": report.html_body,
                "text_body": report.text_body,
                "attachments": {},
            }

        def extract_urls(self, _html_body, _text_body):
            return []

        def extract_domains(self, _urls, _senders):
            return []

        def extract_ips(self, _text_body):
            return []

        def extract_emails(self, _text_body):
            return []

    class FakePhishingService:
        def __init__(self, db):
            assert db is fake_db
            self.db = db

        def create_report(self, tenant, report_data):
            assert str(tenant) == tenant_id
            return report

        def add_observable(self, tenant, report_id, observable_data):
            assert str(tenant) == tenant_id
            assert report_id == report.id
            return observable

        def list_reports(self, tenant, status, classification, limit, offset):
            assert str(tenant) == tenant_id
            return [report]

        def get_report(self, tenant, report_id):
            assert str(tenant) == tenant_id
            assert report_id == report.id
            return report

        def get_observables(self, tenant, report_id):
            assert str(tenant) == tenant_id
            assert report_id == report.id
            return [observable]

        def update_report(self, tenant, report_id, update_data):
            assert str(tenant) == tenant_id
            assert report_id == report.id
            report.status = update_data.status or report.status
            return report

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return SimpleNamespace(raise_for_status=lambda: None)

    monkeypatch.setattr(phishing_api, "EmailParser", FakeParser)
    monkeypatch.setattr(phishing_api, "PhishingService", FakePhishingService)
    monkeypatch.setattr(phishing_api.httpx, "AsyncClient", lambda *args, **kwargs: FakeAsyncClient())
    monkeypatch.setattr(phishing_api, "_trigger_classification_async", lambda *args, **kwargs: None)

    def consume_task(coro):
        if hasattr(coro, "close"):
            coro.close()
        return None

    monkeypatch.setattr(phishing_api.asyncio, "create_task", consume_task)

    ingest_response = client.post(
        f"/api/v1/phishing/ingest?tenant_id={tenant_id}",
        params={"raw_email": "From: attacker@example.com"},
    )
    assert ingest_response.status_code == 201

    list_response = client.get(f"/api/v1/phishing/reports?tenant_id={tenant_id}")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/api/v1/phishing/reports/{report.id}?tenant_id={tenant_id}")
    assert get_response.status_code == 200

    observables_response = client.get(
        f"/api/v1/phishing/reports/{report.id}/observables?tenant_id={tenant_id}"
    )
    assert observables_response.status_code == 200
    assert len(observables_response.json()) == 1

    classify_response = client.post(
        f"/api/v1/phishing/reports/{report.id}/classify?tenant_id={tenant_id}"
    )
    assert classify_response.status_code == 200

    update_response = client.put(
        f"/api/v1/phishing/reports/{report.id}?tenant_id={tenant_id}",
        json={"status": "resolved"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "resolved"


def test_containment_routes_use_query_tenant_session(monkeypatch, tenant_scoped_client):
    client, fake_db = tenant_scoped_client
    tenant_id = str(uuid4())
    report = _make_report(tenant_id)
    observable = _make_observable(tenant_id, report.id)

    class FakePhishingService:
        def __init__(self, db):
            assert db is fake_db
            self.db = db

        def get_report(self, tenant, report_id):
            assert str(tenant) == tenant_id
            assert report_id == report.id
            return report

        def get_observables(self, tenant, report_id):
            assert str(tenant) == tenant_id
            assert report_id == report.id
            return [observable]

    class FakeEmailSearchService:
        async def search_similar_emails(self, tenant, search_criteria, provider):
            assert tenant == tenant_id
            return [{"id": "email-1", "subject": "Urgent"}]

    class FakeEmailDeletionService:
        async def delete_emails(self, tenant, email_ids, provider, action):
            assert tenant == tenant_id
            return {"success_count": len(email_ids), "failure_count": 0}

    monkeypatch.setattr(containment_api, "PhishingService", FakePhishingService)
    monkeypatch.setattr(containment_api, "EmailSearchService", FakeEmailSearchService)
    monkeypatch.setattr(containment_api, "EmailDeletionService", FakeEmailDeletionService)
    monkeypatch.setattr(
        containment_api,
        "logger",
        SimpleNamespace(info=lambda *args, **kwargs: None),
        raising=False,
    )

    search_response = client.post(
        f"/api/v1/phishing/reports/{report.id}/search-similar?tenant_id={tenant_id}",
        json={"provider": "microsoft_graph"},
    )
    assert search_response.status_code == 200
    assert search_response.json()["count"] == 1

    delete_response = client.post(
        f"/api/v1/phishing/reports/{report.id}/delete-similar?tenant_id={tenant_id}",
        json={"email_ids": ["email-1"], "provider": "microsoft_graph", "action": "delete"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["success_count"] == 1

    playbook_response = client.post(
        f"/api/v1/phishing/reports/{report.id}/run-containment-playbook?tenant_id={tenant_id}",
        json={
            "quarantine_emails": True,
            "block_domains": True,
            "create_ticket": False,
            "notify_users": False,
        },
    )
    assert playbook_response.status_code == 200
    assert playbook_response.json()["status"] == "completed"
    assert fake_db.commits >= 2
