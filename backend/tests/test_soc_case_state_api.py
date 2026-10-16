"""Focused tests for SOC case-state read APIs in the agent runtime."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException


LIBS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "libs"))
if LIBS_PATH not in sys.path:
    sys.path.insert(0, LIBS_PATH)

from sg_agent_runtime import service as runtime_service  # noqa: E402
from sg_agent_runtime.models import AgentTask  # noqa: E402
from sg_agent_runtime.soc_models import (  # noqa: E402
    SOCActionRecommendation,
    SOCCaseContext,
    SOCCaseMemory,
    SOCPlaybookRecommendation,
    SOCRecommendationOutput,
)


class FakeMemoryStore:
    def __init__(self, *, case_context=None, case_memory=None):
        self.case_context = case_context
        self.case_memory = case_memory

    async def recall_case_context(self, tenant_id: str, incident_id: str):
        return self.case_context

    async def recall_case_memory(self, tenant_id: str, incident_id: str):
        return self.case_memory

    async def store_case_context(self, case_context):
        self.case_context = case_context

    async def store_case_memory(self, case_memory):
        self.case_memory = case_memory


class FakeTaskQueue:
    def __init__(self, tasks):
        self.tasks = tasks

    async def list_tasks(self, agent_id=None, tenant_id=None, status=None):
        return list(self.tasks)


def _sample_case_context() -> SOCCaseContext:
    return SOCCaseContext(
        incident_id="inc-1",
        tenant_id="tenant-1",
        incident_title="Suspicious login from new geography",
        incident_type="account_takeover",
        severity="high",
        status="investigating",
        phase="detection_and_analysis",
    )


def _sample_case_memory() -> SOCCaseMemory:
    recommendation = SOCRecommendationOutput(
        case_summary="Identity-led triage indicates likely session abuse.",
        response_pack_id="account_takeover",
        response_pack_label="Account takeover containment",
        confidence=0.82,
        rationale=["Suspicious login and identity signals align with account takeover."],
    )
    return SOCCaseMemory(
        tenant_id="tenant-1",
        incident_id="inc-1",
        current_phase="detection_and_analysis",
        current_status="investigating",
        last_recommendation=recommendation,
        recommendation_versions=[recommendation],
    )


@pytest.mark.asyncio
async def test_get_soc_case_state_returns_context_memory_and_recent_tasks(monkeypatch):
    case_context = _sample_case_context()
    case_memory = _sample_case_memory()
    recent_task = AgentTask(
        tenant_id="tenant-1",
        incident_id="inc-1",
        case_id="case-1",
        agent_id="soc_case_agent",
        task_type="refresh_case_after_action",
        status="completed",
        result={"answer": "Updated case plan."},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    monkeypatch.setattr(
        runtime_service,
        "_memory",
        FakeMemoryStore(case_context=case_context, case_memory=case_memory),
    )
    monkeypatch.setattr(runtime_service, "_task_queue", FakeTaskQueue([recent_task]))

    response = await runtime_service.get_soc_case_state(
        "inc-1",
        tenant_id="tenant-1",
        include_tasks=True,
        task_limit=10,
    )

    assert response.incident_id == "inc-1"
    assert response.case_context is not None
    assert response.case_context.recommended_response_pack is None
    assert response.case_memory is not None
    assert response.latest_recommendation is not None
    assert response.latest_recommendation.response_pack_id == "account_takeover"
    assert len(response.recommendation_versions) == 1
    assert response.recommendation_versions[0].response_pack_label == "Account takeover containment"
    assert len(response.recent_tasks) == 1
    assert response.recent_tasks[0].task_type == "refresh_case_after_action"


@pytest.mark.asyncio
async def test_get_soc_case_state_raises_404_when_missing(monkeypatch):
    monkeypatch.setattr(runtime_service, "_memory", FakeMemoryStore())
    monkeypatch.setattr(runtime_service, "_task_queue", FakeTaskQueue([]))

    with pytest.raises(HTTPException) as exc_info:
        await runtime_service.get_soc_case_state(
            "inc-missing",
            tenant_id="tenant-1",
            include_tasks=False,
            task_limit=10,
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_submit_soc_case_feedback_updates_action_and_playbook_status(monkeypatch):
    case_context = _sample_case_context()
    case_context.recommended_playbooks = [
        SOCPlaybookRecommendation(
            playbook_id="playbook-1",
            playbook_key="ACCOUNT-COMPROMISE",
            playbook_name="Account compromise investigation",
            rank=1,
            confidence=0.88,
        )
    ]
    case_memory = _sample_case_memory()
    case_memory.last_recommendation.recommended_playbooks = [
        SOCPlaybookRecommendation(
            playbook_id="playbook-1",
            playbook_key="ACCOUNT-COMPROMISE",
            playbook_name="Account compromise investigation",
            rank=1,
            confidence=0.88,
        )
    ]
    case_memory.last_recommendation.recommended_actions = [
        SOCActionRecommendation(
            action_id="action-1",
            action_type="review_identity",
            label="Review identity sign-in history",
            description="Review whether the login aligns to known behavior.",
        )
    ]

    monkeypatch.setattr(
        runtime_service,
        "_memory",
        FakeMemoryStore(case_context=case_context, case_memory=case_memory),
    )
    monkeypatch.setattr(runtime_service, "_task_queue", FakeTaskQueue([]))

    response = await runtime_service.submit_soc_case_feedback(
        "inc-1",
        runtime_service.SubmitSOCFeedbackRequest(
            tenant_id="tenant-1",
            recommendation_id=case_memory.last_recommendation.recommendation_id,
            feedback_type="accepted_recommendation",
            actor_id="analyst@example.com",
            actor_role="HUMAN_OWNER",
            accepted=True,
            action_id="action-1",
            playbook_id="playbook-1",
            playbook_key="ACCOUNT-COMPROMISE",
            playbook_name="Account compromise investigation",
        ),
        include_tasks=False,
        task_limit=10,
    )

    assert response.case_context is not None
    assert response.case_context.feedback_history[-1].actor_id == "analyst@example.com"
    assert response.case_context.recommended_playbooks[0].status == "accepted"
    assert response.case_memory is not None
    assert response.case_memory.feedback_history[-1].accepted is True
    assert response.latest_recommendation is not None
    assert response.latest_recommendation.recommended_playbooks[0].status == "accepted"
    assert response.latest_recommendation.recommended_actions[0].status == "accepted"
    assert response.recommendation_versions[0].recommended_playbooks[0].status == "accepted"
