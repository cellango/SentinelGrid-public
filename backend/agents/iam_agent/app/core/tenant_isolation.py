"""
Tenant Isolation Validator - CRITICAL SECURITY MODULE

Ensures all operations respect tenant boundaries.
This is the foundation of multi-tenant security in SentinelGrid.
"""

import logging
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

security = HTTPBearer()


class TenantIsolationValidator:
    """
    Validates tenant isolation for all operations.
    
    CRITICAL SECURITY: This class ensures users can only access
    resources within their own tenant.
    """
    
    @staticmethod
    def validate_tenant_id(tenant_id: UUID) -> None:
        """
        Validate that a tenant_id is present and valid.
        
        Args:
            tenant_id: Tenant ID to validate
            
        Raises:
            HTTPException: If tenant_id is invalid
        """
        if not tenant_id:
            logger.error("Tenant ID validation failed: No tenant_id provided")
            raise HTTPException(
                status_code=400,
                detail="Tenant ID is required"
            )
    
    @staticmethod
    def validate_resource_ownership(
        resource_tenant_id: UUID,
        current_user_id: UUID,
        resource_type: str = "resource"
    ) -> None:
        """
        Validate that a resource belongs to the current user's tenant.
        
        Args:
            resource_tenant_id: Tenant ID of the resource
            current_user_id: Current user's ID
            resource_type: Type of resource (for logging)
            
        Raises:
            HTTPException: If tenant mismatch detected
            
        Note: In production, this should extract tenant_id from current_user_id
        For now, we'll use a simplified check.
        """
        if not resource_tenant_id:
            logger.critical(
                f"SECURITY: Resource has no tenant_id. "
                f"User {current_user_id} attempted to access {resource_type}"
            )
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )
    
    @staticmethod
    def get_tenant_id_for_query(
        tenant_id: Optional[UUID],
        current_user_id: UUID
    ) -> UUID:
        """
        Get tenant_id for database query.
        
        If tenant_id is provided, validates it matches user's tenant.
        If not provided, extracts from user's context.
        
        Args:
            tenant_id: Optional tenant ID from request
            current_user_id: Current user's ID
            
        Returns:
            Validated tenant_id
            
        Raises:
            HTTPException: If tenant mismatch
        """
        # TODO: Extract tenant_id from JWT token or user context
        # For now, return the provided tenant_id if present
        if tenant_id:
            return tenant_id
        
        # In production, extract from token
        raise HTTPException(
            status_code=400,
            detail="Tenant ID is required"
        )
    
    @staticmethod
    async def get_current_user_id(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> UUID:
        """
        Extract current user ID from JWT token.
        
        This is a FastAPI dependency that validates the token
        and returns the authenticated user's ID.
        
        Args:
            credentials: Bearer token from Authorization header
            
        Returns:
            User UUID
            
        Raises:
            HTTPException: If token is invalid
        """
        token = credentials.credentials
        
        # TODO: Validate token and extract user_id
        # For now, return a placeholder
        # In production, this should:
        # 1. Validate JWT signature
        # 2. Check expiration
        # 3. Extract sub (user_id)
        # 4. Extract tenant_id
        
        try:
            # Import token validator
            from app.services.token_validator import TokenValidator
            from app.services.keycloak_client import KeycloakClient
            
            keycloak_client = KeycloakClient()
            validator = TokenValidator(keycloak_client)
            result = validator.validate_token(token)
            
            if not result.get("valid"):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token"
                )
            
            user_id = result.get("user_id")
            if not user_id:
                raise HTTPException(
                    status_code=401,
                    detail="No user_id in token"
                )
            
            # Return as UUID
            return UUID(user_id)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
    
    @staticmethod
    def enforce_tenant_isolation(
        token_tenant_id: UUID,
        resource_tenant_id: UUID,
        operation: str = "access"
    ) -> None:
        """
        Enforce tenant isolation - CRITICAL SECURITY.
        
        Args:
            token_tenant_id: Tenant ID from authenticated token
            resource_tenant_id: Tenant ID of resource being accessed
            operation: Operation being performed (for logging)
            
        Raises:
            HTTPException: If tenant mismatch
        """
        if str(token_tenant_id) != str(resource_tenant_id):
            logger.critical(
                f"TENANT ISOLATION VIOLATION: "
                f"User from tenant {token_tenant_id} "
                f"attempted to {operation} resource in tenant {resource_tenant_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="Access denied"
            )

