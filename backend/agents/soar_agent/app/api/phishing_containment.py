"""API endpoints for phishing containment playbook."""

import sys
import os
from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Add libs to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from app.core.database import get_tenant_db
from app.services.phishing_containment_playbook import PhishingContainmentPlaybook

router = APIRouter(prefix="/api/v1/playbooks", tags=["phishing-containment"])


def get_query_tenant_session(
    tenant_id: UUID = Query(..., description="Tenant ID"),
):
    """Open a tenant-scoped DB session for query-derived tenant context."""
    yield from get_tenant_db(str(tenant_id))


class ContainmentPlaybookRequest(BaseModel):
    """Request to execute containment playbook."""
    phishing_report_id: UUID
    context: Dict[str, Any] = {
        "search_emails": True,
        "quarantine_emails": True,
        "block_domains": True,
        "create_ticket": True,
        "notify_users": True,
        "email_provider": "microsoft_graph",
    }


@router.post("/phishing-containment/execute")
async def execute_containment_playbook(
    request: ContainmentPlaybookRequest,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_query_tenant_session)
):
    """
    Execute phishing containment playbook.
    
    This playbook:
    1. Extracts observables from phishing report
    2. Searches for similar emails
    3. Quarantines similar emails
    4. Blocks malicious domains/IPs
    5. Creates incident ticket
    6. Notifies affected users
    """
    try:
        playbook = PhishingContainmentPlaybook()
        result = await playbook.execute(
            tenant_id=tenant_id,
            phishing_report_id=request.phishing_report_id,
            context=request.context
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing containment playbook: {str(e)}")
