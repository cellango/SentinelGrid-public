"""Webhook handlers for TheHive updates."""

import logging
from uuid import UUID
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
import httpx

from app.core.database import get_tenant_db
from app.core.config import settings
from sg_core.models import Ticket, Incident

from app.core.security import require_soar_request

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_soar_request)])


def validate_thehive_webhook_auth(
    x_api_key: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> UUID:
    raise HTTPException(503, "Owned SOAR webhook identity and effect contract required")


def get_thehive_tenant_session(
    tenant_id: UUID = Depends(validate_thehive_webhook_auth),
):
    yield from get_tenant_db(tenant_id)


@router.post("/thehive/case/update")
async def handle_thehive_case_update(
    request: Request,
    tenant_id: UUID = Depends(validate_thehive_webhook_auth),
    db: Session = Depends(get_thehive_tenant_session),
):
    """
    Handle TheHive case update webhook.
    
    This endpoint receives webhooks from TheHive when cases are updated.
    We sync the updates back to SentinelGrid tickets/incidents.
    """
    try:
        webhook_data = await request.json()
        logger.info(f"Received TheHive webhook: {webhook_data}")
        
        # Extract case data
        case_data = webhook_data.get("object", {})
        case_id = case_data.get("_id") or case_data.get("id")
        
        if not case_id:
            logger.warning("No case ID in webhook data")
            return {"status": "ignored", "reason": "No case ID"}
        
        # Find corresponding ticket/incident by external_id
        ticket = db.query(Ticket).filter(
            Ticket.external_id == case_id,
            Ticket.tenant_id == tenant_id,
        ).first()
        
        incident = db.query(Incident).filter(
            Incident.external_id == case_id,
            Incident.tenant_id == tenant_id,
        ).first()
        
        # Update ticket if found
        if ticket:
            # Map TheHive status to ticket status
            thehive_status = case_data.get("status", "").lower()
            status_map = {
                "open": "open",
                "inprogress": "in_progress",
                "resolved": "resolved",
                "closed": "resolved",
            }
            ticket.status = status_map.get(thehive_status, ticket.status)
            
            # Map TheHive severity to ticket severity
            thehive_severity = case_data.get("severity")
            if thehive_severity:
                severity_map = {4: "critical", 3: "high", 2: "medium", 1: "low"}
                ticket.severity = severity_map.get(thehive_severity, ticket.severity)
            
            db.commit()
            logger.info(f"Updated ticket {ticket.id} from TheHive case {case_id}")
        
        # Update incident if found
        if incident:
            thehive_status = case_data.get("status", "").lower()
            status_map = {
                "open": "open",
                "inprogress": "in_progress",
                "resolved": "resolved",
                "closed": "closed",
            }
            incident.status = status_map.get(thehive_status, incident.status)
            
            thehive_severity = case_data.get("severity")
            if thehive_severity:
                severity_map = {4: "critical", 3: "high", 2: "medium", 1: "low"}
                incident.severity = severity_map.get(thehive_severity, incident.severity)
            
            db.commit()
            logger.info(f"Updated incident {incident.id} from TheHive case {case_id}")
        
        if not ticket and not incident:
            logger.warning(f"No ticket or incident found for TheHive case {case_id}")
            return {"status": "ignored", "reason": "No matching ticket/incident"}
        
        return {"status": "processed", "case_id": case_id}
    
    except Exception as e:
        logger.error(f"Error processing TheHive webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/thehive/observable/update")
async def handle_thehive_observable_update(
    request: Request,
    tenant_id: UUID = Depends(validate_thehive_webhook_auth),
    db: Session = Depends(get_thehive_tenant_session),
):
    """
    Handle TheHive observable update webhook.
    
    This endpoint receives webhooks from TheHive when observables are updated
    (e.g., after analyzer runs).
    """
    try:
        webhook_data = await request.json()
        logger.info(f"Received TheHive observable webhook: {webhook_data}")
        del db
        
        # Extract observable data
        observable_data = webhook_data.get("object", {})
        observable_id = observable_data.get("_id") or observable_data.get("id")
        
        if not observable_id:
            logger.warning("No observable ID in webhook data")
            return {"status": "ignored", "reason": "No observable ID"}
        
        # Process observable update
        # This could trigger additional enrichment or update ticket data
        logger.info(f"Processed observable update: {observable_id}")
        
        return {"status": "processed", "observable_id": observable_id, "tenant_id": str(tenant_id)}
    
    except Exception as e:
        logger.error(f"Error processing TheHive observable webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
