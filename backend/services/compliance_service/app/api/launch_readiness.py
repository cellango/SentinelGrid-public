"""Compliance launch readiness and admin rollout controls."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_tenant_session
from app.services.launch_readiness import (
    CONTROL_DEFINITIONS,
    ComplianceLaunchControlError,
    launch_readiness_service,
)
from sg_core.security import get_current_payload, get_current_tenant


router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])

ADMIN_CONTROL_ROLES = {
    "admin",
    "tenant_admin",
    "superadmin",
    "super_admin",
    "platform_admin",
    "compliance_manager",
}


class ComplianceAdminSettingsUpdateRequest(BaseModel):
    multi_framework_selection: bool | None = None
    durable_evidence_repository: bool | None = None
    compliance_agent_workflows: bool | None = None


def _normalize_role(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def _roles_from_payload(token_payload: dict[str, Any]) -> set[str]:
    roles = token_payload.get("roles") or token_payload.get("realm_roles") or []
    return {_normalize_role(str(role)) for role in roles if str(role).strip()}


def _require_admin_control_role(token_payload: dict[str, Any]) -> None:
    if not _roles_from_payload(token_payload).intersection(ADMIN_CONTROL_ROLES):
        raise HTTPException(status_code=403, detail="Insufficient role for compliance launch controls")


def _actor_id(token_payload: dict[str, Any], actor_header: str | None = None) -> str:
    return (
        actor_header
        or token_payload.get("user_id")
        or token_payload.get("sub")
        or token_payload.get("preferred_username")
        or "authenticated_user"
    )


@router.get("/launch-readiness")
def get_compliance_launch_readiness(
    current_tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Return launch-readiness metadata, framework limits, and effective controls."""
    return launch_readiness_service.build_launch_readiness(db, current_tenant_id)


@router.get("/admin/settings")
def get_compliance_admin_settings(
    current_tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
    token_payload: dict[str, Any] = Depends(get_current_payload),
):
    """Return tenant-scoped Compliance module launch controls."""
    _require_admin_control_role(token_payload)
    return launch_readiness_service.get_admin_settings(db, current_tenant_id)


@router.put("/admin/settings")
def update_compliance_admin_settings(
    request: ComplianceAdminSettingsUpdateRequest,
    current_tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    actor_header: str | None = Header(None, alias="X-Actor-ID"),
):
    """Update tenant-scoped Compliance module launch controls."""
    _require_admin_control_role(token_payload)
    updates = {
        key: value
        for key, value in request.model_dump(exclude_none=True).items()
        if key in CONTROL_DEFINITIONS
    }
    if not updates:
        raise HTTPException(status_code=400, detail="At least one compliance launch control is required")

    try:
        return launch_readiness_service.update_admin_settings(
            db,
            current_tenant_id,
            updates,
            actor_id=_actor_id(token_payload, actor_header),
        )
    except ComplianceLaunchControlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
