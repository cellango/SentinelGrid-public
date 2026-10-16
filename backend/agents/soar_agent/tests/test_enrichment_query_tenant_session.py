"""Focused tenant-scoped DB coverage for SOAR enrichment query-tenant routes."""

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.api import enrichment, phishing_containment


def test_enrichment_and_phishing_routes_use_query_tenant_session(monkeypatch):
    """Query-tenant SOAR routes should open tenant-scoped sessions from tenant_id."""
    calls = {"enrichment": 0, "phishing": 0}

    def override_enrichment_session():
        calls["enrichment"] += 1
        yield object()

    def override_phishing_session():
        calls["phishing"] += 1
        yield object()

    def make_enrichment(ticket_id, tenant_id, enrichment_type):
        return SimpleNamespace(
            id=uuid4(),
            ticket_id=ticket_id,
            enrichment_type=enrichment_type,
            model_name="sentinelgrid-enrichment",
            model_version="1.0",
            content={"tenant_id": str(tenant_id)},
            created_at=datetime(2026, 3, 28, 12, 0, 0),
            updated_at=datetime(2026, 3, 28, 12, 1, 0),
        )

    async def fake_enrich_ticket(db, ticket_id, tenant_id, enrichment_type):
        return make_enrichment(ticket_id, tenant_id, enrichment_type)

    def fake_get_enrichment(db, ticket_id, tenant_id):
        return make_enrichment(ticket_id, tenant_id, "all")

    async def fake_execute_playbook(self, tenant_id, phishing_report_id, context):
        return {"status": "completed", "tenant_id": str(tenant_id), "phishing_report_id": str(phishing_report_id)}

    monkeypatch.setattr(enrichment.enrichment_service, "enrich_ticket", fake_enrich_ticket)
    monkeypatch.setattr(enrichment.enrichment_service, "get_enrichment", fake_get_enrichment)
    monkeypatch.setattr(phishing_containment.PhishingContainmentPlaybook, "execute", fake_execute_playbook)

    app.dependency_overrides[enrichment.get_query_tenant_session] = override_enrichment_session
    app.dependency_overrides[phishing_containment.get_query_tenant_session] = override_phishing_session

    try:
        client = TestClient(app)
        tenant_id = str(uuid4())
        ticket_id = str(uuid4())
        report_id = str(uuid4())

        response = client.post(
            f"/api/v1/enrichment/ticket/{ticket_id}",
            params={"tenant_id": tenant_id, "enrichment_type": "all"},
        )
        assert response.status_code == 200

        response = client.get(
            f"/api/v1/enrichment/ticket/{ticket_id}",
            params={"tenant_id": tenant_id},
        )
        assert response.status_code == 200

        response = client.post(
            "/api/v1/playbooks/phishing-containment/execute",
            params={"tenant_id": tenant_id},
            json={"phishing_report_id": report_id},
        )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()

    assert calls == {"enrichment": 2, "phishing": 1}
