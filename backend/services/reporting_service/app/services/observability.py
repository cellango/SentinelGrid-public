"""Reporting-service operational metrics helpers."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from sg_core.service_metrics import get_service_metrics


PROMETHEUS_MEDIA_TYPE = "text/plain; version=0.0.4; charset=utf-8"

runtime_metrics = get_service_metrics(settings.SERVICE_NAME)


def _label(value: Any, fallback: str = "unknown") -> str:
    rendered = str(value or "").strip()
    return rendered or fallback


def record_report_generation(
    *,
    outcome: str,
    report_format: str | None = None,
    template_type: str | None = None,
) -> None:
    runtime_metrics.increment_counter(
        "compliance_report_generation_total",
        outcome=_label(outcome),
        report_format=_label(report_format),
        template_type=_label(template_type),
    )
    if outcome == "failed":
        runtime_metrics.increment_counter(
            "compliance_report_generation_failures_total",
            report_format=_label(report_format),
            template_type=_label(template_type),
        )
