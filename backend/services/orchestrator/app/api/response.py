"""API endpoints for response orchestration."""

import logging
from typing import Optional
from uuid import UUID
from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from app.core.security import get_current_tenant, require_orchestrator_request
from app.services.response_orchestrator import ResponseOrchestrator, ResponseType
from app.services.metrics import metrics_tracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/orchestrator", tags=["orchestration"], dependencies=[Depends(require_orchestrator_request)])


class OrchestrateAlertRequest(BaseModel):
    """Request to orchestrate alert response."""
    response_type: str = "automated_response"  # 'automated_response'


class OrchestrateAlertResponse(BaseModel):
    """Response for alert orchestration."""
    alert_id: str
    status: str
    playbooks_triggered: int
    playbooks: list
    orchestrated_at: str


class OrchestrateRemediationRequest(BaseModel):
    """Request to orchestrate finding remediation."""
    playbook_id: Optional[str] = None


class OrchestrateRemediationResponse(BaseModel):
    """Response for remediation orchestration."""
    finding_id: str
    finding_type: str
    status: str
    remediation_id: str
    execution_id: str
    orchestrated_at: str


@router.post("/alerts/{alert_id}/orchestrate", response_model=OrchestrateAlertResponse)
async def orchestrate_alert_response(
    alert_id: UUID,
    request: OrchestrateAlertRequest,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """
    Orchestrate automated response for an alert.
    
    This endpoint coordinates the full automated response workflow:
    1. Evaluates alert against playbook triggers
    2. Triggers matching playbooks
    3. Tracks execution status
    
    Returns orchestration result with triggered playbooks.
    """
    try:
        metrics_tracker.mark_queued("automated_response")
        orchestrator = ResponseOrchestrator()
        
        response_type = ResponseType(request.response_type)
        result = await orchestrator.orchestrate_alert_response(
            alert_id=alert_id,
            tenant_id=tenant_id,
            response_type=response_type
        )
        
        return OrchestrateAlertResponse(
            alert_id=result["alert_id"],
            status=result["status"],
            playbooks_triggered=result.get("playbooks_triggered", 0),
            playbooks=result.get("playbooks", []),
            orchestrated_at=result.get("orchestrated_at", datetime.now(UTC).isoformat())
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error orchestrating alert response for {alert_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error orchestrating response: {str(e)}"
        )


@router.post("/findings/{finding_id}/orchestrate", response_model=OrchestrateRemediationResponse)
async def orchestrate_finding_remediation(
    finding_id: UUID,
    finding_type: str = Query(..., description="Finding type: 'iam_finding' or 'posture_finding'"),
    request: OrchestrateRemediationRequest = None,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """
    Orchestrate compliance remediation for a finding.
    
    This endpoint coordinates the full remediation workflow:
    1. Enhances finding with compliance metadata (if needed)
    2. Creates remediation plan (if needed)
    3. Executes remediation via playbook
    4. Tracks execution status
    
    Returns orchestration result with remediation and execution IDs.
    """
    try:
        metrics_tracker.mark_queued("compliance_remediation")
        orchestrator = ResponseOrchestrator()
        
        playbook_id = UUID(request.playbook_id) if request and request.playbook_id else None
        
        result = await orchestrator.orchestrate_finding_remediation(
            finding_id=finding_id,
            finding_type=finding_type,
            tenant_id=tenant_id,
            playbook_id=playbook_id
        )
        
        return OrchestrateRemediationResponse(
            finding_id=result["finding_id"],
            finding_type=result["finding_type"],
            status=result["status"],
            remediation_id=result.get("remediation_id", ""),
            execution_id=result.get("execution_id", ""),
            orchestrated_at=result.get("orchestrated_at", datetime.now(UTC).isoformat())
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error orchestrating remediation for {finding_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error orchestrating remediation: {str(e)}"
        )


@router.get("/executions/{execution_id}/status")
async def get_execution_status(
    execution_id: UUID,
    execution_type: str = Query("playbook", description="Execution type: 'playbook' or 'remediation'"),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """
    Get execution status for an orchestrated response.
    
    Returns status of playbook execution or remediation execution.
    """
    try:
        orchestrator = ResponseOrchestrator()
        status_result = await orchestrator.get_execution_status(
            execution_id=execution_id,
            tenant_id=tenant_id,
            execution_type=execution_type
        )
        
        return status_result
    
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting execution status for {execution_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting execution status: {str(e)}"
        )


@router.get("/reports/executions")
async def get_execution_report(
    start_date: Optional[datetime] = Query(None, description="Start date for report"),
    end_date: Optional[datetime] = Query(None, description="End date for report"),
    tenant_id: UUID = Depends(get_current_tenant),
):
    """
    Generate execution report for orchestrated responses.
    
    Returns aggregated statistics about orchestrated responses and remediations.
    """
    try:
        orchestrator = ResponseOrchestrator()
        report = await orchestrator.generate_execution_report(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return report
    
    except Exception as e:
        logger.error(f"Error generating execution report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating report: {str(e)}"
        )
