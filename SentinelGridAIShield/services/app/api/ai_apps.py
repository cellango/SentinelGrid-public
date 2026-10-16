from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.security import (
    enforce_org_scope,
    ensure_record_org_access,
    generate_api_key,
    get_internal_org_id,
    hash_api_key,
    require_internal_service_token,
)
from app import models, schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.AiAppResponse])
def list_ai_apps(
    org_id: UUID,
    _: str = Depends(require_internal_service_token),
    current_org_id: UUID = Depends(get_internal_org_id),
    db: Session = Depends(get_db),
):
    """List all AI apps for an organization"""
    org_id = enforce_org_scope(current_org_id, org_id)
    apps = db.query(models.AiApp).filter(models.AiApp.org_id == org_id).all()
    return apps

@router.post("/", response_model=schemas.AiAppWithKey)
def create_ai_app(
    app: schemas.AiAppCreate,
    _: str = Depends(require_internal_service_token),
    current_org_id: UUID = Depends(get_internal_org_id),
    db: Session = Depends(get_db),
):
    """Create a new AI app with API key"""
    org_id = enforce_org_scope(current_org_id, app.org_id)
    # Generate API key
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    
    db_app = models.AiApp(
        **app.dict(exclude={"org_id"}),
        org_id=org_id,
        api_key_hash=api_key_hash
    )
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    
    # Return app with plain API key (only time it's visible)
    response = schemas.AiAppWithKey(**db_app.__dict__, api_key=api_key)
    return response

@router.get("/{app_id}", response_model=schemas.AiAppResponse)
def get_ai_app(
    app_id: UUID,
    _: str = Depends(require_internal_service_token),
    current_org_id: UUID = Depends(get_internal_org_id),
    db: Session = Depends(get_db),
):
    """Get AI app by ID"""
    app = db.query(models.AiApp).filter(models.AiApp.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="AI App not found")
    ensure_record_org_access(current_org_id, app.org_id)
    return app

@router.put("/{app_id}", response_model=schemas.AiAppResponse)
def update_ai_app(
    app_id: UUID,
    update: schemas.AiAppUpdate,
    _: str = Depends(require_internal_service_token),
    current_org_id: UUID = Depends(get_internal_org_id),
    db: Session = Depends(get_db),
):
    """Update AI app"""
    app = db.query(models.AiApp).filter(models.AiApp.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="AI App not found")
    ensure_record_org_access(current_org_id, app.org_id)
    
    for key, value in update.dict(exclude_unset=True).items():
        setattr(app, key, value)
    
    db.commit()
    db.refresh(app)
    return app

@router.delete("/{app_id}")
def delete_ai_app(
    app_id: UUID,
    _: str = Depends(require_internal_service_token),
    current_org_id: UUID = Depends(get_internal_org_id),
    db: Session = Depends(get_db),
):
    """Delete AI app"""
    app = db.query(models.AiApp).filter(models.AiApp.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="AI App not found")
    ensure_record_org_access(current_org_id, app.org_id)
    
    db.delete(app)
    db.commit()
    return {"status": "deleted"}

@router.post("/{app_id}/keys", response_model=dict)
def regenerate_api_key(
    app_id: UUID,
    _: str = Depends(require_internal_service_token),
    current_org_id: UUID = Depends(get_internal_org_id),
    db: Session = Depends(get_db),
):
    """Regenerate API key for an app"""
    app = db.query(models.AiApp).filter(models.AiApp.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="AI App not found")
    ensure_record_org_access(current_org_id, app.org_id)
    
    api_key = generate_api_key()
    app.api_key_hash = hash_api_key(api_key)
    
    db.commit()
    return {"api_key": api_key}
