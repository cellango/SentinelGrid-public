"""Authenticated request context helpers for tenant-scoped routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import get_token_validator
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.token_validator import TokenValidator


@dataclass(frozen=True)
class RequestContext:
    tenant_id: UUID
    user_id: str | None = None
    roles: tuple[str, ...] = ()


def _bearer_token_from_request(request: Request) -> str:
    authorization = request.headers.get("authorization") or request.headers.get("Authorization")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )
    return authorization.split(" ", 1)[1].strip()


def _tenant_id_from_internal_header(request: Request) -> UUID:
    tenant_header = request.headers.get("x-tenant-id") or request.headers.get("X-Tenant-ID")
    if not tenant_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID header is required for internal service requests",
        )
    try:
        return UUID(str(tenant_header))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-ID header format",
        ) from exc


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
    token = _bearer_token_from_request(request)
    if token == settings.INTERNAL_SERVICE_TOKEN:
        return RequestContext(
            tenant_id=_tenant_id_from_internal_header(request),
            roles=("INTERNAL_SERVICE",),
        )

    result = validator.validate_token(token)

    if not result.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.get("error") or "Invalid token",
        )

    tenant_id = result.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenant_id in token",
        )

    try:
        parsed_tenant_id = UUID(str(tenant_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant_id in token",
        ) from exc

    return RequestContext(
        tenant_id=parsed_tenant_id,
        user_id=result.get("user_id"),
        roles=tuple(str(role) for role in (result.get("roles") or []) if role),
    )


def get_current_tenant_id(
    request_context: RequestContext = Depends(get_current_request_context),
) -> UUID:
    """Expose the authenticated tenant ID as a standalone dependency."""
    return request_context.tenant_id


def get_tenant_session(
    request_context: RequestContext = Depends(get_current_request_context),
) -> Generator[Session, None, None]:
    """Yield a DB session with tenant-scoped RLS context from the validated token."""
    db = SessionLocal()
    try:
        db.execute(
            text("SET LOCAL app.current_tenant_id = :tenant_id"),
            {"tenant_id": str(request_context.tenant_id)},
        )
        db.execute(text("SET LOCAL app.is_superadmin = 'false'"))
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        try:
            db.execute(text("RESET app.current_tenant_id"))
            db.execute(text("RESET app.is_superadmin"))
        except Exception:
            pass
        db.close()


def get_superadmin_db(
    request_context: RequestContext = Depends(get_current_request_context),
) -> Generator[Session, None, None]:
    """Yield a DB session with explicit superadmin RLS bypass for platform-admin routes."""
    ensure_request_has_any_role(request_context, "PLATFORM_ADMIN")

    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_superadmin = 'true'"))
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        try:
            db.execute(text("RESET app.is_superadmin"))
            db.execute(text("RESET app.current_tenant_id"))
        except Exception:
            pass
        db.close()
