from __future__ import annotations

"""Detection rule management endpoints for the no-code alarm editor."""

import logging
import os
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_tenant_session
from app.services import detection_rule_service
from app.services.detection_rule_service import preview_rule as preview_rule_service
from app.services.detection_rule_service import deploy_rule as deploy_rule_service
from app.services.detection_rule_service import disable_rule as disable_rule_service
from app.services.detection_rule_service import upsert_playbook_mapping

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/detection-rules", tags=["detection-rules"])


class RuleTemplateMetadata(BaseModel):
    alert_type: Optional[str] = None
    category: Optional[str] = None
    playbook_key: Optional[str] = None
    severity: Optional[str] = None
    is_template: bool = False


class DeploymentStatus(BaseModel):
    monitor_id: Optional[str] = None
    destination_id: Optional[str] = None
    is_enabled: Optional[bool] = None
    approval_status: Optional[str] = None
    rule_version: Optional[str] = None


class PlaybookMapping(BaseModel):
    alert_type: Optional[str] = None
    playbook_key: Optional[str] = None
    auto_execute: bool = False
    requires_approval: bool = False


class DetectionRuleVersion(BaseModel):
    id: Optional[UUID] = None
    version: str = "1.0.0"
    index_pattern: str
    query: dict
    trigger_condition: dict
    severity: str
    action_config: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    is_active: bool = True
    is_template: bool = False
    graph_json: Optional[dict] = None


class DetectionRuleCreate(BaseModel):
    rule_key: str
    name: str
    description: Optional[str] = None
    category: str
    version: DetectionRuleVersion
    approval_required: bool = False


class CloneRequest(BaseModel):
    name: Optional[str] = None
    rule_key: str
    description: Optional[str] = None


class DetectionRuleResponse(BaseModel):
    id: UUID
    rule_key: str
    name: str
    description: Optional[str]
    category: str
    current_version: str
    approval_required: bool
    versions: List[DetectionRuleVersion] = []
    deployment: Optional[DeploymentStatus] = None
    mapping: Optional[PlaybookMapping] = None


def get_tenant_context(
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    x_realm: str | None = Header(None, alias="X-Realm"),
) -> tuple[str, str]:
    """
    Resolve tenant and realm from headers, falling back to the default realm when X-Realm is absent.
    The frontend currently only sends X-Tenant-ID; requiring X-Realm caused 422s and empty UI.
    """
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing tenant context header X-Tenant-ID",
        )
    realm = x_realm or os.getenv("KEYCLOAK_REALM", "demo")
    return x_tenant_id, realm


@router.post("", response_model=DetectionRuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: DetectionRuleCreate,
    tenant: tuple[str, str] = Depends(get_tenant_context),
    db: Session = Depends(get_tenant_session),
):
    """Create a detection rule with initial version."""
    logger.info("Create rule requested for tenant=%s rule_key=%s", tenant[0], payload.rule_key)
    try:
        return detection_rule_service.create_rule(db, payload, created_by=tenant[0])
    except Exception as e:
        logger.error("Failed to create rule: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[DetectionRuleResponse])
def list_rules(
    tenant: tuple[str, str] = Depends(get_tenant_context),
    db: Session = Depends(get_tenant_session),
):
    """List detection rules (global) for now."""
    logger.info("List rules requested for tenant=%s", tenant[0])
    return detection_rule_service.list_rules(db, tenant_id=tenant[0])


@router.get("/{rule_id}", response_model=DetectionRuleResponse)
def get_rule(
    rule_id: UUID,
    tenant: tuple[str, str] = Depends(get_tenant_context),
    db: Session = Depends(get_tenant_session),
):
    """Get a detection rule with versions."""
    logger.info("Get rule requested for tenant=%s rule_id=%s", tenant[0], rule_id)
    rule = detection_rule_service.get_rule(db, rule_id, tenant_id=tenant[0])
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return rule


class PreviewRequest(BaseModel):
    index_pattern: str
    query: dict
    trigger_condition: dict
    time_range_minutes: int = 60


class PreviewResponse(BaseModel):
    hits: int
    sample: list
    aggregations: Optional[dict] = None


@router.post("/{rule_id}/preview", response_model=PreviewResponse)
def preview_rule(
    rule_id: UUID,
    payload: PreviewRequest,
    tenant: tuple[str, str] = Depends(get_tenant_context),
    db: Session = Depends(get_tenant_session),
):
    """Preview a detection rule by running the query/trigger against OpenSearch."""
    logger.info("Preview rule requested for tenant=%s rule_id=%s", tenant[0], rule_id)
    # Ensure rule exists
    rule = detection_rule_service.get_rule(db, rule_id, tenant_id=tenant[0])
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    try:
        return preview_rule_service(tenant_id=tenant[0], realm=tenant[1], req=payload)
    except Exception as e:
        logger.error("Preview failed: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Preview failed")


class DeployRequest(BaseModel):
    destination_id: Optional[str] = None
    auto_execute: bool = False
    schedule_minutes: int = 5
    message_template: Optional[dict] = None
    severity: Optional[str] = None  # override severity


class DeployResponse(BaseModel):
    monitor_id: str
    destination_id: Optional[str] = None
    deployed: bool = True
    approval_status: Optional[str] = None


@router.post("/{rule_id}/deploy", response_model=DeployResponse)
def deploy_rule(
    rule_id: UUID,
    payload: DeployRequest,
    tenant: tuple[str, str] = Depends(get_tenant_context),
    db: Session = Depends(get_tenant_session),
):
    """Deploy or update an OpenSearch monitor for this rule."""
    logger.info("Deploy rule requested for tenant=%s rule_id=%s", tenant[0], rule_id)
    try:
        # Ensure rule exists
        rule = detection_rule_service.get_rule(db, rule_id, tenant_id=tenant[0])
        if not rule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
        monitor_id, destination_id, approval_status = deploy_rule_service(
            db=db,
            rule_id=rule_id,
            tenant_id=tenant[0],
            destination_id=payload.destination_id or "",
            auto_execute=payload.auto_execute,
            schedule_minutes=payload.schedule_minutes,
            message_template=payload.message_template,
            severity_override=payload.severity,
        )
        return DeployResponse(
            monitor_id=monitor_id,
            destination_id=destination_id,
            approval_status=approval_status,
            deployed=approval_status == "approved",
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error("Failed to deploy rule: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to deploy rule")


@router.post("/{rule_id}/disable")
def disable_rule(
    rule_id: UUID,
    tenant: tuple[str, str] = Depends(get_tenant_context),
    db: Session = Depends(get_tenant_session),
):
    """Disable (delete) the deployed monitor for this rule/tenant."""
    try:
        disable_rule_service(db=db, rule_id=rule_id, tenant_id=tenant[0])
        return {"rule_id": rule_id, "disabled": True}
    except Exception as e:
        logger.error("Failed to disable rule: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to disable rule")


class CloneRequest(BaseModel):
    name: str
    rule_key: str
    description: Optional[str] = None


class ApprovalRequest(BaseModel):
    status: str  # 'approved' or 'rejected'


@router.post("/{rule_id}/clone", response_model=DetectionRuleResponse)
def clone_rule(
    rule_id: UUID,
    payload: CloneRequest,
    tenant: tuple[str, str] = Depends(get_tenant_context),
    db: Session = Depends(get_tenant_session),
):
    """Clone an existing rule/template into a new draft."""
    logger.info("Clone rule requested for tenant=%s rule_id=%s", tenant[0], rule_id)
    try:
        return detection_rule_service.clone_rule(db, rule_id, payload, created_by=tenant[0], tenant_id=tenant[0])
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error("Failed to clone rule: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to clone rule")


class MappingRequest(BaseModel):
    alert_type: str
    playbook_key: str
    auto_execute: bool = False
    requires_approval: bool = False


@router.post("/{rule_id}/mapping", response_model=DetectionRuleResponse)
def set_mapping(
    rule_id: UUID,
    payload: MappingRequest,
    tenant: tuple[str, str] = Depends(get_tenant_context),
    db: Session = Depends(get_tenant_session),
):
    """Set detection to playbook mapping for this tenant/rule."""
    # Ensure rule exists
    rule = detection_rule_service.get_rule(db, rule_id, tenant_id=tenant[0])
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    try:
        upsert_playbook_mapping(
            db=db,
            tenant_id=tenant[0],
            rule_id=rule_id,
            alert_type=payload.alert_type,
            playbook_key=payload.playbook_key,
            auto_execute=payload.auto_execute,
            requires_approval=payload.requires_approval,
        )
        # Return updated rule with mapping
        updated_rule = detection_rule_service.get_rule(db, rule_id, tenant_id=tenant[0])
        return updated_rule
    except Exception as e:
        logger.error("Failed to set mapping: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to set mapping")


@router.post("/{rule_id}/approve")
def approve_rule(
    rule_id: UUID,
    tenant: tuple[str, str] = Depends(get_tenant_context),
    db: Session = Depends(get_tenant_session),
):
    """Approve a rule for deployment for this tenant."""
    try:
        status_value = detection_rule_service.set_rule_approval_status(
            db, rule_id=rule_id, tenant_id=tenant[0], approval_status="approved"
        )
        return {"rule_id": rule_id, "approval_status": status_value}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error("Failed to approve rule: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to approve rule")


@router.post("/{rule_id}/reject")
def reject_rule(
    rule_id: UUID,
    tenant: tuple[str, str] = Depends(get_tenant_context),
    db: Session = Depends(get_tenant_session),
):
    """Reject a rule for deployment for this tenant."""
    try:
        status_value = detection_rule_service.set_rule_approval_status(
            db, rule_id=rule_id, tenant_id=tenant[0], approval_status="rejected"
        )
        return {"rule_id": rule_id, "approval_status": status_value}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error("Failed to reject rule: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to reject rule")
