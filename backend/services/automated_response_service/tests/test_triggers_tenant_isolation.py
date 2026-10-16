"""Focused tenant-isolation coverage for automated-response trigger routes."""

from pathlib import Path
import os
import sys
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

os.environ.setdefault("DB_HOST", "localhost")

from app.main import app
from app.api import triggers as triggers_api
from app.core.database import get_current_tenant, get_tenant_session


TENANT_ID = "00000000-0000-0000-0000-000000000111"


@pytest.fixture
def client():
    def override_get_current_tenant():
        return TENANT_ID

    def override_get_tenant_session():
        yield object()

    app.dependency_overrides[get_current_tenant] = override_get_current_tenant
    app.dependency_overrides[get_tenant_session] = override_get_tenant_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_evaluate_alert_triggers_uses_authenticated_tenant(client, monkeypatch):
    alert_id = "00000000-0000-0000-0000-000000000001"
    observed = {}

    class DummyTriggerEngine:
        def __init__(self, db):
            observed["db"] = db

        def evaluate_alert(self, incoming_alert_id, tenant_id):
            observed["call"] = (str(incoming_alert_id), str(tenant_id))
            return [{"playbook_id": "pb-1", "playbook_name": "Test", "trigger_reason": "matched", "priority": 10}]

    monkeypatch.setattr(triggers_api, "PlaybookTriggerEngine", DummyTriggerEngine)

    response = client.post(f"/api/v1/automated-response/alerts/{alert_id}/evaluate")

    assert response.status_code == 200
    assert observed["call"] == (alert_id, TENANT_ID)
    assert response.json()["total_matched"] == 1


def test_trigger_playbook_for_alert_uses_authenticated_tenant(client, monkeypatch):
    alert_id = "00000000-0000-0000-0000-000000000002"
    playbook_id = "00000000-0000-0000-0000-000000000099"
    observed = {}

    class DummyOrchestrator:
        def __init__(self, db):
            observed["db"] = db

        async def trigger_playbook(self, playbook_id, alert_id, tenant_id, trigger_reason):
            observed["call"] = (
                str(playbook_id),
                str(alert_id),
                str(tenant_id),
                trigger_reason,
            )
            return {
                "trigger_id": "trigger-1",
                "execution_id": "exec-1",
                "status": "queued",
                "trigger_reason": trigger_reason,
            }

    monkeypatch.setattr(triggers_api, "PlaybookOrchestrator", DummyOrchestrator)

    response = client.post(
        f"/api/v1/automated-response/alerts/{alert_id}/trigger",
        json={"playbook_id": playbook_id, "trigger_reason": "manual approval"},
    )

    assert response.status_code == 200
    assert observed["call"] == (playbook_id, alert_id, TENANT_ID, "manual approval")
    assert response.json()["execution_id"] == "exec-1"


def test_auto_trigger_for_alert_uses_authenticated_tenant(client, monkeypatch):
    alert_id = "00000000-0000-0000-0000-000000000003"
    observed = {"trigger_calls": []}

    class DummyTriggerEngine:
        def __init__(self, db):
            observed["engine_db"] = db

        def evaluate_alert(self, incoming_alert_id, tenant_id):
            observed["evaluate"] = (str(incoming_alert_id), str(tenant_id))
            return [
                {
                    "playbook_id": UUID("00000000-0000-0000-0000-000000000010"),
                    "playbook_name": "Auto PB",
                    "trigger_reason": "severity matches high",
                }
            ]

    class DummyOrchestrator:
        def __init__(self, db):
            observed["orchestrator_db"] = db

        async def trigger_playbook(self, playbook_id, alert_id, tenant_id, trigger_reason):
            observed["trigger_calls"].append(
                (str(playbook_id), str(alert_id), str(tenant_id), trigger_reason)
            )
            return {
                "trigger_id": "trigger-2",
                "execution_id": "exec-2",
                "status": "queued",
            }

    monkeypatch.setattr(triggers_api, "PlaybookTriggerEngine", DummyTriggerEngine)
    monkeypatch.setattr(triggers_api, "PlaybookOrchestrator", DummyOrchestrator)

    response = client.post(f"/api/v1/automated-response/alerts/{alert_id}/auto-trigger")

    assert response.status_code == 200
    assert observed["evaluate"] == (alert_id, TENANT_ID)
    assert observed["trigger_calls"] == [
        (
            "00000000-0000-0000-0000-000000000010",
            alert_id,
            TENANT_ID,
            "severity matches high",
        )
    ]
    assert response.json()["playbooks_triggered"] == 1
