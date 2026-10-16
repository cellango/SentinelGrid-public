"""Security utilities for Connector Service."""

from typing import Optional
from fastapi import HTTPException, Security, Request, Depends, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import httpx
from app.core.config import settings

# IAM Agent configuration
IAM_AGENT_URL = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")

security = HTTPBearer(auto_error=False)


async def verify_token_with_iam_agent(token: str) -> dict:
    """
    Verify JWT token using IAM Agent service.
    Returns validated token payload with tenant_id and roles.
    """
    if settings.DEBUG_MODE and token == "dev-token":
        return {
            "valid": True,
            "payload": {"sub": "dev-user", "tenant_id": "dev-tenant", "roles": ["admin"]},
            "tenant_id": "dev-tenant",
            "roles": ["admin"],
            "user_id": "dev-user"
        }
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{IAM_AGENT_URL}/internal/iam/auth/validate-token",
                json={"token": token}
            )
            response.raise_for_status()
            result = response.json()

            if not result.get("valid"):
                error = result.get("error", "Token validation failed")
                raise HTTPException(status_code=401, detail=f"Invalid token: {error}")

            payload = result.get("payload", {})
            payload["tenant_id"] = result.get("tenant_id")
            payload["roles"] = result.get("roles", [])
            payload["user_id"] = result.get("user_id")

            return payload

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to IAM Agent: {str(e)}"
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid token")
        raise HTTPException(
            status_code=503,
            detail=f"IAM Agent error: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Token validation error: {str(e)}"
        )


async def get_current_tenant(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> str:
    """
    FastAPI dependency to extract tenant_id from request.
    """
    # 1. Check for X-Tenant-ID header (for internal service communication)
    if x_tenant_id:
        request.state.tenant_id = x_tenant_id
        return x_tenant_id

    # 2. Validate JWT token via IAM Agent
    if credentials:
        token = credentials.credentials
        payload = await verify_token_with_iam_agent(token)
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(
                status_code=403,
                detail="No tenant_id in token. User must be assigned to a tenant."
            )
        request.state.tenant_id = tenant_id
        return tenant_id
    
    # 3. Fallback for development/testing
    if settings.DEBUG_MODE:
        dev_tenant_id = os.getenv("DEV_TENANT_ID", "9c7df7a9-5a0b-4412-a41c-0c0ea777b2f0")
        request.state.tenant_id = dev_tenant_id
        return dev_tenant_id

    raise HTTPException(
        status_code=401,
        detail="Not authenticated: Missing X-Tenant-ID header or valid JWT token"
    )
