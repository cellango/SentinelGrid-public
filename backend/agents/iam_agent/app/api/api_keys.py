"""
API Key Management API endpoints.

Historical API-key shapes; operations explicitly blocked until qualified.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from datetime import datetime

from app.api.request_context import RequestContext, get_current_request_context
from app.services.nhi_service import unavailable_api_keys

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

# ============================================================================
# API Key Endpoints
# ============================================================================

@router.post("", response_model=APIKeyCreateResponse)
async def create_api_key(
    request: APIKeyCreateRequest,
    request_context: RequestContext = Depends(get_current_request_context)
):
    """Unavailable until real persistence and authentication are qualified."""
    unavailable_api_keys()


@router.get("", response_model=List[APIKeyResponse])
async def list_api_keys(
    request_context: RequestContext = Depends(get_current_request_context)
):
    """Unavailable until real persistence and authentication are qualified."""
    unavailable_api_keys()


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
    request_context: RequestContext = Depends(get_current_request_context)
):
    """Unavailable until real persistence and authentication are qualified."""
    unavailable_api_keys()


@router.post("/{key_id}/rotate")
async def rotate_api_key(
    key_id: str,
    request_context: RequestContext = Depends(get_current_request_context)
):
    """Unavailable until real persistence and authentication are qualified."""
    unavailable_api_keys()
