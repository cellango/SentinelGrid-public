"""
Realm Creation API - Centralized realm creation endpoint.

CRITICAL: This endpoint ensures all realms are created with:
1. User Profile configuration (tenant_id attribute) - REQUIRED for Keycloak v25+
2. Standard clients, roles, and protocol mappers
3. Naming convention enforcement

This is a foundational API - all realm creation MUST go through this endpoint.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, status
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError

from app.api.request_context import (
    RequestContext,
    ensure_request_has_any_role,
    get_current_request_context,
)
from app.models.realm import RealmCreateRequest, RealmCreateResponse, RealmType
from app.services.realm_creation_service import (
    RealmCreationService,
    RealmCreationError,
    RealmNamingError
)
from app.services.keycloak_admin_factory import build_keycloak_admin
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/realms", tags=["realms"])

# Global KeycloakAdmin instance (initialized on first use)
_keycloak_admin: KeycloakAdmin = None


def get_keycloak_admin() -> KeycloakAdmin:
    """
    Get or create KeycloakAdmin instance for realm creation.
    
    Uses configured Keycloak admin authentication for realm creation operations.
    """
    global _keycloak_admin
    
    if _keycloak_admin is None:
        try:
            _keycloak_admin = build_keycloak_admin(realm_name="master")
            logger.info("✅ Initialized KeycloakAdmin for realm creation API")
        except Exception as e:
            logger.error(f"Failed to initialize KeycloakAdmin: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Keycloak admin service unavailable"
            )
    
    return _keycloak_admin


def require_platform_admin_request_context(
    request_context: RequestContext = Depends(get_current_request_context),
) -> RequestContext:
    """Require a validated platform-admin identity for realm provisioning operations."""
    ensure_request_has_any_role(request_context, "PLATFORM_ADMIN")
    return request_context


@router.post("", response_model=RealmCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_realm(
    request: RealmCreateRequest,
    request_context: RequestContext = Depends(require_platform_admin_request_context),
) -> RealmCreateResponse:
    """
    Create a new Keycloak realm with all standard configuration.
    
    CRITICAL: This endpoint ensures:
    - User Profile is configured with tenant_id attribute (REQUIRED for Keycloak v25+)
    - Standard clients are created (web, api, iam-agent)
    - Standard roles are created (TENANT_ADMIN, SOC_MANAGER, SOC_ANALYST, VIEW_ONLY)
    - Protocol mappers are configured for tenant_id claim
    - Naming conventions are enforced
    
    **Naming Conventions:**
    - Platform admin: `sg-admin`
    - Multi-tenant: `sg-mt-{region}-{shard}` (e.g., `sg-mt-us-1`)
    - Dedicated customer: `{customer-slug}` (validated slug)
    - Demo: `demo`
    
    **Authorization:**
    - Requires platform admin privileges (PLATFORM_ADMIN role in sg-admin realm)
    
    **Returns:**
    - 201 Created: Realm created successfully
    - 200 OK: Realm already exists (idempotent)
    - 400 Bad Request: Invalid request (naming convention violation, missing required fields)
    - 409 Conflict: Realm name conflict (should not occur with proper validation)
    - 503 Service Unavailable: Keycloak admin service unavailable
    """
    try:
        _ = request_context
        # Get KeycloakAdmin instance
        keycloak_admin = get_keycloak_admin()
        
        # Create realm creation service
        service = RealmCreationService(keycloak_admin)
        
        # Create realm
        result = service.create_realm(
            realm_name=request.realm_name,
            realm_type=RealmType(request.realm_type),
            display_name=request.display_name,
            region=request.region,
            shard_number=request.shard_number,
            customer_slug=request.customer_slug
        )
        
        # Determine HTTP status code
        if result["status"] == "created":
            status_code = status.HTTP_201_CREATED
        else:
            status_code = status.HTTP_200_OK
        
        response = RealmCreateResponse(**result)
        
        # Log warning if User Profile configuration failed
        if not result["user_profile_configured"]:
            logger.error(
                f"⚠️  CRITICAL WARNING: User Profile configuration failed for realm '{request.realm_name}'. "
                "Custom attributes (tenant_id) will NOT persist without User Profile configuration."
            )
        
        return response
        
    except RealmNamingError as e:
        logger.warning(f"Realm naming error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid realm name: {str(e)}"
        )
    
    except RealmCreationError as e:
        logger.error(f"Realm creation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create realm: {str(e)}"
        )
    
    except KeycloakError as e:
        error_msg = str(e)
        if "already exists" in error_msg.lower() or "409" in error_msg:
            # Realm was created concurrently - return existing realm info
            try:
                keycloak_admin = get_keycloak_admin()
                realm_info = keycloak_admin.get_realm(request.realm_name)
                
                # Verify User Profile is configured
                import sys
                # Add /app/libs to path for sg_core imports (mounted at /app/libs in container)
                libs_path = "/app/libs"
                if libs_path not in sys.path:
                    sys.path.insert(0, libs_path)
                from sg_core.keycloak_user_profile import verify_user_profile_configured
                user_profile_configured = verify_user_profile_configured(
                    request.realm_name,
                    keycloak_url=settings.KEYCLOAK_URL
                )
                
                return RealmCreateResponse(
                    realm_name=request.realm_name,
                    keycloak_realm_id=realm_info.get("id", ""),
                    status="exists",
                    user_profile_configured=user_profile_configured
                )
            except Exception as e2:
                logger.error(f"Error handling concurrent realm creation: {e2}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Realm '{request.realm_name}' already exists, but could not verify configuration"
                )
        else:
            logger.error(f"Keycloak error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Keycloak error: {str(e)}"
            )
    
    except Exception as e:
        logger.error(f"Unexpected error creating realm: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/{realm_name}/status")
async def get_realm_status(
    realm_name: str,
    request_context: RequestContext = Depends(require_platform_admin_request_context),
) -> dict:
    """
    Get status of a realm, including User Profile configuration.
    
    Returns:
        {
            "realm_name": str,
            "exists": bool,
            "user_profile_configured": bool,
            "keycloak_realm_id": str | None
        }
    """
    try:
        _ = request_context
        keycloak_admin = get_keycloak_admin()
        
        # Check if realm exists
        try:
            realm_info = keycloak_admin.get_realm(realm_name)
            realm_exists = True
            keycloak_realm_id = realm_info.get("id", "")
        except KeycloakError as e:
            if "not found" in str(e).lower():
                realm_exists = False
                keycloak_realm_id = None
            else:
                raise
        
        # Verify User Profile configuration
        user_profile_configured = False
        if realm_exists:
            import sys
            # Add /app/libs to path for sg_core imports (mounted at /app/libs in container)
            libs_path = "/app/libs"
            if libs_path not in sys.path:
                sys.path.insert(0, libs_path)
            from sg_core.keycloak_user_profile import verify_user_profile_configured
            user_profile_configured = verify_user_profile_configured(
                realm_name,
                keycloak_url=settings.KEYCLOAK_URL
            )
        
        return {
            "realm_name": realm_name,
            "exists": realm_exists,
            "user_profile_configured": user_profile_configured,
            "keycloak_realm_id": keycloak_realm_id
        }
        
    except Exception as e:
        logger.error(f"Error getting realm status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
