from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.schemas import TelemetryEventCreate
from app.services.siem_export_interface import NormalizedSiemEvent


def _severity_for_event(event: TelemetryEventCreate) -> str:
    if event.policy_decision == "blocked" and event.has_secrets:
        return "critical"
    if event.policy_decision == "blocked" and (event.prompt_injection_suspected or event.has_pii):
        return "high"
    if event.has_secrets:
        return "high"
    if event.prompt_injection_suspected or event.has_pii:
        return "medium"
    if event.policy_decision == "blocked":
        return "medium"
    if event.policy_decision == "allowed":
        return "info"
    return "low"


def _event_type_for_event(event: TelemetryEventCreate) -> str:
    if event.policy_decision == "blocked":
        return "ai.request.blocked"
    return "ai.request.allowed"


def normalize_ai_event(event: TelemetryEventCreate) -> NormalizedSiemEvent:
    occurred_at = event.created_at or datetime.now(timezone.utc)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)

    previews = {}
    if event.prompt_preview:
        previews["prompt"] = event.prompt_preview
    if event.response_preview:
        previews["response"] = event.response_preview

    labels = {}
    if event.violation_reason:
        labels["violation_reason"] = event.violation_reason

    return NormalizedSiemEvent(
        event_id=event.event_id or f"telemetry:{uuid4()}",
        event_type=_event_type_for_event(event),
        occurred_at=occurred_at.astimezone(timezone.utc),
        tenant_id=str(event.org_id),
        realm=event.realm,
        ai_app_id=str(event.ai_app_id) if event.ai_app_id else None,
        user_id=event.user_id,
        provider=event.provider,
        model=event.model,
        policy_decision=event.policy_decision,
        severity=_severity_for_event(event),
        risk_flags={
            "has_pii": event.has_pii,
            "has_secrets": event.has_secrets,
            "prompt_injection_suspected": event.prompt_injection_suspected,
        },
        metrics={
            "tokens_in": event.tokens_in or 0,
            "tokens_out": event.tokens_out or 0,
        },
        previews=previews,
        labels=labels,
        raw=event.model_dump(mode="json", exclude_none=True),
    )
