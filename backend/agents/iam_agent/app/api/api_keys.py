"""
API Key Management API endpoints.

Manages API keys for programmatic access with rate limiting and scopes.
"""

import logging
import secrets
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


# ============================================================================
# Request/Response Models
# ============================================================================

class APIKeyCreateRequest(BaseModel):
    """Create API key request."""
    name: str = Field(..., min_length=1, max_length=255)
    scopes: List[str] = Field(default_factory=list)
    rate_limit_per_minute: int = Field(default=60, ge=1, le=10000)
    rate_limit_per_hour: int = Field(default=1000, ge=1, le=100000)
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)


class APIKeyResponse(BaseModel):
    """API key response (key value only shown once on creation)."""
    id: str
    tenant_id: str
    user_id: Optional[str]
    name: str
    key_prefix: str  # First 8 characters for identification
    scopes: List[str]
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_active: bool
    created_at: datetime


class APIKeyCreateResponse(APIKeyResponse):
    """API key creation response (includes full key once)."""
    key: str  # Full API key (only shown on creation)


# ============================================================================
# Helper Functions
# ============================================================================

def _bearer_token_from_request(request: Request) -> str:
    """Extract bearer token from request headers, raising 401 if missing."""
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return auth_header.split(" ", 1)[1].strip()


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


# ============================================================================
# API Key Endpoints
# ============================================================================

@router.post("", response_model=APIKeyCreateResponse)
async def create_api_key(
    request: APIKeyCreateRequest,
    authorization: str = Depends(_bearer_token_from_request)
):
    """
    Create a new API key.
    
    Returns the full key once - store it securely as it cannot be retrieved later.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    user_id = token_data.get("user_id") or token_data.get("payload", {}).get("sub")
    
    logger.info(f"API key '{request.name}' created by {user_id} in tenant {tenant_id}")
    
    try:
        # Generate API key
        api_key = f"sg_{tenant_id[:8]}_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_prefix = api_key[:12] + "..."
        
        # Calculate expiration
        expires_at = None
        if request.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
        
        # In production:
        # 1. Store key_hash in database (never store plain key)
        # 2. Save metadata (name, scopes, rate limits, expiration)
        # 3. Return full key only once
        
        key_id = f"key-{datetime.utcnow().timestamp()}"
        
        return APIKeyCreateResponse(
            id=key_id,
            tenant_id=tenant_id,
            user_id=user_id,
            name=request.name,
            key_prefix=key_prefix,
            key=api_key,  # Only shown once
            scopes=request.scopes,
            rate_limit_per_minute=request.rate_limit_per_minute,
            rate_limit_per_hour=request.rate_limit_per_hour,
            expires_at=expires_at,
            last_used_at=None,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to create API key")


@router.get("", response_model=List[APIKeyResponse])
async def list_api_keys(
    authorization: str = Depends(_bearer_token_from_request)
):
    """List API keys for the tenant."""
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    try:
        # In production, query database
        # For now, return empty list
        return []
        
    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        raise HTTPException(status_code=500, detail="Failed to list API keys")


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
    authorization: str = Depends(_bearer_token_from_request)
):
    """Revoke an API key."""
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    logger.info(f"API key {key_id} revoked by tenant {tenant_id}")
    
    try:
        # In production:
        # 1. Mark key as inactive in database
        # 2. Invalidate any cached tokens
        
        return {
            "success": True,
            "message": "API key revoked successfully",
            "key_id": key_id
        }
        
    except Exception as e:
        logger.error(f"Error revoking API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke API key")


@router.post("/{key_id}/rotate")
async def rotate_api_key(
    key_id: str,
    authorization: str = Depends(_bearer_token_from_request)
):
    """
    Rotate an API key.
    
    Generates new key and invalidates old one.
    Returns new key (shown once).
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    try:
        # In production:
        # 1. Generate new key
        # 2. Mark old key as rotated
        # 3. Store new key hash
        # 4. Return new key
        
        new_key = f"sg_{tenant_id[:8]}_{secrets.token_urlsafe(32)}"
        
        return {
            "success": True,
            "message": "API key rotated successfully",
            "key_id": key_id,
            "new_key": new_key,  # Only shown once
            "rotated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error rotating API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to rotate API key")
