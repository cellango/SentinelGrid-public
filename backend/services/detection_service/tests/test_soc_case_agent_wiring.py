"""Focused tests for detection-service SOC case-agent task submission."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

SERVICE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIBS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../libs"))
for path in (SERVICE_ROOT, LIBS_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.services import incident_creator as incident_creator_module  # noqa: E402
from app.services.incident_creator import IncidentCreator  # noqa: E402


TENANT_ID = "11111111-1111-1111-1111-111111111111"
TICKET_ID = "22222222-2222-2222-2222-222222222222"


class _RuntimeClient:
    calls: list[dict] = []

    def __init__(self, *, runtime_url, internal_token):
        self.runtime_url = runtime_url
        self.internal_token = internal_token

    async def submit_case_refresh(self, **kwargs):
        self.__class__.calls.append(
            {
                "runtime_url": self.runtime_url,
                "internal_token": self.internal_token,
                "kwargs": kwargs,
            }
        )
        return {"id": "task-123"}


class _TicketResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "id": TICKET_ID,
            "title": "Impossible travel",
            "external_id": "SG-tenant-123",
            "source": "internal",
        }


class _AsyncClient:
    calls: list[dict] = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, *, headers=None, json=None, params=None):
        self.__class__.calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "params": params,
            }
        )
        return _TicketResponse()


class _Query:
    def __init__(self, model):
        self.model = model

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        if getattr(self.model, "__name__", "") == "Tenant":
            return None
        return _Session.incident


class _Session:
    incident = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def query(self, model):
        return _Query(model)

    def add(self, obj):
        if obj.__class__.__name__ == "Incident":
            self.__class__.incident = obj

    def commit(self):
        return None


def _alert_data(alert_id: str | None = "alert-1") -> dict:
    return {
        "id": alert_id,
        "source": "siem",
        "title": "Impossible travel",
        "description": "A user signed in from distant locations.",
        "raw_severity": "high",
        "asset_id": "laptop-7",
        "user_identifier": "alice@example.com",
        "detection_rule_id": "SG-ID-001",
        "detection_rule_version_id": "rule-version-1",
        "recommended_playbook": "account_takeover",
        "nist_controls": ["AC-2"],
        "mitre_tactics": ["Credential Access"],
        "mitre_techniques": ["T1110"],
    }


@pytest.mark.asyncio
async def test_detection_incident_triage_task_uses_agent_runtime_client(monkeypatch):
    _RuntimeClient.calls = []
    monkeypatch.setattr(incident_creator_module, "SOCCaseRuntimeClient", _RuntimeClient)

    creator = IncidentCreator()
    creator.agent_runtime_url = "http://agent-runtime:8000"
    creator.internal_token = "internal-token"
    incident_id = uuid4()

    result = await creator._submit_soc_case_triage_task(
        tenant_id=TENANT_ID,
        incident_id=incident_id,
        alert_data=_alert_data(),
        ai_analysis={"ai_category": "identity"},
        severity="high",
        incident_raw={"related_alert_ids": ["alert-1"]},
    )

    assert result == {"id": "task-123"}
    call = _RuntimeClient.calls[0]
    assert call["runtime_url"] == "http://agent-runtime:8000"
    assert call["internal_token"] == "internal-token"
    assert call["kwargs"]["tenant_id"] == TENANT_ID
    assert call["kwargs"]["incident_id"] == str(incident_id)
    assert call["kwargs"]["trigger_type"] == "incident_created"
    assert call["kwargs"]["source_kind"] == "detection_alert"
    assert call["kwargs"]["source_event_id"] == "alert-1"
    assert call["kwargs"]["priority"] == "high"
    assert call["kwargs"]["payload"]["incident_type"] == "identity"
    assert call["kwargs"]["payload"]["user_identifier"] == "alice@example.com"
    assert call["kwargs"]["payload"]["related_alert_ids"] == ["alert-1"]


@pytest.mark.asyncio
async def test_detection_incident_creation_submits_soc_case_task_best_effort(monkeypatch):
    _Session.incident = None
    _AsyncClient.calls = []
    monkeypatch.setattr(incident_creator_module, "SessionLocal", _Session)
    monkeypatch.setattr(incident_creator_module, "publish_workflow_event", lambda **kwargs: None)
    monkeypatch.setattr(incident_creator_module.httpx, "AsyncClient", _AsyncClient)

    creator = IncidentCreator()
    creator.ticketing_service_url = "http://ticketing-service:8000"
    creator._map_to_frameworks = AsyncMock(return_value=None)
    creator._submit_soc_case_triage_task = AsyncMock(return_value={"id": "task-123"})

    result = await creator.create_incident_from_alert(
        alert_data=_alert_data(),
        ai_analysis={"ai_severity": "high", "ai_category": "identity"},
        tenant_id=UUID(TENANT_ID),
    )

    assert result["id"] == TICKET_ID
    assert result["soc_case_task_id"] == "task-123"
    creator._submit_soc_case_triage_task.assert_awaited_once()
    triage_kwargs = creator._submit_soc_case_triage_task.await_args.kwargs
    assert triage_kwargs["tenant_id"] == UUID(TENANT_ID)
    assert triage_kwargs["severity"] == "high"
    assert triage_kwargs["alert_data"]["id"] == "alert-1"
    ticket_call = _AsyncClient.calls[0]
    assert ticket_call["url"] == "http://ticketing-service:8000/api/v1/tickets"
    assert ticket_call["json"]["incident_id"] == str(triage_kwargs["incident_id"])
    assert ticket_call["params"] == {"tenant_id": TENANT_ID}


@pytest.mark.asyncio
async def test_detection_incident_creation_continues_when_soc_case_runtime_fails(monkeypatch, caplog):
    _Session.incident = None
    _AsyncClient.calls = []
    monkeypatch.setattr(incident_creator_module, "SessionLocal", _Session)
    monkeypatch.setattr(incident_creator_module, "publish_workflow_event", lambda **kwargs: None)
    monkeypatch.setattr(incident_creator_module.httpx, "AsyncClient", _AsyncClient)

    creator = IncidentCreator()
    creator.ticketing_service_url = "http://ticketing-service:8000"
    creator._map_to_frameworks = AsyncMock(return_value=None)
    creator._submit_soc_case_triage_task = AsyncMock(side_effect=RuntimeError("runtime unavailable"))

    result = await creator.create_incident_from_alert(
        alert_data=_alert_data(),
        ai_analysis={"ai_severity": "high", "ai_category": "identity"},
        tenant_id=UUID(TENANT_ID),
    )

    assert result["id"] == TICKET_ID
    assert "soc_case_task_id" not in result
    assert "Failed submitting SOC case-agent triage task" in caplog.text
