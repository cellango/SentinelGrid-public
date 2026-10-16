"""Focused tenant-scoped DB coverage for SOAR playbook routes."""

from contextlib import ExitStack
from datetime import datetime
import sys
import types
from types import SimpleNamespace
from uuid import UUID, uuid4
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

playbook_execution_service = types.ModuleType("app.services.playbook_execution_service")


class _PlaybookExecutionService:
    def __init__(self, db):
        self.db = db

    async def execute_playbook(self, **kwargs):
        return _sample_execution(uuid4(), kwargs["playbook_id"])


playbook_execution_service.PlaybookExecutionService = _PlaybookExecutionService
sys.modules.setdefault("app.services.playbook_execution_service", playbook_execution_service)

from app.main import app, get_tenant_session
from app.models import Playbook, PlaybookValidationResult, PlaybookExecution, WorkflowStructure


def _sample_playbook(playbook_id: UUID) -> Playbook:
    return Playbook(
        id=playbook_id,
        tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
        key="playbook-key",
        playbook_key="playbook-key",
        name="Test Playbook",
        description="Playbook description",
        category="phishing",
        version="1.0.0",
        workflow=WorkflowStructure(nodes=[{"id": "trigger-1", "type": "manual_trigger"}], edges=[]),
        timeout_seconds=300,
        on_failure="fail",
        is_template=False,
        requires_approval=False,
        tags=[],
        is_builtin=False,
        severity_default=None,
        applicable_sources=[],
        triggers=[],
        prerequisites=[],
        artifacts_required=[],
        phases=None,
        cis_controls=[],
        nist_controls=[],
        mitre_tactics=[],
        mitre_techniques=[],
        trigger_conditions=None,
        auto_trigger_enabled=False,
        trigger_priority=0,
        created_by=None,
        created_at=datetime(2026, 3, 28, 12, 0, 0),
        updated_at=datetime(2026, 3, 28, 12, 0, 0),
        n8n_workflow_id=None,
        n8n_webhook_url=None,
    )


def _sample_execution(execution_id: UUID, playbook_id: UUID):
    return SimpleNamespace(
        id=execution_id,
        playbook_id=playbook_id,
        tenant_id=UUID("11111111-1111-1111-1111-111111111111"),
        trigger_type="manual",
        trigger_id=None,
        status="pending",
        started_at=datetime(2026, 3, 28, 12, 0, 0),
        completed_at=None,
        workflow_exec_id="celery-task-1",
        n8n_execution_id=None,
        result={"message": "Execution request recorded and pending SOAR worker handoff."},
        error_message=None,
        logs=[],
        created_at=datetime(2026, 3, 28, 12, 0, 0),
    )


async def _async_sample_execution(self, **kwargs):
    return _sample_execution(uuid4(), kwargs["playbook_id"])


@pytest.mark.parametrize(
    ("method", "path", "json_body", "expected_calls", "patches"),
    [
        (
            "post",
            "/soar/playbooks",
            {
                "name": "PB",
                "description": "desc",
                "category": "phishing",
                "version": "1.0.0",
                "workflow": {"nodes": [{"id": "trigger-1", "type": "manual_trigger"}], "edges": []},
                "is_template": False,
                "requires_approval": False,
                "tags": [],
            },
            1,
            {"app.services.playbook_service.PlaybookService.create": lambda self, tenant_id, playbook_data: _sample_playbook(uuid4())},
        ),
        (
            "get",
            "/soar/playbooks",
            None,
            1,
            {"app.services.playbook_service.PlaybookService.list": lambda self, **kwargs: [_sample_playbook(uuid4())]},
        ),
        (
            "get",
            f"/soar/playbooks/{uuid4()}",
            None,
            1,
            {"app.services.playbook_service.PlaybookService.get_by_id": lambda self, playbook_id, tenant_id: _sample_playbook(playbook_id)},
        ),
        (
            "post",
            f"/soar/playbooks/{uuid4()}/approve",
            None,
            1,
            {"app.services.playbook_service.PlaybookService.set_approval_status": lambda self, playbook_id, tenant_id, approve: _sample_playbook(playbook_id)},
        ),
        (
            "post",
            f"/soar/playbooks/{uuid4()}/reject",
            None,
            1,
            {"app.services.playbook_service.PlaybookService.set_approval_status": lambda self, playbook_id, tenant_id, approve: _sample_playbook(playbook_id)},
        ),
        (
            "post",
            f"/soar/playbooks/{uuid4()}/preview",
            None,
            1,
            {
                "app.services.playbook_service.PlaybookService.get_by_id": lambda self, playbook_id, tenant_id: _sample_playbook(playbook_id),
                "app.services.playbook_service.PlaybookService.validate": lambda self, playbook: PlaybookValidationResult(valid=True, errors=[], warnings=[]),
            },
        ),
        (
            "post",
            f"/soar/playbooks/{uuid4()}/validate",
            None,
            1,
            {
                "app.services.playbook_service.PlaybookService.get_by_id": lambda self, playbook_id, tenant_id: _sample_playbook(playbook_id),
                "app.services.playbook_service.PlaybookService.validate": lambda self, playbook: PlaybookValidationResult(valid=True, errors=[], warnings=[]),
            },
        ),
        (
            "put",
            f"/soar/playbooks/{uuid4()}",
            {"name": "Updated PB"},
            1,
            {"app.services.playbook_service.PlaybookService.update": lambda self, playbook_id, tenant_id, playbook_data: _sample_playbook(playbook_id)},
        ),
        (
            "delete",
            f"/soar/playbooks/{uuid4()}",
            None,
            1,
            {"app.services.playbook_service.PlaybookService.delete": lambda self, playbook_id, tenant_id: True},
        ),
        (
            "post",
            f"/soar/playbooks/{uuid4()}/copy",
            {"new_name": "Copied PB"},
            1,
            {"app.services.playbook_service.PlaybookService.copy": lambda self, playbook_id, tenant_id, copy_request: _sample_playbook(uuid4())},
        ),
        (
            "post",
            f"/soar/playbooks/{uuid4()}/execute",
            {"trigger_type": "manual", "parameters": {"k": "v"}},
            1,
            {
                "app.services.playbook_service.PlaybookService.get_by_id": lambda self, playbook_id, tenant_id: _sample_playbook(playbook_id),
                "PlaybookExecutionService.execute_playbook": _async_sample_execution,
            },
        ),
        (
            "get",
            f"/soar/executions/{uuid4()}",
            None,
            1,
            {"PlaybookExecutionService.get_execution": lambda self, execution_id, tenant_id: _sample_execution(execution_id, uuid4())},
        ),
    ],
)
def test_playbook_routes_use_tenant_session(method, path, json_body, expected_calls, patches):
    """SOAR playbook routes should obtain DB access through get_tenant_session."""
    calls = {"session": 0}

    def override_get_tenant_session():
        calls["session"] += 1
        yield object()

    app.dependency_overrides[get_tenant_session] = override_get_tenant_session
    client = TestClient(app)

    try:
        with ExitStack() as stack:
            stack.enter_context(
                patch("app.services.playbook_service.PlaybookService.__init__", lambda self, db: setattr(self, "db", db))
            )
            for target, replacement in patches.items():
                if target.startswith("PlaybookExecutionService."):
                    attribute = target.split(".", 1)[1]
                    stack.enter_context(
                        patch(
                            f"app.services.playbook_execution_service.PlaybookExecutionService.{attribute}",
                            replacement,
                            create=True,
                        )
                    )
                else:
                    stack.enter_context(patch(target, replacement))

            request_kwargs = {
                "headers": {"X-Tenant-ID": "11111111-1111-1111-1111-111111111111"},
            }
            if json_body is not None:
                request_kwargs["json"] = json_body
            response = getattr(client, method)(path, **request_kwargs)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code < 500
    assert calls == {"session": expected_calls}
