"""Compliance reporting adapters for SOC 2 and dashboard views."""

from __future__ import annotations

from typing import Any, Dict, Iterable
from uuid import UUID

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))
from sg_core.models import Alert, IAMFinding, Playbook, PlaybookExecution, PostureFinding  # noqa: E402

from app.services.control_signal_mapper import build_soc2_legacy_coverage_payload
from app.services.framework_starter_packs import build_framework_starter_packs


SYSTEM_TENANT_ID = UUID("f0fbc168-b457-47c4-9f41-d4076051f963")


def build_soc2_coverage_payload(
    tenant_id: str,
    iam_rows: Iterable[IAMFinding],
    posture_rows: Iterable[PostureFinding],
    alerts: Iterable[Alert],
    playbooks: Iterable[Playbook],
    executions: Iterable[PlaybookExecution],
) -> Dict[str, Any]:
    """Build the legacy SOC 2 coverage shape from generalized control coverage."""
    return build_soc2_legacy_coverage_payload(
        tenant_id=tenant_id,
        iam_rows=iam_rows,
        posture_rows=posture_rows,
        alerts=alerts,
        playbooks=playbooks,
        executions=executions,
    )


def build_compliance_dashboard_payload(coverage: Dict[str, Any]) -> Dict[str, Any]:
    summary = coverage.get("summary", {})
    reporting_summary = coverage.get("reporting_summary", {})

    overall_stats = {
        "overall_score": coverage.get("overall_score", 0),
        "controls_implemented": reporting_summary.get("criteria_ready", 0),
        "total_controls": summary.get("total_criteria", 0),
        "evidence_items": summary.get("evidence_items", 0),
        "last_assessment": summary.get("last_assessment"),
        "mapped_detections": summary.get("mapped_detections", 0),
        "control_checks": summary.get("control_checks", 0),
    }

    priority_criteria = sorted(
        coverage.get("controls", []),
        key=lambda item: (-item.get("open_findings", 0), -item.get("evidence_items", 0), item.get("id", "")),
    )[:5]

    return {
        "overall_stats": overall_stats,
        "soc2": coverage,
        "reporting_summary": reporting_summary,
        "priority_criteria": priority_criteria,
        "key_detections": coverage.get("key_detections", [])[:5],
        "control_checks": coverage.get("control_checks", [])[:5],
        "framework_starter_packs": build_framework_starter_packs(coverage),
    }
