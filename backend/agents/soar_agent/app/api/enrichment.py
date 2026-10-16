"""API endpoints for ticket enrichment."""

import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_tenant_db
from app.services.enrichment_service import EnrichmentService
from sg_core.schemas import TicketAIEnrichmentResponse

logger = logging.getLogger(__name__)

router = APIRouter()
enrichment_service = EnrichmentService()


def get_query_tenant_session(
    tenant_id: UUID = Query(..., description="Tenant ID"),
):
    """Open a tenant-scoped DB session for query-derived tenant context."""
    yield from get_tenant_db(str(tenant_id))


@router.post("/ticket/{ticket_id}", response_model=TicketAIEnrichmentResponse)
async def enrich_ticket(
    ticket_id: UUID,
    enrichment_type: str = Query("all", description="Type of enrichment: iam, vulnerability, cmdb, network, framework, all"),
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_query_tenant_session)
):
    """
    Trigger enrichment for a ticket.
    
    Args:
        ticket_id: Ticket ID to enrich
        enrichment_type: Type of enrichment to perform
        tenant_id: Tenant ID
        db: Database session
    
    Returns:
        Enrichment result
    """
    try:
        enrichment = await enrichment_service.enrich_ticket(
            db, ticket_id, tenant_id, enrichment_type
        )
        return enrichment
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error enriching ticket {ticket_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/ticket/{ticket_id}", response_model=TicketAIEnrichmentResponse)
async def get_enrichment(
    ticket_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_query_tenant_session)
):
    """Get enrichment data for a ticket."""
    enrichment = enrichment_service.get_enrichment(db, ticket_id, tenant_id)
    if not enrichment:
        raise HTTPException(status_code=404, detail="Enrichment not found")
    return enrichment
