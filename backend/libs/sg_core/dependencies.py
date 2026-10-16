"""
Common FastAPI dependencies for SentinelGrid services.
"""

from uuid import UUID
from fastapi import Header, HTTPException, status


async def get_current_tenant(
    x_tenant_id: str = Header(..., description="Tenant UUID")
) -> UUID:
    """
    Extract and validate tenant ID from request headers.
    
    Headers:
        X-Tenant-ID: Tenant UUID
    
    Returns:
        UUID: Validated tenant ID
        
    Raises:
        HTTPException: If tenant_id is missing or invalid
    """
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required"
        )
    
    try:
        return UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant_id format (must be UUID)"
        )

