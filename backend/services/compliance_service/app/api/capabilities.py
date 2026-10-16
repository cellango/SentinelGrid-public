"""Compliance runtime capability metadata."""

from fastapi import APIRouter

from app.core.config import settings
from app.services.launch_readiness import CONTROL_DEFINITIONS, FRAMEWORK_LIMITATIONS

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])


def _runtime_labels() -> dict[str, str]:
    return {
        "dashboard_title": "Compliance Dashboard"
        if settings.COMPLIANCE_MULTI_FRAMEWORK_ENABLED
        else "SOC 2 Readiness Dashboard",
        "reports_title": "Compliance Reports"
        if settings.COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED
        else "Trust & SOC 2 Reports",
        "evidence_label": "Evidence items"
        if settings.COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED
        else "Report-ready signals",
    }


def build_compliance_capabilities() -> dict:
    """Return truthful capability metadata for the current compliance runtime."""
    runtime_mode = (
        "multi_framework_compliance"
        if settings.COMPLIANCE_MULTI_FRAMEWORK_ENABLED
        else "soc2_readiness"
    )
    return {
        "runtime_mode": runtime_mode,
        "capabilities": {
            "soc2_readiness": True,
            "framework_starter_packs": True,
            "multi_framework_selection": settings.COMPLIANCE_MULTI_FRAMEWORK_ENABLED,
            "durable_evidence_repository": settings.COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED,
            "compliance_agent_workflows": settings.COMPLIANCE_AGENT_ENABLED,
        },
        "compatibility_endpoints": [
            "/api/v1/compliance/soc2/coverage",
            "/api/v1/compliance/dashboard",
            "/api/v1/compliance/evidence/collect",
        ],
        "stub_endpoints": [],
        "deprecated_endpoints": [
            {
                "path": "/api/v1/compliance/report",
                "replacement": "/api/v1/reports",
                "reason": "Legacy entitlement-style report shape is retained at the gateway for compatibility.",
            },
        ],
        "truth_labels": _runtime_labels(),
        "admin_control_paths": {
            "readiness": "/api/v1/compliance/launch-readiness",
            "settings": "/api/v1/compliance/admin/settings",
        },
        "admin_controls": [
            {
                "key": key,
                "label": value["label"],
                "env_var": value["env_var"],
                "feature_flag_key": value["feature_flag_key"],
            }
            for key, value in CONTROL_DEFINITIONS.items()
        ],
        "known_limitations": [
            {
                "framework_id": item["framework_id"],
                "support_level": item["support_level"],
                "limitations": item["limitations"],
            }
            for item in FRAMEWORK_LIMITATIONS
        ],
    }


@router.get("/capabilities")
def get_compliance_capabilities():
    """Expose rollout flags and truthful runtime labels to callers."""
    return build_compliance_capabilities()
