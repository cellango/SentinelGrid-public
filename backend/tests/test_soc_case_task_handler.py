"""Focused tests for deterministic SOC case-agent runtime handling."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest


LIBS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "libs"))
if LIBS_PATH not in sys.path:
    sys.path.insert(0, LIBS_PATH)

from sg_agent_runtime.agent_loop import AgentLoop  # noqa: E402
from sg_agent_runtime.agents import SOC_CASE_AGENT  # noqa: E402
from sg_agent_runtime.models import AgentTask  # noqa: E402
from sg_agent_runtime.soc_case_task_handler import SOCCaseTaskHandler  # noqa: E402
from sg_agent_runtime.soc_models import SOCCaseContext, SOCCaseMemory  # noqa: E402


SAMPLE_PLAYBOOKS = [
    {
        "id": "pb-1",
        "playbook_key": "ACCOUNT-COMPROMISE",
        "key": "account-compromise",
        "name": "Account Compromise / Suspicious Login",
        "category": "identity",
        "tags": ["identity", "suspicious_login"],
        "mitre_tactics": ["TA0006"],
        "mitre_techniques": ["T1078"],
        "nist_controls": ["AC-2", "IR-4"],
    },
    {
        "id": "pb-2",
        "playbook_key": "PASSWORD-SPRAY",
        "key": "password-spray",
        "name": "Password Spray Response",
        "category": "identity",
        "tags": ["password spray"],
        "mitre_tactics": ["TA0006"],
        "mitre_techniques": ["T1110.003"],
        "nist_controls": ["AC-7", "IR-4"],
    },
]


class FakeMemoryStore:
    """Small in-memory stand-in for the Redis-backed case memory store."""

    def __init__(self, case_context: SOCCaseContext | None = None, case_memory: SOCCaseMemory | None = None):
        self.case_context = case_context
        self.case_memory = case_memory
        self.saved_memories: list[dict[str, object]] = []

    async def recall_case_context(self, tenant_id: str, incident_id: str):
        return self.case_context

    async def recall_case_memory(self, tenant_id: str, incident_id: str):
        return self.case_memory

    async def store_case_context(self, case_context: SOCCaseContext):
        self.case_context = case_context

    async def store_case_memory(self, case_memory: SOCCaseMemory):
        self.case_memory = case_memory

    async def store(self, agent_id: str, tenant_id: str, key: str, value: dict, ttl_seconds: int | None = None):
        self.saved_memories.append(
            {
                "agent_id": agent_id,
                "tenant_id": tenant_id,
                "key": key,
                "value": value,
                "ttl_seconds": ttl_seconds,
            }
        )

    async def search(self, agent_id: str, tenant_id: str, prefix: str = ""):
        return []


class FakeTaskQueue:
    def __init__(self):
        self.completed = None
        self.failed = None

    async def complete(self, task_id, result):
        self.completed = (task_id, result)

    async def fail(self, task_id, error):
        self.failed = (task_id, error)


class FakeLLMClient:
    def __init__(self):
        self.calls = 0

    async def chat(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("SOC case tasks should bypass the LLM loop")


def _sample_case_context() -> SOCCaseContext:
    return SOCCaseContext(
        incident_id="inc-1",
        tenant_id="tenant-1",
        incident_title="Suspicious login from new geography",
        incident_type="account_takeover",
        severity="high",
        status="new",
        phase="detection_and_analysis",
        related_detections=[{"id": "det-1", "source": "opensearch_detection", "label": "Impossible travel"}],
        entities=[{"id": "user-1", "source": "identity_provider", "label": "alice@example.com"}],
        mitre_tactics=["TA0006"],
        mitre_techniques=["T1078"],
    )


@pytest.mark.asyncio
async def test_soc_case_task_handler_updates_case_memory_with_recommendation():
    memory = FakeMemoryStore()
    handler = SOCCaseTaskHandler(
        memory=memory,
        catalog_loader=lambda: list(SAMPLE_PLAYBOOKS),
    )

    task = AgentTask(
        tenant_id="tenant-1",
        incident_id="inc-1",
        case_id="case-1",
        agent_id="soc_case_agent",
        task_type="triage_new_incident",
        payload={"source_kind": "detection_event"},
        context={
            "case_context": _sample_case_context().model_dump(mode="json"),
            "trigger_event": {
                "trigger_type": "incident_created",
                "incident_id": "inc-1",
                "tenant_id": "tenant-1",
                "source_kind": "detection_event",
            },
        },
    )

    result = await handler.handle(task)

    assert result.status == "completed"
    assert result.result["recommendation"]["response_pack_id"] == "account_takeover"
    assert memory.case_context is not None
    assert memory.case_context.recommended_response_pack == "account_takeover"
    assert memory.case_context.recommendation_history[-1].trigger_type == "incident_created"
    assert memory.case_memory is not None
    assert memory.case_memory.last_recommendation is not None
    assert memory.case_memory.last_recommendation.response_pack_id == "account_takeover"
    assert memory.case_memory.summary == result.result["recommendation"]["case_summary"]
    assert memory.case_memory.last_recommendation.documentation_bundle is not None
    assert memory.case_memory.last_recommendation.documentation_bundle.template_kind == "triage_note"
    assert len(memory.case_memory.recommendation_versions) == 1
    assert "SOC AI triage completed" in (
        memory.case_memory.last_recommendation.timeline_event_draft or ""
    )


@pytest.mark.asyncio
async def test_soc_case_task_handler_preserves_prior_recommendation_versions():
    initial_memory = SOCCaseMemory(
        tenant_id="tenant-1",
        incident_id="inc-1",
        current_phase="detection_and_analysis",
        current_status="investigating",
        recommendation_versions=[
            {
                "recommendation_id": "rec-prior",
                "case_summary": "Prior recommendation",
                "response_pack_id": "manual_investigation",
                "response_pack_label": "Manual investigation",
                "confidence": 0.25,
                "rationale": ["Initial analyst review pending"],
            }
        ],
    )
    memory = FakeMemoryStore(case_context=_sample_case_context(), case_memory=initial_memory)
    handler = SOCCaseTaskHandler(
        memory=memory,
        catalog_loader=lambda: list(SAMPLE_PLAYBOOKS),
    )

    task = AgentTask(
        tenant_id="tenant-1",
        incident_id="inc-1",
        case_id="case-1",
        agent_id="soc_case_agent",
        task_type="refresh_case_after_action",
        payload={"source_kind": "ticket_update"},
        context={
            "trigger_event": {
                "trigger_type": "ticket_updated",
                "incident_id": "inc-1",
                "tenant_id": "tenant-1",
                "source_kind": "ticket_update",
            }
        },
    )

    await handler.handle(task)

    assert memory.case_memory is not None
    assert len(memory.case_memory.recommendation_versions) == 2
    assert memory.case_memory.recommendation_versions[0].recommendation_id == "rec-prior"
    assert memory.case_memory.recommendation_versions[-1].response_pack_id == "account_takeover"


@pytest.mark.asyncio
async def test_agent_loop_routes_soc_case_tasks_to_deterministic_handler():
    case_context = _sample_case_context()
    case_memory = SOCCaseMemory(
        tenant_id="tenant-1",
        incident_id="inc-1",
        current_phase="detection_and_analysis",
        current_status="new",
    )
    memory = FakeMemoryStore(case_context=case_context, case_memory=case_memory)
    queue = FakeTaskQueue()
    llm_client = FakeLLMClient()
    tool_registry = SimpleNamespace()
    loop = AgentLoop(
        agent_def=SOC_CASE_AGENT,
        task_queue=queue,
        tool_registry=tool_registry,
        memory=memory,
        llm_client=llm_client,
    )

    task = AgentTask(
        tenant_id="tenant-1",
        incident_id="inc-1",
        case_id="case-1",
        agent_id="soc_case_agent",
        task_type="refresh_case_after_action",
        payload={"source_kind": "ticket_update"},
        context={
            "trigger_event": {
                "trigger_type": "ticket_updated",
                "incident_id": "inc-1",
                "tenant_id": "tenant-1",
                "source_kind": "ticket_update",
            }
        },
    )

    result = await loop.execute_task(task)

    assert result.status == "completed"
    assert result.result["trigger_type"] == "ticket_updated"
    assert result.result["recommendation"]["response_pack_id"] == "account_takeover"
    assert queue.completed is not None
    assert queue.completed[0] == task.id
    assert llm_client.calls == 0
    assert memory.saved_memories
