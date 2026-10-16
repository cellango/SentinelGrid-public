"""Security utilities for SOAR Agent."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import Header, HTTPException, Request, status

from app.core.config import settings
from sg_core.security import verify_token as verify_token_with_iam

logger = logging.getLogger(__name__)


def _parse_tenant_header(x_tenant_id: Optional[str]) -> UUID | None:
    if x_tenant_id is None:
        return None

    try:
        return UUID(str(x_tenant_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-ID header format",
        ) from exc


def _extract_bearer_token(authorization: Optional[str]) -> str | None:
    if authorization is None:
        return None

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    return token


def _is_dev_or_test_environment() -> bool:
    return settings.ENVIRONMENT in {"development", "test"}


def get_current_tenant(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> UUID:
    """
    Resolve tenant context from either:
    1. a validated end-user bearer token, or
    2. the internal service token plus an explicit X-Tenant-ID header.

    Header-only tenant assertion remains available only in development/test to
    avoid blocking direct-service local workflows and existing unit tests.
    """
    resolved_authorization = (
        authorization if isinstance(authorization, str) else request.headers.get("authorization")
    )
    resolved_tenant_header = (
        x_tenant_id if isinstance(x_tenant_id, str) else request.headers.get("x-tenant-id")
    )

    header_tenant_id = _parse_tenant_header(resolved_tenant_header)
    bearer_token = _extract_bearer_token(resolved_authorization)

    if bearer_token:
        if bearer_token == settings.INTERNAL_SERVICE_TOKEN:
            if header_tenant_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="X-Tenant-ID header is required for internal service requests",
                )
            request.state.tenant_id = str(header_tenant_id)
            request.state.auth_mode = "internal_service"
            return header_tenant_id

        payload = verify_token_with_iam(bearer_token)
        token_tenant_id = payload.get("tenant_id")
        if not token_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenant_id in token. User must be assigned to a tenant.",
            )

        try:
            authenticated_tenant_id = UUID(str(token_tenant_id))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid tenant_id in validated token",
            ) from exc

        if header_tenant_id and header_tenant_id != authenticated_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Tenant mismatch",
            )

        request.state.tenant_id = str(authenticated_tenant_id)
        request.state.auth_mode = "validated_user_token"
        request.state.user_id = payload.get("user_id")
        return authenticated_tenant_id

    if header_tenant_id and _is_dev_or_test_environment():
        logger.warning(
            "Accepting X-Tenant-ID without Authorization in %s mode for SOAR direct-service path",
            settings.ENVIRONMENT,
        )
        request.state.tenant_id = str(header_tenant_id)
        request.state.auth_mode = "dev_header_only"
        return header_tenant_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tenant ID required (validated bearer token or internal service token + X-Tenant-ID)",
    )
