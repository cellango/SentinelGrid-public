"""
Middleware to audit admin/API actions.

Lightweight logging to `realm_audit_log` (or no-op if DB unavailable). The
middleware is intentionally permissive: it never blocks requests and skips
noise endpoints.
"""

import logging
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.audit_service import AuditService
from app.core.config import settings

logger = logging.getLogger(__name__)


class AdminAuditMiddleware(BaseHTTPMiddleware):
    """Audit mutating API calls with actor and path context."""

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        method = request.method.upper()
        # SCIM/editor own their audit; unavailable AI/protocol paths must not
        # initialize a legacy realm client before rejecting an operation.
        # Never reinterpret its opaque credential as a user JWT or initialize an
        # unrelated provider client in this best-effort middleware.
        if (path.startswith(("/api/v1/scim/v2/", "/api/v1/ai/editor/",
                             "/internal/iam/protocols", "/internal/iam/ai/"))
                or path == "/internal/iam/chat"
                or (path.startswith("/api/iam-portal/policies/")
                    and path.rsplit("/", 1)[-1] in {"generate", "explain", "analyze"})):
            return await call_next(request)

        # Skip non-interesting endpoints
        if path in {"/", "/health"} or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)

        # Only audit mutating or sensitive paths
        should_audit = method in {"POST", "PUT", "PATCH", "DELETE"}
        if not should_audit and "/api/v1/" not in path:
            return await call_next(request)

        tenant_id = None
        user_id = None
        actor_email = None
        try:
            auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "", 1)
                from app.services.token_validator import TokenValidator
                from app.services.keycloak_client import KeycloakClient

                validator = TokenValidator(KeycloakClient())
                result = validator.validate_token(token)
                if result.get("valid"):
                    tenant_id = result.get("tenant_id")
                    user_id = result.get("user_id")
                    actor_email = result.get("email") or result.get("username")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Admin audit token parse skipped")

        response = await call_next(request)

        try:
            AuditService.log_auth_event(
                realm_name=settings.KEYCLOAK_REALM,
                action=f"{method} {path}",
                actor_user_id=user_id,
                actor_email=actor_email,
                customer_id=None,
                organization_id=None,
                details={
                    "tenant_id": tenant_id,
                    "status_code": response.status_code,
                    "path": path,
                    "method": method,
                },
                ip_address=(request.client.host if request.client else None),
                user_agent=request.headers.get("user-agent"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Admin audit logging skipped: %s", exc)

        return response
