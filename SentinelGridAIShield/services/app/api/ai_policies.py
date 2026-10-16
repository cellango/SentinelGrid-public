from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.security import (
    enforce_org_scope,
    ensure_record_org_access,
    get_internal_org_id,
    require_internal_service_token,
)
from app import models, schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.AiPolicyResponse])
def list_policies(
    org_id: UUID,
    ai_app_id: Optional[UUID] = None,
    _: str = Depends(require_internal_service_token),
    current_org_id: UUID = Depends(get_internal_org_id),
    db: Session = Depends(get_db),
):
    """List policies for an organization"""
    org_id = enforce_org_scope(current_org_id, org_id)
    query = db.query(models.AiPolicy).filter(models.AiPolicy.org_id == org_id)
    if ai_app_id:
        query = query.filter(models.AiPolicy.ai_app_id == ai_app_id)
    return query.all()

@router.post("/", response_model=schemas.AiPolicyResponse)
def create_policy(
    policy: schemas.AiPolicyCreate,
    _: str = Depends(require_internal_service_token),
    current_org_id: UUID = Depends(get_internal_org_id),
    db: Session = Depends(get_db),
):
    """Create a new policy"""
    org_id = enforce_org_scope(current_org_id, policy.org_id)
    db_policy = models.AiPolicy(**policy.dict(exclude={"org_id"}), org_id=org_id)
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    return db_policy

@router.get("/{policy_id}", response_model=schemas.AiPolicyResponse)
def get_policy(
    policy_id: UUID,
    _: str = Depends(require_internal_service_token),
    current_org_id: UUID = Depends(get_internal_org_id),
    db: Session = Depends(get_db),
):
    """Get policy by ID"""
    policy = db.query(models.AiPolicy).filter(models.AiPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    ensure_record_org_access(current_org_id, policy.org_id)
    return policy

@router.put("/{policy_id}", response_model=schemas.AiPolicyResponse)
def update_policy(
    policy_id: UUID,
    update: schemas.AiPolicyUpdate,
    _: str = Depends(require_internal_service_token),
    current_org_id: UUID = Depends(get_internal_org_id),
    db: Session = Depends(get_db),
):
    """Update policy"""
    policy = db.query(models.AiPolicy).filter(models.AiPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    ensure_record_org_access(current_org_id, policy.org_id)
    
    for key, value in update.dict(exclude_unset=True).items():
        setattr(policy, key, value)
    
    db.commit()
    db.refresh(policy)
    return policy

@router.delete("/{policy_id}")
def delete_policy(
    policy_id: UUID,
    _: str = Depends(require_internal_service_token),
    current_org_id: UUID = Depends(get_internal_org_id),
    db: Session = Depends(get_db),
):
    """Delete policy"""
    policy = db.query(models.AiPolicy).filter(models.AiPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    ensure_record_org_access(current_org_id, policy.org_id)
    
    db.delete(policy)
    db.commit()
    return {"status": "deleted"}
