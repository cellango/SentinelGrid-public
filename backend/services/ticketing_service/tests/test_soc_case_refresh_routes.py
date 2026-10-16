"""Focused tests for ticketing-to-SOC-case refresh wiring."""

from __future__ import annotations

from uuid import UUID

from app.api import tickets


TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")


def test_submit_soc_case_refresh_uses_shared_runtime_client(monkeypatch):
    captured = {}

    class _RuntimeClient:
        def __init__(self, *, runtime_url, internal_token):
            captured["runtime_url"] = runtime_url
            captured["internal_token"] = internal_token

        def submit_case_refresh_sync(self, **kwargs):
            captured["kwargs"] = kwargs
            return {"id": "task-123"}

    monkeypatch.setattr(tickets.settings, "AGENT_RUNTIME_URL", "http://agent-runtime:8000", raising=False)
    monkeypatch.setattr(tickets.settings, "INTERNAL_SERVICE_TOKEN", "internal-token", raising=False)
    monkeypatch.setattr(tickets, "SOCCaseRuntimeClient", _RuntimeClient)

    result = tickets._submit_soc_case_refresh(
        TENANT_ID,
        "incident-1",
        "ticket-1",
        ["assigned_to", "status"],
        "Ticket fields were updated for a linked incident.",
    )

    assert result == {"id": "task-123"}
    assert captured["runtime_url"] == "http://agent-runtime:8000"
    assert captured["internal_token"] == "internal-token"
    assert captured["kwargs"] == {
        "tenant_id": str(TENANT_ID),
        "incident_id": "incident-1",
        "trigger_type": "ticket_updated",
        "source_kind": "ticket_update",
        "source_event_id": "ticket-1",
        "changed_fields": ["assigned_to", "status"],
        "reason": "Ticket fields were updated for a linked incident.",
    }


def test_submit_soc_case_refresh_best_effort_does_not_fail_ticket_write(monkeypatch, caplog):
    def _raise(*args, **kwargs):
        raise RuntimeError("runtime unavailable")

    monkeypatch.setattr(tickets, "_submit_soc_case_refresh", _raise)

    result = tickets._submit_soc_case_refresh_best_effort(
        TENANT_ID,
        "incident-1",
        "ticket-1",
        ["comment"],
        "A linked ticket comment was added by an operator.",
    )

    assert result is None
    assert "Failed submitting SOC case refresh" in caplog.text
