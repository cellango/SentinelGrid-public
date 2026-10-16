"""HTTP client helpers for submitting SOC case-agent tasks to the runtime."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .soc_models import SOCIncidentTriggerEvent

logger = logging.getLogger(__name__)


class SOCCaseRuntimeClient:
    """Small client for submitting SOC case refresh tasks across services."""

    def __init__(
        self,
        *,
        runtime_url: str | None,
        internal_token: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.runtime_url = (runtime_url or "").rstrip("/")
        self.internal_token = internal_token
        self.timeout_seconds = timeout_seconds

    def submit_case_refresh_sync(
        self,
        *,
        tenant_id: str,
        incident_id: str,
        trigger_type: str,
        source_kind: str,
        case_id: str | None = None,
        source_event_id: str | None = None,
        changed_fields: list[str] | None = None,
        reason: str | None = None,
        priority: str = "medium",
        payload: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Submit a refresh task using a blocking HTTP call."""
        request_payload = self._build_request_payload(
            tenant_id=tenant_id,
            incident_id=incident_id,
            case_id=case_id,
            trigger_type=trigger_type,
            source_kind=source_kind,
            source_event_id=source_event_id,
            changed_fields=changed_fields or [],
            reason=reason,
            priority=priority,
            payload=payload or {},
            context=context or {},
        )
        if not request_payload:
            return None

        headers = {
            "Authorization": f"Bearer {self.internal_token}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.runtime_url}/agents/tasks",
                json=request_payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json() if response.content else {}

    async def submit_case_refresh(
        self,
        *,
        tenant_id: str,
        incident_id: str,
        trigger_type: str,
        source_kind: str,
        case_id: str | None = None,
        source_event_id: str | None = None,
        changed_fields: list[str] | None = None,
        reason: str | None = None,
        priority: str = "medium",
        payload: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Submit a refresh task using an async HTTP call."""
        request_payload = self._build_request_payload(
            tenant_id=tenant_id,
            incident_id=incident_id,
            case_id=case_id,
            trigger_type=trigger_type,
            source_kind=source_kind,
            source_event_id=source_event_id,
            changed_fields=changed_fields or [],
            reason=reason,
            priority=priority,
            payload=payload or {},
            context=context or {},
        )
        if not request_payload:
            return None

        headers = {
            "Authorization": f"Bearer {self.internal_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.runtime_url}/agents/tasks",
                json=request_payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json() if response.content else {}

    def record_feedback_sync(
        self,
        *,
        incident_id: str,
        tenant_id: str,
        recommendation_id: str,
        feedback_type: str,
        actor_id: str,
        actor_role: str,
        accepted: bool,
        action_id: str | None = None,
        playbook_id: str | None = None,
        playbook_key: str | None = None,
        playbook_name: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any] | None:
        """Persist analyst feedback for a SOC recommendation cycle."""
        if not self.runtime_url:
            logger.warning(
                "SOC case runtime URL is not configured; skipping feedback for incident %s",
                incident_id,
            )
            return None

        headers = {
            "Authorization": f"Bearer {self.internal_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "tenant_id": tenant_id,
            "recommendation_id": recommendation_id,
            "feedback_type": feedback_type,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "accepted": accepted,
            "action_id": action_id,
            "playbook_id": playbook_id,
            "playbook_key": playbook_key,
            "playbook_name": playbook_name,
            "notes": notes,
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.runtime_url}/agents/cases/{incident_id}/feedback",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json() if response.content else {}

    def _build_request_payload(
        self,
        *,
        tenant_id: str,
        incident_id: str,
        case_id: str | None,
        trigger_type: str,
        source_kind: str,
        source_event_id: str | None,
        changed_fields: list[str],
        reason: str | None,
        priority: str,
        payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not self.runtime_url:
            logger.warning(
                "SOC case runtime URL is not configured; skipping refresh for incident %s",
                incident_id,
            )
            return None

        trigger_event = SOCIncidentTriggerEvent(
            trigger_type=trigger_type,  # type: ignore[arg-type]
            incident_id=incident_id,
            tenant_id=tenant_id,
            source_kind=source_kind,
            source_event_id=source_event_id,
            changed_fields=changed_fields,
            reason=reason,
        )
        return {
            "tenant_id": tenant_id,
            "incident_id": incident_id,
            "case_id": case_id or incident_id,
            "agent_id": "soc_case_agent",
            "task_type": "triage_new_incident"
            if trigger_type == "incident_created"
            else "refresh_case_after_action",
            "priority": priority,
            "payload": {
                **payload,
                "trigger_type": trigger_type,
                "source_kind": source_kind,
            },
            "context": {
                **context,
                "trigger_event": trigger_event.model_dump(mode="json"),
            },
        }
