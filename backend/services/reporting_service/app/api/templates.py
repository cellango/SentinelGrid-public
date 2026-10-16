"""Report template API endpoints."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
import sys
import os

# Add libs directory to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)
else:
    sys.path.insert(0, "/app/libs")

from app.core.database import get_tenant_session
from sg_core.security import get_current_tenant
from app.models.report import ReportTemplate
from app.models.template import (
    ReportTemplateCreate,
    ReportTemplateResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[ReportTemplateResponse])
async def list_templates(
    type_filter: Optional[str] = None,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """
    List available report templates.
    Returns both system templates (tenant_id=NULL) and tenant-specific templates.
    """
    query = db.query(ReportTemplate).filter(
        or_(
            ReportTemplate.tenant_id == tenant_id,
            ReportTemplate.tenant_id.is_(None)  # System templates
        )
    )
    
    if type_filter:
        query = query.filter(ReportTemplate.type == type_filter)
    
    templates = query.order_by(ReportTemplate.created_at.desc()).all()
    return [ReportTemplateResponse.model_validate(t) for t in templates]


@router.get("/{template_id}", response_model=ReportTemplateResponse)
async def get_template(
    template_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Get a specific report template."""
    template = db.query(ReportTemplate).filter(
        ReportTemplate.id == template_id
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found"
        )
    
    # Check access (system templates are accessible to all)
    if template.tenant_id and template.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Template not accessible for this tenant"
        )
    
    return ReportTemplateResponse.model_validate(template)


@router.post("/", response_model=ReportTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template: ReportTemplateCreate,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Create a new report template."""
    try:
        db_template = ReportTemplate(
            tenant_id=tenant_id,
            name=template.name,
            description=template.description,
            type=template.type,
            sections=template.sections,
            data_queries=template.data_queries,
            schedule=template.schedule.model_dump() if template.schedule else None,
            required_roles=template.required_roles
        )
        
        db.add(db_template)
        db.commit()
        db.refresh(db_template)
        
        return ReportTemplateResponse.model_validate(db_template)
    
    except Exception as e:
        logger.error(f"Failed to create template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}"
        )
