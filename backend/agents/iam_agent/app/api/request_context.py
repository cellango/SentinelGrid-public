"""Authenticated request context helpers for tenant-scoped routes."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.auth import get_token_validator
from app.core.config import settings
from app.core.database import SessionLocal, IAMSessionLocal, IAMDatabaseNotConfigured
from sg_core.tenant_session import tenant_session
from sg_core.request_credentials import request_bearer_token
from sg_core.iam_verification import checked_validation_result
from sg_core.user_principals import require_user_binding
from app.services.token_validator import TokenValidator


@dataclass(frozen=True)
class RequestContext:
    tenant_id: UUID
    user_id: str | None = None
    roles: tuple[str, ...] = ()
    client_ip: str | None = None
    realm_name: str | None = None
    email: str | None = None
    username: str | None = None


@dataclass(frozen=True)
class _RequestContextCache:
    fingerprint: str
    context: RequestContext


_CONTEXT_CACHE = object()
_BEARER_DOCUMENTATION = HTTPBearer(auto_error=False)


def _require_context_hints(request: Request, context: RequestContext) -> None:
    for name, expected in {"x-tenant-id": str(context.tenant_id), "x-realm": context.realm_name}.items():
        supplied = request.headers.getlist(name)
        if len(supplied) > 1 or supplied and supplied[0] != expected:
            raise HTTPException(403, "Conflicting identity context")
    if any(name in request.headers for name in ("x-user-id", "x-roles", "x-internal-token", "x-internal-service-token")):
        raise HTTPException(403, "Conflicting identity context")


def ensure_request_tenant_matches(authenticated_tenant_id: UUID, requested_tenant_id: UUID | None) -> None:
    if requested_tenant_id is None:
        return
    if authenticated_tenant_id != requested_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Tenant mismatch",
        )


def ensure_request_has_any_role(request_context: RequestContext, *required_roles: str) -> None:
    normalized_roles = {role.upper() for role in request_context.roles}
    normalized_required = {role.upper() for role in required_roles}
    if normalized_roles.intersection(normalized_required):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: Missing required role",
    )


async def get_current_request_context(
    request: Request,
    validator: TokenValidator = Depends(get_token_validator),
) -> RequestContext:
    # Direct IAM remains bearer-only. Browser cookie/marker compatibility belongs
    # to the gateway; a cookie alone must not expand direct mutation authority.
    token = request_bearer_token(request)
    fingerprint = hashlib.sha256(token.encode("ascii")).hexdigest()
    cached = request.scope.get(_CONTEXT_CACHE)
    if cached is not None:
        if not isinstance(cached, _RequestContextCache) or cached.fingerprint != fingerprint:
            raise HTTPException(401, "Conflicting authentication credentials")
        _require_context_hints(request, cached.context)
        return cached.context
    try:
        result = validator.validate_token(token)
    except Exception:
        raise HTTPException(503, "Token verification unavailable") from None
    payload = checked_validation_result(token, result, audience=settings.KEYCLOAK_CLIENT_ID)
    # The same provider/client/tenant contract as the user gateway, without an IAM
    # HTTP round trip or a second JWT verification engine. Empty policy is closed.
    config = getattr(request.app.state, "user_principal_settings", None)
    binding = require_user_binding(payload, config=config)
    context = RequestContext(
        tenant_id=UUID(payload["tenant_id"]), user_id=payload["sub"],
        client_ip=request.client.host if request.client else None,
        roles=tuple(payload["roles"]), realm_name=binding.issuer.rsplit("/realms/", 1)[1],
        email=payload.get("email") if isinstance(payload.get("email"), str) else None,
        username=(payload.get("preferred_username") or payload.get("username"))
        if isinstance(payload.get("preferred_username") or payload.get("username"), str) else None,
    )
    _require_context_hints(request, context)
    request.scope[_CONTEXT_CACHE] = _RequestContextCache(fingerprint, context)
    return context


def get_current_user_info(
    context: RequestContext = Depends(get_current_request_context),
    credentials: HTTPAuthorizationCredentials | None = Security(_BEARER_DOCUMENTATION),
) -> dict:
    """Same verified SQL identity; retain the existing OpenAPI bearer declaration.

    The optional framework credential supplies documentation, never authority. Raw
    request credentials were already checked by get_current_request_context.
    """
    return {"roles": list(context.roles), "user_id": context.user_id,
            "tenant_id": str(context.tenant_id), "realm_name": context.realm_name,
            "email": context.email, "username": context.username}


def get_current_tenant_id(
    request_context: RequestContext = Depends(get_current_request_context),
) -> UUID:
    """Expose the authenticated tenant ID as a standalone dependency."""
    return request_context.tenant_id


def get_tenant_session(
    request_context: RequestContext = Depends(get_current_request_context),
) -> Generator[Session, None, None]:
    """Shared catalog/policy database, bound before every transaction."""
    with tenant_session(SessionLocal, request_context.tenant_id) as db:
        yield db


def get_entitlement_session(
    request_context: RequestContext = Depends(get_current_request_context),
) -> Generator[Session, None, None]:
    """Separate IAM grant/audit database. Missing configuration fails closed."""
    try:
        with tenant_session(IAMSessionLocal, request_context.tenant_id) as db:
            yield db
    except IAMDatabaseNotConfigured as exc:
        raise HTTPException(status_code=503, detail="Access-grant database is not configured") from exc


def get_superadmin_db(
    request_context: RequestContext = Depends(get_current_request_context),
) -> Generator[Session, None, None]:
    """Compatibility name: platform administration remains tenant scoped.

    Cross-tenant maintenance needs a separately provisioned operational identity;
    an application-controlled GUC cannot establish it.
    """
    ensure_request_has_any_role(request_context, "PLATFORM_ADMIN")
    yield from get_tenant_session(request_context)
