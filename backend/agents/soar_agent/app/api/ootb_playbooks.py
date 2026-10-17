"""
API endpoints for Out-of-the-Box (OOTB) playbooks.
"""

import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_tenant_session
from app.models import Playbook
from app.services.playbook_seeder import (
    get_builtin_playbooks,
    clone_builtin_playbook,
    seed_all_ootb_playbooks,
)
from sg_core.dependencies import service_tenant_dependency
get_current_tenant = service_tenant_dependency('soar_service')

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/ootb", response_model=List[Playbook])
async def list_ootb_playbooks(
    tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    List all Out-of-the-Box playbooks available to the tenant.
    
    These are built-in playbooks that can be cloned and customized.
    """
    playbooks = get_builtin_playbooks(db, str(tenant_id))
    return [Playbook.model_validate(pb) for pb in playbooks]


@router.post("/ootb/{playbook_key}/clone", response_model=Playbook)
async def clone_ootb_playbook(
    playbook_key: str,
    new_name: str = None,
    tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Clone a built-in playbook for customization.
    
    This creates a copy of the OOTB playbook that the tenant can modify.
    """
    cloned = clone_builtin_playbook(
        db,
        playbook_key,
        str(tenant_id),
        new_name,
        created_by=str(tenant_id)  # TODO: Get actual user ID
    )
    
    if not cloned:
        raise HTTPException(
            status_code=404,
            detail=f"Built-in playbook {playbook_key} not found"
        )
    
    return Playbook.model_validate(cloned)


@router.post("/ootb/seed")
async def seed_ootb_playbooks(
    tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Seed all OOTB playbooks into the database.
    
    This endpoint is typically called during initial setup or migration.
    Should be protected with admin-only access.
    """
    try:
        seeded = seed_all_ootb_playbooks(db)
        return {
            "status": "success",
            "message": f"Seeded {len(seeded)} OOTB playbooks",
            "playbooks": [pb.playbook_key for pb in seeded],
            "tenant_id": str(tenant_id),
        }
    except Exception as e:
        logger.error(f"Error seeding OOTB playbooks: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error seeding playbooks: {str(e)}"
        )
