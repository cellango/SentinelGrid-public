"""Fresh verified users only. Dataclass construction never grants authority."""

from fastapi import HTTPException, Request
from sg_core.security import get_verified_request_identity
from sg_core.request_credentials import request_bearer_token
from sg_core.user_principals import UserPrincipalSettings, require_user_binding
import time


def require_actor(request: Request):
    request_bearer_token(request)
    if "cookie" in request.headers:
        raise HTTPException(401, "Direct bearer authentication required")
    identity = get_verified_request_identity(request)
    config = getattr(request.app.state, "user_principal_settings", None)
    if not isinstance(config, UserPrincipalSettings):
        raise HTTPException(503, "User identity configuration unavailable")
    binding = require_user_binding(identity.payload(), config)
    if identity.payload()["exp"] <= time.time():
        raise HTTPException(401, "Identity expired")
    for name in (
        "x-user-id",
        "x-roles",
        "x-actor-id",
        "x-internal-token",
        "x-internal-service-token",
    ):
        if name in request.headers:
            raise HTTPException(403, "Conflicting action identity")
    values = request.headers.getlist("x-tenant-id")
    if len(values) > 1 or values and values[0] != identity.tenant_id:
        raise HTTPException(403, "Conflicting action tenant")
    realms = request.headers.getlist("x-realm")
    if (
        len(realms) > 1
        or realms
        and realms[0] != binding.issuer.rsplit("/realms/", 1)[1]
    ):
        raise HTTPException(403, "Conflicting action realm")
    return identity
