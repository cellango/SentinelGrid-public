"""Tenant compliance framework selection endpoints."""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_current_tenant, get_tenant_session
from app.api.agent_workflow import get_compliance_agent_workflow_service
from app.services.observability import record_framework_selection_change
from app.services.framework_selection import framework_selection_service
from sg_agent_runtime.compliance_workflow import build_framework_selected_recommendation

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])

logger = logging.getLogger(__name__)


class FrameworkSelectionItem(BaseModel):
    framework_id: str = Field(..., description="Canonical framework id such as soc2, hipaa, pci_dss, nist_800_171")
    status: str = Field(default="active", description="active, inactive, or evaluating")
    priority: Optional[int] = Field(default=None, ge=1)
    target_date: Optional[date] = Field(default=None, description="Target date in YYYY-MM-DD format")


class FrameworkSelectionUpdateRequest(BaseModel):
    tenant_id: Optional[str] = None
    selections: list[FrameworkSelectionItem] = Field(default_factory=list)


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


@router.get("/framework-selections")
def list_framework_selections(
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    tenant_id: Optional[str] = None,
):
    """List persisted framework selections for the current tenant."""
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, tenant_id)
    return framework_selection_service.list_selections(db, resolved_tenant_id)


@router.put("/framework-selections")
async def replace_framework_selections(
    request: FrameworkSelectionUpdateRequest,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_id: Optional[str] = Header(None, alias="X-User-ID"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    workflow_service=Depends(get_compliance_agent_workflow_service),
):
    """Replace the tenant's explicit framework selection set."""
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, request.tenant_id)
    try:
        before = framework_selection_service.list_selections(db, resolved_tenant_id)
        previous_active = {
            item["framework_id"]
            for item in before.get("items", [])
            if item.get("status") in {"active", "evaluating"}
        }
        previous_by_framework = {
            item["framework_id"]: item
            for item in before.get("items", [])
            if item.get("framework_id")
        }
        result = framework_selection_service.replace_selections(
            db,
            resolved_tenant_id,
            [item.model_dump() for item in request.selections],
            selected_by=actor_id,
        )
        for item in result.get("items", []):
            previous = previous_by_framework.get(item.get("framework_id"))
            if not previous or previous.get("status") != item.get("status"):
                record_framework_selection_change(
                    framework_id=item.get("framework_id"),
                    status=item.get("status"),
                )
            if item.get("status") not in {"active", "evaluating"}:
                continue
            framework_id = item.get("framework_id")
            if not framework_id or framework_id in previous_active:
                continue
            recommendation = build_framework_selected_recommendation(
                framework_id=framework_id,
                framework_name=item.get("framework_name"),
            )
            try:
                await workflow_service.create_recommendation_and_task(
                    db,
                    tenant_id=resolved_tenant_id,
                    created_by=actor_id,
                    authorization=authorization,
                    metadata={"framework_selection": item},
                    **recommendation,
                )
            except Exception as exc:  # pragma: no cover - recommendation triggers are side effects.
                logger.warning(
                    "Failed to trigger Compliance Agent framework recommendation for tenant %s framework %s: %s",
                    resolved_tenant_id,
                    framework_id,
                    exc,
                )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
