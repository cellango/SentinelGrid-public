"""API endpoints for phishing email ingestion."""

import sys
import os
import asyncio
import httpx
import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Add libs to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from app.core.database import get_query_tenant_session
from app.services.phishing_service import PhishingService
from app.services.email_parser import EmailParser
from sg_core.schemas import (
    PhishingReportResponse,
    PhishingReportCreate,
    PhishingReportUpdate,
    PhishingObservableCreate,
    PhishingObservableResponse,
)
from app.core.config import settings

router = APIRouter(prefix="/api/v1/phishing", tags=["phishing"])


@router.post("/ingest", response_model=PhishingReportResponse, status_code=201)
async def ingest_email(
    raw_email: str,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_query_tenant_session)
):
    """
    Ingest a raw email (RFC 822 format).
    
    This endpoint accepts emails from webhooks or email providers.
    """
    try:
        # Parse email
        parser = EmailParser()
        parsed = parser.parse(raw_email)
        
        # Create report
        report_data = PhishingReportCreate(
            message_id=parsed["message_id"],
            subject=parsed["subject"],
            from_address=parsed["from_address"],
            to_address=parsed["to_address"],
            reply_to=parsed["reply_to"],
            received_date=parsed["received_date"],
            reported_by=parsed["reported_by"],
            raw_email=raw_email,
            html_body=parsed["html_body"],
            text_body=parsed["text_body"],
            attachments=parsed["attachments"]
        )
        
        service = PhishingService(db)
        report = service.create_report(tenant_id, report_data)
        
        # Extract observables
        urls = parser.extract_urls(parsed["html_body"], parsed["text_body"])
        domains = parser.extract_domains(urls, [parsed["from_address"]])
        ips = parser.extract_ips(parsed["text_body"] or "")
        emails = parser.extract_emails(parsed["text_body"] or "")
        
        # Add observables
        for url in urls:
            service.add_observable(
                tenant_id,
                report.id,
                PhishingObservableCreate(
                    observable_type="url",
                    observable_value=url,
                    observable_context="Email body"
                )
            )
        
        for domain in domains:
            service.add_observable(
                tenant_id,
                report.id,
                PhishingObservableCreate(
                    observable_type="domain",
                    observable_value=domain,
                    observable_context="Email content"
                )
            )
        
        # Trigger AI classification (async via background task)
        # Note: This is a simple implementation. In production, use a proper task queue.
        try:
            # Trigger classification asynchronously (non-blocking)
            asyncio.create_task(
                _trigger_classification_async(
                    settings.ORCHESTRATOR_URL,
                    settings.INTERNAL_SERVICE_TOKEN,
                    str(report.id),
                    str(tenant_id)
                )
            )
        except Exception as e:
            logger.warning(f"Failed to schedule AI classification: {e}")
        
        return PhishingReportResponse.model_validate(report)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ingesting email: {str(e)}")


@router.get("/reports", response_model=List[PhishingReportResponse])
async def list_reports(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    classification: Optional[str] = Query(None, description="Filter by classification"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_query_tenant_session)
):
    """List phishing reports with optional filters."""
    service = PhishingService(db)
    reports = service.list_reports(tenant_id, status, classification, limit, offset)
    return [PhishingReportResponse.model_validate(r) for r in reports]


@router.get("/reports/{report_id}", response_model=PhishingReportResponse)
async def get_report(
    report_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_query_tenant_session)
):
    """Get a phishing report by ID."""
    service = PhishingService(db)
    report = service.get_report(tenant_id, report_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Phishing report not found")
    
    return PhishingReportResponse.model_validate(report)


@router.get("/reports/{report_id}/observables", response_model=List[PhishingObservableResponse])
async def get_observables(
    report_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_query_tenant_session)
):
    """Get observables for a phishing report."""
    service = PhishingService(db)
    observables = service.get_observables(tenant_id, report_id)
    return [PhishingObservableResponse.model_validate(o) for o in observables]


@router.post("/reports/{report_id}/classify", response_model=PhishingReportResponse)
async def trigger_classification(
    report_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_query_tenant_session)
):
    """
    Trigger AI classification for a phishing report.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.ORCHESTRATOR_URL}/api/v1/orchestrator/analyze-phishing-email",
                json={
                    "phishing_report_id": str(report_id),
                    "tenant_id": str(tenant_id),
                    "force_reanalyze": False
                },
                headers={
                    "Authorization": f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"
                }
            )
            response.raise_for_status()
        
        # Fetch updated report
        service = PhishingService(db)
        report = service.get_report(tenant_id, report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Phishing report not found")
        
        return PhishingReportResponse.model_validate(report)
        
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Error calling orchestrator: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering classification: {str(e)}")


async def _trigger_classification_async(
    orchestrator_url: str,
    internal_token: str,
    report_id: str,
    tenant_id: str
):
    """Background task to trigger AI classification."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            await client.post(
                f"{orchestrator_url}/api/v1/orchestrator/analyze-phishing-email",
                json={
                    "phishing_report_id": report_id,
                    "tenant_id": tenant_id,
                    "force_reanalyze": False
                },
                headers={
                    "Authorization": f"Bearer {internal_token}"
                }
            )
    except Exception as e:
        logger.error(f"Failed to trigger AI classification for report {report_id}: {e}")


@router.put("/reports/{report_id}", response_model=PhishingReportResponse)
async def update_report(
    report_id: UUID,
    update_data: PhishingReportUpdate,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_query_tenant_session)
):
    """Update a phishing report."""
    service = PhishingService(db)
    report = service.update_report(tenant_id, report_id, update_data)
    
    if not report:
        raise HTTPException(status_code=404, detail="Phishing report not found")
    
    return PhishingReportResponse.model_validate(report)
