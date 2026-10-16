"""Focused tests for supervised Compliance Agent workflow recommendations."""

from __future__ import annotations

import os
import sys
from typing import Any

import pytest


LIBS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "libs"))
if LIBS_PATH not in sys.path:
    sys.path.insert(0, LIBS_PATH)

from sg_agent_runtime import compliance_workflow  # noqa: E402
from sg_agent_runtime.compliance_workflow import (  # noqa: E402
    ComplianceAgentRuntimeClient,
    ComplianceAgentWorkflowService,
    build_control_gap_recommendation,
    build_framework_selected_recommendation,
)


class FakeRecommendationRepository:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.attached: list[dict[str, Any]] = []

    def create_recommendation(self, db, **kwargs):
        self.created.append({"db": db, **kwargs})
        return {
            "id": "rec-1",
            "tenant_id": kwargs["tenant_id"],
            "trigger_type": kwargs["trigger_type"],
            "recommendation_type": kwargs["recommendation_type"],
            "source_type": kwargs["source_type"],
            "source_id": kwargs.get("source_id"),
            "proposed_actions": kwargs.get("proposed_actions") or [],
            "requires_approval": kwargs["requires_approval"],
        }

    def attach_agent_task(self, db, **kwargs):
        self.attached.append({"db": db, **kwargs})
        return {"id": kwargs["recommendation_id"], "agent_task_id": kwargs["agent_task_id"]}


class FakeRuntimeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def submit_compliance_task(self, **kwargs):
        self.calls.append(kwargs)
        return {"id": "task-1"}


@pytest.mark.asyncio
async def test_workflow_service_is_feature_flagged():
    repository = FakeRecommendationRepository()
    runtime = FakeRuntimeClient()
    service = ComplianceAgentWorkflowService(
        repository=repository,
        runtime_client=runtime,
        enabled=False,
    )

    result = await service.create_recommendation_and_task(
        object(),
        tenant_id="tenant-a",
        **build_framework_selected_recommendation(framework_id="soc2"),
    )

    assert result is None
    assert repository.created == []
    assert runtime.calls == []


@pytest.mark.asyncio
async def test_write_action_recommendations_require_approval_and_attach_task():
    repository = FakeRecommendationRepository()
    runtime = FakeRuntimeClient()
    service = ComplianceAgentWorkflowService(
        repository=repository,
        runtime_client=runtime,
        enabled=True,
    )

    result = await service.create_recommendation_and_task(
        "db-session",
        tenant_id="tenant-a",
        created_by="user-123",
        authorization="Bearer user-token",
        metadata={"gap": {"id": "gap-1"}},
        **build_control_gap_recommendation(
            framework_id="soc2",
            control_id="CC6.1",
            gap={"id": "gap-1", "severity": "high", "remediation_hint": "Collect MFA evidence"},
        ),
    )

    assert repository.created[0]["requires_approval"] is True
    assert repository.created[0]["recommendation_type"] == "create_evidence_collection_task"
    assert runtime.calls[0]["authorization"] == "Bearer user-token"
    assert runtime.calls[0]["actor_id"] == "user-123"
    assert repository.attached[0]["agent_task_id"] == "task-1"
    assert result["agent_task_id"] == "task-1"


@pytest.mark.asyncio
async def test_read_only_recommendations_do_not_require_approval():
    repository = FakeRecommendationRepository()
    service = ComplianceAgentWorkflowService(
        repository=repository,
        runtime_client=None,
        enabled=True,
    )

    result = await service.create_recommendation_and_task(
        "db-session",
        tenant_id="tenant-a",
        **build_framework_selected_recommendation(framework_id="soc2"),
    )

    assert repository.created[0]["requires_approval"] is False
    assert repository.created[0]["recommendation_type"] == "read_only_summary"
    assert result["id"] == "rec-1"


@pytest.mark.asyncio
async def test_runtime_client_submits_supervised_task_payload(monkeypatch):
    captured: dict[str, Any] = {}

    class FakeResponse:
        content = b'{"id":"task-1"}'

        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "task-1"}

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, *, json, headers):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(compliance_workflow.httpx, "AsyncClient", FakeAsyncClient)
    client = ComplianceAgentRuntimeClient(
        runtime_url="http://runtime",
        internal_token="internal-token",
        timeout_seconds=3,
    )

    response = await client.submit_compliance_task(
        tenant_id="tenant-a",
        trigger_type="high_priority_control_gap_detected",
        source_type="control_gap",
        recommendation={
            "id": "rec-1",
            "source_id": "gap-1",
            "recommendation_type": "create_evidence_collection_task",
            "proposed_actions": [{"action": "create_evidence_collection_task"}],
        },
        priority="high",
        payload={"control_id": "CC6.1"},
        authorization="Bearer user-token",
        actor_id="user-123",
    )

    assert response == {"id": "task-1"}
    assert captured["url"] == "http://runtime/agents/tasks"
    assert captured["headers"]["Authorization"] == "Bearer internal-token"
    task_payload = captured["json"]
    assert task_payload["agent_id"] == "compliance_agent"
    assert task_payload["payload"]["supervision"] == {
        "mode": "human_approval_required",
        "write_actions_require_approval": True,
        "read_only_summary_allowed": True,
    }
    assert task_payload["context"]["auth"]["authorization"] == "Bearer user-token"
    assert task_payload["context"]["auth"]["user_id"] == "user-123"
