"""Framework starter-pack builders for compliance dashboard workflows."""

from __future__ import annotations

from typing import Any


def build_framework_starter_packs(coverage: dict[str, Any]) -> list[dict[str, Any]]:
    """Build guided starter packs for SOC 2 and ISO 27001."""

    return [
        _build_soc2_starter_pack(coverage),
        _build_iso27001_starter_pack(coverage),
    ]


def _build_soc2_starter_pack(coverage: dict[str, Any]) -> dict[str, Any]:
    summary = coverage.get("summary", {})
    reporting_summary = coverage.get("reporting_summary", {})
    controls = coverage.get("controls", [])
    score = round(float(coverage.get("overall_score", 0) or 0))
    mapped_signals = int(summary.get("mapped_detections", 0) or 0) + int(summary.get("control_checks", 0) or 0)

    focus_areas = [
        _soc2_focus_area(
            key="access_control",
            title="Access control and authentication",
            description="Start with identity, MFA, and privileged-access evidence for customer reviews and audit scoping.",
            controls=controls,
            prefixes=("CC6.1", "CC6.2", "CC6.3", "CC6.6"),
        ),
        _soc2_focus_area(
            key="monitoring",
            title="Monitoring and detection",
            description="Use mapped detections and log-related criteria to support the control story.",
            controls=controls,
            prefixes=("CC7.1", "CC7.2", "CC7.3"),
        ),
        _soc2_focus_area(
            key="response",
            title="Response and remediation",
            description="Show how alerts, playbooks, and response activity support operational follow-through.",
            controls=controls,
            prefixes=("CC7.4", "CC7.5", "CC8.1"),
        ),
    ]

    return {
        "framework_key": "soc2",
        "framework_name": "SOC 2",
        "launch_state": "live",
        "score_label": "Framework coverage",
        "score": score,
        "summary": "Use the live readiness layer to move from abstract SOC 2 talk to exportable evidence, mapped detections, and priority criteria.",
        "note": "This pack is backed by the current SOC 2 reporting payload and trust artifacts already available in product.",
        "metrics": {
            "criteria_ready": int(reporting_summary.get("criteria_ready", 0) or 0),
            "criteria_needing_attention": int(reporting_summary.get("criteria_needing_attention", 0) or 0),
            "mapped_signals": mapped_signals,
            "evidence_items": int(summary.get("evidence_items", 0) or 0),
        },
        "artifact_template_keys": [
            "smb_audit_readiness_pack",
            "smb_customer_security_review_pack",
            "smb_evidence_attachment_export",
        ],
        "focus_areas": focus_areas,
        "quick_actions": [
            {
                "title": "Generate trust artifacts",
                "description": "Open the trust-center kit and generate a SOC 2-ready export.",
                "href": "/dashboard/compliance/reports#trust-center-kit",
            },
            {
                "title": "Run questionnaire assist",
                "description": "Draft customer-review answers from the live compliance payload.",
                "href": "/dashboard/compliance/reports#questionnaire-assist",
            },
            {
                "title": "Review priority criteria",
                "description": "Work the criteria most likely to block an audit or customer review.",
                "href": "/dashboard/compliance",
            },
        ],
    }


def _build_iso27001_starter_pack(coverage: dict[str, Any]) -> dict[str, Any]:
    summary = coverage.get("summary", {})
    reporting_summary = coverage.get("reporting_summary", {})
    controls = coverage.get("controls", [])
    starter_score = round(float(coverage.get("overall_score", 0) or 0))
    mapped_signals = int(summary.get("mapped_detections", 0) or 0) + int(summary.get("control_checks", 0) or 0)

    access_controls = _soc2_focus_area(
        key="annex_a_access",
        title="Access control baseline",
        description="Reuse identity and MFA evidence as the first Annex A conversation instead of starting from scratch.",
        controls=controls,
        prefixes=("CC6.1", "CC6.2", "CC6.3", "CC6.6"),
    )
    monitoring = _soc2_focus_area(
        key="annex_a_monitoring",
        title="Logging and monitoring baseline",
        description="Use monitoring-oriented detections and checks to seed Annex A logging and event-monitoring discussions.",
        controls=controls,
        prefixes=("CC7.1", "CC7.2", "CC7.3"),
    )
    response = _soc2_focus_area(
        key="annex_a_response",
        title="Incident management baseline",
        description="Carry over the same response signals and evidence into an ISO 27001 starter narrative.",
        controls=controls,
        prefixes=("CC7.4", "CC7.5", "CC8.1"),
    )

    return {
        "framework_key": "iso27001",
        "framework_name": "ISO 27001",
        "launch_state": "starter",
        "score_label": "Starter readiness",
        "score": starter_score,
        "summary": "Start ISO 27001 conversations using the existing trust-evidence layer, then expand into a fuller ISMS program over time.",
        "note": "This is a guided starter pack, not a full Annex A control tracker yet. It uses the current SOC 2 and NIST-aligned evidence layer to accelerate ISO 27001 planning.",
        "metrics": {
            "criteria_ready": int(reporting_summary.get("criteria_ready", 0) or 0),
            "criteria_needing_attention": int(reporting_summary.get("criteria_needing_attention", 0) or 0),
            "mapped_signals": mapped_signals,
            "evidence_items": int(summary.get("evidence_items", 0) or 0),
        },
        "artifact_template_keys": [
            "smb_customer_security_review_pack",
            "smb_evidence_attachment_export",
        ],
        "focus_areas": [
            access_controls,
            monitoring,
            response,
        ],
        "quick_actions": [
            {
                "title": "Generate evidence-first exports",
                "description": "Use the customer review and evidence attachment packs as ISO starter material.",
                "href": "/dashboard/compliance/reports#trust-center-kit",
            },
            {
                "title": "Draft ISO questionnaire answers",
                "description": "Use questionnaire assist to answer early ISO and supplier-review prompts.",
                "href": "/dashboard/compliance/reports#questionnaire-assist",
            },
            {
                "title": "Triage open gaps",
                "description": "Use the same priority criteria list to decide where ISO starter work needs manual follow-up.",
                "href": "/dashboard/compliance",
            },
        ],
    }


def _soc2_focus_area(
    *,
    key: str,
    title: str,
    description: str,
    controls: list[dict[str, Any]],
    prefixes: tuple[str, ...],
) -> dict[str, Any]:
    matching_controls = [
        control
        for control in controls
        if any(str(control.get("id", "")).startswith(prefix) for prefix in prefixes)
    ]
    open_findings = sum(int(control.get("open_findings", 0) or 0) for control in matching_controls)
    evidence_items = sum(int(control.get("evidence_items", 0) or 0) for control in matching_controls)

    if matching_controls and open_findings == 0:
        status = "ready"
    elif matching_controls:
        status = "needs_attention"
    else:
        status = "starter"

    return {
        "key": key,
        "title": title,
        "description": description,
        "status": status,
        "detail": (
            f"{len(matching_controls)} mapped criteria, {open_findings} open findings, "
            f"{evidence_items} evidence items"
        ),
    }
