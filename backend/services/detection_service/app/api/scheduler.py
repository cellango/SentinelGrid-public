"""Scheduler management API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_tenant
from app.services.scheduler import (
    get_scheduler,
    start_scheduler,
    stop_scheduler,
    evaluate_all_rules_job,
)
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("/status")
def get_scheduler_status():
    """Get scheduler status."""
    scheduler = get_scheduler()
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        })
    
    return {
        "running": scheduler.running,
        "jobs": jobs,
    }


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

