"""Supervised Compliance Agent workflow triggers and recommendations."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)

RECOMMENDATION_STATES = {"draft", "proposed", "accepted", "rejected", "superseded"}
DECISION_STATES = {"accepted", "rejected", "superseded"}
WRITE_ACTION_RECOMMENDATION_TYPES = {
    "create_evidence_collection_task",
    "collect_evidence",
    "create_evidence_package",
    "generate_compliance_report",
}


class ComplianceAgentWorkflowError(ValueError):
    """Raised for invalid Compliance Agent workflow input."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json(value: Any) -> str:
    return json.dumps(value or {}, default=str)


def _json_array(value: Any) -> str:
    return json.dumps(value or [], default=str)


def _row_mapping(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    if isinstance(row, dict):
        return dict(row)
    return {}


def _first_mapping(result: Any) -> dict[str, Any]:
    if hasattr(result, "mappings"):
        mapped = result.mappings()
        if hasattr(mapped, "first"):
            return _row_mapping(mapped.first())
    if hasattr(result, "first"):
        return _row_mapping(result.first())
    return {}


def _all_mappings(result: Any) -> list[dict[str, Any]]:
    if hasattr(result, "mappings"):
        mapped = result.mappings()
        if hasattr(mapped, "all"):
            return [_row_mapping(row) for row in mapped.all()]
    if hasattr(result, "all"):
        return [_row_mapping(row) for row in result.all()]
    return []


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _iso(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _normalize_priority(value: str | None) -> str:
    priority = str(value or "medium").strip().lower()
    return priority if priority in {"critical", "high", "medium", "low"} else "medium"


def _normalize_state(value: str | None) -> str:
    state = str(value or "proposed").strip().lower()
    if state not in RECOMMENDATION_STATES:
        raise ComplianceAgentWorkflowError(f"Unsupported recommendation state: {state}")
    return state


def _serialize_recommendation(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id")),
        "tenant_id": str(row.get("tenant_id")),
        "agent_task_id": row.get("agent_task_id"),
        "trigger_type": row.get("trigger_type"),
        "recommendation_type": row.get("recommendation_type"),
        "state": row.get("state"),
        "priority": row.get("priority"),
        "source_type": row.get("source_type"),
        "source_id": row.get("source_id"),
        "framework_id": row.get("framework_id"),
        "control_id": row.get("control_id"),
        "evidence_item_id": row.get("evidence_item_id"),
        "evidence_package_id": row.get("evidence_package_id"),
        "report_id": row.get("report_id"),
        "title": row.get("title"),
        "summary": row.get("summary"),
        "proposed_actions": _json_list(row.get("proposed_actions")),
        "requires_approval": bool(row.get("requires_approval")),
        "created_by": row.get("created_by"),
        "decided_by": row.get("decided_by"),
        "decided_at": _iso(row.get("decided_at")),
        "decision_notes": row.get("decision_notes"),
        "superseded_by": str(row["superseded_by"]) if row.get("superseded_by") else None,
        "idempotency_key": row.get("idempotency_key"),
        "metadata": _json_object(row.get("metadata")),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
        "deleted_at": _iso(row.get("deleted_at")),
    }


class ComplianceAgentRecommendationRepository:
    """Persistence for reviewable Compliance Agent recommendations."""

    def create_recommendation(
        self,
        db: Session,
        *,
        tenant_id: str,
        trigger_type: str,
        recommendation_type: str,
        source_type: str,
        title: str,
        summary: str,
        source_id: str | None = None,
        framework_id: str | None = None,
        control_id: str | None = None,
        evidence_item_id: str | None = None,
        evidence_package_id: str | None = None,
        report_id: str | None = None,
        priority: str = "medium",
        proposed_actions: list[dict[str, Any]] | None = None,
        requires_approval: bool = True,
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        state: str = "proposed",
    ) -> dict[str, Any]:
        state = _normalize_state(state)
        priority = _normalize_priority(priority)
        idempotency_key = idempotency_key or self._idempotency_key(
            trigger_type,
            source_type,
            source_id,
            framework_id,
            control_id,
            evidence_item_id,
            evidence_package_id,
            report_id,
        )

        existing = self.get_open_by_idempotency_key(db, tenant_id, idempotency_key)
        if existing:
            existing["duplicate"] = True
            return existing

        params = {
            "tenant_id": tenant_id,
            "trigger_type": trigger_type,
            "recommendation_type": recommendation_type,
            "state": state,
            "priority": priority,
            "source_type": source_type,
            "source_id": source_id,
            "framework_id": framework_id,
            "control_id": control_id,
            "evidence_item_id": evidence_item_id,
            "evidence_package_id": evidence_package_id,
            "report_id": report_id,
            "title": title,
            "summary": summary,
            "proposed_actions": _json_array(proposed_actions or []),
            "requires_approval": requires_approval,
            "created_by": created_by,
            "metadata": _json(metadata or {}),
            "idempotency_key": idempotency_key,
        }

        try:
            row = _first_mapping(
                db.execute(
                    text(
                        """
                        INSERT INTO compliance_agent_recommendations (
                            tenant_id, trigger_type, recommendation_type, state,
                            priority, source_type, source_id, framework_id, control_id,
                            evidence_item_id, evidence_package_id, report_id, title,
                            summary, proposed_actions, requires_approval, created_by,
                            metadata, idempotency_key
                        )
                        VALUES (
                            CAST(:tenant_id AS uuid), :trigger_type, :recommendation_type,
                            :state, :priority, :source_type, :source_id, :framework_id,
                            :control_id, :evidence_item_id, :evidence_package_id,
                            :report_id, :title, :summary,
                            CAST(:proposed_actions AS jsonb), :requires_approval,
                            :created_by, CAST(:metadata AS jsonb), :idempotency_key
                        )
                        RETURNING *
                        """
                    ),
                    params,
                )
            )
            return _serialize_recommendation(row)
        except IntegrityError:
            db.rollback()
            existing = self.get_open_by_idempotency_key(db, tenant_id, idempotency_key)
            if existing:
                existing["duplicate"] = True
                return existing
            raise

    def get_open_by_idempotency_key(
        self,
        db: Session,
        tenant_id: str,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        row = _first_mapping(
            db.execute(
                text(
                    """
                    SELECT *
                    FROM compliance_agent_recommendations
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND idempotency_key = :idempotency_key
                      AND state IN ('draft', 'proposed')
                      AND deleted_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id, "idempotency_key": idempotency_key},
            )
        )
        return _serialize_recommendation(row) if row else None

    def attach_agent_task(
        self,
        db: Session,
        *,
        tenant_id: str,
        recommendation_id: str,
        agent_task_id: str,
    ) -> dict[str, Any] | None:
        row = _first_mapping(
            db.execute(
                text(
                    """
                    UPDATE compliance_agent_recommendations
                    SET agent_task_id = :agent_task_id
                    WHERE id = CAST(:recommendation_id AS uuid)
                      AND tenant_id = CAST(:tenant_id AS uuid)
                      AND deleted_at IS NULL
                    RETURNING *
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "recommendation_id": recommendation_id,
                    "agent_task_id": agent_task_id,
                },
            )
        )
        return _serialize_recommendation(row) if row else None

    def list_recommendations(
        self,
        db: Session,
        tenant_id: str,
        *,
        state: str | None = None,
        trigger_type: str | None = None,
        source_type: str | None = None,
        framework_id: str | None = None,
        control_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        where = ["tenant_id = CAST(:tenant_id AS uuid)", "deleted_at IS NULL"]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "limit": max(1, min(limit, 200)),
            "offset": max(0, offset),
        }
        for field, value in (
            ("state", state),
            ("trigger_type", trigger_type),
            ("source_type", source_type),
            ("framework_id", framework_id),
            ("control_id", control_id),
        ):
            if value:
                where.append(f"{field} = :{field}")
                params[field] = value

        where_sql = " AND ".join(where)
        count_row = _first_mapping(
            db.execute(
                text(f"SELECT COUNT(*) AS count FROM compliance_agent_recommendations WHERE {where_sql}"),
                params,
            )
        )
        rows = _all_mappings(
            db.execute(
                text(
                    f"""
                    SELECT *
                    FROM compliance_agent_recommendations
                    WHERE {where_sql}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            )
        )
        return {
            "tenant_id": tenant_id,
            "items": [_serialize_recommendation(row) for row in rows],
            "count": int(count_row.get("count") or 0),
            "limit": params["limit"],
            "offset": params["offset"],
        }

    def record_decision(
        self,
        db: Session,
        *,
        tenant_id: str,
        recommendation_id: str,
        state: str,
        decided_by: str,
        decision_notes: str | None = None,
        superseded_by: str | None = None,
    ) -> dict[str, Any] | None:
        state = _normalize_state(state)
        if state not in DECISION_STATES:
            raise ComplianceAgentWorkflowError(
                "Recommendation decisions must be accepted, rejected, or superseded"
            )
        row = _first_mapping(
            db.execute(
                text(
                    """
                    UPDATE compliance_agent_recommendations
                    SET state = :state,
                        decided_by = :decided_by,
                        decided_at = NOW(),
                        decision_notes = :decision_notes,
                        superseded_by = CASE
                            WHEN :superseded_by IS NULL THEN superseded_by
                            ELSE CAST(:superseded_by AS uuid)
                        END
                    WHERE id = CAST(:recommendation_id AS uuid)
                      AND tenant_id = CAST(:tenant_id AS uuid)
                      AND deleted_at IS NULL
                    RETURNING *
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "recommendation_id": recommendation_id,
                    "state": state,
                    "decided_by": decided_by,
                    "decision_notes": decision_notes,
                    "superseded_by": superseded_by,
                },
            )
        )
        return _serialize_recommendation(row) if row else None

    def _idempotency_key(self, *parts: str | None) -> str:
        body = ":".join(str(part or "") for part in parts)
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"sentinelgrid:compliance-agent:{body}"))


class ComplianceAgentRuntimeClient:
    """HTTP client for submitting Compliance Agent tasks."""

    def __init__(
        self,
        *,
        runtime_url: str | None,
        internal_token: str | None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.runtime_url = (runtime_url or "").rstrip("/")
        self.internal_token = internal_token or ""
        self.timeout_seconds = timeout_seconds

    async def submit_compliance_task(
        self,
        *,
        tenant_id: str,
        trigger_type: str,
        source_type: str,
        recommendation: dict[str, Any],
        priority: str,
        payload: dict[str, Any] | None = None,
        authorization: str | None = None,
        actor_id: str | None = None,
    ) -> dict[str, Any] | None:
        if not self.runtime_url:
            logger.warning("Agent runtime URL is not configured; skipping compliance task submission")
            return None

        task_payload = {
            "tenant_id": tenant_id,
            "agent_id": "compliance_agent",
            "task_type": trigger_type,
            "priority": priority,
            "payload": {
                **(payload or {}),
                "trigger_type": trigger_type,
                "source_type": source_type,
                "recommendation_id": recommendation.get("id"),
                "recommendation_type": recommendation.get("recommendation_type"),
                "proposed_actions": recommendation.get("proposed_actions") or [],
                "supervision": {
                    "mode": "human_approval_required",
                    "write_actions_require_approval": True,
                    "read_only_summary_allowed": True,
                },
            },
            "context": {
                "trigger_event": {
                    "trigger_type": trigger_type,
                    "tenant_id": tenant_id,
                    "source_type": source_type,
                    "source_id": recommendation.get("source_id"),
                    "recommendation_id": recommendation.get("id"),
                },
                "auth": {
                    "authorization": authorization,
                    "user_id": actor_id,
                },
            },
        }
        headers = {
            "Authorization": f"Bearer {self.internal_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.runtime_url}/agents/tasks",
                json=task_payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json() if response.content else {}


class ComplianceAgentWorkflowService:
    """Creates supervised recommendations and optional agent runtime tasks."""

    def __init__(
        self,
        *,
        repository: ComplianceAgentRecommendationRepository | None = None,
        runtime_client: ComplianceAgentRuntimeClient | None = None,
        enabled: bool = False,
    ) -> None:
        self.repository = repository or ComplianceAgentRecommendationRepository()
        self.runtime_client = runtime_client
        self.enabled = enabled

    async def create_recommendation_and_task(
        self,
        db: Session,
        *,
        tenant_id: str,
        trigger_type: str,
        recommendation_type: str,
        source_type: str,
        title: str,
        summary: str,
        priority: str = "medium",
        source_id: str | None = None,
        framework_id: str | None = None,
        control_id: str | None = None,
        evidence_item_id: str | None = None,
        evidence_package_id: str | None = None,
        report_id: str | None = None,
        proposed_actions: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        created_by: str | None = None,
        authorization: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return None

        requires_approval = recommendation_type in WRITE_ACTION_RECOMMENDATION_TYPES
        recommendation = self.repository.create_recommendation(
            db,
            tenant_id=tenant_id,
            trigger_type=trigger_type,
            recommendation_type=recommendation_type,
            source_type=source_type,
            source_id=source_id,
            framework_id=framework_id,
            control_id=control_id,
            evidence_item_id=evidence_item_id,
            evidence_package_id=evidence_package_id,
            report_id=report_id,
            title=title,
            summary=summary,
            priority=priority,
            proposed_actions=proposed_actions or [],
            requires_approval=requires_approval,
            created_by=created_by,
            metadata=metadata or {},
            idempotency_key=idempotency_key,
        )

        if recommendation.get("duplicate"):
            return recommendation

        if self.runtime_client is None:
            return recommendation

        try:
            task_response = await self.runtime_client.submit_compliance_task(
                tenant_id=tenant_id,
                trigger_type=trigger_type,
                source_type=source_type,
                recommendation=recommendation,
                priority=priority,
                payload=metadata or {},
                authorization=authorization,
                actor_id=created_by,
            )
        except Exception as exc:  # pragma: no cover - caller should not fail because async agent task failed.
            logger.warning("Failed to submit Compliance Agent task for %s: %s", trigger_type, exc)
            return recommendation

        task_id = (task_response or {}).get("id")
        if task_id:
            updated = self.repository.attach_agent_task(
                db,
                tenant_id=tenant_id,
                recommendation_id=recommendation["id"],
                agent_task_id=task_id,
            )
            return updated or recommendation
        return recommendation


def build_framework_selected_recommendation(
    *,
    framework_id: str,
    framework_name: str | None = None,
) -> dict[str, Any]:
    label = framework_name or framework_id
    return {
        "trigger_type": "framework_selected",
        "recommendation_type": "read_only_summary",
        "source_type": "framework",
        "source_id": framework_id,
        "framework_id": framework_id,
        "title": f"Assess {label} readiness",
        "summary": (
            f"{label} was selected for this tenant. Review coverage, open gaps, "
            "and evidence requirements before proposing collection work."
        ),
        "priority": "medium",
        "proposed_actions": [
            {
                "action": "summarize_framework_coverage",
                "requires_approval": False,
                "tool": "get_framework_coverage",
                "arguments": {"framework_id": framework_id},
            }
        ],
    }


def build_evidence_collected_recommendation(evidence: dict[str, Any]) -> dict[str, Any]:
    evidence_id = str(evidence.get("id") or evidence.get("evidence_item_id") or "")
    control_id = evidence.get("control_id")
    framework_id = evidence.get("framework_id")
    return {
        "trigger_type": "evidence_collection_completed",
        "recommendation_type": "read_only_summary",
        "source_type": "evidence",
        "source_id": evidence_id,
        "evidence_item_id": evidence_id,
        "framework_id": framework_id,
        "control_id": control_id,
        "title": "Review newly collected compliance evidence",
        "summary": (
            "New evidence was collected. Review linked controls, validity window, "
            "and whether related gaps can move to ready for review."
        ),
        "priority": "medium",
        "proposed_actions": [
            {
                "action": "summarize_evidence_links",
                "requires_approval": False,
                "tool": "list_evidence",
                "arguments": {"control_id": control_id} if control_id else {},
            }
        ],
    }


def build_evidence_expiration_recommendation(
    evidence: dict[str, Any],
    *,
    expired: bool,
) -> dict[str, Any]:
    evidence_id = str(evidence.get("id") or evidence.get("evidence_item_id") or "")
    control_id = evidence.get("control_id")
    title = "Replace expired compliance evidence" if expired else "Refresh expiring compliance evidence"
    summary = (
        "Evidence has expired and should be replaced before audit use."
        if expired
        else "Evidence is approaching expiration and should be refreshed before it becomes unusable."
    )
    return {
        "trigger_type": "evidence_expired" if expired else "evidence_expiring",
        "recommendation_type": "create_evidence_collection_task",
        "source_type": "evidence",
        "source_id": evidence_id,
        "evidence_item_id": evidence_id,
        "control_id": control_id,
        "framework_id": evidence.get("framework_id"),
        "title": title,
        "summary": summary,
        "priority": "high" if expired else "medium",
        "proposed_actions": [
            {
                "action": "create_evidence_collection_task",
                "requires_approval": True,
                "tool": "create_evidence_collection_task",
                "arguments": {
                    "task_name": title,
                    "task_type": "refresh_expired_evidence" if expired else "refresh_expiring_evidence",
                    "source_system": evidence.get("source_system"),
                    "source_resource_id": evidence.get("source_resource_id"),
                    "metadata": {"evidence_item_id": evidence_id, "control_id": control_id},
                },
            }
        ],
    }


def build_report_generation_recommendation(report: dict[str, Any]) -> dict[str, Any]:
    report_id = str(report.get("id") or report.get("report_id") or "")
    return {
        "trigger_type": "report_generation_requested",
        "recommendation_type": "read_only_summary",
        "source_type": "report",
        "source_id": report_id,
        "report_id": report_id,
        "title": "Review generated compliance report inputs",
        "summary": (
            "A compliance report was requested. Verify selected frameworks, evidence packages, "
            "and open gaps before the report is treated as audit-ready."
        ),
        "priority": "medium",
        "proposed_actions": [
            {
                "action": "summarize_report_inputs",
                "requires_approval": False,
                "tool": "get_selected_frameworks",
                "arguments": {},
            }
        ],
    }


def build_control_gap_recommendation(
    *,
    framework_id: str | None,
    control_id: str | None,
    gap: dict[str, Any],
) -> dict[str, Any]:
    gap_id = str(gap.get("id") or gap.get("gap_id") or f"{framework_id}:{control_id}:{gap.get('title') or gap.get('reason')}")
    severity = _normalize_priority(str(gap.get("severity") or "high"))
    return {
        "trigger_type": "high_priority_control_gap_detected",
        "recommendation_type": "create_evidence_collection_task",
        "source_type": "control_gap",
        "source_id": gap_id,
        "framework_id": framework_id,
        "control_id": control_id,
        "title": f"Close high-priority control gap {control_id or ''}".strip(),
        "summary": str(
            gap.get("remediation_hint")
            or gap.get("reason")
            or gap.get("description")
            or "A high-priority compliance control gap requires review."
        ),
        "priority": severity if severity in {"critical", "high"} else "high",
        "proposed_actions": [
            {
                "action": "create_evidence_collection_task",
                "requires_approval": True,
                "tool": "create_evidence_collection_task",
                "arguments": {
                    "task_name": f"Collect evidence for {control_id or 'control gap'}",
                    "task_type": "control_gap_evidence_collection",
                    "metadata": {"gap": gap, "framework_id": framework_id, "control_id": control_id},
                },
            }
        ],
    }


repository = ComplianceAgentRecommendationRepository()
