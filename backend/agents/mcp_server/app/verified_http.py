"""Opt-in authenticated MCP discovery using the installed SDK HTTP transport.

The default stdio preview is unchanged. This factory is not mounted/deployed by
any entrypoint. It authenticates a user, grants no tool/action capability, and
keeps every execution path denied until domain contracts are qualified.
"""

from contextlib import asynccontextmanager
from dataclasses import dataclass
import time
from uuid import UUID

import anyio
from fastapi import HTTPException
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.servers.core_server import create_core_server
from sg_core.http_ingress import GatewayIngressMiddleware, IngressPolicy
from sg_core.http_rate_limit import (
    RateLimitPolicy,
    create_budget_store,
    PeerBudgetMiddleware,
)
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.request_credentials import request_bearer_token
from sg_core.security import get_verified_request_identity
from sg_core.user_principals import UserPrincipalSettings, require_user_binding

_CONTEXT = object()


@dataclass(frozen=True)
class MCPTransportCaller:
    tenant_id: UUID
    actor_subject_id: UUID
    client_id: str
    expires_at: float
    # Identity and discovery never grant an execution capability.
    capabilities: tuple[str, ...] = ()


def _authenticate(request: Request) -> MCPTransportCaller:
    request_bearer_token(request)
    if "cookie" in request.headers:
        raise HTTPException(401, "MCP requires non-cookie bearer authentication")
    identity = get_verified_request_identity(request)
    binding = require_user_binding(
        identity.payload(), request.app.state.user_principal_settings
    )
    for name in (
        "x-tenant-id",
        "x-user-id",
        "x-roles",
        "x-realm",
        "x-actor-id",
        "x-internal-token",
        "x-internal-service-token",
    ):
        if name in request.headers:
            raise HTTPException(403, "MCP identity comes from the verified transport")
    expires = identity.payload()["exp"]
    if expires <= time.time():
        raise HTTPException(401, "MCP identity expired")
    store = request.app.state.request_budget_store
    if store is not None:
        store.check_identity(identity)
    return MCPTransportCaller(
        UUID(identity.tenant_id),
        UUID(identity.user_id),
        binding.client_id,
        float(expires),
    )


def get_transport_caller(request: Request) -> MCPTransportCaller:
    """Read only a request verified by this transport; construction grants nothing."""
    value = request.scope.get(_CONTEXT)
    if not isinstance(value, MCPTransportCaller) or value.expires_at <= time.time():
        raise HTTPException(401, "Verified MCP transport context required")
    return value


def create_verified_http_app(
    *,
    verification: IAMVerificationSettings,
    users: UserPrincipalSettings,
    allowed_hosts: tuple[str, ...],
    allowed_origins: tuple[str, ...] = (),
    rate_policy: RateLimitPolicy = RateLimitPolicy(),
) -> Starlette:
    if not isinstance(verification, IAMVerificationSettings) or not isinstance(
        users, UserPrincipalSettings
    ):
        raise ValueError("Owned verifier and user-client configuration required")
    if not allowed_hosts or any(
        not h or "*" in h or "/" in h or len(h) > 256 for h in allowed_hosts
    ):
        raise ValueError("Exact owned MCP hosts required")
    if any(
        not o.startswith(("https://", "http://")) or "*" in o or o == "null"
        for o in allowed_origins
    ):
        raise ValueError("Exact owned MCP origins required")
    if not isinstance(rate_policy, RateLimitPolicy):
        raise ValueError("Owned MCP budget policy required")
    if verification.ENVIRONMENT not in {"development", "test"} and (
        not rate_policy.enabled
        or not rate_policy.fail_closed
        or not rate_policy.redis_url.startswith("rediss://")
    ):
        raise ValueError(
            "Non-development MCP requires TLS Redis and fail-closed rate limiting"
        )
    server = create_core_server()
    manager = StreamableHTTPSessionManager(
        server,
        stateless=True,
        json_response=True,
        max_request_body_size=2 * 1024 * 1024,
        security_settings=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=list(allowed_hosts),
            allowed_origins=list(allowed_origins),
        ),
    )

    @asynccontextmanager
    async def lifespan(app):
        async with manager.run():
            yield

    async def endpoint(scope, receive, send):
        request = Request(scope, receive)
        try:
            origins = request.headers.getlist("origin")
            if len(origins) > 1 or origins and origins[0] not in allowed_origins:
                raise HTTPException(403, "MCP origin not allowed")
            caller = await anyio.to_thread.run_sync(_authenticate, request)
            scope[_CONTEXT] = caller
        except HTTPException as exc:
            return await JSONResponse(
                {"detail": exc.detail},
                status_code=exc.status_code,
                headers={"WWW-Authenticate": "Bearer"}
                if exc.status_code == 401
                else {},
            )(scope, receive, send)
        # No resumable session or cross-request caller cache. The SDK receives
        # this exact authenticated request and immutable context for each POST.
        await manager.handle_request(scope, receive, send)

    class Handler:
        async def __call__(self, scope, receive, send):
            await endpoint(scope, receive, send)

    app = Starlette(
        routes=[Route("/mcp", endpoint=Handler(), methods=["POST"])], lifespan=lifespan
    )
    app.state.request_budget_store = create_budget_store(rate_policy)
    app.add_middleware(PeerBudgetMiddleware, store=app.state.request_budget_store)
    app.add_middleware(
        GatewayIngressMiddleware, policy=IngressPolicy(allowed_origins=allowed_origins)
    )
    app.state.iam_verification_settings = verification
    app.state.user_principal_settings = users
    return app
