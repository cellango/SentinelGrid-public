"""Focused tests for incident-triggered SOC case-agent wiring."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import httpx
import pytest

from sg_agent_runtime.soc_models import SOCCaseContext, SOCIncidentTriggerEvent

from app.services.incident_creator import IncidentCreator
from app.services.soc_case_agent_bridge import SOCCaseAgentBridge


class FakeMemoryStore:
    """Test double for the Redis-backed SOC case memory store."""

    stored_contexts = []
    stored_memories = []

    def __init__(self, redis_url=None):
        self.redis_url = redis_url

    async def connect(self):
        return None

    async def close(self):
        return None

    async def store_case_context(self, case_context):
        self.__class__.stored_contexts.append(case_context)

    async def store_case_memory(self, case_memory):
        self.__class__.stored_memories.append(case_memory)


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeAsyncClient:
    calls = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, headers=None):
        self.__class__.calls.append({"url": url, "json": json, "headers": headers})
        return DummyResponse({"id": "task-123"})


class FakeDB:
    def __init__(self):
        self.executed = []
        self.commit_calls = 0
        self.rollback_calls = 0

    def execute(self, statement, params):
        self.executed.append({"statement": str(statement), "params": params})
        return SimpleNamespace()

    def commit(self):
        self.commit_calls += 1

    def rollback(self):
        self.rollback_calls += 1


@pytest.mark.asyncio
async def test_soc_case_agent_bridge_persists_case_state_and_submits_task(monkeypatch):
    FakeMemoryStore.stored_contexts = []
    FakeMemoryStore.stored_memories = []
    FakeAsyncClient.calls = []
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    bridge = SOCCaseAgentBridge(
        runtime_url="http://agent-runtime:8000",
        internal_token="internal-token",
        redis_url="redis://fake:6379",
        memory_store_factory=FakeMemoryStore,
    )

    case_context = SOCCaseContext(
        incident_id="inc-1",
        tenant_id="tenant-1",
        incident_title="Suspicious login",
        incident_type="account_takeover",
        severity="high",
        status="new",
        phase="detection_and_analysis",
        related_detections=[{"id": "det-1", "source": "opensearch_detection", "label": "Impossible travel"}],
        open_questions=["Confirm the affected identity."],
    )
    trigger_event = SOCIncidentTriggerEvent(
        trigger_type="incident_created",
        incident_id="inc-1",
        tenant_id="tenant-1",
        source_kind="detection_event",
        source_event_id="det-1",
    )

    result = await bridge.initialize_case(case_context, trigger_event)

    assert result == {"case_id": "inc-1", "task_id": "task-123"}
    assert FakeMemoryStore.stored_contexts[0].incident_id == "inc-1"
    assert FakeMemoryStore.stored_memories[0].incident_id == "inc-1"
    assert FakeAsyncClient.calls[0]["url"] == "http://agent-runtime:8000/agents/tasks"
    assert FakeAsyncClient.calls[0]["json"]["agent_id"] == "soc_case_agent"
    assert FakeAsyncClient.calls[0]["json"]["incident_id"] == "inc-1"
    assert FakeAsyncClient.calls[0]["json"]["task_type"] == "triage_new_incident"


@pytest.mark.asyncio
async def test_incident_creator_triggers_soc_case_agent_for_new_incident():
    fake_db = FakeDB()
    fake_bridge = SimpleNamespace(
        initialize_case=AsyncMock(return_value={"case_id": "case-1", "task_id": "task-123"})
    )
    creator = IncidentCreator(fake_db, soc_case_agent_bridge=fake_bridge)
    creator.dedup_service = SimpleNamespace(
        process_detection_event=AsyncMock(return_value=(True, None, None)),
        create_dedup_record=AsyncMock(return_value=None),
    )
    creator._create_traceability_records = AsyncMock(return_value=None)
    creator._extract_observables = AsyncMock(return_value=None)
    creator._handle_playbook_execution = AsyncMock(return_value=None)

    detection_event = {
        "event_id": "det-42",
        "sg": {
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "alert_type": "ACCOUNT-COMPROMISE",
            "severity": "high",
            "category": "identity",
        },
        "rule": {"name": "Impossible travel detected"},
        "user": {"email": "alice@example.com"},
        "host": {"name": "laptop-7"},
        "source": {"ip": "10.10.10.7"},
    }

    result = await creator.create_incident_from_detection(
        detection_event=detection_event,
        tenant_id="11111111-1111-1111-1111-111111111111",
    )

    assert result["soc_case_task_id"] == "task-123"
    fake_bridge.initialize_case.assert_awaited_once()
    case_context, trigger_event = fake_bridge.initialize_case.await_args.args
    assert case_context.incident_title == "Impossible travel detected - User: alice@example.com"
    assert case_context.tenant_id == "11111111-1111-1111-1111-111111111111"
    assert trigger_event.trigger_type == "incident_created"
    assert trigger_event.source_event_id == "det-42"
    assert fake_db.commit_calls >= 1
