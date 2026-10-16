"""Scheduled reports API endpoints."""

import logging
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy import or_
from sqlalchemy.orm import Session
import sys
import os

# Add libs directory to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)
else:
    sys.path.insert(0, "/app/libs")

from app.core.database import get_tenant_session
from sg_core.security import get_current_payload, get_current_tenant
from app.models.report import ReportTemplate
from app.services.scheduler import get_scheduler
from app.models.template import ScheduleConfig
from app.services.report_access import (
    actor_id_from_payload,
    audit_report_event,
    enforce_template_roles,
    template_roles_satisfied,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _load_schedulable_template(
    db: Session,
    template_id: str,
    tenant_id: str,
    token_payload: dict[str, Any],
    *,
    allow_system_template_copy: bool = False,
) -> ReportTemplate:
    template = db.query(ReportTemplate).filter(
        ReportTemplate.id == template_id
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found"
        )

    enforce_template_roles(template, token_payload)

    if template.tenant_id is None:
        if not allow_system_template_copy:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System templates must be copied before updating schedules",
            )
        return _get_or_create_tenant_template_copy(db, template, tenant_id)

    if template.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Template not accessible for this tenant"
        )

    return template


def _get_or_create_tenant_template_copy(
    db: Session,
    system_template: ReportTemplate,
    tenant_id: str,
) -> ReportTemplate:
    existing_copy = db.query(ReportTemplate).filter(
        ReportTemplate.tenant_id == tenant_id,
        ReportTemplate.name == system_template.name,
        ReportTemplate.type == system_template.type,
    ).first()
    if existing_copy:
        return existing_copy

    tenant_template = ReportTemplate(
        tenant_id=tenant_id,
        name=system_template.name,
        description=system_template.description,
        type=system_template.type,
        sections=system_template.sections,
        data_queries=system_template.data_queries,
        schedule=None,
        required_roles=system_template.required_roles,
    )
    db.add(tenant_template)
    db.commit()
    db.refresh(tenant_template)
    return tenant_template


@router.get("/templates")
async def list_schedulable_templates(
    type_filter: Optional[str] = None,
    tenant_id: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    db: Session = Depends(get_tenant_session)
):
    """
    List tenant-owned and approved system templates that can be scheduled.
    Scheduling a system template creates or reuses a tenant-owned copy so
    schedule state never mutates the shared system template row.
    """
    query = db.query(ReportTemplate).filter(
        or_(
            ReportTemplate.tenant_id == tenant_id,
            ReportTemplate.tenant_id.is_(None),
        )
    )

    if type_filter:
        query = query.filter(ReportTemplate.type == type_filter)

    templates = [
        template
        for template in query.order_by(ReportTemplate.created_at.desc()).all()
        if template_roles_satisfied(template, token_payload)
    ]
    return [
        {
            "id": t.id,
            "name": t.name,
            "type": t.type,
            "schedule": t.schedule,
            "tenant_id": t.tenant_id,
            "is_system_template": t.tenant_id is None,
        }
        for t in templates
    ]


@router.get("/")
async def list_scheduled_reports(
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """List scheduled reports for the current tenant."""
    scheduler = get_scheduler()
    jobs = scheduler.list_scheduled_reports(tenant_id)
    
    # Enrich with template information
    enriched_jobs = []
    for job in jobs:
        # Extract template_id from job_id (format: report_{template_id}_{tenant_id})
        parts = job['job_id'].split('_')
        if len(parts) >= 2:
            template_id = parts[1]
            template = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
            if template:
                job['template_name'] = template.name
                job['template_id'] = template.id
        enriched_jobs.append(job)
    
    return {"items": enriched_jobs}


@router.post("/")
async def create_scheduled_report(
    request: dict = Body(...),
    tenant_id: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    db: Session = Depends(get_tenant_session)
):
    """Create a scheduled report."""
    template_id = request.get('template_id')
    schedule_data = request.get('schedule', {})
    
    if not template_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="template_id is required"
        )
    
    # Parse schedule config
    schedule = ScheduleConfig(**schedule_data)
    
    actor_user_id = actor_id_from_payload(token_payload)
    template = _load_schedulable_template(
        db,
        template_id,
        tenant_id,
        token_payload,
        allow_system_template_copy=True,
    )
    
    # Update template schedule
    schedule_payload = schedule.model_dump()
    template.schedule = schedule_payload
    db.commit()
    
    # Schedule the report
    scheduler = get_scheduler()
    job_id = scheduler.schedule_report(
        template,
        tenant_id,
        schedule_payload
    )

    await audit_report_event(
        action="report_schedule_created",
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        resource_type="report_template",
        resource_id=template.id,
        resource_name=template.name,
        metadata={
            "requested_template_id": template_id,
            "template_type": template.type,
            "job_id": job_id,
            "schedule": schedule_payload,
        },
    )
    
    return {
        "job_id": job_id,
        "template_id": template.id,
        "source_template_id": template_id if template.id != template_id else None,
        "schedule": schedule_payload,
        "message": "Scheduled report created successfully"
    }


@router.put("/{job_id}")
async def update_scheduled_report(
    job_id: str,
    schedule: ScheduleConfig,
    tenant_id: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    db: Session = Depends(get_tenant_session)
):
    """Update a scheduled report."""
    # Extract template_id from job_id
    parts = job_id.split('_')
    if len(parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    template_id = parts[1]
    
    actor_user_id = actor_id_from_payload(token_payload)
    template = _load_schedulable_template(db, template_id, tenant_id, token_payload)
    
    # Remove old job
    scheduler = get_scheduler()
    scheduler.unschedule_report(job_id)
    
    # Create new schedule
    schedule_payload = schedule.model_dump()
    template.schedule = schedule_payload
    db.commit()
    
    # Schedule new job
    new_job_id = scheduler.schedule_report(
        template,
        tenant_id,
        schedule_payload
    )

    await audit_report_event(
        action="report_schedule_updated",
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        resource_type="report_template",
        resource_id=template.id,
        resource_name=template.name,
        metadata={
            "previous_job_id": job_id,
            "job_id": new_job_id,
            "schedule": schedule_payload,
        },
    )
    
    return {
        "job_id": new_job_id,
        "schedule": schedule_payload,
        "message": "Scheduled report updated successfully"
    }


@router.delete("/{job_id}")
async def delete_scheduled_report(
    job_id: str,
    tenant_id: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    db: Session = Depends(get_tenant_session)
):
    """Delete a scheduled report."""
    # Extract template_id from job_id
    parts = job_id.split('_')
    if len(parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )
    
    template_id = parts[1]
    
    actor_user_id = actor_id_from_payload(token_payload)
    template = _load_schedulable_template(db, template_id, tenant_id, token_payload)
    
    # Remove schedule from template
    template.schedule = None
    db.commit()
    
    # Remove scheduled job
    scheduler = get_scheduler()
    scheduler.unschedule_report(job_id)

    await audit_report_event(
        action="report_schedule_deleted",
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        resource_type="report_template",
        resource_id=template.id,
        resource_name=template.name,
        metadata={"job_id": job_id},
    )
    
    return {"message": "Scheduled report deleted successfully"}
