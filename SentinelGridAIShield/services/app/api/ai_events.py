from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.security import enforce_org_scope, get_internal_org_id, require_internal_service_token
from app import models, schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.AiEventResponse])
def list_events(
    org_id: UUID,
    ai_app_id: Optional[UUID] = None,
    limit: int = 100,
    _: str = Depends(require_internal_service_token),
    current_org_id: UUID = Depends(get_internal_org_id),
    db: Session = Depends(get_db)
):
    """List AI events for an organization"""
    org_id = enforce_org_scope(current_org_id, org_id)
    query = db.query(models.AiEvent).filter(models.AiEvent.org_id == org_id)
    if ai_app_id:
        query = query.filter(models.AiEvent.ai_app_id == ai_app_id)
    
    return query.order_by(models.AiEvent.created_at.desc()).limit(limit).all()
