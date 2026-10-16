"""Internal statistics API endpoints for IAM Agent."""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.config import settings
from app.services.keycloak_client import KeycloakClient
from sg_core.service_security import verify_internal_service_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/iam/stats", tags=["stats"])


def get_keycloak_client() -> KeycloakClient:
    """Dependency to get Keycloak client."""
    return KeycloakClient()


def verify_internal_token(
    authorization: Optional[str] = Header(None),
    x_internal_service_token: Optional[str] = Header(None, alias="X-Internal-Service-Token"),
) -> bool:
    """Verify the internal service token for service-to-service stats access."""
    verify_internal_service_token(
        settings.INTERNAL_SERVICE_TOKEN,
        authorization=authorization,
        x_internal_service_token=x_internal_service_token,
        missing_detail="Missing authorization header",
        invalid_detail="Invalid internal service token",
    )
    return True


def extract_tenant_id_from_user(user: dict) -> Optional[str]:
    """Extract tenant_id from Keycloak user attributes."""
    attributes = user.get("attributes", {})
    tenant_id = attributes.get("tenant_id")
    return tenant_id[0] if isinstance(tenant_id, list) and tenant_id else tenant_id


@router.get("/{tenant_id}")
async def get_identity_stats(
    tenant_id: str,
    keycloak_client: KeycloakClient = Depends(get_keycloak_client),
    _verified: bool = Depends(verify_internal_token),
) -> Dict[str, Any]:
    """
    Get identity statistics for a tenant over the internal orchestrator boundary.

    Counts are scoped to users that carry the requested tenant_id in Keycloak attributes.
    Role and group counts are derived from memberships on those tenant-owned users.
    """
    try:
        if not keycloak_client.admin:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Keycloak admin client not available",
            )

        all_users = keycloak_client.admin.get_users()
        tenant_users = [user for user in all_users if extract_tenant_id_from_user(user) == tenant_id]
        active_users_count = len([user for user in tenant_users if user.get("enabled", True)])

        role_names: set[str] = set()
        group_ids: set[str] = set()
        for user in tenant_users:
            user_id = user.get("id")
            if not user_id:
                continue

            try:
                user_roles = keycloak_client.admin.get_realm_roles_of_user(user_id) or []
            except Exception as exc:
                logger.warning("Failed to load roles for user %s: %s", user_id, exc)
                user_roles = []
            for role in user_roles:
                role_name = role.get("name")
                if role_name:
                    role_names.add(role_name)

            try:
                user_groups = keycloak_client.admin.get_user_groups(user_id) or []
            except Exception as exc:
                logger.warning("Failed to load groups for user %s: %s", user_id, exc)
                user_groups = []
            for group in user_groups:
                group_id = group.get("id") or group.get("path") or group.get("name")
                if group_id:
                    group_ids.add(group_id)

        return {
            "users_count": len(tenant_users),
            "active_users_count": active_users_count,
            "roles_count": len(role_names),
            "groups_count": len(group_ids),
            "last_sync_at": None,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error getting identity stats: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get identity stats: {str(exc)}",
        )
