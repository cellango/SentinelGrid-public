"""API endpoints for ticket management."""

import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db, get_tenant_session
from app.services.ticket_service import TicketService
from app.services.thehive_integration import TheHiveIntegration
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))
from sg_core.dependencies import get_current_tenant
from sg_core.models import Incident
from sg_events.workflow import (
    WorkflowEventType,
    WorkflowStage,
)
from sg_agent_runtime.soc_case_runtime_client import SOCCaseRuntimeClient
from app.core.config import settings


class TicketResponse(BaseModel):
    """Ticket response schema."""
    id: UUID
    tenant_id: UUID
    title: str
    description: Optional[str] = None
    status: str
    severity: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None
    source: Optional[str] = None
    external_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

logger = logging.getLogger(__name__)

router = APIRouter()
ticket_service = TicketService()
thehive_integration = TheHiveIntegration()


class TicketCreate(BaseModel):
    """Ticket creation schema."""
    title: str
    description: Optional[str] = None
    status: str = "open"
    severity: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    source: str = "thehive"
    external_id: Optional[str] = None
    alert_ids: Optional[List[str]] = None
    cve_ids: Optional[List[str]] = None
    exploit_indicators: Optional[dict] = None
    assigned_to: Optional[str] = None
    created_by: Optional[str] = None
    due_date: Optional[str] = None
    incident_id: Optional[str] = None
    incident_management_mode: Optional[str] = None
    fix_group_id: Optional[str] = None
    scan_id: Optional[str] = None
    workflow_id: Optional[str] = None


class TicketUpdate(BaseModel):
    """Ticket update schema."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None


class TicketCommentCreate(BaseModel):
    """Ticket comment schema."""
    comment: str


def _find_linked_incident_id(
    db: Session,
    tenant_id: UUID,
    ticket_id: UUID,
) -> str | None:
    incident = (
        db.query(Incident)
        .filter(
            Incident.ticket_id == ticket_id,
            Incident.tenant_id == tenant_id,
        )
        .first()
    )
    return str(incident.id) if incident else None


def _submit_soc_case_refresh(
    tenant_id: UUID,
    incident_id: str,
    source_event_id: str,
    changed_fields: list[str],
    reason: str,
) -> dict | None:
    client = SOCCaseRuntimeClient(
        runtime_url=getattr(settings, "AGENT_RUNTIME_URL", None),
        internal_token=settings.INTERNAL_SERVICE_TOKEN,
    )
    return client.submit_case_refresh_sync(
        tenant_id=str(tenant_id),
        incident_id=incident_id,
        trigger_type="ticket_updated",
        source_kind="ticket_update",
        source_event_id=source_event_id,
        changed_fields=changed_fields,
        reason=reason,
    )


def _submit_soc_case_refresh_best_effort(
    tenant_id: UUID,
    incident_id: str,
    source_event_id: str,
    changed_fields: list[str],
    reason: str,
) -> dict | None:
    try:
        return _submit_soc_case_refresh(
            tenant_id,
            incident_id,
            source_event_id,
            changed_fields,
            reason,
        )
    except Exception as exc:
        logger.warning(
            "Failed submitting SOC case refresh for linked incident %s from ticket event %s: %s",
            incident_id,
            source_event_id,
            exc,
        )
        return None


def _skip_soc_case_refresh(request: Request) -> bool:
    return request.headers.get("X-SG-SOC-Refresh-Skip", "").lower() == "true"


@router.post("", response_model=TicketResponse)
async def create_ticket(
    ticket: TicketCreate,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """
    Create a new ticket with automatic enrichment.
    """
    try:
        from app.services.tenant_context import get_tenant_slug_for_id

        ticket_data = ticket.dict()
        tenant_uuid = UUID(str(tenant_id))
        tenant_slug = get_tenant_slug_for_id(db, tenant_uuid)
        if tenant_slug:
            ticket_data["tenant_slug"] = tenant_slug
        handoff_config = ticket_service.resolve_handoff_config(db, tenant_uuid, ticket_data)
        created_ticket = await ticket_service.create_ticket(
            db,
            tenant_uuid,
            ticket_data,
            handoff_config=handoff_config,
        )
        
        # Create TheHive case only for SaaS-managed tenants
        if thehive_integration.base_url and not handoff_config.customer_managed:
            thehive_case = await thehive_integration.create_case_from_ticket({
                **ticket_data,
                "id": str(created_ticket.id),
                "tenant_id": str(tenant_uuid)
            })
            if thehive_case:
                created_ticket.external_vendor_id = thehive_case.get("id")
                created_ticket.timeline_data = ticket_service._annotate_external_provider(
                    created_ticket.timeline_data,
                    "thehive",
                )
                if ticket_data.get("incident_id"):
                    db.execute(
                        text(
                            """
                            UPDATE incidents
                            SET external_ticket_id = :external_id,
                                external_ticket_provider = :provider
                            WHERE id = :incident_id AND tenant_id = :tenant_id
                            """
                        ),
                        {
                            "external_id": str(thehive_case.get("id")),
                            "provider": "thehive",
                            "incident_id": ticket_data["incident_id"],
                            "tenant_id": str(tenant_uuid),
                        },
                    )
                db.commit()
                db.refresh(created_ticket)
                ticket_service._publish_workflow_event_safe(
                    event_type=WorkflowEventType.TICKET_HANDOFF_COMPLETED,
                    stage=WorkflowStage.TICKETING,
                    db=db,
                    tenant_id=tenant_uuid,
                    workflow_id=ticket_data.get("workflow_id") or ticket_data.get("incident_id") or created_ticket.id,
                    title="TheHive handoff created",
                    resource_type="incident" if ticket_data.get("incident_id") else "ticket",
                    resource_id=ticket_data.get("incident_id") or created_ticket.id,
                    resource_name=created_ticket.title,
                    related_resources=[
                        {
                            "type": "ticket",
                            "id": str(created_ticket.id),
                            "title": created_ticket.title,
                        }
                    ],
                    metadata={
                        "provider": "thehive",
                        "external_vendor_id": str(thehive_case.get("id")),
                        "ticket_id": str(created_ticket.id),
                    },
                )
            else:
                ticket_service._publish_workflow_event_safe(
                    event_type=WorkflowEventType.TICKET_HANDOFF_SKIPPED,
                    stage=WorkflowStage.TICKETING,
                    db=db,
                    tenant_id=tenant_uuid,
                    workflow_id=ticket_data.get("workflow_id") or ticket_data.get("incident_id") or created_ticket.id,
                    title="TheHive handoff not completed",
                    resource_type="incident" if ticket_data.get("incident_id") else "ticket",
                    resource_id=ticket_data.get("incident_id") or created_ticket.id,
                    resource_name=created_ticket.title,
                    related_resources=[
                        {
                            "type": "ticket",
                            "id": str(created_ticket.id),
                            "title": created_ticket.title,
                        }
                    ],
                    metadata={
                        "provider": "thehive",
                        "ticket_id": str(created_ticket.id),
                    },
                )

        return created_ticket
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Get ticket by ID."""
    tenant_uuid = UUID(str(tenant_id))
    ticket = ticket_service.get_ticket(db, ticket_id, tenant_uuid)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    ticket: TicketUpdate,
    request: Request,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Update ticket."""
    try:
        ticket_data = {k: v for k, v in ticket.dict().items() if v is not None}
        tenant_uuid = UUID(str(tenant_id))
        updated_ticket = await ticket_service.update_ticket(db, ticket_id, tenant_uuid, ticket_data)
        
        external_provider = (updated_ticket.timeline_data or {}).get("external_ticket_provider")

        # Sync status to TheHive only when the stored external provider is TheHive
        if external_provider == "thehive" and updated_ticket.external_vendor_id and ticket_data.get("status"):
            await thehive_integration.sync_case_status(
                updated_ticket.external_vendor_id,
                ticket_data["status"]
            )

        # If ticket is closed/resolved and linked to a FixGroup, trigger verification
        if ticket_data.get("status") and ticket_data["status"].lower() in ("closed", "resolved"):
            vm_data = updated_ticket.vm_data or {}
            await ticket_service._trigger_fixgroup_verification(
                tenant_id=tenant_uuid,
                scan_id=vm_data.get("scan_id"),
                fix_group_id=vm_data.get("fix_group_id"),
            )

        if not _skip_soc_case_refresh(request):
            linked_incident_id = _find_linked_incident_id(db, tenant_uuid, updated_ticket.id)
            if linked_incident_id:
                _submit_soc_case_refresh_best_effort(
                    tenant_uuid,
                    linked_incident_id,
                    str(updated_ticket.id),
                    sorted(ticket_data.keys()),
                    "Ticket fields were updated for a linked incident.",
                )
        
        return updated_ticket
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating ticket: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{ticket_id}/comments", response_model=TicketResponse)
async def add_ticket_comment(
    ticket_id: str,
    payload: TicketCommentCreate,
    request: Request,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Add a ticket comment and sync it downstream when supported."""
    try:
        tenant_uuid = UUID(str(tenant_id))
        updated_ticket = await ticket_service.add_comment(
            db,
            ticket_id,
            tenant_uuid,
            payload.comment,
        )
        if not _skip_soc_case_refresh(request):
            linked_incident_id = _find_linked_incident_id(db, tenant_uuid, updated_ticket.id)
            if linked_incident_id:
                _submit_soc_case_refresh_best_effort(
                    tenant_uuid,
                    linked_incident_id,
                    str(updated_ticket.id),
                    ["comment"],
                    "A linked ticket comment was added by an operator.",
                )
        return updated_ticket
    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 422
        raise HTTPException(status_code=status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding ticket comment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=List[TicketResponse])
async def search_tickets(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Search tickets."""
    tenant_uuid = UUID(str(tenant_id))
    tickets = ticket_service.search_tickets(
        db=db,
        tenant_id=tenant_uuid,
        status=status,
        severity=severity,
        category=category,
        limit=limit,
        offset=offset
    )
    return tickets


@router.get("/{ticket_id}/tabs/{tab_name}")
async def get_tab_data(
    ticket_id: UUID,
    tab_name: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """
    Get tab-specific data for a ticket.
    
    Tab names: iam, vm, cmdb, network, timeline
    """
    tenant_uuid = UUID(str(tenant_id))
    ticket = ticket_service.get_ticket(db, ticket_id, tenant_uuid)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    
    tab_data_map = {
        "iam": ticket.iam_data,
        "vm": ticket.vm_data,
        "cmdb": ticket.cmdb_data,
        "network": ticket.network_data,
        "timeline": ticket.timeline_data
    }
    
    if tab_name not in tab_data_map:
        raise HTTPException(status_code=400, detail=f"Invalid tab name: {tab_name}")
    
    return {
        "tab": tab_name,
        "data": tab_data_map[tab_name] or {}
    }
