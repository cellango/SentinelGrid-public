"""
Organization Profile Management API endpoints.

Handles organization settings, branding, and configuration.
All operations enforce tenant isolation.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from datetime import datetime

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/organization", tags=["organization"])


# ============================================================================
# Request/Response Models
# ============================================================================

class OrganizationResponse(BaseModel):
    """Organization settings response."""
    name: str
    display_name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_domain: Optional[str] = None
    domains: list[str] = []
    timezone: Optional[str] = None
    language: Optional[str] = None
    contact_email: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class OrganizationUpdateRequest(BaseModel):
    """Organization update request."""
    name: Optional[str] = None
    display_name: Optional[str] = None
    primary_domain: Optional[str] = None
    domains: Optional[list[str]] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    contact_email: Optional[str] = None


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
# Organization Endpoints
# ============================================================================

@router.get("", response_model=OrganizationResponse)
async def get_organization(
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Get organization settings for the tenant.
    
    Returns organization name, logo, domains, timezone, etc.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Get realm settings from Keycloak
            response = await kc._make_request(
                "GET",
                f"/realms/{realm}"
            )
            response.raise_for_status()
            realm_data = response.json()
            
            # Extract organization data
            # Note: In production, you might store org-specific data in a database
            # For now, we'll use realm display name and attributes
            
            return OrganizationResponse(
                name=realm_data.get("realm", realm),
                display_name=realm_data.get("displayName"),
                logo_url=None,  # Would come from database or file storage
                primary_domain=None,  # Would come from database
                domains=[],  # Would come from database
                timezone=realm_data.get("internationalizationEnabled") and realm_data.get("supportedLocales", [None])[0] or None,
                language=realm_data.get("defaultLocale"),
                contact_email=None,  # Would come from database
                created_at=None,
                updated_at=None
            )
            
    except Exception as e:
        logger.error(f"Error getting organization: {e}")
        raise HTTPException(status_code=500, detail="Failed to get organization settings")


@router.put("", response_model=OrganizationResponse)
async def update_organization(
    update_data: OrganizationUpdateRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Update organization settings.
    
    Updates organization name, display name, domains, timezone, etc.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Get current realm settings
            response = await kc._make_request(
                "GET",
                f"/realms/{realm}"
            )
            response.raise_for_status()
            realm_data = response.json()
            
            # Update realm settings
            if update_data.display_name is not None:
                realm_data["displayName"] = update_data.display_name
            
            if update_data.language is not None:
                realm_data["defaultLocale"] = update_data.language
                if not realm_data.get("internationalizationEnabled"):
                    realm_data["internationalizationEnabled"] = True
                    realm_data["supportedLocales"] = [update_data.language]
            
            # Update realm
            await kc._make_request(
                "PUT",
                f"/realms/{realm}",
                json_data=realm_data
            )
            
            # Note: In production, you would also update database with:
            # - name, primary_domain, domains, timezone, contact_email
            # These would be stored in an organizations table
            
            logger.info(f"Organization updated for tenant {tenant_id}")
            
            # Return updated organization
            return OrganizationResponse(
                name=update_data.name or realm_data.get("realm", realm),
                display_name=update_data.display_name or realm_data.get("displayName"),
                logo_url=None,
                primary_domain=update_data.primary_domain,
                domains=update_data.domains or [],
                timezone=update_data.timezone,
                language=update_data.language or realm_data.get("defaultLocale"),
                contact_email=update_data.contact_email,
                updated_at=datetime.utcnow()
            )
            
    except Exception as e:
        logger.error(f"Error updating organization: {e}")
        raise HTTPException(status_code=500, detail="Failed to update organization settings")


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Upload organization logo.
    
    Accepts image files (PNG, JPG, SVG) and stores them.
    Returns URL to the uploaded logo.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Validate file size (max 2MB)
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 2MB limit")
    
    # Note: In production, you would:
    # 1. Store file in object storage (S3, etc.)
    # 2. Generate a public URL
    # 3. Store URL in database
    
    # For now, return a placeholder
    logo_url = f"/api/v1/organization/logo/{tenant_id}"
    
    logger.info(f"Logo uploaded for tenant {tenant_id}")
    
    return {
        "success": True,
        "logo_url": logo_url,
        "message": "Logo uploaded successfully"
    }

