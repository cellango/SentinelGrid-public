"""Report sharing API endpoints."""

import os
import sys
import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

# Add libs directory to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)
else:
    sys.path.insert(0, "/app/libs")

from app.core.database import get_db, get_tenant_db, get_tenant_session
from sg_core.security import get_current_payload, get_current_tenant
from app.models.report import Report, ReportShare
from app.services.share_service import ShareService
from app.services.report_access import (
    actor_id_from_payload,
    audit_report_event,
    enforce_report_template_roles,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


def _report_status_value(report: Report) -> str:
    value = getattr(report, "status", "")
    if hasattr(value, "value"):
        return str(value.value).lower()
    return str(value).lower()


class ShareCreateRequest(BaseModel):
    """Request model for creating a share."""
    expires_in_days: int = 7
    password: Optional[str] = None


class ShareResponse(BaseModel):
    """Response model for a share."""
    id: str
    report_id: str
    share_token: str
    share_url: str
    expires_at: Optional[str]
    password_protected: bool
    access_count: int
    last_accessed_at: Optional[str]
    created_at: str
    
    class Config:
        from_attributes = True


@router.post("/reports/{report_id}/share", response_model=ShareResponse)
async def create_share(
    report_id: str,
    request: ShareCreateRequest,
    tenant_id: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    db: Session = Depends(get_tenant_session)
):
    """Create a shareable link for a report."""
    try:
        report = db.query(Report).filter(
            Report.id == report_id,
            Report.tenant_id == tenant_id,
        ).first()

        if not report:
            raise ValueError(f"Report {report_id} not found or not accessible")

        enforce_report_template_roles(db, report, token_payload)
        actor_user_id = actor_id_from_payload(token_payload)
        share_service = ShareService()
        share = share_service.create_share(
            db,
            report_id,
            tenant_id,
            expires_in_days=request.expires_in_days,
            password=request.password,
            created_by=actor_user_id,
        )
        
        share_url = share_service.generate_share_url(share.share_token)

        await audit_report_event(
            action="report_share_created",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            resource_type="report_share",
            resource_id=share.id,
            resource_name=report.name,
            metadata={
                "report_id": report.id,
                "expires_at": share.expires_at.isoformat() if share.expires_at else None,
                "password_protected": share.password_hash is not None,
            },
        )
        
        return ShareResponse(
            id=share.id,
            report_id=share.report_id,
            share_token=share.share_token,
            share_url=share_url,
            expires_at=share.expires_at.isoformat() if share.expires_at else None,
            password_protected=share.password_hash is not None,
            access_count=share.access_count,
            last_accessed_at=share.last_accessed_at.isoformat() if share.last_accessed_at else None,
            created_at=share.created_at.isoformat()
        )
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create share: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create share: {str(e)}"
        )


@router.get("/reports/{report_id}/shares", response_model=List[ShareResponse])
async def list_shares(
    report_id: str,
    tenant_id: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    db: Session = Depends(get_tenant_session)
):
    """List all shares for a report."""
    # Verify report belongs to tenant
    report = db.query(Report).filter(
        Report.id == report_id,
        Report.tenant_id == tenant_id
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found"
        )

    enforce_report_template_roles(db, report, token_payload)
    
    share_service = ShareService()
    shares = share_service.list_shares(db, report_id=report_id, tenant_id=tenant_id)
    
    return [
        ShareResponse(
            id=share.id,
            report_id=share.report_id,
            share_token=share.share_token,
            share_url=share_service.generate_share_url(share.share_token),
            expires_at=share.expires_at.isoformat() if share.expires_at else None,
            password_protected=share.password_hash is not None,
            access_count=share.access_count,
            last_accessed_at=share.last_accessed_at.isoformat() if share.last_accessed_at else None,
            created_at=share.created_at.isoformat()
        )
        for share in shares
    ]


@router.delete("/shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_share(
    share_id: str,
    tenant_id: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    db: Session = Depends(get_tenant_session)
):
    """Delete a share."""
    try:
        share_service = ShareService()
        share = db.query(ReportShare).filter(
            ReportShare.id == share_id,
            ReportShare.tenant_id == tenant_id,
        ).first()
        if not share:
            raise ValueError(f"Share {share_id} not found")
        report = db.query(Report).filter(
            Report.id == share.report_id,
            Report.tenant_id == tenant_id,
        ).first()
        if report:
            enforce_report_template_roles(db, report, token_payload)
        share_service.delete_share(db, share_id, tenant_id)
        await audit_report_event(
            action="report_share_deleted",
            tenant_id=tenant_id,
            actor_user_id=actor_id_from_payload(token_payload),
            resource_type="report_share",
            resource_id=share_id,
            resource_name=getattr(report, "name", None),
            metadata={"report_id": getattr(share, "report_id", None)},
        )
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


def resolve_shared_report_tenant(
    share_token: str,
    db: Session = Depends(get_db)
) -> str:
    """Resolve the report tenant from the public share token."""
    share_service = ShareService()
    share = share_service.get_share_record(db, share_token)

    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found or expired"
        )

    return share.tenant_id


def get_shared_report_session(
    tenant_id: str = Depends(resolve_shared_report_tenant)
):
    """Open a tenant-scoped DB session for public share access."""
    yield from get_tenant_db(tenant_id)


@router.get("/shared/{share_token}")
async def access_shared_report(
    share_token: str,
    password: Optional[str] = Query(None),
    tenant_id: str = Depends(resolve_shared_report_tenant),
    db: Session = Depends(get_shared_report_session)
):
    """
    Access a shared report (public endpoint, no auth required).
    Returns the report download URL if access is granted.
    """
    del tenant_id
    share_service = ShareService()
    share = share_service.get_share_record(db, share_token)
    
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found or expired"
        )

    if share_service.is_expired(share):
        await audit_report_event(
            action="report_share_expired_access",
            tenant_id=share.tenant_id,
            actor_user_id="public_share_viewer",
            resource_type="report_share",
            resource_id=share.id,
            success=False,
            metadata={
                "report_id": share.report_id,
                "share_token": share_token,
                "expires_at": share.expires_at.isoformat() if share.expires_at else None,
            },
            error_message="Share not found or expired",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found or expired",
        )
    
    # Check password if protected
    if share.password_hash:
        if not password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password required"
            )
        
        if not share_service.verify_password(share, password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )
    
    # Get report
    report = db.query(Report).filter(Report.id == share.report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    if _report_status_value(report) != 'completed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report is not ready yet"
        )
    
    # Record access
    share_service.access_share(db, share)

    await audit_report_event(
        action="report_share_viewed",
        tenant_id=share.tenant_id,
        actor_user_id="public_share_viewer",
        resource_type="report_share",
        resource_id=share.id,
        resource_name=report.name,
        metadata={
            "report_id": report.id,
            "format": report.format.value if hasattr(report.format, "value") else str(report.format),
            "access_count": share.access_count,
        },
    )
    
    return {
        "report_id": report.id,
        "report_name": report.name,
        "download_url": report.download_url,
        "format": report.format,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None
    }
