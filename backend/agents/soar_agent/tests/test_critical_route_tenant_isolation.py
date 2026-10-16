"""Focused tenant-isolation coverage for SOAR critical routes."""

from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4
import sys

import pytest
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

from app.main import app
from app.api import detection_events, ootb_playbooks, webhooks
from app.core import config as soar_config


TENANT_ID = UUID("00000000-0000-0000-0000-000000000111")
INTERNAL_TOKEN = "internal-test-token"


class FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class FakeDB:
    def __init__(self):
        self.ticket = None
        self.incident = None
        self.commit_calls = 0

    def query(self, model):
        model_name = getattr(model, "__name__", "")
        if model_name == "Ticket":
            return FakeQuery(self.ticket)
        if model_name == "Incident":
            return FakeQuery(self.incident)
        return FakeQuery(None)

    def commit(self):
        self.commit_calls += 1


@pytest.fixture
def fake_db():
    return FakeDB()


@pytest.fixture
def client(fake_db, monkeypatch):
    monkeypatch.setattr(soar_config.settings, "THEHIVE_API_KEY", "test-api-key")
    monkeypatch.setattr(soar_config.settings, "INTERNAL_SERVICE_TOKEN", INTERNAL_TOKEN)

    async def fake_map_incident(*args, **kwargs):
        return None

    def override_tenant_session():
        yield fake_db

    app.dependency_overrides[detection_events.get_webhook_tenant_session] = override_tenant_session
    app.dependency_overrides[ootb_playbooks.get_current_tenant] = lambda: TENANT_ID
    app.dependency_overrides[ootb_playbooks.get_tenant_session] = override_tenant_session
    app.dependency_overrides[webhooks.get_thehive_tenant_session] = override_tenant_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_detection_event_ingest_uses_authenticated_tenant(client, monkeypatch):
    class DummyIncidentCreator:
        def __init__(self, db):
            self.db = db

        async def create_incident_from_detection(self, detection_event, tenant_id):
            assert detection_event["sg"]["tenant_id"] == str(TENANT_ID)
            assert tenant_id == str(TENANT_ID)
            return {"incident_id": "inc-1", "playbook_execution_id": "exec-1"}

    monkeypatch.setattr(detection_events, "IncidentCreator", DummyIncidentCreator)

    response = client.post(
        "/api/v1/detection-events/ingest",
        headers={
            "Authorization": f"Bearer {INTERNAL_TOKEN}",
            "X-Tenant-ID": str(TENANT_ID),
        },
        json={"sg": {"tenant_id": str(TENANT_ID), "alert_type": "phishing", "severity": "high"}},
    )

    assert response.status_code == 202
    assert response.json()["incident_id"] == "inc-1"


def test_detection_event_ingest_blocks_tenant_mismatch(client, monkeypatch):
    class DummyIncidentCreator:
        def __init__(self, db):
            self.db = db

        async def create_incident_from_detection(self, detection_event, tenant_id):
            raise AssertionError("should not be called")

    monkeypatch.setattr(detection_events, "IncidentCreator", DummyIncidentCreator)

    response = client.post(
        "/api/v1/detection-events/ingest",
        headers={
            "Authorization": f"Bearer {INTERNAL_TOKEN}",
            "X-Tenant-ID": str(TENANT_ID),
        },
        json={"sg": {"tenant_id": "00000000-0000-0000-0000-000000000222", "alert_type": "phishing"}},
    )

    assert response.status_code == 400
    assert "Tenant ID mismatch" in response.json()["detail"]


def test_seed_ootb_playbooks_requires_authenticated_tenant(client, monkeypatch):
    seeded = [
        SimpleNamespace(playbook_key="phishing-investigation"),
        SimpleNamespace(playbook_key="malware-containment"),
    ]
    monkeypatch.setattr(ootb_playbooks, "seed_all_ootb_playbooks", lambda db: seeded)

    response = client.post("/soar/ootb/seed", headers={"X-Tenant-ID": str(TENANT_ID)})

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "Seeded 2 OOTB playbooks",
        "playbooks": ["phishing-investigation", "malware-containment"],
        "tenant_id": str(TENANT_ID),
    }


def test_thehive_case_update_scopes_lookup_to_authenticated_tenant(client, fake_db):
    fake_db.ticket = SimpleNamespace(
        id=uuid4(),
        status="open",
        severity="low",
        external_id="case-123",
        tenant_id=TENANT_ID,
    )

    response = client.post(
        "/api/v1/thehive/case/update",
        headers={"X-API-Key": "test-api-key", "X-Tenant-ID": str(TENANT_ID)},
        json={"object": {"id": "case-123", "status": "Resolved", "severity": 3}},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "processed", "case_id": "case-123"}
    assert fake_db.ticket.status == "resolved"
    assert fake_db.ticket.severity == "high"
    assert fake_db.commit_calls == 1


def test_thehive_observable_update_requires_authenticated_tenant(client):
    response = client.post(
        "/api/v1/thehive/observable/update",
        headers={"X-API-Key": "test-api-key", "X-Tenant-ID": str(TENANT_ID)},
        json={"object": {"id": "observable-123"}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "processed",
        "observable_id": "observable-123",
        "tenant_id": str(TENANT_ID),
    }
