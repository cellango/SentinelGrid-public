"""Compliance-service operational metrics helpers."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from sg_core.service_metrics import get_service_metrics


PROMETHEUS_MEDIA_TYPE = "text/plain; version=0.0.4; charset=utf-8"

runtime_metrics = get_service_metrics(settings.SERVICE_NAME)


def _label(value: Any, fallback: str = "unknown") -> str:
    rendered = str(value or "").strip()
    return rendered or fallback


def record_evidence_collection(
    *,
    outcome: str,
    source_system: str | None = None,
    collection_method: str | None = None,
) -> None:
    runtime_metrics.increment_counter(
        "compliance_evidence_collection_total",
        outcome=_label(outcome),
        source_system=_label(source_system),
        collection_method=_label(collection_method),
    )


def record_evidence_collection_task(*, status: str, task_type: str | None = None) -> None:
    runtime_metrics.increment_counter(
        "compliance_evidence_collection_tasks_total",
        status=_label(status),
        task_type=_label(task_type),
    )


def record_stale_evidence_count(*, tenant_id: str, count: int | float) -> None:
    runtime_metrics.set_gauge(
        "compliance_stale_evidence_items",
        float(count),
        tenant_id=_label(tenant_id),
    )


def record_framework_selection_change(*, framework_id: str | None, status: str | None) -> None:
    runtime_metrics.increment_counter(
        "compliance_framework_selection_changes_total",
        framework_id=_label(framework_id),
        status=_label(status),
    )


def record_agent_recommendation_decision(*, state: str, trigger_type: str | None = None) -> None:
    runtime_metrics.increment_counter(
        "compliance_agent_recommendation_decisions_total",
        state=_label(state),
        trigger_type=_label(trigger_type),
    )
