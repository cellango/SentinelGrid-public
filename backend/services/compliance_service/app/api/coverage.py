"""Compliance coverage endpoints (SOC 2 and reporting readiness)."""

import logging
import os
import sys
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_agent_runtime.compliance_workflow import build_control_gap_recommendation  # noqa: E402
from app.core.database import get_current_tenant, get_tenant_session
from app.api.agent_workflow import get_compliance_agent_workflow_service  # noqa: E402
from sg_core.models import Alert, IAMFinding, Playbook, PlaybookExecution, PostureFinding  # noqa: E402
from app.services.reporting_mapper import (  # noqa: E402
    SYSTEM_TENANT_ID,
    build_compliance_dashboard_payload,
    build_soc2_coverage_payload,
)
from app.services.multi_framework_coverage import (  # noqa: E402
    build_control_status_payload,
    build_framework_coverage_payload,
    build_multi_framework_coverage_payload,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])

HIGH_PRIORITY_GAP_SEVERITIES = {"critical", "high"}


def _resolve_tenant_id(
    current_tenant: str,
    override_tenant: Optional[str],
    tenant_id: Optional[str],
) -> str:
    if override_tenant and override_tenant != current_tenant:
        raise HTTPException(status_code=403, detail="Cross-tenant access denied")
    if tenant_id and tenant_id != current_tenant:
        raise HTTPException(status_code=403, detail="Cross-tenant access denied")
    return current_tenant


def _load_soc2_reporting_inputs(db: Session, tenant_id: str) -> dict[str, list]:
    tenant_uuid = UUID(tenant_id)
    playbook_tenants = [tenant_uuid, SYSTEM_TENANT_ID]

    return {
        "iam_rows": db.query(IAMFinding).filter(IAMFinding.tenant_id == tenant_uuid).all(),
        "posture_rows": db.query(PostureFinding).filter(PostureFinding.tenant_id == tenant_uuid).all(),
        "alerts": db.query(Alert).filter(Alert.tenant_id == tenant_uuid).all(),
        "playbooks": db.query(Playbook).filter(Playbook.tenant_id.in_(playbook_tenants), Playbook.is_enabled == True).all(),
        "executions": db.query(PlaybookExecution).filter(PlaybookExecution.tenant_id == tenant_uuid).all(),
    }


def _framework_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("items"), list):
        return [item for item in payload["items"] if isinstance(item, dict)]
    return [payload]


def _iter_high_priority_control_gaps(payload: dict[str, Any]):
    for framework in _framework_items(payload):
        framework_id = framework.get("framework_id") or framework.get("id")
        for control in framework.get("controls") or framework.get("items") or []:
            if not isinstance(control, dict):
                continue
            control_id = control.get("control_id") or control.get("id")
            for gap in control.get("gaps") or control.get("coverage_gaps") or []:
                if not isinstance(gap, dict):
                    continue
                severity = str(gap.get("severity") or "").strip().lower()
                if severity in HIGH_PRIORITY_GAP_SEVERITIES:
                    yield framework_id, control_id, gap


async def _trigger_high_priority_gap_recommendations(
    *,
    workflow_service,
    db: Session,
    tenant_id: str,
    payload: dict[str, Any],
    actor_id: str | None,
    authorization: str | None,
) -> None:
    for framework_id, control_id, gap in _iter_high_priority_control_gaps(payload):
        recommendation = build_control_gap_recommendation(
            framework_id=framework_id,
            control_id=control_id,
            gap=gap,
        )
        try:
            await workflow_service.create_recommendation_and_task(
                db,
                tenant_id=tenant_id,
                created_by=actor_id,
                authorization=authorization,
                metadata={
                    "framework_id": framework_id,
                    "control_id": control_id,
                    "gap": gap,
                    "coverage_source": payload.get("source"),
                },
                **recommendation,
            )
        except Exception as exc:  # pragma: no cover - recommendation triggers are side effects.
            logger.warning(
                "Failed to trigger Compliance Agent gap recommendation for tenant %s control %s: %s",
                tenant_id,
                control_id,
                exc,
            )


@router.get("/soc2/coverage")
def soc2_coverage(
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    tenant_id: Optional[str] = None,
):
    """Summarize SOC 2 coverage and reporting readiness based on tenant security data."""
    del authorization  # internal proxy compatibility only

    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, tenant_id)
    inputs = _load_soc2_reporting_inputs(db, resolved_tenant_id)

    return build_soc2_coverage_payload(
        tenant_id=resolved_tenant_id,
        iam_rows=inputs["iam_rows"],
        posture_rows=inputs["posture_rows"],
        alerts=inputs["alerts"],
        playbooks=inputs["playbooks"],
        executions=inputs["executions"],
    )


@router.get("/coverage")
async def multi_framework_coverage(
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_id: Optional[str] = Header(None, alias="X-User-ID"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    tenant_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    workflow_service=Depends(get_compliance_agent_workflow_service),
):
    """Return generalized coverage for the tenant's selected compliance frameworks."""
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, tenant_id)
    inputs = _load_soc2_reporting_inputs(db, resolved_tenant_id)
    payload = build_multi_framework_coverage_payload(
        db,
        resolved_tenant_id,
        inputs,
        limit=limit,
        offset=offset,
    )
    await _trigger_high_priority_gap_recommendations(
        workflow_service=workflow_service,
        db=db,
        tenant_id=resolved_tenant_id,
        payload=payload,
        actor_id=actor_id,
        authorization=authorization,
    )
    return payload


@router.get("/frameworks/{framework_id}/coverage")
async def framework_coverage(
    framework_id: str,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_id: Optional[str] = Header(None, alias="X-User-ID"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    tenant_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    workflow_service=Depends(get_compliance_agent_workflow_service),
):
    """Return generalized coverage for one compliance framework."""
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, tenant_id)
    inputs = _load_soc2_reporting_inputs(db, resolved_tenant_id)
    payload = build_framework_coverage_payload(
        db,
        resolved_tenant_id,
        framework_id,
        inputs,
        limit=limit,
        offset=offset,
    )
    if not payload:
        raise HTTPException(status_code=404, detail="Framework coverage not found")
    await _trigger_high_priority_gap_recommendations(
        workflow_service=workflow_service,
        db=db,
        tenant_id=resolved_tenant_id,
        payload=payload,
        actor_id=actor_id,
        authorization=authorization,
    )
    return payload


@router.get("/controls/{control_id}/status")
def control_status(
    control_id: str,
    framework_id: Optional[str] = None,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    tenant_id: Optional[str] = None,
):
    """Return generalized status for a control, optionally within a specific framework."""
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, tenant_id)
    inputs = _load_soc2_reporting_inputs(db, resolved_tenant_id)
    payload = build_control_status_payload(
        db,
        resolved_tenant_id,
        control_id,
        inputs,
        framework_id=framework_id,
    )
    if not payload:
        raise HTTPException(status_code=404, detail="Control status not found")
    return payload


@router.get("/dashboard")
def compliance_dashboard(
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    tenant_id: Optional[str] = None,
):
    """Compliance dashboard aggregate built from the same report-ready SOC 2 coverage payload."""
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, tenant_id)
    inputs = _load_soc2_reporting_inputs(db, resolved_tenant_id)

    coverage = build_soc2_coverage_payload(
        tenant_id=resolved_tenant_id,
        iam_rows=inputs["iam_rows"],
        posture_rows=inputs["posture_rows"],
        alerts=inputs["alerts"],
        playbooks=inputs["playbooks"],
        executions=inputs["executions"],
    )

    dashboard = build_compliance_dashboard_payload(coverage)
    framework_coverage = build_multi_framework_coverage_payload(
        db,
        resolved_tenant_id,
        inputs,
        limit=50,
        offset=0,
    )
    dashboard["framework_coverage"] = framework_coverage
    dashboard["selected_frameworks"] = [
        {
            key: value
            for key, value in item.items()
            if key != "controls"
        }
        for item in framework_coverage.get("items", [])
    ]
    return dashboard
