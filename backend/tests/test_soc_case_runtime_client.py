"""Focused tests for cross-service SOC case runtime submissions."""

from __future__ import annotations

import httpx

from sg_agent_runtime.soc_case_runtime_client import SOCCaseRuntimeClient


class _Response:
    content = b'{"id":"task-123"}'

    def raise_for_status(self):
        return None

    def json(self):
        return {"id": "task-123"}


class _Client:
    calls: list[dict] = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, *, json=None, headers=None):
        self.__class__.calls.append({"url": url, "json": json, "headers": headers})
        return _Response()


def test_submit_case_refresh_sync_posts_soc_case_agent_task(monkeypatch):
    _Client.calls = []
    monkeypatch.setattr(httpx, "Client", _Client)

    client = SOCCaseRuntimeClient(
        runtime_url="http://agent-runtime:8000",
        internal_token="internal-token",
    )

    result = client.submit_case_refresh_sync(
        tenant_id="tenant-1",
        incident_id="incident-1",
        trigger_type="ticket_updated",
        source_kind="ticket_update",
        source_event_id="ticket-1",
        changed_fields=["assigned_to", "status"],
        reason="Ticket fields changed.",
        payload={"status": "resolved"},
    )

    assert result == {"id": "task-123"}
    call = _Client.calls[0]
    assert call["url"] == "http://agent-runtime:8000/agents/tasks"
    assert call["headers"]["Authorization"] == "Bearer internal-token"
    assert call["json"]["agent_id"] == "soc_case_agent"
    assert call["json"]["task_type"] == "refresh_case_after_action"
    assert call["json"]["tenant_id"] == "tenant-1"
    assert call["json"]["incident_id"] == "incident-1"
    assert call["json"]["payload"]["status"] == "resolved"
    assert call["json"]["payload"]["trigger_type"] == "ticket_updated"
    assert call["json"]["payload"]["source_kind"] == "ticket_update"
    trigger_event = call["json"]["context"]["trigger_event"]
    assert trigger_event["source_event_id"] == "ticket-1"
    assert trigger_event["changed_fields"] == ["assigned_to", "status"]
    assert trigger_event["reason"] == "Ticket fields changed."


def test_submit_case_refresh_sync_is_noop_without_runtime_url(monkeypatch):
    _Client.calls = []
    monkeypatch.setattr(httpx, "Client", _Client)

    client = SOCCaseRuntimeClient(runtime_url=None, internal_token="internal-token")

    result = client.submit_case_refresh_sync(
        tenant_id="tenant-1",
        incident_id="incident-1",
        trigger_type="ticket_updated",
        source_kind="ticket_update",
    )

    assert result is None
    assert _Client.calls == []
