"""Security utilities for authentication and authorization."""

from typing import Optional
from uuid import UUID
from fastapi import Header, HTTPException, status

from app.core.config import settings
from sg_core.service_security import verify_internal_service_token


async def verify_internal_token(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_internal_service_token: Optional[str] = Header(None, alias="X-Internal-Service-Token"),
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token"),
) -> bool:
    """Verify internal service token."""
    verify_internal_service_token(
        settings.INTERNAL_SERVICE_TOKEN,
        authorization=authorization,
        x_internal_service_token=x_internal_service_token,
        x_internal_token=x_internal_token,
        missing_detail="Invalid or missing internal service token",
        invalid_detail="Invalid or missing internal service token",
    )
    return True


async def get_tenant_id(
    x_tenant_id: Optional[str] = Header(None)
) -> UUID:
    """Extract tenant ID from header."""
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing tenant ID header"
        )
    
    try:
        return UUID(x_tenant_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant ID format"
        )
