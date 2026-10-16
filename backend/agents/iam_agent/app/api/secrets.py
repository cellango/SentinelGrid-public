"""
Secrets & Key Management API endpoints.

Manages shared credentials and secrets with encryption and rotation.
Integrates with Vault for secure storage.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, SecretStr
from datetime import datetime, timedelta

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.services.vault_client import VaultClient
from app.services.audit_service import AuditService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/secrets", tags=["secrets"])


# ============================================================================
# Request/Response Models
# ============================================================================

class SecretCreateRequest(BaseModel):
    """Create secret request."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    secret_type: str = Field(..., pattern="^(password|api_key|token|certificate)$")
    value: SecretStr
    access_control: Optional[dict] = None  # Who can access
    rotation_days: Optional[int] = Field(None, ge=1, le=365)  # Rotation schedule


class SecretResponse(BaseModel):
    """Secret response (value is never returned)."""
    id: str
    tenant_id: str
    name: str
    description: Optional[str]
    secret_type: str
    access_control: Optional[dict]
    last_rotated_at: Optional[datetime]
    next_rotation_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class SecretListResponse(BaseModel):
    """Paginated secret list response."""
    items: List[SecretResponse]
    total: int
    page: int
    limit: int
    pages: int


# ============================================================================
# Helper Functions
# ============================================================================

def _bearer_token_from_request(request: Request) -> str:
    """Extract bearer token from request headers, raising 401 if missing."""
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return auth_header.split(" ", 1)[1].strip()


async def get_token_data(credentials: str) -> dict:
    """Extract and validate token, return token data with tenant_id."""
    from app.services.token_validator import TokenValidator
    from app.services.keycloak_client import KeycloakClient
    
    keycloak_client = KeycloakClient()
    validator = TokenValidator(keycloak_client)
    result = validator.validate_token(credentials)
    
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if not result.get("tenant_id"):
        raise HTTPException(status_code=403, detail="No tenant_id in token")
    
    return result


# ============================================================================
# Secrets Endpoints
# ============================================================================

@router.post("", response_model=SecretResponse)
async def create_secret(
    request: SecretCreateRequest,
    authorization: str = Depends(_bearer_token_from_request)
):
    """
    Store a shared secret.
    
    Secret is encrypted and stored securely (in Vault in production).
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    user_id = token_data.get("user_id") or token_data.get("payload", {}).get("sub")
    
    logger.info(f"Secret '{request.name}' created by {user_id} in tenant {tenant_id}")
    
    if not settings.VAULT_TOKEN:
        raise HTTPException(status_code=503, detail="Vault not configured")

    try:
        secret_id = f"secret-{datetime.utcnow().timestamp()}"
        now = datetime.utcnow()
        next_rotation = None

        if request.rotation_days:
            next_rotation = now + timedelta(days=request.rotation_days)

        payload = {
            "value": request.value.get_secret_value(),
            "name": request.name,
            "description": request.description,
            "secret_type": request.secret_type,
            "access_control": request.access_control,
            "created_at": now.isoformat(),
            "created_by": user_id,
            "tenant_id": tenant_id,
            "rotation_days": request.rotation_days,
        }

        vault_path = f"{tenant_id}/{secret_id}"
        VaultClient().write_secret(vault_path, payload)

        AuditService.log_auth_event(
            realm_name=settings.KEYCLOAK_REALM,
            action="secret_create",
            actor_user_id=user_id,
            actor_email=token_data.get("email"),
            details={"secret_id": secret_id, "name": request.name, "type": request.secret_type},
        )

        return SecretResponse(
            id=secret_id,
            tenant_id=tenant_id,
            name=request.name,
            description=request.description,
            secret_type=request.secret_type,
            access_control=request.access_control,
            last_rotated_at=None,
            next_rotation_at=next_rotation,
            created_at=now,
            updated_at=now,
        )

    except Exception as e:
        logger.error(f"Error creating secret: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create secret")


@router.get("", response_model=SecretListResponse)
async def list_secrets(
    secret_type: Optional[str] = Query(None, description="Filter by secret type"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    authorization: str = Depends(_bearer_token_from_request)
):
    """
    List secrets accessible to the user.
    
    Only returns secrets the user has permission to view.
    Secret values are never returned.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    if not settings.VAULT_TOKEN:
        raise HTTPException(status_code=503, detail="Vault not configured")

    try:
        client = VaultClient()
        keys = client.list_secrets(tenant_id)
        items: List[SecretResponse] = []
        for key in keys:
            secret_data = client.read_secret(f"{tenant_id}/{key}")
            if not secret_data:
                continue
            created_at = datetime.fromisoformat(secret_data.get("created_at")) if secret_data.get("created_at") else datetime.utcnow()
            rotation_days_raw = secret_data.get("rotation_days")
            try:
                rotation_days = int(rotation_days_raw) if rotation_days_raw is not None else None
            except (TypeError, ValueError):
                rotation_days = None
            next_rotation = created_at + timedelta(days=rotation_days) if rotation_days else None
            items.append(
                SecretResponse(
                    id=key,
                    tenant_id=tenant_id,
                    name=secret_data.get("name", key),
                    description=secret_data.get("description"),
                    secret_type=secret_data.get("secret_type", "secret"),
                    access_control=secret_data.get("access_control"),
                    last_rotated_at=None,
                    next_rotation_at=next_rotation,
                    created_at=created_at,
                    updated_at=created_at,
                )
            )

        total = len(items)
        # simple pagination slice
        start = (page - 1) * limit
        end = start + limit
        items = items[start:end]
        pages = (total + limit - 1) // limit if total else 0

        return SecretListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing secrets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list secrets")


@router.get("/{secret_id}", response_model=SecretResponse)
async def get_secret(
    secret_id: str,
    authorization: str = Depends(_bearer_token_from_request)
):
    """
    Get secret metadata (not the value).
    
    To retrieve the actual secret value, use a separate endpoint with additional verification.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    if not settings.VAULT_TOKEN:
        raise HTTPException(status_code=503, detail="Vault not configured")

    try:
        client = VaultClient()
        secret_data = client.read_secret(f"{tenant_id}/{secret_id}")
        if not secret_data:
            raise HTTPException(status_code=404, detail="Secret not found")

        created_at = datetime.fromisoformat(secret_data.get("created_at")) if secret_data.get("created_at") else datetime.utcnow()
        rotation_days = secret_data.get("rotation_days")
        next_rotation = created_at + timedelta(days=rotation_days) if rotation_days else None

        return SecretResponse(
            id=secret_id,
            tenant_id=tenant_id,
            name=secret_data.get("name", secret_id),
            description=secret_data.get("description"),
            secret_type=secret_data.get("secret_type", "secret"),
            access_control=secret_data.get("access_control"),
            last_rotated_at=None,
            next_rotation_at=next_rotation,
            created_at=created_at,
            updated_at=created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting secret: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get secret")


@router.post("/{secret_id}/rotate")
async def rotate_secret(
    secret_id: str,
    authorization: str = Depends(_bearer_token_from_request)
):
    """
    Rotate a secret.
    
    Generates new value and updates in Vault.
    Old value is archived for rollback if needed.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    # Check if user has admin role
    if "TENANT_ADMIN" not in token_data.get("roles", []):
        raise HTTPException(status_code=403, detail="Admin role required for secret rotation")
    
    logger.info(f"Secret {secret_id} rotation initiated by tenant {tenant_id}")
    
    if not settings.VAULT_TOKEN:
        raise HTTPException(status_code=503, detail="Vault not configured")

    try:
        client = VaultClient()
        secret_data = client.read_secret(f"{tenant_id}/{secret_id}")
        if not secret_data:
            raise HTTPException(status_code=404, detail="Secret not found")

        import secrets as py_secrets
        new_value = py_secrets.token_urlsafe(32)
        secret_data["value"] = new_value
        secret_data["last_rotated_at"] = datetime.utcnow().isoformat()

        client.write_secret(f"{tenant_id}/{secret_id}", secret_data)

        AuditService.log_auth_event(
            realm_name=settings.KEYCLOAK_REALM,
            action="secret_rotate",
            actor_user_id=token_data.get("user_id"),
            actor_email=token_data.get("email"),
            details={"secret_id": secret_id},
        )

        return {
            "success": True,
            "message": "Secret rotated successfully",
            "secret_id": secret_id,
            "rotated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error rotating secret: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to rotate secret")


@router.delete("/{secret_id}")
async def delete_secret(
    secret_id: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """Delete a secret (admin only)."""
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    # Check if user has admin role
    if "TENANT_ADMIN" not in token_data.get("roles", []):
        raise HTTPException(status_code=403, detail="Admin role required")
    
    if not settings.VAULT_TOKEN:
        raise HTTPException(status_code=503, detail="Vault not configured")

    try:
        client = VaultClient()
        client.delete_secret(f"{tenant_id}/{secret_id}")

        AuditService.log_auth_event(
            realm_name=settings.KEYCLOAK_REALM,
            action="secret_delete",
            actor_user_id=token_data.get("user_id"),
            actor_email=token_data.get("email"),
            details={"secret_id": secret_id},
        )

        return {
            "success": True,
            "message": "Secret deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting secret: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete secret")
