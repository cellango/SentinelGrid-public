from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_playbook_executions
from sg_core.db import get_tenant_session
from sg_core.security import get_current_tenant


class QueryStub:
    def __init__(self, response):
        self._response = response

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def offset(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def all(self):
        if isinstance(self._response, list):
            return self._response
        return []

    def first(self):
        if isinstance(self._response, list):
            return self._response[0] if self._response else None
        return self._response


class FakeDB:
    def __init__(self, query_responses):
        self.query_responses = list(query_responses)
        self.query_models = []

    def query(self, model):
        self.query_models.append(getattr(model, "__name__", str(model)))
        if not self.query_responses:
            raise AssertionError("Unexpected query() call")
        return QueryStub(self.query_responses.pop(0))


def _playbook_execution(*, execution_id, tenant_id, playbook_id, alert_id):
    return SimpleNamespace(
        id=execution_id,
        tenant_id=UUID(str(tenant_id)),
        playbook_id=playbook_id,
        alert_id=alert_id,
        target_type="alert",
        target_id=alert_id,
        status="completed",
        workflow_exec_id="wf-123",
        triggered_by="analyst@example.com",
        approval_status="approved",
        started_at=datetime(2026, 3, 28, 12, 0, 0),
        finished_at=datetime(2026, 3, 28, 12, 5, 0),
        result_summary={"result": "ok"},
        logs=[{"step": "notify"}],
        created_at=datetime(2026, 3, 28, 12, 0, 0),
        updated_at=datetime(2026, 3, 28, 12, 5, 0),
    )


def _playbook(*, playbook_id, tenant_id):
    return SimpleNamespace(
        id=playbook_id,
        tenant_id=UUID(str(tenant_id)),
        name="Contain suspicious login",
        version="1.2.0",
    )


def _alert(*, alert_id, tenant_id):
    return SimpleNamespace(
        id=alert_id,
        tenant_id=UUID(str(tenant_id)),
        raw_payload={
            "sg": {
                "detection_rule_id": "SG-001",
                "detection_rule_version_id": "5",
            }
        },
    )


@pytest.fixture
def playbook_executions_client(monkeypatch):
    app = FastAPI()
    app.include_router(routes_playbook_executions.router, prefix="/playbook-executions")

    tenant_id = str(uuid4())
    system_tenant_id = str(uuid4())
    monkeypatch.setenv("SYSTEM_TENANT_ID", system_tenant_id)

    fake_db = FakeDB(query_responses=[])

    def _get_tenant():
        return tenant_id

    def _get_db():
        yield fake_db

    app.dependency_overrides[get_current_tenant] = _get_tenant
    app.dependency_overrides[get_tenant_session] = _get_db

    with TestClient(app) as client:
        yield client, fake_db, tenant_id, system_tenant_id

    app.dependency_overrides.clear()


def test_list_executions_uses_tenant_scoped_dependency(playbook_executions_client):
    client, fake_db, tenant_id, system_tenant_id = playbook_executions_client
    execution_id = uuid4()
    alert_id = uuid4()
    playbook_id = uuid4()

    fake_db.query_responses = [
        [_playbook_execution(execution_id=execution_id, tenant_id=tenant_id, playbook_id=playbook_id, alert_id=alert_id)],
        [_alert(alert_id=alert_id, tenant_id=tenant_id)],
        [_playbook(playbook_id=playbook_id, tenant_id=system_tenant_id)],
    ]

    response = client.get("/playbook-executions?status=completed&approval_status=approved&limit=25&offset=10")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(execution_id)
    assert payload[0]["tenant_id"] == tenant_id
    assert payload[0]["playbook_name"] == "Contain suspicious login"
    assert payload[0]["playbook_version_id"] == "1.2.0"
    assert payload[0]["detection_rule_id"] == "SG-001"
    assert payload[0]["detection_rule_version_id"] == "5"
    assert fake_db.query_models == ["PlaybookExecution", "Alert", "Playbook"]


def test_get_execution_scopes_lookup_to_authenticated_tenant(playbook_executions_client):
    client, fake_db, tenant_id, system_tenant_id = playbook_executions_client
    execution_id = uuid4()
    alert_id = uuid4()
    playbook_id = uuid4()

    fake_db.query_responses = [
        _playbook_execution(execution_id=execution_id, tenant_id=tenant_id, playbook_id=playbook_id, alert_id=alert_id),
        _playbook(playbook_id=playbook_id, tenant_id=system_tenant_id),
        _alert(alert_id=alert_id, tenant_id=tenant_id),
    ]

    response = client.get(f"/playbook-executions/{execution_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(execution_id)
    assert payload["tenant_id"] == tenant_id
    assert payload["playbook_id"] == str(playbook_id)
    assert payload["alert_id"] == str(alert_id)
    assert fake_db.query_models == ["PlaybookExecution", "Playbook", "Alert"]
