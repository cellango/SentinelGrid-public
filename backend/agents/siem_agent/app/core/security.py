"""Security utilities for SIEM Agent."""

from typing import Optional
from uuid import UUID
from fastapi import HTTPException, Security, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import httpx
from app.core.config import settings
from sg_core.request_tracing import build_trace_headers

# IAM Agent configuration
IAM_AGENT_URL = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")

security = HTTPBearer(auto_error=False)


async def verify_token_with_iam_agent(token: str) -> dict:
    """
    Verify JWT token using IAM Agent service.
    Returns validated token payload with tenant_id and roles.
    """
    if settings.DEBUG_MODE and token == "dev-token":
        # Allow a simple dev token in debug mode
        return {
            "valid": True,
            "payload": {"sub": "dev-user", "tenant_id": "dev-tenant", "roles": ["admin"]},
            "tenant_id": "dev-tenant",
            "roles": ["admin"],
            "user_id": "dev-user"
        }
    
    try:
        async with httpx.AsyncClient(timeout=5.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
            response = await client.post(
                f"{IAM_AGENT_URL}/internal/iam/auth/validate-token",
                json={"token": token},
                headers=build_trace_headers(),
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
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> str:
    """
    FastAPI dependency to extract tenant_id from request.
    Prioritizes X-Tenant-ID header for internal service calls,
    then falls back to JWT token validation via IAM Agent.
    """
    # 1. Check for X-Tenant-ID header (for internal service communication)
    x_tenant_id = request.headers.get("X-Tenant-ID")
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
    
    # 3. Fallback for development/testing if no token or header
    if settings.DEBUG_MODE:
        dev_tenant_id = os.getenv("DEV_TENANT_ID", "9c7df7a9-5a0b-4412-a41c-0c0ea777b2f0")
        request.state.tenant_id = dev_tenant_id
        return dev_tenant_id

    raise HTTPException(
        status_code=401,
        detail="Not authenticated: Missing X-Tenant-ID header or valid JWT token"
    )


def get_current_tenant_from_context(request: Request) -> str:
    """
    Retrieves the tenant_id from the request state, assuming it was set by get_current_tenant.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=500,
            detail="Tenant ID not found in request state. Ensure get_current_tenant is used upstream."
        )
    return tenant_id
