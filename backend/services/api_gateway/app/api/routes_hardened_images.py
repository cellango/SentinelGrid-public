"""Hardened image management routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.db import get_tenant_session
from sg_core.security import get_current_tenant

router = APIRouter()


@router.get("/recommendations/list")
def list_hardened_image_recommendations(
    cloud_provider: Optional[str] = Query(None, description="Filter by cloud provider: aws|azure|gcp"),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Get hardened image recommendations."""
    # Stub implementation - return empty list
    return {
        "items": [],
        "total": 0,
        "cloud_provider": cloud_provider
    }
