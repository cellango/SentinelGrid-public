"""Authentication models."""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class TokenValidationRequest(BaseModel):
    """Request to validate a token."""
    token: str


class TokenValidationResponse(BaseModel):
    """Response from token validation."""
    valid: bool
    payload: Optional[Dict[str, Any]] = None
    tenant_id: Optional[str] = None
    plan_tier: Optional[str] = None
    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = []
    error: Optional[str] = None
    expires_at: Optional[datetime] = None


class TokenIntrospectionRequest(BaseModel):
    """Request to introspect a token."""
    token: str


class TokenIntrospectionResponse(BaseModel):
    """Response from token introspection."""
    active: bool
    sub: Optional[str] = None
    tenant_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    realm_access: Optional[Dict[str, Any]] = None
    roles: List[str] = []
    exp: Optional[int] = None
    iat: Optional[int] = None
    error: Optional[str] = None
