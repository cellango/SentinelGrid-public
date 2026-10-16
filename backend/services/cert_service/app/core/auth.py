"""Authentication and authorization for certificate service."""

import logging
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import os

from app.core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()

# IAM Agent URL for token validation
IAM_AGENT_URL = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify JWT token and extract tenant_id.
    
    Args:
        token: JWT token string
        
    Returns:
        Dict with tenant_id, user_id, and roles
        
    Raises:
        HTTPException: If token is invalid or missing tenant_id
    """
    try:
        logger.debug(f"Verifying token with IAM Agent at {IAM_AGENT_URL}")
        
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                f"{IAM_AGENT_URL}/internal/iam/auth/validate-token",
                json={"token": token}
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("valid"):
                error = result.get("error", "Token validation failed")
                logger.warning(f"Token validation failed: {error}")
                raise HTTPException(status_code=401, detail=f"Invalid token: {error}")
            
            payload = result.get("payload", {})
            tenant_id = result.get("tenant_id")
            
            if not tenant_id:
                logger.warning("Token missing tenant_id")
                raise HTTPException(
                    status_code=403,
                    detail="Token missing tenant_id - cannot access certificate service"
                )
            
            logger.debug(f"Token validated: tenant_id={tenant_id}, user_id={result.get('user_id')}")
            
            return {
                "tenant_id": tenant_id,
                "user_id": result.get("user_id"),
                "roles": result.get("roles", [])
            }
            
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to IAM Agent: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to IAM Agent: {str(e)}"
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid token")
        logger.error(f"IAM Agent error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=503,
            detail=f"IAM Agent error: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Token validation error: {str(e)}"
        )


def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> UUID:
    """
    FastAPI dependency to extract and validate tenant_id from JWT token.
    
    Usage:
        @router.get("/certificates")
        def list_certificates(tenant_id: UUID = Depends(get_current_tenant)):
            ...
    
    Returns:
        UUID: Tenant ID from token
        
    Raises:
        HTTPException: If token is invalid or missing tenant_id
    """
    token = credentials.credentials
    payload = verify_token(token)
    tenant_id_str = payload.get("tenant_id")
    
    if not tenant_id_str:
        raise HTTPException(
            status_code=403,
            detail="Missing tenant_id in token"
        )
    
    try:
        return UUID(tenant_id_str)
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid tenant_id format: {tenant_id_str}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tenant_id format: {str(e)}"
        )


def require_role(allowed_roles: list[str]):
    """
    Dependency factory to require specific roles.
    
    Usage:
        @router.post("/certificates")
        def create_certificate(
            tenant_id: UUID = Depends(get_current_tenant),
            _roles: dict = Depends(require_role(["TENANT_ADMIN", "SOC_MANAGER"]))
        ):
            ...
    
    Args:
        allowed_roles: List of role names that are allowed
        
    Returns:
        Dependency function that validates roles
    """
    def role_checker(
        credentials: HTTPAuthorizationCredentials = Security(security)
    ) -> Dict[str, Any]:
        token = credentials.credentials
        payload = verify_token(token)
        roles = payload.get("roles", [])
        
        if not any(role in roles for role in allowed_roles):
            logger.warning(f"Role check failed: user has {roles}, required {allowed_roles}")
            raise HTTPException(
                status_code=403,
                detail=f"Required role not found. Allowed: {allowed_roles}, User roles: {roles}"
            )
        
        return payload
    
    return role_checker


def get_current_user_info(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get full user info from token.
    
    Usage:
        @router.get("/certificates")
        def list_certificates(
            tenant_id: UUID = Depends(get_current_tenant),
            user_info: dict = Depends(get_current_user_info)
        ):
            user_id = user_info["user_id"]
            ...
    
    Returns:
        Dict with tenant_id, user_id, and roles
    """
    token = credentials.credentials
    return verify_token(token)

