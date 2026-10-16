"""API endpoints for alert-to-playbook trigger evaluation and execution."""

import logging
from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_current_tenant, get_tenant_session
from app.services.playbook_trigger_engine import PlaybookTriggerEngine
from app.services.playbook_orchestrator import PlaybookOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/automated-response", tags=["automated-response"])


class TriggerEvaluationResponse(BaseModel):
    """Response for trigger evaluation."""
    alert_id: str
    matching_playbooks: List[Dict[str, Any]]
    total_matched: int


class TriggerPlaybookRequest(BaseModel):
    """Request to trigger a playbook."""
    playbook_id: str
    trigger_reason: str


class TriggerPlaybookResponse(BaseModel):
    """Response for playbook trigger."""
    trigger_id: str
    execution_id: str
    status: str
    trigger_reason: str


@router.post("/alerts/{alert_id}/evaluate", response_model=TriggerEvaluationResponse)
async def evaluate_alert_triggers(
    alert_id: UUID,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Evaluate an alert against all enabled playbooks with auto-trigger enabled.
    
    Returns matching playbooks that should be triggered for this alert.
    """
    try:
        engine = PlaybookTriggerEngine(db)
        matching_playbooks = engine.evaluate_alert(alert_id, UUID(tenant_id))
        
        return TriggerEvaluationResponse(
            alert_id=str(alert_id),
            matching_playbooks=matching_playbooks,
            total_matched=len(matching_playbooks)
        )
    except Exception as e:
        logger.error(f"Error evaluating triggers for alert {alert_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error evaluating triggers: {str(e)}"
        )


@router.post("/alerts/{alert_id}/trigger", response_model=TriggerPlaybookResponse)
async def trigger_playbook_for_alert(
    alert_id: UUID,
    request: TriggerPlaybookRequest,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Trigger a specific playbook for an alert.
    
    This endpoint is called after evaluation to actually trigger a playbook.
    """
    try:
        orchestrator = PlaybookOrchestrator(db)
        result = await orchestrator.trigger_playbook(
            playbook_id=UUID(request.playbook_id),
            alert_id=alert_id,
            tenant_id=UUID(tenant_id),
            trigger_reason=request.trigger_reason
        )
        
        return TriggerPlaybookResponse(
            trigger_id=result["trigger_id"],
            execution_id=result.get("execution_id", ""),
            status=result["status"],
            trigger_reason=result["trigger_reason"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error triggering playbook for alert {alert_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering playbook: {str(e)}"
        )


@router.post("/alerts/{alert_id}/auto-trigger")
async def auto_trigger_for_alert(
    alert_id: UUID,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Automatically evaluate and trigger all matching playbooks for an alert.
    
    This is the main endpoint called by the Detection Service when a new alert is created.
    """
    try:
        engine = PlaybookTriggerEngine(db)
        orchestrator = PlaybookOrchestrator(db)
        
        # Evaluate triggers
        matching_playbooks = engine.evaluate_alert(alert_id, UUID(tenant_id))
        
        if not matching_playbooks:
            return {
                "alert_id": str(alert_id),
                "triggered": False,
                "reason": "No matching playbooks found"
            }
        
        # Trigger all matching playbooks
        triggered = []
        for playbook in matching_playbooks:
            try:
                result = await orchestrator.trigger_playbook(
                    playbook_id=playbook["playbook_id"],
                    alert_id=alert_id,
                    tenant_id=UUID(tenant_id),
                    trigger_reason=playbook["trigger_reason"]
                )
                triggered.append({
                    "playbook_id": str(playbook["playbook_id"]),
                    "playbook_name": playbook["playbook_name"],
                    "execution_id": result.get("execution_id"),
                    "status": result["status"]
                })
            except Exception as e:
                logger.error(
                    f"Failed to trigger playbook {playbook['playbook_id']} for alert {alert_id}: {e}",
                    exc_info=True
                )
                triggered.append({
                    "playbook_id": str(playbook["playbook_id"]),
                    "playbook_name": playbook["playbook_name"],
                    "error": str(e)
                })
        
        return {
            "alert_id": str(alert_id),
            "triggered": True,
            "playbooks_triggered": len(triggered),
            "results": triggered
        }
    
    except Exception as e:
        logger.error(f"Error in auto-trigger for alert {alert_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in auto-trigger: {str(e)}"
        )
