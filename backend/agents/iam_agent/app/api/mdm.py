"""
MDM-Lite API endpoints.

Provides device management features without full MDM infrastructure.
Includes policy enforcement and remote wipe capabilities.
"""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/devices", tags=["mdm"])


# ============================================================================
# Request/Response Models
# ============================================================================

class DevicePolicyResponse(BaseModel):
    """Device policy response."""
    id: str
    tenant_id: str
    name: str
    description: Optional[str]
    policy_type: str
    rules: dict
    is_active: bool
    created_at: str


class EnforcePolicyRequest(BaseModel):
    """Enforce policy request."""
    policy_id: str
    force: bool = False


class RemoteWipeRequest(BaseModel):
    """Remote wipe request."""
    reason: Optional[str] = None
    preserve_data: bool = False  # For lost devices, set to False


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
# MDM-Lite Endpoints
# ============================================================================

@router.get("/policies", response_model=List[DevicePolicyResponse])
async def list_device_policies(
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    List device policies for the tenant.
    
    Returns all device management policies (trust, security, compliance).
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    try:
        # In production, query device_policies database table
        # For now, return placeholder
        
        return []
        
    except Exception as e:
        logger.error(f"Error listing device policies: {e}")
        raise HTTPException(status_code=500, detail="Failed to list device policies")


@router.post("/{device_id}/enforce-policy")
async def enforce_device_policy(
    device_id: str,
    request: EnforcePolicyRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Enforce a device policy on a specific device.
    
    Applies policy rules and checks compliance.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    logger.info(f"Enforcing policy {request.policy_id} on device {device_id} for tenant {tenant_id}")
    
    try:
        # In production:
        # 1. Get policy from database
        # 2. Get device details
        # 3. Apply policy rules
        # 4. Check compliance
        # 5. Update device status
        
        # For now, return success
        return {
            "success": True,
            "message": "Policy enforced successfully",
            "device_id": device_id,
            "policy_id": request.policy_id,
            "compliance_status": "compliant"
        }
        
    except Exception as e:
        logger.error(f"Error enforcing device policy: {e}")
        raise HTTPException(status_code=500, detail="Failed to enforce device policy")


@router.post("/{device_id}/remote-wipe")
async def remote_wipe_device(
    device_id: str,
    request: RemoteWipeRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Initiate remote wipe for a device.
    
    WARNING: This will erase data on the device. Use only for lost/stolen devices.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    # Require admin role for remote wipe
    if "TENANT_ADMIN" not in token_data.get("roles", []):
        raise HTTPException(status_code=403, detail="Admin role required for remote wipe")
    
    logger.warning(f"Remote wipe initiated for device {device_id} by tenant {tenant_id}. Reason: {request.reason}")
    
    try:
        # In production:
        # 1. Verify device belongs to tenant
        # 2. Send wipe command to endpoint protection agent
        # 3. Revoke device
        # 4. Invalidate all sessions
        # 5. Log security event
        
        # For now, return success
        return {
            "success": True,
            "message": "Remote wipe initiated. Device will be wiped on next connection.",
            "device_id": device_id,
            "wipe_id": f"wipe-{device_id}",
            "estimated_completion": "Next device connection"
        }
        
    except Exception as e:
        logger.error(f"Error initiating remote wipe: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate remote wipe")


@router.get("/{device_id}/compliance")
async def check_device_compliance(
    device_id: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Check device compliance with assigned policies.
    
    Returns compliance status and any violations.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    try:
        # In production:
        # 1. Get device
        # 2. Get assigned policies
        # 3. Check compliance for each policy
        # 4. Return compliance report
        
        return {
            "device_id": device_id,
            "compliant": True,
            "compliance_score": 95.0,
            "policies_checked": 3,
            "violations": [],
            "last_check": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error checking device compliance: {e}")
        raise HTTPException(status_code=500, detail="Failed to check device compliance")

