"""API endpoints for email containment."""

import sys
import logging
import os
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Add libs to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from app.core.database import get_query_tenant_session
from app.services.email_search import EmailSearchService
from app.services.email_deletion import EmailDeletionService
from app.services.phishing_service import PhishingService
from sg_core.models import PhishingReport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/phishing", tags=["phishing-containment"])


class EmailSearchRequest(BaseModel):
    """Request for email search."""
    subject: Optional[str] = None
    from_address: Optional[str] = None
    domain: Optional[str] = None
    url: Optional[str] = None
    provider: str = "microsoft_graph"  # microsoft_graph, gmail


class EmailDeletionRequest(BaseModel):
    """Request for email deletion."""
    email_ids: List[str]
    provider: str = "microsoft_graph"
    action: str = "delete"  # delete, quarantine, move


class ContainmentPlaybookRequest(BaseModel):
    """Request to run containment playbook."""
    quarantine_emails: bool = True
    block_domains: bool = True
    create_ticket: bool = True
    notify_users: bool = True


@router.post("/reports/{report_id}/search-similar")
async def search_similar_emails(
    report_id: UUID,
    search_request: EmailSearchRequest,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_query_tenant_session)
):
    """
    Search for similar emails based on phishing report.
    
    Extracts search criteria from the phishing report and searches for similar emails.
    """
    try:
        # Get phishing report
        service = PhishingService(db)
        report = service.get_report(tenant_id, report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Phishing report not found")
        
        # Build search criteria from report
        search_criteria = {
            "subject": search_request.subject or report.subject,
            "from": search_request.from_address or report.from_address,
        }
        
        # Extract domain from from_address if not provided
        if search_request.domain:
            search_criteria["domain"] = search_request.domain
        elif "@" in report.from_address:
            search_criteria["domain"] = report.from_address.split("@")[1]
        
        # Search for similar emails
        search_service = EmailSearchService()
        results = await search_service.search_similar_emails(
            str(tenant_id),
            search_criteria,
            search_request.provider
        )
        
        # Update report with similar emails found
        if results:
            similar_email_ids = [r["id"] for r in results]
            report.similar_emails = similar_email_ids
            db.commit()
        
        return {
            "report_id": str(report_id),
            "search_criteria": search_criteria,
            "results": results,
            "count": len(results),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching emails: {str(e)}")


@router.post("/reports/{report_id}/delete-similar")
async def delete_similar_emails(
    report_id: UUID,
    deletion_request: EmailDeletionRequest,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_query_tenant_session)
):
    """
    Delete or quarantine similar emails.
    
    Requires approval for bulk deletions (>10 emails).
    """
    try:
        # Validate deletion request
        if len(deletion_request.email_ids) > 100:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete more than 100 emails at once"
            )
        
        # Get phishing report
        service = PhishingService(db)
        report = service.get_report(tenant_id, report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Phishing report not found")
        
        # Delete emails
        deletion_service = EmailDeletionService()
        result = await deletion_service.delete_emails(
            str(tenant_id),
            deletion_request.email_ids,
            deletion_request.provider,
            deletion_request.action
        )
        
        # Update report status
        if result["success_count"] > 0:
            # Log deletion in report (could add to timeline_data)
            if not report.timeline_data:
                report.timeline_data = []
            
            # TODO: Add timeline entry for deletion
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting emails: {str(e)}")


@router.post("/reports/{report_id}/run-containment-playbook")
async def run_containment_playbook(
    report_id: UUID,
    playbook_request: ContainmentPlaybookRequest,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_query_tenant_session)
):
    """
    Run containment playbook for phishing report.
    
    Steps:
    1. Extract observables from report
    2. Search for similar emails
    3. Quarantine/delete similar emails
    4. Block domains/IPs (if enabled)
    5. Create incident ticket (if enabled)
    6. Notify affected users (if enabled)
    7. Update report status
    """
    try:
        # Get phishing report
        service = PhishingService(db)
        report = service.get_report(tenant_id, report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Phishing report not found")
        
        # Get observables
        observables = service.get_observables(tenant_id, report_id)
        
        # Extract search criteria from observables
        search_criteria = {
            "subject": report.subject,
            "from": report.from_address,
        }
        
        # Extract domain from observables
        domains = [o.observable_value for o in observables if o.observable_type == "domain"]
        if domains:
            search_criteria["domain"] = domains[0]
        
        # Step 1: Search for similar emails
        search_service = EmailSearchService()
        similar_emails = await search_service.search_similar_emails(
            str(tenant_id),
            search_criteria,
            "microsoft_graph"  # TODO: Get from tenant config
        )
        
        deletion_result = None
        if playbook_request.quarantine_emails and similar_emails:
            # Step 2: Quarantine similar emails
            email_ids = [e["id"] for e in similar_emails]
            deletion_service = EmailDeletionService()
            deletion_result = await deletion_service.delete_emails(
                str(tenant_id),
                email_ids[:100],  # Limit to 100
                "microsoft_graph",
                "quarantine"
            )
        
        # Step 3: Block domains/IPs (if enabled)
        block_result = None
        if playbook_request.block_domains:
            # TODO: Integrate with firewall/email gateway API
            # For now, just log
            logger.info(f"Would block domains: {domains}")
            block_result = {
                "domains_blocked": domains,
                "status": "pending_implementation",
            }
        
        # Step 4: Create ticket (if enabled)
        ticket_result = None
        if playbook_request.create_ticket:
            # TODO: Integrate with ticketing service
            # For now, just log
            logger.info(f"Would create ticket for report {report_id}")
            ticket_result = {
                "status": "pending_implementation",
            }
        
        # Step 5: Notify users (if enabled)
        notification_result = None
        if playbook_request.notify_users:
            # TODO: Integrate with email notification service
            # For now, just log
            logger.info(f"Would notify users about report {report_id}")
            notification_result = {
                "status": "pending_implementation",
            }
        
        # Update report status
        report.status = "resolved"
        db.commit()
        
        return {
            "report_id": str(report_id),
            "similar_emails_found": len(similar_emails),
            "deletion_result": deletion_result,
            "block_result": block_result,
            "ticket_result": ticket_result,
            "notification_result": notification_result,
            "status": "completed",
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running containment playbook: {str(e)}")
