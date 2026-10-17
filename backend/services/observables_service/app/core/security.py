"""Observable HTTP source admission; no header-only, shared-token or body authority."""

from dataclasses import dataclass
from uuid import UUID
from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.routing import compile_path
from app.core.principal_policy import ObservablePrincipalSettings
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.request_credentials import request_bearer_token
from sg_core.security import get_verified_request_identity
from sg_core.user_principals import require_user_binding

DETAIL_PATH = "/observables/{observable_id}"
_DETAIL_PATTERN = compile_path(DETAIL_PATH)[0]
_BEARER_DOCUMENTATION = HTTPBearer(auto_error=False)
_PUBLIC = frozenset(
    {("GET", "/", "app.main", "root"), ("GET", "/health", "app.main", "health")}
)


@dataclass(frozen=True)
class ObservableReadContext:
    """Constructing this object is not authentication or action authority."""

    tenant_id: UUID
    subject_id: UUID
    permission: str


def require_observable_request(request: Request) -> ObservableReadContext | None:
    endpoint = request.scope.get("endpoint")
    path = request.scope.get("path", "")
    owner = (getattr(endpoint, "__module__", None), getattr(endpoint, "__name__", None))
    if (request.method, path, *owner) in _PUBLIC:
        return None
    detail = _DETAIL_PATTERN.fullmatch(path) and owner == ("app.main", "get_observable")
    if request.method != "GET" or not detail:
        raise HTTPException(
            503,
            "Observable operation requires an owned data, workload or action contract",
        )
    request_bearer_token(request)
    if not isinstance(
        getattr(request.app.state, "iam_verification_settings", None),
        IAMVerificationSettings,
    ):
        raise HTTPException(503, "Observable verifier configuration unavailable")
    identity = get_verified_request_identity(request)
    policy = getattr(request.app.state, "observable_principal_settings", None)
    if not isinstance(policy, ObservablePrincipalSettings):
        raise HTTPException(503, "Observable identity configuration unavailable")
    binding = require_user_binding(identity.payload(), config=policy)
    if not any(
        (b.issuer, b.client_id, b.tenant_id, b.subject_id, b.permission)
        == (
            binding.issuer,
            binding.client_id,
            identity.tenant_id,
            identity.user_id,
            "observable.read_owned",
        )
        for b in policy.OBSERVABLE_READERS
    ):
        raise HTTPException(403, "Owned observable reader permission required")
    if detail:
        value = request.path_params.get("observable_id")
        try:
            target = UUID(value)
            if not target.int or str(target) != value:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(403, "Canonical observable UUID required") from None
    raw = request.scope.get("raw_path")
    try:
        encoded = path.encode("ascii")
    except UnicodeError:
        raise HTTPException(403, "Ambiguous observable read target") from None
    if (
        request.scope.get("root_path")
        or not isinstance(raw, bytes)
        or raw != encoded
        or b"%" in raw
        or b"\\" in raw
    ):
        raise HTTPException(403, "Ambiguous observable read target")
    for name, expected in {
        "x-tenant-id": identity.tenant_id,
        "x-realm": binding.issuer.rsplit("/realms/", 1)[1],
    }.items():
        supplied = request.headers.getlist(name)
        if len(supplied) > 1 or supplied and supplied[0] != expected:
            raise HTTPException(403, "Conflicting identity context")
    if any(
        name in request.headers
        for name in (
            "x-user-id",
            "x-roles",
            "x-internal-token",
            "x-internal-service-token",
            "x-api-key",
        )
    ):
        raise HTTPException(403, "Conflicting identity context")
    if request.query_params:
        raise HTTPException(400, "Observable detail accepts no query")
    if (
        request.headers.get("content-length", "0") != "0"
        or "transfer-encoding" in request.headers
    ):
        raise HTTPException(400, "Observable read body is unsupported")
    return ObservableReadContext(
        UUID(identity.tenant_id), UUID(identity.user_id), "observable.read_owned"
    )


def get_current_tenant(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_BEARER_DOCUMENTATION),
) -> UUID:
    context = require_observable_request(request)
    if context is None:
        raise HTTPException(503, "Tenant-scoped Observable operation required")
    return context.tenant_id


async def verify_internal_token(*args, **kwargs) -> bool:
    """Legacy token-only helper supplies no owned observable operation authority."""
    raise HTTPException(503, "Owned observable request identity required")


async def get_tenant_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_BEARER_DOCUMENTATION),
) -> UUID:
    """Compatibility name; headers and UUIDs alone never establish identity."""
    return get_current_tenant(request)


def require_owned_observable_operation():
    """Legacy raw sessions/UUIDs/provider credentials do not grant action authority."""
    raise HTTPException(
        503, "Owned observable data, workload and provider contract required"
    )
