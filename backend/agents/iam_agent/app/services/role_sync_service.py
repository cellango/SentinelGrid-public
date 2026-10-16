"""Service for synchronizing Keycloak roles with entitlements."""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.entitlement import Entitlement
from app.models.role_entitlement_pattern import RoleEntitlementPattern
from app.services.keycloak_client import KeycloakRoleClient
from app.services.redis_cache import cache

logger = logging.getLogger(__name__)


class RoleSyncService:
    """Service for synchronizing roles with entitlements."""
    
    def __init__(self, db: Session):
        """Initialize role sync service."""
        self.db = db
        self.keycloak_client = KeycloakRoleClient()
    
    async def sync_user_roles_to_entitlements(
        self,
        user_id: str,
        tenant_id: UUID,
        granted_by: UUID
    ) -> Dict[str, Any]:
        """
        Synchronize a user's Keycloak roles to entitlements.
        
        For each role the user has, grant them the entitlements
        defined in the role_entitlement_patterns table.
        """
        result = {
            "user_id": user_id,
            "roles_processed": 0,
            "entitlements_created": 0,
            "entitlements_existing": 0,
            "errors": []
        }
        
        try:
            # Get user's roles from Keycloak
            role_names = await self.keycloak_client.get_user_role_names(user_id)
            if not role_names:
                logger.info(f"User {user_id} has no roles, skipping sync")
                return result
            
            # For each role, get entitlement patterns
            for role_name in role_names:
                try:
                    patterns = self.db.query(RoleEntitlementPattern).filter(
                        RoleEntitlementPattern.role_name == role_name,
                        RoleEntitlementPattern.tenant_id.in_([None, tenant_id]),  # Global or tenant-specific
                        RoleEntitlementPattern.auto_grant == True
                    ).all()
                    
                    result["roles_processed"] += 1
                    
                    # Create entitlements for each pattern
                    for pattern in patterns:
                        try:
                            # Parse entitlement pattern: resource_type:resource_id:action
                            parts = pattern.entitlement_pattern.split(":")
                            if len(parts) != 3:
                                logger.warning(f"Invalid entitlement pattern: {pattern.entitlement_pattern}")
                                continue
                            
                            resource_type, resource_id, action = parts
                            
                            # Check if entitlement already exists (active or revoked)
                            existing = self.db.query(Entitlement).filter(
                                Entitlement.tenant_id == tenant_id,
                                Entitlement.resource_type == resource_type,
                                Entitlement.resource_id == resource_id,
                                Entitlement.action == action,
                                Entitlement.granted_to_type == "user",
                                Entitlement.granted_to_id == UUID(user_id)
                            ).first()
                            
                            if existing:
                                result["entitlements_existing"] += 1
                                continue
                            
                            # Create new entitlement
                            entitlement = Entitlement(
                                tenant_id=tenant_id,
                                resource_type=resource_type,
                                resource_id=resource_id,
                                action=action,
                                granted_to_type="user",
                                granted_to_id=UUID(user_id),
                                granted_to_name=None,
                                status="active",
                                granted_by=granted_by,
                                metadata_json={"source": "role_sync", "role": role_name}
                            )
                            self.db.add(entitlement)
                            result["entitlements_created"] += 1
                            
                        except Exception as e:
                            error_msg = f"Error creating entitlement for pattern {pattern.entitlement_pattern}: {e}"
                            logger.error(error_msg)
                            result["errors"].append(error_msg)
                    
                except Exception as e:
                    error_msg = f"Error processing role {role_name}: {e}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)
            
            # Commit all changes
            self.db.commit()
            
            # Invalidate cache for this tenant
            cache.invalidate_tenant_entitlements(str(tenant_id))
            
            logger.info(
                f"Role sync completed for user {user_id}: "
                f"{result['entitlements_created']} created, "
                f"{result['entitlements_existing']} existing"
            )
            
        except Exception as e:
            self.db.rollback()
            error_msg = f"Role sync failed for user {user_id}: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
        
        return result
    
    async def sync_role_to_all_users(
        self,
        role_name: str,
        tenant_id: UUID,
        granted_by: UUID
    ) -> Dict[str, Any]:
        """
        Sync a role's entitlement patterns to all users who have that role.
        
        Useful when a role's entitlement patterns are updated.
        """
        result = {
            "role_name": role_name,
            "users_processed": 0,
            "entitlements_created": 0,
            "errors": []
        }
        
        try:
            # Get all users with this role from Keycloak
            users = await self.keycloak_client.get_users_with_role(role_name)
            
            for user in users:
                user_id = user.get("id")
                if not user_id:
                    continue
                
                # Get user's tenant_id (from user attributes)
                user_attrs = user.get("attributes", {})
                user_tenant_id = user_attrs.get("tenant_id", [None])[0] if user_attrs.get("tenant_id") else None
                
                # Use provided tenant_id or user's tenant_id
                effective_tenant_id = tenant_id if tenant_id else (UUID(user_tenant_id) if user_tenant_id else None)
                
                if not effective_tenant_id:
                    logger.warning(f"User {user_id} has no tenant_id, skipping")
                    continue
                
                # Sync entitlements for this user
                user_result = await self.sync_user_roles_to_entitlements(
                    user_id,
                    effective_tenant_id,
                    granted_by
                )
                
                result["users_processed"] += 1
                result["entitlements_created"] += user_result["entitlements_created"]
                result["errors"].extend(user_result["errors"])
            
        except Exception as e:
            error_msg = f"Failed to sync role {role_name} to all users: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
        
        return result
    
    async def revoke_user_entitlements_for_role(
        self,
        user_id: str,
        role_name: str,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """
        Revoke entitlements that were granted by a specific role.
        
        Called when a role is removed from a user.
        """
        result = {
            "user_id": user_id,
            "role_name": role_name,
            "entitlements_revoked": 0,
            "errors": []
        }
        
        try:
            # Get entitlement patterns for this role
            patterns = self.db.query(RoleEntitlementPattern).filter(
                RoleEntitlementPattern.role_name == role_name,
                RoleEntitlementPattern.tenant_id.in_([None, tenant_id]),
                RoleEntitlementPattern.auto_grant == True
            ).all()
            
            for pattern in patterns:
                try:
                    # Parse pattern
                    parts = pattern.entitlement_pattern.split(":")
                    if len(parts) != 3:
                        continue
                    
                    resource_type, resource_id, action = parts
                    
                    # Find and revoke entitlements
                    # Use JSONB query for metadata
                    from sqlalchemy import text
                    entitlements = self.db.query(Entitlement).filter(
                        Entitlement.tenant_id == tenant_id,
                        Entitlement.resource_type == resource_type,
                        Entitlement.resource_id == resource_id,
                        Entitlement.action == action,
                        Entitlement.granted_to_type == "user",
                        Entitlement.granted_to_id == UUID(user_id),
                        Entitlement.status == "active",
                        text("metadata_json->>'source' = 'role_sync'"),
                        text("metadata_json->>'role' = :role_name").bindparam(role_name=role_name)
                    ).all()
                    
                    for entitlement in entitlements:
                        entitlement.status = "revoked"
                        result["entitlements_revoked"] += 1
                    
                except Exception as e:
                    error_msg = f"Error revoking entitlement for pattern {pattern.entitlement_pattern}: {e}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)
            
            self.db.commit()
            cache.invalidate_tenant_entitlements(str(tenant_id))
            
        except Exception as e:
            self.db.rollback()
            error_msg = f"Failed to revoke entitlements for role {role_name}: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)
        
        return result

