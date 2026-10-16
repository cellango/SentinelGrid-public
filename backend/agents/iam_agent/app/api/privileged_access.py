"""
Privileged Access Controls API endpoints.

Manages just-in-time (JIT) privileged access with approval workflows.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.services.privileged_access_service import PrivilegedAccessService
from app.services.audit_service import AuditService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/privileged-access", tags=["privileged-access"])


# ============================================================================
# Request/Response Models
# ============================================================================

class PrivilegedAccessRequest(BaseModel):
    """Privileged access request."""
    resource_type: str = Field(..., pattern="^(role|permission|resource)$")
    resource_id: str
    resource_name: Optional[str] = None
    reason: str = Field(..., min_length=10)
    duration_hours: int = Field(default=1, ge=1, le=24)
    session_recording: bool = Field(default=False, description="Enable session recording for this grant (flag only)")


class PrivilegedAccessResponse(BaseModel):
    """Privileged access response."""
    id: str
    tenant_id: str
    requested_by: str
    resource_type: str
    resource_id: str
    resource_name: Optional[str]
    reason: str
    duration_hours: int
    status: str
    requested_at: datetime
    approved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    session_recording: bool = False


class ApproveRequest(BaseModel):
    """Approve privileged access request."""
    comments: Optional[str] = None


class RejectRequest(BaseModel):
    """Reject privileged access request."""
    rejection_reason: str = Field(..., min_length=5)


# ============================================================================
# Helper Functions
# ============================================================================

async def get_token_data(credentials: str) -> dict:
    """Extract and validate token, return token data with tenant_id."""
    from app.services.token_validator import TokenValidator
    from app.services.keycloak_client import KeycloakClient
    
    keycloak_client = KeycloakClient()
    validator = TokenValidator(keycloak_client)
    result = validator.validate_token(credentials)
    
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if not result.get("tenant_id"):
        raise HTTPException(status_code=403, detail="No tenant_id in token")
    
    return result


def get_realm_for_tenant(tenant_id: str) -> str:
    """Get Keycloak realm name for tenant."""
    return settings.KEYCLOAK_REALM


# ============================================================================
# Privileged Access Endpoints
# ============================================================================

@router.post("/request", response_model=PrivilegedAccessResponse)
async def request_privileged_access(
    request: PrivilegedAccessRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Request privileged access (JIT - Just In Time).
    
    Creates a request that requires approval before granting temporary elevated access.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    user_id = token_data.get("user_id") or token_data.get("payload", {}).get("sub")
    user_email = token_data.get("email")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="No user ID in token")
    
    logger.info(f"Privileged access requested by {user_id} for {request.resource_type}:{request.resource_id}")
    
    try:
        svc = PrivilegedAccessService()
        record = svc.create_request(
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            resource_name=request.resource_name,
            reason=request.reason,
            duration_hours=request.duration_hours,
            session_recording=request.session_recording,
        )

        try:
            AuditService.log_auth_event(
                realm_name=settings.KEYCLOAK_REALM,
                action="privileged_access_requested",
                actor_user_id=user_id,
                actor_email=user_email,
                details={
                    "request_id": record["id"],
                    "resource": request.resource_id,
                    "duration_hours": request.duration_hours,
                    "session_recording": request.session_recording,
                },
            )
        except Exception:
            logger.debug("Audit write skipped for privileged access request")

        return PrivilegedAccessResponse(**record)
        
    except Exception as e:
        logger.error(f"Error creating privileged access request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create request")


@router.get("/requests", response_model=List[PrivilegedAccessResponse])
async def list_privileged_access_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    requested_by: Optional[str] = Query(None, description="Filter by requester user id/email"),
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """List privileged access requests for the tenant."""
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    try:
        svc = PrivilegedAccessService()
        records = svc.list_requests(tenant_id, status=status, resource_type=resource_type, requested_by=requested_by)
        return [PrivilegedAccessResponse(**rec) for rec in records]

    except Exception as e:
        logger.error(f"Error listing privileged access requests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list requests")


@router.post("/requests/{request_id}/approve")
async def approve_privileged_access(
    request_id: str,
    approval: ApproveRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Approve a privileged access request.
    
    Requires approver role. Grants temporary access for specified duration.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    approver_id = token_data.get("user_id") or token_data.get("payload", {}).get("sub")
    approver_email = token_data.get("email")
    
    # Check if user has approver role
    if "TENANT_ADMIN" not in token_data.get("roles", []):
        raise HTTPException(status_code=403, detail="Approver role required")
    
    logger.info(f"Privileged access request {request_id} approved by {approver_id}")
    
    try:
        svc = PrivilegedAccessService()
        request_row = svc.get_request(request_id, tenant_id)
        if not request_row:
            raise HTTPException(status_code=404, detail="Request not found")
        if request_row["status"] not in {"pending", "approved"}:
            raise HTTPException(status_code=400, detail=f"Request already {request_row['status']}")

        realm = get_realm_for_tenant(tenant_id)
        await svc.grant_temporary_role(realm, request_row["requested_by"], request_row["resource_id"])

        expires_at = datetime.utcnow() + timedelta(hours=request_row.get("duration_hours") or 1)
        svc.update_status(
            request_id,
            status="approved",
            approver_id=approver_id,
            expires_at=expires_at,
            tenant_id=tenant_id,
        )

        try:
            AuditService.log_auth_event(
                realm_name=settings.KEYCLOAK_REALM,
                action="privileged_access_approved",
                actor_user_id=approver_id,
                actor_email=approver_email,
                details={
                    "request_id": request_id,
                    "resource": request_row["resource_id"],
                    "requested_by": request_row["requested_by"],
                    "expires_at": expires_at.isoformat(),
                    "session_recording": request_row.get("session_recording", False),
                },
            )
        except Exception:
            logger.debug("Audit write skipped for privileged access approval")

        return {
            "success": True,
            "message": "Privileged access approved",
            "request_id": request_id,
            "approved_at": datetime.utcnow().isoformat(),
            "approved_by": approver_id
        }

    except Exception as e:
        logger.error(f"Error approving privileged access: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to approve request")


@router.post("/requests/{request_id}/reject")
async def reject_privileged_access(
    request_id: str,
    rejection: RejectRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """Reject a privileged access request."""
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    approver_id = token_data.get("user_id") or token_data.get("payload", {}).get("sub")
    approver_email = token_data.get("email")
    
    # Check if user has approver role
    if "TENANT_ADMIN" not in token_data.get("roles", []):
        raise HTTPException(status_code=403, detail="Approver role required")
    
    try:
        svc = PrivilegedAccessService()
        request_row = svc.get_request(request_id, tenant_id)
        if not request_row:
            raise HTTPException(status_code=404, detail="Request not found")

        svc.update_status(
            request_id,
            status="rejected",
            approver_id=approver_id,
            tenant_id=tenant_id,
            rejection_reason=rejection.rejection_reason,
        )

        try:
            AuditService.log_auth_event(
                realm_name=settings.KEYCLOAK_REALM,
                action="privileged_access_rejected",
                actor_user_id=approver_id,
                actor_email=approver_email,
                details={"request_id": request_id, "reason": rejection.rejection_reason},
            )
        except Exception:
            logger.debug("Audit write skipped for privileged access rejection")

        return {
            "success": True,
            "message": "Privileged access rejected",
            "request_id": request_id,
            "rejected_at": datetime.utcnow().isoformat(),
            "rejected_by": approver_id
        }
    
    except Exception as e:
        logger.error(f"Error rejecting privileged access: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reject request")


@router.post("/requests/{request_id}/revoke")
async def revoke_privileged_access(
    request_id: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Revoke privileged access before expiration.
    
    Removes temporary access immediately.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    revoker_id = token_data.get("user_id") or token_data.get("payload", {}).get("sub")
    
    # Check if user has admin role
    if "TENANT_ADMIN" not in token_data.get("roles", []):
        raise HTTPException(status_code=403, detail="Admin role required")
    
    logger.warning(f"Privileged access {request_id} revoked by {revoker_id}")
    
    try:
        svc = PrivilegedAccessService()
        request_row = svc.get_request(request_id, tenant_id)
        if not request_row:
            raise HTTPException(status_code=404, detail="Request not found")

        realm = get_realm_for_tenant(tenant_id)
        await svc.revoke_role(realm, request_row["requested_by"], request_row["resource_id"])
        svc.update_status(
            request_id,
            status="revoked",
            approver_id=revoker_id,
            tenant_id=tenant_id,
            revoked_at=datetime.utcnow(),
        )

        try:
            AuditService.log_auth_event(
                realm_name=settings.KEYCLOAK_REALM,
                action="privileged_access_revoked",
                actor_user_id=revoker_id,
                actor_email=token_data.get("email"),
                details={"request_id": request_id, "resource": request_row["resource_id"], "requested_by": request_row["requested_by"]},
            )
        except Exception:
            logger.debug("Audit write skipped for privileged access revoke")

        return {
            "success": True,
            "message": "Privileged access revoked",
            "request_id": request_id,
            "revoked_at": datetime.utcnow().isoformat(),
            "revoked_by": revoker_id
        }
        
    except Exception as e:
        logger.error(f"Error revoking privileged access: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke access")
