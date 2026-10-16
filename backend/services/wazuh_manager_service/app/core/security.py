"""Security utilities for authentication and authorization."""

import logging
from uuid import UUID
from fastapi import Depends, HTTPException, status, Header
from typing import Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_current_tenant(authorization: Optional[str] = Header(None)) -> UUID:
    """
    Extract tenant_id from JWT token via IAM Agent.
    
    This function validates the token and extracts the tenant_id claim.
    All endpoints use this for multi-tenant isolation.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )
    
    # Extract token from "Bearer <token>" format
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    # Validate token with IAM Agent
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.IAM_AGENT_URL}/internal/iam/auth/validate-token",
                json={"token": token},
                timeout=5.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token"
                )
            
            result = response.json()
            
            if not result.get("valid"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=result.get("error", "Token validation failed")
                )
            
            tenant_id = result.get("tenant_id")
            if not tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tenant_id in token - user not associated with tenant"
                )
            
            return UUID(tenant_id)
            
    except httpx.RequestError as e:
        logger.error(f"Failed to validate token with IAM Agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="IAM Agent unavailable"
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant_id format"
        )

