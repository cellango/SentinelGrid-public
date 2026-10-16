"""Bridge from SOAR incident creation into the SOC agent runtime."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from sg_agent_runtime.memory import AgentMemoryStore
from sg_agent_runtime.soc_models import (
    SOCCaseContext,
    SOCCaseMemory,
    SOCIncidentTriggerEvent,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class SOCCaseAgentBridge:
    """Persists initial case state and submits the SOC case-agent task."""

    def __init__(
        self,
        *,
        runtime_url: str | None = None,
        internal_token: str | None = None,
        redis_url: str | None = None,
        memory_store_factory: type[AgentMemoryStore] = AgentMemoryStore,
    ) -> None:
        self.runtime_url = (runtime_url or getattr(settings, "AGENT_RUNTIME_URL", None) or "").rstrip("/")
        self.internal_token = internal_token or settings.INTERNAL_SERVICE_TOKEN
        self.redis_url = redis_url or settings.REDIS_URL
        self.memory_store_factory = memory_store_factory

    async def initialize_case(
        self,
        case_context: SOCCaseContext,
        trigger_event: SOCIncidentTriggerEvent,
    ) -> dict[str, Any]:
        """Persist case state and submit the first SOC case-agent task."""
        await self._persist_case_state(case_context)
        task_id = await self._submit_case_task(case_context, trigger_event)
        return {
            "case_id": case_context.case_id,
            "task_id": task_id,
        }

    async def _persist_case_state(self, case_context: SOCCaseContext) -> None:
        memory_store = self.memory_store_factory(self.redis_url)
        await memory_store.connect()
        try:
            await memory_store.store_case_context(case_context)
            await memory_store.store_case_memory(
                SOCCaseMemory(
                    tenant_id=case_context.tenant_id,
                    incident_id=case_context.incident_id,
                    case_id=case_context.case_id,
                    summary=(
                        f"Incident '{case_context.incident_title}' entered the SOC AI workflow "
                        f"in phase '{case_context.phase}'."
                    ),
                    current_phase=case_context.phase,
                    current_status=case_context.status,
                    open_questions=list(case_context.open_questions),
                    evidence_snapshot=[
                        *(record.label or record.id for record in case_context.related_detections),
                        *(record.label or record.id for record in case_context.related_observables),
                    ],
                )
            )
        finally:
            await memory_store.close()

    async def _submit_case_task(
        self,
        case_context: SOCCaseContext,
        trigger_event: SOCIncidentTriggerEvent,
    ) -> str | None:
        if not self.runtime_url:
            logger.warning(
                "SOC case agent runtime URL is not configured; skipping task submission for incident %s",
                case_context.incident_id,
            )
            return None

        payload = {
            "tenant_id": case_context.tenant_id,
            "incident_id": case_context.incident_id,
            "case_id": case_context.case_id,
            "agent_id": "soc_case_agent",
            "task_type": self._task_type_for_trigger(trigger_event.trigger_type),
            "priority": self._priority_for_severity(case_context.severity),
            "payload": {
                "trigger_type": trigger_event.trigger_type,
                "source_kind": trigger_event.source_kind,
                "source_event_id": trigger_event.source_event_id,
            },
            "context": {
                "case_context": case_context.model_dump(mode="json"),
                "trigger_event": trigger_event.model_dump(mode="json"),
            },
        }

        headers = {
            "Authorization": f"Bearer {self.internal_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.runtime_url}/agents/tasks",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json() or {}
            task_id = data.get("id")
            logger.info(
                "Submitted SOC case-agent task %s for incident %s",
                task_id,
                case_context.incident_id,
            )
            return task_id

    @staticmethod
    def _priority_for_severity(severity: str | None) -> str:
        normalized = str(severity or "").lower()
        if normalized == "critical":
            return "critical"
        if normalized == "high":
            return "high"
        if normalized == "medium":
            return "medium"
        return "low"

    @staticmethod
    def _task_type_for_trigger(trigger_type: str) -> str:
        if trigger_type == "incident_created":
            return "triage_new_incident"
        return "refresh_case_after_action"
