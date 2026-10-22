"""Common user-identity gate for every mounted FastAPI application route.

This gate authenticates a caller, not an action. Route/domain authorization and
provider/credential policies remain necessary before any effect is admitted.
"""

from fastapi import HTTPException, Request
from sg_core.security import get_verified_request_identity
from sg_core.user_principals import UserPrincipalSettings, require_user_binding

# Exact method/path pairs only; no prefix skips or caller-controlled bypass flag.
_PUBLIC = frozenset({
    ("GET", "/"), ("GET", "/health"), ("GET", "/ready"),
    ("GET", "/metrics"), ("GET", "/metrics/prometheus"),
    ("POST", "/api/v1/auth/login"), ("POST", "/api/v1/auth/refresh"),
})
_BLOCKED = frozenset({
    ("POST", "/api/v1/internal/ai-shield/events"),
    ("GET", "/api/v1/ingest/pipelines"), ("GET", "/api/v1/ingest/templates"),
    ("POST", "/api/v1/ingest/test-pipeline"),
})


def require_gateway_identity(request: Request):
    route = (request.method, request.url.path)
    if route in _PUBLIC:
        return None
    if route in _BLOCKED:
        # The shared service token is not delegated tenant authority; global
        # diagnostics also need their own administrator/capability contract.
        raise HTTPException(503, "Gateway operation unavailable")
    identity = get_verified_request_identity(request)
    config = request.app.state.user_principal_settings
    if not isinstance(config, UserPrincipalSettings):
        raise HTTPException(503, "User identity configuration unavailable")
    binding = require_user_binding(identity.payload(), config)
    expected = {"x-tenant-id": identity.tenant_id, "x-realm": binding.issuer.rsplit("/realms/", 1)[1]}
    for name, value in expected.items():
        supplied = request.headers.getlist(name)
        if len(supplied) > 1 or supplied and supplied[0] != value:
            raise HTTPException(403, "Conflicting identity context")
    for name in ("x-user-id", "x-roles", "x-actor-id", "x-internal-service-token", "x-internal-token"):
        if name in request.headers:
            raise HTTPException(403, "Conflicting identity context")
    budget_store = request.app.state.request_budget_store
    if budget_store is not None:
        budget_store.check_identity(identity)
    return identity
