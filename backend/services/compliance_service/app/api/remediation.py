"""API endpoints for compliance remediation."""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_current_tenant, get_tenant_session
from app.services.finding_enhancer import FindingEnhancer
from app.services.remediation_planner import RemediationPlanner
from app.services.remediation_orchestrator import RemediationOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])


class EnhanceFindingRequest(BaseModel):
    """Request to enhance a finding with compliance metadata."""
    finding_type: str  # 'iam_finding' or 'posture_finding'


class EnhanceFindingResponse(BaseModel):
    """Response for finding enhancement."""
    finding_id: str
    nist_control_id: Optional[str] = None
    remediation_plan: Dict[str, Any]
    remediation_status: str


class CreateRemediationPlanRequest(BaseModel):
    """Request to create a remediation plan."""
    finding_type: str
    custom_steps: Optional[List[Dict[str, Any]]] = None


class RemediationPlanResponse(BaseModel):
    """Response for remediation plan."""
    plan: Dict[str, Any]


class ExecuteRemediationRequest(BaseModel):
    """Request to execute remediation."""
    playbook_id: Optional[str] = None
    auto_approve: bool = False


class ExecuteRemediationResponse(BaseModel):
    """Response for remediation execution."""
    remediation_id: str
    execution_id: str
    status: str
    finding_id: str
    finding_type: str


@router.post("/findings/{finding_id}/enhance", response_model=EnhanceFindingResponse)
async def enhance_finding(
    finding_id: UUID,
    request: EnhanceFindingRequest,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Enhance an existing finding with compliance metadata (NIST control mapping, remediation plan).
    
    This endpoint enhances findings created by IAM Agent or Posture Agent with compliance metadata.
    It does NOT create findings - that's done by those agents.
    """
    try:
        enhancer = FindingEnhancer(db)
        
        if request.finding_type == "iam_finding":
            result = await enhancer.enhance_iam_finding(finding_id, UUID(tenant_id))
        elif request.finding_type == "posture_finding":
            result = await enhancer.enhance_posture_finding(finding_id, UUID(tenant_id))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid finding type: {request.finding_type}"
            )
        
        return EnhanceFindingResponse(
            finding_id=result["finding_id"],
            nist_control_id=result.get("nist_control_id"),
            remediation_plan=result["remediation_plan"],
            remediation_status=result["remediation_status"]
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error enhancing finding {finding_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enhancing finding: {str(e)}"
        )


@router.post("/findings/{finding_id}/remediation-plan", response_model=RemediationPlanResponse)
async def create_remediation_plan(
    finding_id: UUID,
    request: CreateRemediationPlanRequest,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Create a detailed remediation plan for a finding.
    
    This can be called to create or update a remediation plan for a finding.
    """
    try:
        planner = RemediationPlanner(db)
        plan = planner.create_remediation_plan(
            finding_id=finding_id,
            finding_type=request.finding_type,
            tenant_id=UUID(tenant_id),
            custom_steps=request.custom_steps
        )
        
        return RemediationPlanResponse(plan=plan)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating remediation plan for {finding_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating remediation plan: {str(e)}"
        )


@router.post("/findings/{finding_id}/remediate", response_model=ExecuteRemediationResponse)
async def execute_remediation(
    finding_id: UUID,
    request: ExecuteRemediationRequest,
    finding_type: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Execute remediation for a finding via playbook.
    
    This triggers a playbook to remediate the finding. The actual remediation actions
    are executed by n8n workflows referenced in the playbook.
    """
    try:
        orchestrator = RemediationOrchestrator(db)
        
        playbook_id = UUID(request.playbook_id) if request.playbook_id else None
        
        result = await orchestrator.execute_remediation(
            finding_id=finding_id,
            finding_type=finding_type,
            tenant_id=UUID(tenant_id),
            playbook_id=playbook_id,
            auto_approve=request.auto_approve
        )
        
        return ExecuteRemediationResponse(
            remediation_id=result["remediation_id"],
            execution_id=result.get("execution_id", ""),
            status=result["status"],
            finding_id=result["finding_id"],
            finding_type=result["finding_type"]
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error executing remediation for {finding_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing remediation: {str(e)}"
        )


@router.get("/findings/{finding_id}/remediation-status")
async def get_remediation_status(
    finding_id: UUID,
    finding_type: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Get remediation status for a finding.
    """
    try:
        from sg_core.models import RemediationMetadata
        
        remediation = db.query(RemediationMetadata).filter(
            and_(
                RemediationMetadata.finding_id == finding_id,
                RemediationMetadata.finding_type == finding_type,
                RemediationMetadata.tenant_id == UUID(tenant_id)
            )
        ).first()
        
        if not remediation:
            return {
                "finding_id": str(finding_id),
                "status": "not_started",
                "remediation_id": None
            }
        
        return {
            "finding_id": str(finding_id),
            "remediation_id": str(remediation.id),
            "status": remediation.status,
            "execution_id": str(remediation.playbook_execution_id) if remediation.playbook_execution_id else None,
            "created_at": remediation.created_at.isoformat() if hasattr(remediation.created_at, 'isoformat') else str(remediation.created_at)
        }
    
    except Exception as e:
        logger.error(f"Error getting remediation status for {finding_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting remediation status: {str(e)}"
        )
