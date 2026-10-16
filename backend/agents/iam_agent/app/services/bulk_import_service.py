"""
Bulk Import Service for user onboarding.

Handles CSV-based bulk user imports.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class BulkImportService:
    """Service for bulk importing users from CSV."""
    
    def __init__(self):
        self.keycloak_admin = KeycloakAdminClient()
    
    def _ensure_user_profile_configured(self, realm: str) -> None:
        """
        Fail-safe: Ensure User Profile is configured for the realm.
        
        If User Profile is not configured, attempts to configure it automatically.
        This ensures tenant_id attributes will persist even if realm was created
        outside of the centralized realm creation service.
        """
        try:
            import sys
            # Add /app/libs to path for sg_core imports (mounted at /app/libs in container)
            libs_path = "/app/libs"
            if libs_path not in sys.path:
                sys.path.insert(0, libs_path)
            from sg_core.keycloak_user_profile import verify_user_profile_configured, configure_realm_user_profile
            
            # Check if User Profile is configured
            is_configured = verify_user_profile_configured(realm)
            
            if not is_configured:
                logger.warning(
                    f"⚠️  User Profile not configured for realm '{realm}'. "
                    "Attempting to configure automatically (fail-safe)..."
                )
                
                # Attempt to configure User Profile
                success = configure_realm_user_profile(realm)
                
                if success:
                    logger.info(f"✅ User Profile configured for realm '{realm}' (fail-safe)")
                else:
                    logger.error(
                        f"❌ CRITICAL: Failed to configure User Profile for realm '{realm}'. "
                        "Custom attributes (tenant_id) will NOT persist!"
                    )
        except Exception as e:
            logger.warning(f"Error checking/configuring User Profile (fail-safe): {e}")
    
    async def import_users(
        self,
        tenant_id: str,
        realm: str,
        csv_rows: List[Dict[str, str]]
    ) -> Dict:
        """
        Import users from CSV rows.
        
        Expected CSV columns:
        - email (required)
        - firstName (optional)
        - lastName (optional)
        - role (optional)
        - enabled (optional, default: false)
        
        Returns summary of import results.
        
        CRITICAL: Verifies User Profile is configured before creating users.
        If not configured, attempts to configure it automatically (fail-safe).
        """
        # Fail-safe: Verify User Profile is configured
        self._ensure_user_profile_configured(realm)
        
        results = {
            "total_rows": len(csv_rows),
            "successful": 0,
            "failed": 0,
            "errors": [],
            "created_users": []
        }
        
        try:
            async with self.keycloak_admin as kc:
                for idx, row in enumerate(csv_rows, start=1):
                    try:
                        # Validate required fields
                        email = row.get("email", "").strip()
                        if not email:
                            results["errors"].append({
                                "row": idx,
                                "email": email or "N/A",
                                "error": "Email is required"
                            })
                            results["failed"] += 1
                            continue
                        
                        # Check if user already exists
                        existing = await kc._make_request(
                            "GET",
                            f"/realms/{realm}/users",
                            params={"email": email, "exact": "true"}
                        )
                        existing.raise_for_status()
                        existing_users = existing.json()
                        
                        if existing_users:
                            results["errors"].append({
                                "row": idx,
                                "email": email,
                                "error": "User already exists"
                            })
                            results["failed"] += 1
                            continue
                        
                        # Prepare user data
                        user_data = {
                            "username": email,
                            "email": email,
                            "firstName": row.get("firstName", "").strip() or "",
                            "lastName": row.get("lastName", "").strip() or "",
                            "enabled": row.get("enabled", "false").lower() == "true",
                            "emailVerified": False,
                            "attributes": {
                                "tenant_id": [tenant_id]
                            }
                        }
                        
                        # Create user
                        response = await kc._make_request(
                            "POST",
                            f"/realms/{realm}/users",
                            json_data=user_data
                        )
                        response.raise_for_status()
                        
                        user_id = response.headers.get("Location", "").split("/")[-1]
                        
                        # Assign role if specified
                        role = row.get("role", "").strip()
                        if role:
                            try:
                                realm_roles = await kc._make_request(
                                    "GET",
                                    f"/realms/{realm}/roles"
                                )
                                realm_roles.raise_for_status()
                                roles = realm_roles.json()
                                
                                role_obj = next((r for r in roles if r["name"] == role), None)
                                if role_obj:
                                    await kc._make_request(
                                        "POST",
                                        f"/realms/{realm}/users/{user_id}/role-mappings/realm",
                                        json_data=[role_obj]
                                    )
                            except Exception as e:
                                logger.warning(f"Failed to assign role {role} to {email}: {e}")
                        
                        results["successful"] += 1
                        results["created_users"].append({"email": email, "user_id": user_id})
                        logger.info(f"Successfully imported user {email}")
                        
                    except Exception as e:
                        error_msg = str(e)
                        results["errors"].append({
                            "row": idx,
                            "email": row.get("email", "N/A"),
                            "error": error_msg
                        })
                        results["failed"] += 1
                        logger.error(f"Error importing row {idx}: {e}")
                
                return results
                
        except Exception as e:
            logger.error(f"Error in bulk import: {e}", exc_info=True)
            raise
