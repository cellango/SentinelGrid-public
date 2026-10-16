"""Alert routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.db import get_tenant_session
from sg_core.security import get_current_tenant
from sg_core.schemas import AlertResponse
from app.services.alert_service import AlertService

router = APIRouter()


@router.get("/", response_model=dict)
def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status: open|triaged|closed"),
    severity: Optional[str] = Query(None, description="Filter by severity: critical|high|medium|low"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """List alerts for the current tenant."""
    service = AlertService(db, tenant_id)
    alerts, total = service.list_alerts(status=status, severity=severity, limit=limit, offset=offset)
    
    return {
        "items": [AlertResponse.from_orm(alert).dict() for alert in alerts],
        "total": total
    }


@router.get("/{alert_id}", response_model=dict)
def get_alert(
    alert_id: UUID,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Get alert details with AI analysis."""
    service = AlertService(db, tenant_id)
    alert = service.get_alert(alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Get AI analysis if available
    ai_analysis = service.get_ai_analysis(alert_id)
    
    return {
        **AlertResponse.from_orm(alert).dict(),
        "ai_analyses": [ai.dict() for ai in ai_analysis] if ai_analysis else []
    }


@router.post("/{alert_id}/triage", response_model=dict)
def trigger_triage(
    alert_id: UUID,
    force_reanalyze: bool = False,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Trigger AI triage for an alert."""
    service = AlertService(db, tenant_id)
    result = service.triage_alert(alert_id, force_reanalyze)
    
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return result


@router.post("/{alert_id}/feedback")
def submit_feedback(
    alert_id: UUID,
    feedback: dict,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Submit feedback on AI triage."""
    service = AlertService(db, tenant_id)
    result = service.submit_feedback(alert_id, feedback)
    return {"feedback_id": result, "status": "recorded"}
