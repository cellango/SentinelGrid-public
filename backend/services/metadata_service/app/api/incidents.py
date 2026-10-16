"""Incident management router (from incident_service)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_current_tenant, get_tenant_session

router = APIRouter()


@router.get("/")
async def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_tenant: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """List incidents with filters."""
    # Implementation from incident_service
    return {"items": [], "total": 0, "tenant_id": current_tenant}


@router.get("/{incident_id}")
async def get_incident(
    incident_id: str,
    current_tenant: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Get incident by ID."""
    return {"id": incident_id, "status": "stub", "tenant_id": current_tenant}


@router.post("/")
async def create_incident(
    incident: dict,
    current_tenant: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Create new incident."""
    return {"id": "new-id", "status": "created", "tenant_id": current_tenant}
