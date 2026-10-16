from datetime import datetime, timezone
from uuid import uuid4

from sg_core.models import Alert, Incident, Tenant


class _QueryResult:
    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


def test_ai_shield_ingest_creates_alert_and_incident(client, mock_db_session):
    tenant_uuid = uuid4()
    added = []

    mock_db_session.add.side_effect = lambda obj: added.append(obj)
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.side_effect = lambda obj: None

    def query_side_effect(model):
        if model is Alert:
            return _QueryResult(None)
        if model is Incident:
            return _QueryResult(None)
        if model is Tenant:
            return _QueryResult(
                Tenant(
                    id=tenant_uuid,
                    name="Acme",
                    slug="acme",
                    status="active",
                    incident_management_mode="saas_managed",
                )
            )
        raise AssertionError(f"Unexpected model query: {model}")

    mock_db_session.query.side_effect = query_side_effect

    response = client.post(
        "/api/v1/internal/ai-shield/events",
        headers={
            "Authorization": "Bearer internal-service-token-change-in-production",
            "X-Tenant-ID": str(tenant_uuid),
        },
        json={
            "event_id": "evt-123",
            "org_id": str(tenant_uuid),
            "ai_app_id": "support-assistant",
            "user_id": "owner@example.com",
            "provider": "openai",
            "model": "gpt-4.1",
            "prompt_injection_suspected": True,
            "policy_decision": "blocked",
            "created_at": "2026-03-26T18:15:00Z",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "created"
    assert data["alert"]["title"] == "Prompt injection attempt detected in support-assistant"
    assert "ai" in data["alert"]["story_domains"]
    assert data["alert"]["raw_payload"]["source_label"] == "AI Shield"
    assert data["alert"]["raw_payload"]["sg"]["playbook_id"] == "AI-PROMPT-INJECTION"
    assert data["incident"] is not None
    assert "ai" in data["incident"]["story_domains"]
    assert data["incident"]["timeline"][0]["text"] == "Incident created from AI Shield alert"
    assert any(isinstance(item, Alert) for item in added)
    assert any(isinstance(item, Incident) for item in added)


def test_ai_shield_ingest_returns_duplicate_for_existing_alert(client, mock_db_session):
    tenant_uuid = uuid4()
    incident = Incident(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="sentinelgrid_ai_shield",
        title="Prompt injection attempt detected in support-assistant",
        status="open",
        severity="high",
        raw_payload={
            "audit": [
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "text": "Incident created from AI Shield alert",
                    "actor": "system",
                }
            ],
            "category": "ai",
            "ai": {"app_id": "support-assistant"},
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    existing_alert = Alert(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="sentinelgrid_ai_shield",
        external_id="evt-dup",
        title="Prompt injection attempt detected in support-assistant",
        description="AI Shield flagged a suspected prompt injection or jailbreak attempt against support-assistant. Review the request path, user context, and downstream tool exposure.",
        raw_severity="high",
        status="open",
        detection_time=datetime.now(timezone.utc),
        asset_id="support-assistant",
        user_identifier="owner@example.com",
        raw_payload={
            "incident_id": str(incident.id),
            "category": "ai",
            "source_label": "AI Shield",
            "ai": {
                "app_id": "support-assistant",
                "provider": "openai",
                "model": "gpt-4.1",
                "user_id": "owner@example.com",
            },
            "sg": {
                "category": "ai",
                "detection_rule_id": "SG-AI-002",
                "playbook_id": "AI-PROMPT-INJECTION",
            },
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    def query_side_effect(model):
        if model is Alert:
            return _QueryResult(existing_alert)
        if model is Incident:
            return _QueryResult(incident)
        if model is Tenant:
            return _QueryResult(None)
        raise AssertionError(f"Unexpected model query: {model}")

    mock_db_session.query.side_effect = query_side_effect

    response = client.post(
        "/api/v1/internal/ai-shield/events",
        headers={
            "Authorization": "Bearer internal-service-token-change-in-production",
            "X-Tenant-ID": str(tenant_uuid),
        },
        json={
            "event_id": "evt-dup",
            "org_id": str(tenant_uuid),
            "ai_app_id": "support-assistant",
            "user_id": "owner@example.com",
            "provider": "openai",
            "model": "gpt-4.1",
            "prompt_injection_suspected": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "duplicate"
    assert data["alert"]["id"] == str(existing_alert.id)
    assert data["incident"]["id"] == str(incident.id)
    mock_db_session.add.assert_not_called()


def test_ai_shield_ingest_skips_low_signal_event(client, mock_db_session):
    response = client.post(
        "/api/v1/internal/ai-shield/events",
        headers={
            "Authorization": "Bearer internal-service-token-change-in-production",
            "X-Tenant-ID": str(uuid4()),
        },
        json={
            "event_id": "evt-low",
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "policy_decision": "allowed",
            "has_pii": False,
            "has_secrets": False,
            "prompt_injection_suspected": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "skipped"
    mock_db_session.query.assert_not_called()
    mock_db_session.add.assert_not_called()


def test_ai_shield_ingest_rejects_mismatched_org_id(client, mock_db_session):
    tenant_uuid = uuid4()

    response = client.post(
        "/api/v1/internal/ai-shield/events",
        headers={
            "Authorization": "Bearer internal-service-token-change-in-production",
            "X-Tenant-ID": str(tenant_uuid),
        },
        json={
            "event_id": "evt-mismatch",
            "org_id": str(uuid4()),
            "ai_app_id": "support-assistant",
            "provider": "openai",
            "model": "gpt-4.1",
            "prompt_injection_suspected": True,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant ID mismatch. You can only access your own tenant's data."
    mock_db_session.query.assert_not_called()
    mock_db_session.add.assert_not_called()
