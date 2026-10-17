"""Focused tests for playbook-execution-driven SOC case refreshes."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4
import types
import pytest


ROOT = Path(__file__).parent.parent
LIBS = ROOT.parent.parent / "libs"
for candidate in (ROOT, LIBS):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

database_module = types.ModuleType("app.database")


class _PlaybookExecutionORM:
    id = "id"


database_module.PlaybookExecutionORM = _PlaybookExecutionORM
from unittest.mock import patch
import importlib.util
spec = importlib.util.spec_from_file_location("soar_execution_refresh_unit_target", ROOT / "app/services/playbook_execution_service.py")
playbook_execution_service_module = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"app.database": database_module}):
    spec.loader.exec_module(playbook_execution_service_module)
PlaybookExecutionService = playbook_execution_service_module.PlaybookExecutionService
from sg_agent_runtime.soc_case_runtime_client import SOCCaseRuntimeClient


class FakeQuery:
    def __init__(self, execution):
        self.execution = execution

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.execution


class FakeDB:
    def __init__(self, execution):
        self.execution = execution
        self.commit_calls = 0
        self.refresh_calls = []

    def query(self, model):
        return FakeQuery(self.execution)

    def commit(self):
        self.commit_calls += 1

    def refresh(self, obj):
        self.refresh_calls.append(obj)


def _execution(logs):
    return SimpleNamespace(
        id=uuid4(),
        tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
        playbook_id=uuid4(),
        status="running",
        workflow_exec_id=None,
        logs=logs,
        results=None,
        finished_at=None,
        last_updated_at=None,
    )


def test_update_execution_status_submits_soc_refresh_for_incident_bound_terminal_status(monkeypatch):
    execution = _execution(
        {
            "trigger_type": "incident",
            "trigger_id": "22222222-2222-2222-2222-222222222222",
        }
    )
    db = FakeDB(execution)
    service = PlaybookExecutionService(db)
    observed = {}

    def fake_submit(self, execution_obj, *, status):
        observed["execution_id"] = str(execution_obj.id)
        observed["status"] = status
        return {"id": "task-123"}

    monkeypatch.setattr(
        PlaybookExecutionService,
        "_submit_soc_case_refresh_for_execution",
        fake_submit,
    )

    updated = service.update_execution_status(execution.id, "completed", results={"ok": True})

    assert updated.status == "completed"
    assert observed == {
        "execution_id": str(execution.id),
        "status": "completed",
    }
    assert db.commit_calls == 1
    assert db.refresh_calls == [execution]


def test_update_execution_status_skips_refresh_for_non_incident_execution(monkeypatch):
    execution = _execution({"trigger_type": "manual"})
    db = FakeDB(execution)
    service = PlaybookExecutionService(db)
    observed = {"count": 0}

    # helper is invoked from update_execution_status, but the internal extraction path
    # should return None and keep behavior safe when not incident-bound.
    monkeypatch.setattr(
        PlaybookExecutionService,
        "_extract_incident_id",
        lambda self, execution_obj: None,
    )
    monkeypatch.setattr(
        SOCCaseRuntimeClient,
        "submit_case_refresh_sync",
        lambda self, **kwargs: observed.__setitem__("count", observed["count"] + 1),
    )

    updated = service.update_execution_status(execution.id, "completed", results={"ok": True})

    assert updated.status == "completed"
    assert observed["count"] == 0


@pytest.mark.asyncio
async def test_execute_playbook_without_worker_stays_pending(monkeypatch):
    execution = _execution({"trigger_type": "incident"})
    db = FakeDB(execution)
    service = PlaybookExecutionService(db)

    monkeypatch.setattr(
        service,
        "create_execution",
        lambda **kwargs: execution,
    )
    monkeypatch.setattr(playbook_execution_service_module, "_celery_available", False)
    monkeypatch.setattr(playbook_execution_service_module, "_run_playbook_task", None)

    observed = {}

    def fake_update(execution_id, status, workflow_exec_id=None, logs=None, results=None):
        observed["execution_id"] = execution_id
        observed["status"] = status
        observed["workflow_exec_id"] = workflow_exec_id
        observed["logs"] = logs
        observed["results"] = results
        execution.status = status
        execution.logs = logs
        execution.results = results
        return execution

    monkeypatch.setattr(service, "update_execution_status", fake_update)

    updated = await service.execute_playbook(
        tenant_id="11111111-1111-1111-1111-111111111111",
        playbook_id=uuid4(),
        triggered_by="api",
        context={"trigger_type": "manual"},
    )

    assert updated.status == "pending"
    assert observed["status"] == "pending"
    assert observed["workflow_exec_id"] is None
    assert observed["logs"] == {"worker_state": "unavailable"}
    assert observed["results"] == {
        "message": "Execution request recorded, but no SOAR worker is currently connected.",
    }
