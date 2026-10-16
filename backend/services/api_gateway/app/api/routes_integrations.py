"""Integration management routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.db import get_tenant_session
from sg_core.security import get_current_tenant

router = APIRouter()


@router.get("/")
def list_integrations(
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """List integrations for tenant."""
    # Stub implementation
    return {"items": []}


@router.post("/")
def create_integration(
    integration: dict,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Create or update an integration."""
    # Stub implementation
    return {"id": "int-1", "status": "created"}
