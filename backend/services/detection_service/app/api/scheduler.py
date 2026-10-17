"""Scheduler management API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_tenant, require_detection_request
from app.services.scheduler import (
    get_scheduler,
    read_scheduler_status,
    start_scheduler,
    stop_scheduler,
    evaluate_all_rules_job,
)
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduler", tags=["scheduler"], dependencies=[Depends(require_detection_request)])


@router.get("/status")
def get_scheduler_status():
    """Observe only an already initialized runtime under exact service-wide authority."""
    try:
        return read_scheduler_status()
    except Exception:
        raise HTTPException(503, "Detection scheduler runtime unavailable") from None


@router.post("/start")
async def start_scheduler_endpoint(
    tenant_id: str = Depends(get_current_tenant)
):
    """Start the rule evaluation scheduler."""
    scheduler = get_scheduler()
    
    if scheduler.running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduler is already running"
        )
    
    start_scheduler(tenant_id)
    
    return {
        "status": "started",
        "tenant_id": tenant_id,
        "interval_seconds": 60,  # From config
    }


@router.post("/stop")
def stop_scheduler_endpoint():
    """Stop the rule evaluation scheduler."""
    scheduler = get_scheduler()
    
    if not scheduler.running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduler is not running"
        )
    
    stop_scheduler()
    
    return {"status": "stopped"}


@router.post("/trigger")
async def trigger_evaluation_now(
    tenant_id: str = Depends(get_current_tenant)
):
    """Manually trigger rule evaluation immediately."""
    try:
        results = await evaluate_all_rules_job(tenant_id)
        
        return {
            "status": "completed",
            "results": results,
        }
    
    except Exception as e:
        logger.error(f"Error triggering rule evaluation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate rules: {str(e)}"
        )

