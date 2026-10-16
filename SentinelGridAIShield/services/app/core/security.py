import hashlib
import secrets
from uuid import UUID

from fastapi import Header, HTTPException, status

from app.core.config import settings

def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()

def generate_api_key() -> str:
    """Generate a new API key"""
    return f"sg-ai-{secrets.token_urlsafe(32)}"

def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash"""
    return hash_api_key(plain_key) == hashed_key


def _extract_internal_token(
    x_internal_service_token: str | None,
    authorization: str | None,
) -> str | None:
    legacy_token = x_internal_service_token.strip() if x_internal_service_token else None
    bearer_token = None
    if authorization:
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid authorization header format",
            )
        bearer_token = authorization.split(" ", 1)[1].strip() or None

    provided_tokens = [token for token in (legacy_token, bearer_token) if token]
    if len(set(provided_tokens)) > 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="conflicting internal service authentication headers",
        )
    return provided_tokens[0] if provided_tokens else None


def require_internal_service_token(
    x_internal_service_token: str | None = Header(default=None, alias="X-Internal-Service-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> str:
    token = _extract_internal_token(x_internal_service_token, authorization)
    if token != settings.INTERNAL_SERVICE_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid internal service token",
        )
    return token


def get_internal_org_id(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> UUID:
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required",
        )
    try:
        return UUID(str(x_tenant_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-ID header format",
        ) from exc


def enforce_org_scope(current_org_id: UUID, requested_org_id: UUID | str) -> UUID:
    try:
        requested_uuid = requested_org_id if isinstance(requested_org_id, UUID) else UUID(str(requested_org_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid org_id format",
        ) from exc

    if requested_uuid != current_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied",
        )
    return requested_uuid


def ensure_record_org_access(current_org_id: UUID, record_org_id: UUID | str) -> None:
    enforce_org_scope(current_org_id, record_org_id)
