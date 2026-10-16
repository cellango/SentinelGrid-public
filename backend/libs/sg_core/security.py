"""Security utilities: token parsing, tenant extraction, auth helpers, tenant isolation enforcement."""

from typing import Optional, Any
from fastapi import HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import httpx
import logging
from functools import lru_cache
from sg_core.service_metrics import get_service_metrics

# IAM Agent configuration
IAM_AGENT_URL = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")

security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


def verify_token(token: str) -> dict:
    """
    Verify JWT token using IAM Agent service.
    
    Returns validated token payload with tenant_id and roles.
    """
    if not token:
        get_service_metrics().increment_counter("auth_failures_total", reason="missing_token")
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        logger.debug(f"🔍 [verify_token] Calling IAM Agent to validate token...")
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                f"{IAM_AGENT_URL}/internal/iam/auth/validate-token",
                json={"token": token}
            )
            response.raise_for_status()
            result = response.json()
            
            logger.debug(f"🔍 [verify_token] IAM Agent response: valid={result.get('valid')}, tenant_id={result.get('tenant_id')}, user_id={result.get('user_id')}")
            
            if not result.get("valid"):
                error = result.get("error", "Token validation failed")
                logger.warning(f"🔍 [verify_token] Token validation failed: {error}")
                get_service_metrics().increment_counter("auth_failures_total", reason="invalid_token")
                get_service_metrics().increment_counter("token_validation_failures_total", reason="invalid_token")
                raise HTTPException(status_code=401, detail=f"Invalid token: {error}")
            
            # Return payload with tenant_id and roles
            payload = result.get("payload", {})
            payload["tenant_id"] = result.get("tenant_id")
            payload["roles"] = result.get("roles", [])
            payload["user_id"] = result.get("user_id")
            if result.get("plan_tier"):
                payload["plan_tier"] = result.get("plan_tier")
            
            logger.debug(f"🔍 [verify_token] Token validated successfully: tenant_id={payload.get('tenant_id')}, user_id={payload.get('user_id')}, roles={payload.get('roles')}")
            get_service_metrics().increment_counter("token_validation_success_total")
            return payload
            
    except httpx.RequestError as e:
        get_service_metrics().increment_counter("auth_failures_total", reason="iam_agent_unreachable")
        get_service_metrics().increment_counter("token_validation_failures_total", reason="iam_agent_unreachable")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to IAM Agent: {str(e)}"
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            get_service_metrics().increment_counter("auth_failures_total", reason="invalid_token")
            get_service_metrics().increment_counter("token_validation_failures_total", reason="invalid_token")
            raise HTTPException(status_code=401, detail="Invalid token")
        get_service_metrics().increment_counter("auth_failures_total", reason="iam_agent_error")
        get_service_metrics().increment_counter("token_validation_failures_total", reason="iam_agent_error")
        raise HTTPException(
            status_code=503,
            detail=f"IAM Agent error: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        get_service_metrics().increment_counter("auth_failures_total", reason="token_validation_error")
        get_service_metrics().increment_counter("token_validation_failures_total", reason="token_validation_error")
        raise HTTPException(
            status_code=500,
            detail=f"Token validation error: {str(e)}"
        )


def get_tenant_id_from_token(token: str) -> Optional[str]:
    """Extract tenant_id from JWT token using IAM Agent."""
    payload = verify_token(token)
    return payload.get("tenant_id")


def _get_token_from_request(credentials: HTTPAuthorizationCredentials, request: Request) -> Optional[str]:
    """Return bearer token from Authorization header or fallback to access_token cookie."""
    if credentials and credentials.credentials:
        return credentials.credentials
    # Fallback: read access_token cookie (e.g., when Authorization header isn't attached)
    try:
        token = request.cookies.get("access_token")
        return token
    except Exception:
        return None


def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Security(security),
    request: Request = None,
) -> str:
    """
    FastAPI dependency to extract tenant_id from request token.
    
    Validates token via IAM Agent and returns tenant_id.
    
    Usage:
        @app.get("/items")
        def read_items(tenant_id: str = Depends(get_current_tenant)):
            ...
    """
    token = _get_token_from_request(credentials, request) if request else (credentials.credentials if credentials else None)
    logger.info(f"[auth] token present={bool(token)} from_header={bool(credentials and credentials.credentials)} from_cookie={bool(request and request.cookies.get('access_token') if request else False)}")
    if not token:
        get_service_metrics().increment_counter("auth_failures_total", reason="missing_authorization_token")
        raise HTTPException(status_code=401, detail="Missing Authorization token")
    logger.debug(f"🔍 [get_current_tenant] Validating token to extract tenant_id...")
    tenant_id = get_tenant_id_from_token(token)
    logger.debug(f"🔍 [get_current_tenant] Extracted tenant_id: {tenant_id}")
    if not tenant_id:
        logger.warning(f"🔍 [get_current_tenant] No tenant_id in token - returning 403")
        get_service_metrics().increment_counter("auth_failures_total", reason="missing_tenant_id")
        raise HTTPException(
            status_code=403,
            detail="No tenant_id in token. User must be assigned to a tenant."
        )
    logger.info(f"🔍 [get_current_tenant] Successfully extracted tenant_id: {tenant_id}")
    get_service_metrics().increment_counter("auth_success_total")
    return tenant_id


def get_user_roles_from_token(token: str) -> list[str]:
    """Extract user roles from JWT token using IAM Agent."""
    payload = verify_token(token)
    return payload.get("roles", [])


def get_current_payload(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    FastAPI dependency to return the validated token payload (with tenant_id, roles, plan_tier, user_id).
    """
    token = credentials.credentials
    return verify_token(token)


# ============================================================================
# Tenant Isolation Enforcement - CRITICAL SECURITY FUNCTIONS
# ============================================================================

def enforce_tenant_isolation(
    token_tenant_id: str,
    resource_tenant_id: str,
    operation: str = "access",
    resource_type: Optional[str] = None
) -> None:
    """
    Enforce tenant isolation - CRITICAL SECURITY FUNCTION.
    
    This function MUST be called before any operation that accesses
    tenant-specific resources. It ensures that users can ONLY access
    resources within their own tenant.
    
    Args:
        token_tenant_id: tenant_id from the authenticated JWT token
        resource_tenant_id: tenant_id of the resource being accessed
        operation: Operation being performed (for logging)
        resource_type: Type of resource (for logging)
    
    Raises:
        HTTPException(403): If tenant_id mismatch detected
        
    Security Notes:
        - Error message intentionally vague to prevent information leakage
        - All violations logged at CRITICAL level for security monitoring
        - Even TENANT_ADMIN cannot cross tenant boundaries
    
    Example Usage:
        @app.get("/users/{user_id}")
        def get_user(user_id: str, tenant_id: str = Depends(get_current_tenant)):
            user = db.get_user(user_id)
            enforce_tenant_isolation(tenant_id, user.tenant_id, "read user")
            return user
    """
    if not token_tenant_id:
        logger.critical(
            f"SECURITY VIOLATION: No tenant_id in token for operation: {operation}"
        )
        raise HTTPException(
            status_code=403,
            detail="Access denied: Invalid token"
        )
    
    if not resource_tenant_id:
        logger.critical(
            f"SECURITY VIOLATION: Resource has no tenant_id. "
            f"Operation: {operation}, Resource type: {resource_type}"
        )
        raise HTTPException(
            status_code=403,
            detail="Access denied: Invalid resource"
        )
    
    if token_tenant_id != resource_tenant_id:
        logger.critical(
            f"TENANT ISOLATION VIOLATION BLOCKED: "
            f"User from tenant {token_tenant_id} "
            f"attempted to {operation} "
            f"{resource_type or 'resource'} in tenant {resource_tenant_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="Access denied"  # Intentionally vague
        )


def validate_tenant_match(
    token_tenant_id: str,
    request_tenant_id: str,
    operation: str = "operation"
) -> None:
    """
    Validate that tenant_id in request matches token tenant_id.
    
    Use this when the API accepts tenant_id as a parameter and you want
    to ensure it matches the authenticated user's tenant.
    
    Args:
        token_tenant_id: tenant_id from authenticated token
        request_tenant_id: tenant_id from API request
        operation: Operation description (for logging)
    
    Raises:
        HTTPException(403): If mismatch detected
    """
    if token_tenant_id != request_tenant_id:
        logger.warning(
            f"Tenant ID mismatch: Token has {token_tenant_id}, "
            f"request has {request_tenant_id} for {operation}"
        )
        raise HTTPException(
            status_code=403,
            detail="Access denied: Tenant mismatch"
        )


def ensure_tenant_id_in_query(
    query_params: dict,
    tenant_id: str
) -> dict:
    """
    Ensure tenant_id is in database query parameters.
    
    This is a safety measure to prevent accidental cross-tenant queries.
    Always include tenant_id in WHERE clauses for tenant-scoped tables.
    
    Args:
        query_params: Query parameters dict
        tenant_id: tenant_id to enforce
    
    Returns:
        Updated query params with tenant_id
        
    Example:
        params = {"status": "active"}
        params = ensure_tenant_id_in_query(params, token_tenant_id)
        # params = {"status": "active", "tenant_id": "uuid"}
    """
    if "tenant_id" in query_params and query_params["tenant_id"] != tenant_id:
        logger.warning(
            f"Query attempted to access different tenant: "
            f"Expected {tenant_id}, got {query_params['tenant_id']}"
        )
        # Override with correct tenant_id
    
    query_params["tenant_id"] = tenant_id
    return query_params


def filter_by_tenant(
    items: list[dict],
    tenant_id: str,
    tenant_field: str = "tenant_id"
) -> list[dict]:
    """
    Filter a list of items to only include those belonging to the tenant.
    
    Use this as a safety check after database queries to ensure no
    cross-tenant data leaks through.
    
    Args:
        items: List of dictionaries (database results)
        tenant_id: tenant_id to filter by
        tenant_field: Name of the tenant_id field (default: "tenant_id")
    
    Returns:
        Filtered list containing only tenant's items
        
    Example:
        users = db.query(User).all()
        users = filter_by_tenant(users, token_tenant_id)
    """
    filtered = []
    leaked_count = 0
    
    for item in items:
        item_tenant = item.get(tenant_field)
        
        # Handle Keycloak attributes format (list)
        if isinstance(item_tenant, list):
            item_tenant = item_tenant[0] if item_tenant else None
        
        if item_tenant == tenant_id:
            filtered.append(item)
        else:
            # Data leak detected!
            leaked_count += 1
            logger.error(
                f"DATA LEAK DETECTED: Item with tenant_id {item_tenant} "
                f"in results for tenant {tenant_id}. Filtering out."
            )
    
    if leaked_count > 0:
        logger.critical(
            f"SECURITY WARNING: {leaked_count} cross-tenant items "
            f"detected and filtered. Review query logic!"
        )
    
    return filtered


def get_tenant_from_token_data(token_data: dict) -> str:
    """
    Extract tenant_id from validated token data.
    
    Args:
        token_data: Token payload from verify_token()
    
    Returns:
        tenant_id string
    
    Raises:
        HTTPException(403): If no tenant_id in token
    """
    tenant_id = token_data.get("tenant_id")
    
    if not tenant_id:
        logger.error("Token has no tenant_id. User not properly provisioned.")
        raise HTTPException(
            status_code=403,
            detail="Access denied: User not assigned to tenant"
        )
    
    return tenant_id
