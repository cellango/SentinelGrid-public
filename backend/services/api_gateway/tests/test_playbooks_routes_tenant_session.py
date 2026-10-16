from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_playbooks
from sg_core.db import get_tenant_session
from sg_core.security import get_current_tenant

_UNSET = object()


class QueryStub:
    def __init__(self, responses):
        self._responses = responses

    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return self._responses.pop(0)

    def first(self):
        return self._responses.pop(0)


class FakeDB:
    def __init__(self, query_responses):
        self.query_responses = list(query_responses)
        self.added = []
        self.committed = False
        self.refreshed = []

    def query(self, _model):
        return QueryStub(self.query_responses)

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)


def _playbook(
    *,
    playbook_id,
    tenant_id,
    is_builtin=False,
    name="Playbook",
    key="pb-1",
    requires_approval=False,
    workflow=_UNSET,
    workflow_ref=None,
):
    resolved_tenant_id = UUID(str(tenant_id))
    return SimpleNamespace(
        id=playbook_id,
        tenant_id=resolved_tenant_id,
        name=name,
        description="Example playbook",
        category_filter=["containment"],
        version="1.0",
        workflow=(
            {"nodes": [{"id": "trigger-1", "type": "trigger"}], "edges": []}
            if workflow is _UNSET
            else workflow
        ),
        timeout_seconds=300,
        retry_policy=None,
        on_failure="fail",
        is_builtin=is_builtin,
        is_enabled=True,
        requires_approval=requires_approval,
        tags=["containment"],
        nist_controls=[],
        soc2_criteria=[],
        mitre_tactics=[],
        mitre_techniques=[],
        triggers=[],
        key=key,
        playbook_key=key,
        created_at=datetime(2026, 3, 28, 0, 0, 0),
        updated_at=datetime(2026, 3, 28, 0, 0, 0),
        target_type="alert",
        severity_filter=None,
        workflow_ref=workflow_ref,
    )


@pytest.fixture
def playbooks_client(monkeypatch):
    app = FastAPI()
    app.include_router(routes_playbooks.router, prefix="/playbooks")
    app.include_router(routes_playbooks.clone_router, prefix="/playbooks")
    tenant_id = str(uuid4())
    system_tenant_id = str(uuid4())
    monkeypatch.setenv("SYSTEM_TENANT_ID", system_tenant_id)

    def _get_tenant():
        return tenant_id

    fake_db = FakeDB(query_responses=[])

    def _get_db():
        yield fake_db

    app.dependency_overrides[get_current_tenant] = _get_tenant
    app.dependency_overrides[get_tenant_session] = _get_db

    with TestClient(app) as client:
        yield client, fake_db, tenant_id, system_tenant_id

    app.dependency_overrides.clear()


def test_list_playbooks_returns_system_and_tenant_playbooks(playbooks_client):
    client, fake_db, tenant_id, system_tenant_id = playbooks_client
    fake_db.query_responses = [
        [_playbook(playbook_id=uuid4(), tenant_id=system_tenant_id, is_builtin=True, name="Builtin", key="builtin")],
        [_playbook(playbook_id=uuid4(), tenant_id=tenant_id, is_builtin=False, name="Tenant", key="tenant")],
    ]

    response = client.get("/playbooks")

    assert response.status_code == 200
    data = response.json()
    assert [item["name"] for item in data] == ["Builtin", "Tenant"]


def test_list_playbooks_marks_missing_workflow_as_missing_state(playbooks_client):
    client, fake_db, tenant_id, _system_tenant_id = playbooks_client
    fake_db.query_responses = [
        [],
        [
            _playbook(
                playbook_id=uuid4(),
                tenant_id=tenant_id,
                name="Draft Playbook",
                key="draft",
                workflow=None,
            )
        ],
    ]

    response = client.get("/playbooks")

    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["workflow"] is None
    assert payload["workflow_status"] == "missing"
    assert "does not have a stored workflow graph yet" in payload["workflow_message"]


def test_execute_playbook_records_execution_for_tenant_scoped_request(playbooks_client):
    client, fake_db, tenant_id, _system_tenant_id = playbooks_client
    playbook_id = uuid4()
    fake_db.query_responses = [_playbook(playbook_id=playbook_id, tenant_id=tenant_id)]

    response = client.post(
        f"/playbooks/{playbook_id}/execute",
        json={"trigger_type": "manual", "parameters": {"foo": "bar"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["approval_status"] == "approved"
    assert payload["message"] == "Execution request recorded and pending SOAR worker handoff."
    assert fake_db.committed is True
    assert fake_db.added
    assert fake_db.added[0].finished_at is None


def test_execute_playbook_marks_approval_required_runs_as_pending(playbooks_client):
    client, fake_db, tenant_id, _system_tenant_id = playbooks_client
    playbook_id = uuid4()
    fake_db.query_responses = [
        _playbook(playbook_id=playbook_id, tenant_id=tenant_id, requires_approval=True)
    ]

    response = client.post(
        f"/playbooks/{playbook_id}/execute",
        json={"trigger_type": "manual", "parameters": {"foo": "bar"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending"
    assert payload["approval_status"] == "pending"
    assert payload["message"] == "Execution request recorded and awaiting approval before automation can start."


def test_execute_playbook_links_alert_id_from_alert_trigger(playbooks_client):
    client, fake_db, tenant_id, _system_tenant_id = playbooks_client
    playbook_id = uuid4()
    alert_id = uuid4()
    fake_db.query_responses = [_playbook(playbook_id=playbook_id, tenant_id=tenant_id)]

    response = client.post(
        f"/playbooks/{playbook_id}/execute",
        json={"trigger_type": "alert", "trigger_id": str(alert_id)},
    )

    assert response.status_code == 200
    assert response.json()["alert_id"] == str(alert_id)
    assert fake_db.added[0].alert_id == alert_id


def test_clone_playbook_creates_tenant_owned_copy(playbooks_client):
    client, fake_db, tenant_id, system_tenant_id = playbooks_client
    source_id = uuid4()
    fake_db.query_responses = [_playbook(playbook_id=source_id, tenant_id=system_tenant_id, is_builtin=True, name="Builtin", key="builtin")]

    response = client.post(
        f"/playbooks/{source_id}/clone",
        json={"name": "Custom Clone", "key": "custom-clone"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Custom Clone"
    assert response.json()["tenant_id"] == tenant_id
    assert fake_db.committed is True


def test_clone_playbook_does_not_persist_placeholder_workflow_when_source_has_no_graph(playbooks_client):
    client, fake_db, tenant_id, system_tenant_id = playbooks_client
    source_id = uuid4()
    fake_db.query_responses = [
        _playbook(
            playbook_id=source_id,
            tenant_id=system_tenant_id,
            is_builtin=True,
            name="Builtin",
            key="builtin",
            workflow=None,
        )
    ]

    response = client.post(
        f"/playbooks/{source_id}/clone",
        json={"name": "Graphless Clone", "key": "graphless-clone"},
    )

    assert response.status_code == 200
    assert fake_db.added[0].workflow is None
    assert response.json()["workflow"] is None
    assert response.json()["workflow_status"] == "missing"


def test_get_playbook_rejects_foreign_tenant_record(playbooks_client):
    client, fake_db, _tenant_id, _system_tenant_id = playbooks_client
    foreign_tenant = str(uuid4())
    playbook_id = uuid4()
    fake_db.query_responses = [_playbook(playbook_id=playbook_id, tenant_id=foreign_tenant)]

    response = client.get(f"/playbooks/{playbook_id}")

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


def test_update_playbook_allows_tenant_owned_record(playbooks_client):
    client, fake_db, tenant_id, _system_tenant_id = playbooks_client
    playbook_id = uuid4()
    tenant_playbook = _playbook(playbook_id=playbook_id, tenant_id=tenant_id, name="Tenant", key="tenant")
    fake_db.query_responses = [tenant_playbook]

    response = client.put(
        f"/playbooks/{playbook_id}",
        json={"name": "Renamed Playbook"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed Playbook"
    assert fake_db.committed is True


def test_validate_playbook_reads_system_builtins(playbooks_client):
    client, fake_db, _tenant_id, system_tenant_id = playbooks_client
    playbook_id = uuid4()
    fake_db.query_responses = [_playbook(playbook_id=playbook_id, tenant_id=system_tenant_id, is_builtin=True)]

    response = client.post(f"/playbooks/{playbook_id}/validate")

    assert response.status_code == 200
    assert response.json() == {"valid": True, "errors": [], "warnings": []}


def test_validate_playbook_fails_when_stored_workflow_is_missing(playbooks_client):
    client, fake_db, tenant_id, _system_tenant_id = playbooks_client
    playbook_id = uuid4()
    fake_db.query_responses = [
        _playbook(playbook_id=playbook_id, tenant_id=tenant_id, workflow=None)
    ]

    response = client.post(f"/playbooks/{playbook_id}/validate")

    assert response.status_code == 200
    assert response.json() == {
        "valid": False,
        "errors": ["Stored workflow is missing. Save a real workflow before validating this playbook."],
        "warnings": [],
    }
