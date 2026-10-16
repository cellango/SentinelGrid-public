"""
User Onboarding API endpoints.

Handles user invitations, bulk imports, and onboarding workflows.
All operations enforce tenant isolation.
"""

import logging
import csv
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.services.invitation_service import InvitationService
from app.services.bulk_import_service import BulkImportService
from app.core.config import settings
from app.api.request_context import get_tenant_session
from app.services.birthright_service import BirthrightService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["user-onboarding"])
security = HTTPBearer()


# ============================================================================
# Request/Response Models
# ============================================================================

class UserInviteRequest(BaseModel):
    """User invitation request."""
    email: EmailStr
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    role: Optional[str] = None
    send_email: bool = True
    expires_in_days: int = Field(default=7, ge=1, le=30)


class UserInviteResponse(BaseModel):
    """User invitation response."""
    invitation_id: str
    email: str
    invitation_token: str
    expires_at: datetime
    status: str


class InvitationListResponse(BaseModel):
    """List of invitations."""
    items: List[UserInviteResponse]
    total: int


class BulkUploadResponse(BaseModel):
    """Bulk upload response."""
    total_rows: int
    successful: int
    failed: int
    errors: List[dict]


# ============================================================================
# Helper Functions
# ============================================================================

def get_current_request_context(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Extract and validate token, returning tenant_id + realm_name for multi-realm setups."""
    from app.services.token_validator import TokenValidator
    from app.services.keycloak_client import KeycloakClient

    validator = TokenValidator(KeycloakClient())
    result = validator.validate_token(credentials.credentials)

    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid token")

    payload = result.get("payload") or {}
    tenant_id = result.get("tenant_id") or payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=403, detail="No tenant_id in token")

    issuer = payload.get("iss", "")
    realm_name = (
        issuer.split("/realms/")[-1].rstrip("/")
        if "/realms/" in issuer
        else settings.KEYCLOAK_REALM
    )

    return {
        "tenant_id": tenant_id,
        "realm_name": realm_name,
        "user_id": result.get("user_id") or payload.get("sub"),
        "email": result.get("email") or payload.get("email"),
    }


# ============================================================================
# User Onboarding Endpoints
# ============================================================================

@router.post("/invite", response_model=UserInviteResponse)
async def invite_user(
    invite_data: UserInviteRequest,
    ctx: dict = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    """
    Send invitation email to a new user.
    
    Creates a user account in Keycloak (disabled) and sends invitation email.
    User must accept invitation and set password before account is enabled.
    """
    tenant_id = ctx["tenant_id"]
    realm = ctx["realm_name"]
    
    logger.info(f"Inviting user {invite_data.email} for tenant {tenant_id}")
    
    try:
        invitation_service = InvitationService()
        
        # Create invitation
        invitation = await invitation_service.create_invitation(
            realm=realm,
            tenant_id=tenant_id,
            email=invite_data.email,
            first_name=invite_data.firstName,
            last_name=invite_data.lastName,
            role=invite_data.role,
            expires_in_days=invite_data.expires_in_days,
            send_email=invite_data.send_email
        )

        # Apply birthright baseline (best-effort; do not fail invitation if not configured)
        try:
            if invitation.get("user_id"):
                BirthrightService.apply_default_access_profile(
                    db,
                    tenant_id=str(tenant_id),
                    user_id=str(invitation["user_id"]),
                    granted_by=ctx.get("user_id"),
                )
        except Exception as e:
            logger.warning(f"Birthright default profile apply failed for invited user: {e}")
        
        return UserInviteResponse(
            invitation_id=invitation["invitation_id"],
            email=invitation["email"],
            invitation_token=invitation["invitation_token"],
            expires_at=invitation["expires_at"],
            status=invitation["status"]
        )
        
    except Exception as e:
        logger.error(f"Error inviting user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to invite user: {str(e)}")


@router.get("/invitations", response_model=InvitationListResponse)
async def list_invitations(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    ctx: dict = Depends(get_current_request_context),
):
    """
    List pending invitations for the tenant.
    
    Can filter by status: 'pending', 'accepted', 'expired', 'cancelled'
    """
    tenant_id = ctx["tenant_id"]
    realm = ctx["realm_name"]
    
    try:
        invitation_service = InvitationService()
        invitations = await invitation_service.list_invitations(
            tenant_id=tenant_id,
            realm=realm,
            status=status,
            page=page,
            limit=limit
        )
        
        return InvitationListResponse(
            items=[
                UserInviteResponse(
                    invitation_id=inv["invitation_id"],
                    email=inv["email"],
                    invitation_token=inv["invitation_token"],
                    expires_at=inv["expires_at"],
                    status=inv["status"]
                )
                for inv in invitations["items"]
            ],
            total=invitations["total"]
        )
        
    except Exception as e:
        logger.error(f"Error listing invitations: {e}")
        raise HTTPException(status_code=500, detail="Failed to list invitations")


@router.post("/bulk-upload", response_model=BulkUploadResponse)
async def bulk_upload_users(
    file: UploadFile = File(...),
    ctx: dict = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session),
):
    """
    Bulk import users from CSV file.
    
    CSV format:
    email,firstName,lastName,role,enabled
    user@example.com,John,Doe,SOC_ANALYST,true
    
    Returns summary of successful and failed imports.
    """
    tenant_id = ctx["tenant_id"]
    realm = ctx["realm_name"]
    
    logger.info(f"Bulk uploading users for tenant {tenant_id}")
    
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    try:
        # Read CSV content
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        bulk_service = BulkImportService()
        result = await bulk_service.import_users(
            tenant_id=tenant_id,
            realm=realm,
            csv_rows=list(csv_reader)
        )

        # Apply birthright baseline for newly created users (best-effort)
        try:
            created_users = result.get("created_users") or []
            for created in created_users:
                created_user_id = created.get("user_id")
                if not created_user_id:
                    continue
                BirthrightService.apply_default_access_profile(
                    db,
                    tenant_id=str(tenant_id),
                    user_id=str(created_user_id),
                    granted_by=ctx.get("user_id"),
                )
        except Exception as e:
            logger.warning(f"Birthright default profile apply failed for bulk upload: {e}")
        
        return BulkUploadResponse(
            total_rows=result["total_rows"],
            successful=result["successful"],
            failed=result["failed"],
            errors=result["errors"]
        )
        
    except Exception as e:
        logger.error(f"Error in bulk upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Bulk upload failed: {str(e)}")


@router.delete("/invitations/{invitation_id}")
async def cancel_invitation(
    invitation_id: str,
    ctx: dict = Depends(get_current_request_context),
):
    """Cancel a pending invitation."""
    tenant_id = ctx["tenant_id"]
    realm = ctx["realm_name"]
    
    try:
        invitation_service = InvitationService()
        await invitation_service.cancel_invitation(tenant_id, invitation_id, realm=realm)
        
        return {"success": True, "message": "Invitation cancelled"}
        
    except Exception as e:
        logger.error(f"Error cancelling invitation: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel invitation")
