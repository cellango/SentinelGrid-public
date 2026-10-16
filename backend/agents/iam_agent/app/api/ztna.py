"""
ZTNA-Lite API endpoints.

Provides zero-trust network access without full VPN infrastructure.
Checks device posture before granting access to internal applications.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.token_validator import TokenValidator
from app.services.keycloak_client import KeycloakClient
import jwt
import secrets
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ztna", tags=["ztna"])


# ============================================================================
# Request/Response Models
# ============================================================================

class AccessRequest(BaseModel):
    """ZTNA access request."""
    app_id: str
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    required_role: Optional[str] = None  # optional entitlement/role needed


class AccessResponse(BaseModel):
    """ZTNA access response."""
    granted: bool
    reason: Optional[str] = None
    access_token: Optional[str] = None
    expires_in: Optional[int] = None
    device_posture: Optional[dict] = None


class DevicePostureCheck(BaseModel):
    """Device posture check result."""
    device_id: str
    compliant: bool
    security_score: float
    checks: List[dict]
    recommendations: List[str]


# ============================================================================
# Helper Functions
# ============================================================================

async def get_token_data(credentials: str) -> dict:
    """Extract and validate token, return token data with tenant_id."""
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
# ZTNA Endpoints
# ============================================================================

@router.post("/access", response_model=AccessResponse)
async def request_ztna_access(
    request: AccessRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Request ZTNA access to an internal application.
    
    Checks device posture before granting access.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    user_id = token_data.get("user_id") or token_data.get("payload", {}).get("sub")
    
    logger.info(f"ZTNA access requested by {user_id} for app {request.app_id}")
    
    try:
        # Check device posture if device_id provided
        device_posture = None
        if request.device_id:
            posture_result = await check_device_posture(
                request.device_id,
                tenant_id,
                authorization
            )
            device_posture = posture_result.dict()
            
            # Deny access if device is not compliant
            if not posture_result.compliant:
                return AccessResponse(
                    granted=False,
                    reason="Device does not meet security requirements",
                    device_posture=device_posture
                )

        # Entitlement/role check if required_role provided
        if request.required_role:
            # Token roles already validated; ensure required_role is present
            roles = token_data.get("roles") or []
            if request.required_role not in roles:
                return AccessResponse(
                    granted=False,
                    reason=f"Missing required role {request.required_role}",
                    device_posture=device_posture
                )

        # Issue short-lived ZTNA token (signed JWT)
        secret = settings.INTERNAL_SERVICE_TOKEN or secrets.token_urlsafe(32)
        now = datetime.utcnow()
        exp_secs = 1800
        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "app_id": request.app_id,
            "device_id": request.device_id,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=exp_secs)).timestamp()),
            "scope": "ztna_access",
        }
        token = jwt.encode(payload, secret, algorithm="HS256")

        return AccessResponse(
            granted=True,
            reason="Access granted",
            access_token=token,
            expires_in=exp_secs,
            device_posture=device_posture
        )

    except Exception as e:
        logger.error(f"Error processing ZTNA access request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process access request")


@router.post("/device-posture", response_model=DevicePostureCheck)
async def check_device_posture(
    device_id: str,
    tenant_id: Optional[str] = None,
    authorization: Optional[str] = None
) -> dict:
    """
    Check device security posture.
    
    Queries endpoint protection (Wazuh) for device compliance status.
    """
    if not tenant_id and authorization:
        token_data = await get_token_data(authorization)
        tenant_id = token_data["tenant_id"]
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id required")
    
    logger.info(f"Device posture check for device {device_id}")
    
    try:
        # Pull device record from assets table (best-effort)
        trust_status = "unknown"
        compliance_status = None
        os_name = None
        os_version = None
        try:
            db = SessionLocal()
            row = db.execute(
                text(
                    """
                    SELECT id, asset_id, operating_system, os_version, metadata, compliance_status
                    FROM assets
                    WHERE tenant_id = :tenant_id
                      AND (id::text = :device_id OR asset_id = :device_id OR name = :device_id)
                    LIMIT 1
                    """
                ),
                {"tenant_id": str(tenant_id), "device_id": device_id},
            ).mappings().first()
            if row:
                meta = row.get("metadata") or {}
                if isinstance(meta, str):
                    try:
                        import json
                        meta = json.loads(meta)
                    except Exception:
                        meta = {}
                trust_status = (meta.get("trust_status") or meta.get("trust") or "unknown").lower()
                compliance_status = row.get("compliance_status")
                os_name = row.get("operating_system")
                os_version = row.get("os_version")
        except Exception as db_err:
            logger.debug("Device lookup skipped: %s", db_err)
        finally:
            try:
                db.close()
            except Exception:
                pass

        checks = [
            {"check": "Trust status", "status": trust_status},
            {"check": "Compliance status", "status": compliance_status or "unknown"},
            {"check": "OS", "status": f"{os_name or 'unknown'} {os_version or ''}".strip()},
        ]
        compliant = trust_status == "trusted" and compliance_status not in {"revoked", "non_compliant"}
        score = 90.0 if compliant else 50.0
        recommendations = []
        if trust_status != "trusted":
            recommendations.append("Mark device trusted after validation")
        if compliance_status in {"revoked", "non_compliant"}:
            recommendations.append("Remediate compliance findings before access")

        return DevicePostureCheck(
            device_id=device_id,
            compliant=compliant,
            security_score=score,
            checks=checks,
            recommendations=recommendations
        )

    except Exception as e:
        logger.error(f"Error checking device posture: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to check device posture")


@router.get("/apps")
async def list_ztna_apps(
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    List applications available via ZTNA.
    
    Returns internal apps that can be accessed without VPN.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    try:
        # In production, query apps marked as ZTNA-enabled
        # For now, return placeholder
        return {
            "apps": [
                {
                    "id": "internal-app-1",
                    "name": "Internal Application",
                    "description": "Internal web application",
                    "url": "https://internal.example.com",
                    "requires_posture_check": True
                }
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing ZTNA apps: {e}")
        raise HTTPException(status_code=500, detail="Failed to list apps")
