"""Deterministic runtime handler for SOC case-agent tasks."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Callable

from .memory import AgentMemoryStore
from .models import AgentTask, TaskResult
from .playbook_ir_loader import load_planner_playbooks
from .soc_models import (
    SOCIncidentTriggerEvent,
    SOCRecommendationHistoryEntry,
    SOCCaseContext,
    SOCCaseMemory,
)
from .soc_response_planner import SOCResponsePlanner


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SOCCaseTaskHandler:
    """Runs deterministic case planning for the visible SOC AI agent."""

    SUPPORTED_TASK_TYPES = {"triage_new_incident", "refresh_case_after_action"}
    MAX_RECOMMENDATION_VERSIONS = 12

    def __init__(
        self,
        *,
        memory: AgentMemoryStore,
        planner: SOCResponsePlanner | None = None,
        catalog_loader: Callable[[], list[dict[str, Any]]] = load_planner_playbooks,
    ) -> None:
        self.memory = memory
        self.planner = planner or SOCResponsePlanner()
        self.catalog_loader = catalog_loader

    @classmethod
    def supports(cls, task: AgentTask) -> bool:
        return task.agent_id == "soc_case_agent" and task.task_type in cls.SUPPORTED_TASK_TYPES

    async def handle(self, task: AgentTask) -> TaskResult:
        """Load the case state, generate a response plan, and persist the result."""
        if not task.incident_id:
            raise ValueError("SOC case-agent tasks require incident_id")

        start = time.monotonic()
        case_context = await self._load_case_context(task)
        case_memory = await self._load_case_memory(task, case_context)
        incident_data = self._build_incident_payload(task, case_context, case_memory)
        recommendation = self.planner.recommend_response_plan(
            incident_data,
            available_playbooks=self.catalog_loader(),
        )

        trigger_type = self._resolve_trigger_type(task)
        history_entry = SOCRecommendationHistoryEntry(
            recommendation_id=recommendation.recommendation_id,
            trigger_type=trigger_type,
            response_pack_id=recommendation.response_pack_id,
            top_playbook_keys=[
                playbook.playbook_key or playbook.playbook_name
                for playbook in recommendation.recommended_playbooks[:3]
            ],
            action_ids=[action.action_id for action in recommendation.recommended_actions],
            confidence=recommendation.confidence,
            rationale=list(recommendation.rationale),
        )

        case_context.recommended_response_pack = recommendation.response_pack_id
        case_context.recommended_playbooks = list(recommendation.recommended_playbooks)
        case_context.status = recommendation.proposed_status or case_context.status
        case_context.phase = recommendation.proposed_phase or case_context.phase
        case_context.open_questions = self._merge_unique(
            case_context.open_questions,
            recommendation.missing_evidence,
        )
        case_context.recommendation_history.append(history_entry)
        case_context.updated_at = _utcnow()

        case_memory.summary = recommendation.case_summary
        case_memory.current_phase = recommendation.proposed_phase or case_memory.current_phase
        case_memory.current_status = recommendation.proposed_status or case_memory.current_status
        case_memory.open_questions = list(case_context.open_questions)
        case_memory.evidence_snapshot = self._build_evidence_snapshot(case_context)
        case_memory.recommendation_history.append(history_entry)
        case_memory.recommendation_versions.append(recommendation)
        case_memory.recommendation_versions = case_memory.recommendation_versions[-self.MAX_RECOMMENDATION_VERSIONS :]
        case_memory.feedback_history = list(case_context.feedback_history)
        case_memory.last_recommendation = recommendation
        case_memory.last_refreshed_at = _utcnow()

        await self.memory.store_case_context(case_context)
        await self.memory.store_case_memory(case_memory)

        result_payload = {
            "answer": recommendation.case_summary,
            "incident_id": case_context.incident_id,
            "case_id": case_context.case_id,
            "trigger_type": trigger_type,
            "recommendation": recommendation.model_dump(mode="json"),
            "case_context": case_context.model_dump(mode="json"),
        }
        return TaskResult(
            task_id=task.id,
            status="completed",
            result=result_payload,
            actions_taken=[
                {
                    "type": "soc_case_recommendation",
                    "response_pack_id": recommendation.response_pack_id,
                    "playbook_keys": history_entry.top_playbook_keys,
                }
            ],
            tokens_used=0,
            duration_seconds=time.monotonic() - start,
        )

    async def _load_case_context(self, task: AgentTask) -> SOCCaseContext:
        raw_context = task.context.get("case_context")
        if raw_context:
            return SOCCaseContext.model_validate(raw_context)

        stored = await self.memory.recall_case_context(task.tenant_id, task.incident_id or "")
        if stored is not None:
            return stored

        payload = task.payload
        return SOCCaseContext(
            incident_id=task.incident_id or task.id,
            tenant_id=task.tenant_id,
            case_id=task.case_id,
            incident_title=str(payload.get("incident_title") or f"Incident {task.incident_id or task.id}"),
            incident_type=str(payload.get("incident_type") or payload.get("category") or "security_incident"),
            severity=str(payload.get("severity") or "unknown"),
            status=str(payload.get("status") or "new"),
            phase=str(payload.get("phase") or "detection_and_analysis"),
        )

    async def _load_case_memory(
        self,
        task: AgentTask,
        case_context: SOCCaseContext,
    ) -> SOCCaseMemory:
        stored = await self.memory.recall_case_memory(task.tenant_id, task.incident_id or "")
        if stored is not None:
            return stored

        return SOCCaseMemory(
            tenant_id=case_context.tenant_id,
            incident_id=case_context.incident_id,
            case_id=case_context.case_id,
            summary=case_context.incident_title,
            current_phase=case_context.phase,
            current_status=case_context.status,
            open_questions=list(case_context.open_questions),
            evidence_snapshot=self._build_evidence_snapshot(case_context),
            feedback_history=list(case_context.feedback_history),
        )

    def _build_incident_payload(
        self,
        task: AgentTask,
        case_context: SOCCaseContext,
        case_memory: SOCCaseMemory,
    ) -> dict[str, Any]:
        trigger_event = self._load_trigger_event(task)
        return {
            "title": case_context.incident_title,
            "incident_type": case_context.incident_type,
            "category": case_context.incident_type,
            "severity": case_context.severity,
            "status": case_context.status,
            "phase": case_context.phase,
            "source": trigger_event.source_kind if trigger_event else task.payload.get("source_kind"),
            "story_domains": self._derive_story_domains(case_context),
            "related_detections": [
                record.model_dump(mode="json") for record in case_context.related_detections
            ],
            "entities": [record.model_dump(mode="json") for record in case_context.entities],
            "evidence": [
                record.model_dump(mode="json")
                for record in [*case_context.related_alerts, *case_context.related_observables]
            ],
            "ticket_id": case_context.ticket_refs[0].id if case_context.ticket_refs else None,
            "recommended_playbook_key": (
                case_context.recommended_playbooks[0].playbook_key
                if case_context.recommended_playbooks
                else None
            ),
            "mitre_tactics": list(case_context.mitre_tactics),
            "mitre_techniques": list(case_context.mitre_techniques),
            "nist_controls": list(case_context.nist_controls),
            "raw_payload": {
                **task.payload,
                "summary": case_memory.summary or case_context.incident_title,
                "source_kind": trigger_event.source_kind if trigger_event else task.payload.get("source_kind"),
                "trigger_type": trigger_event.trigger_type if trigger_event else self._resolve_trigger_type(task),
            },
        }

    def _derive_story_domains(self, case_context: SOCCaseContext) -> list[str]:
        domain_tokens: list[str] = []
        record_sets = (
            case_context.related_alerts,
            case_context.related_detections,
            case_context.related_observables,
            case_context.entities,
        )
        for record_group in record_sets:
            for record in record_group:
                domain_tokens.append(record.source)
                domain_tokens.extend(record.metadata.values())
        domain_tokens.append(case_context.incident_type)
        normalized_tokens = [token.replace("_", " ") for token in domain_tokens if token]
        canonical_domains: list[str] = []
        for token in normalized_tokens:
            lowered = token.lower()
            if any(marker in lowered for marker in ("identity", "auth", "login", "user", "iam", "credential")):
                canonical_domains.append("identity")
            if any(marker in lowered for marker in ("mail", "email", "phish", "inbox", "message")):
                canonical_domains.append("application")
            if any(marker in lowered for marker in ("endpoint", "host", "edr", "device", "malware", "ransomware")):
                canonical_domains.append("endpoint")
            if any(marker in lowered for marker in ("cloud", "bucket", "storage", "database", "kubernetes", "container")):
                canonical_domains.append("cloud")
            if any(marker in lowered for marker in ("repo", "git", "secret", "code", "app", "application")):
                canonical_domains.append("application")
            if any(marker in lowered for marker in ("ai", "prompt", "model", "llm", "guardrail")):
                canonical_domains.append("ai")
            canonical_domains.append(token)
        canonical_domains.append("security")
        return self._merge_unique([], canonical_domains)

    def _build_evidence_snapshot(self, case_context: SOCCaseContext) -> list[str]:
        return self._merge_unique(
            [],
            [
                *(record.label or record.id for record in case_context.related_alerts),
                *(record.label or record.id for record in case_context.related_detections),
                *(record.label or record.id for record in case_context.related_observables),
                *(record.label or record.id for record in case_context.entities),
            ],
        )

    def _load_trigger_event(self, task: AgentTask) -> SOCIncidentTriggerEvent | None:
        raw = task.context.get("trigger_event")
        if not raw:
            return None
        return SOCIncidentTriggerEvent.model_validate(raw)

    @staticmethod
    def _resolve_trigger_type(task: AgentTask) -> str:
        raw = task.context.get("trigger_event")
        if isinstance(raw, dict) and raw.get("trigger_type"):
            return str(raw["trigger_type"])
        if task.task_type == "triage_new_incident":
            return "incident_created"
        return "analyst_action_recorded"

    @staticmethod
    def _merge_unique(existing: list[str], additions: list[str]) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for value in [*existing, *additions]:
            normalized = " ".join(str(value or "").split())
            if normalized and normalized not in seen:
                seen.add(normalized)
                merged.append(normalized)
        return merged
