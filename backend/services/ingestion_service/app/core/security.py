"""Exact ingestion HTTP source admission; no forwarded tenant or debug authority."""

from dataclasses import dataclass
from uuid import UUID
from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.principal_policy import IngestionPrincipalSettings
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.request_credentials import request_bearer_token
from sg_core.security import get_verified_request_identity
from sg_core.user_principals import require_user_binding

_BEARER_DOCUMENTATION = HTTPBearer(auto_error=False)
_RUNTIME = frozenset(
    {
        ("GET", "/metrics", "app.main", "metrics"),
        ("GET", "/metrics/prometheus", "app.main", "metrics_prometheus"),
    }
)


@dataclass(frozen=True)
class RuntimeReadContext:
    """Constructing this object grants no event, tenant or operator authority."""

    reader_tenant_id: UUID
    subject_id: UUID
    permission: str
    scope: str


def require_ingestion_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_BEARER_DOCUMENTATION),
) -> RuntimeReadContext | None:
    endpoint = request.scope.get("endpoint")
    path = request.scope.get("path", "")
    operation = (
        request.method,
        path,
        getattr(endpoint, "__module__", None),
        getattr(endpoint, "__name__", None),
    )
    if operation == ("GET", "/", "app.main", "root"):
        return None
    if operation not in _RUNTIME:
        raise HTTPException(
            503,
            "Ingestion operation requires an owned workload or operational contract",
        )
    request_bearer_token(request)
    if not isinstance(
        getattr(request.app.state, "iam_verification_settings", None),
        IAMVerificationSettings,
    ):
        raise HTTPException(503, "Ingestion verifier configuration unavailable")
    identity = get_verified_request_identity(request)
    policy = getattr(request.app.state, "ingestion_principal_settings", None)
    if not isinstance(policy, IngestionPrincipalSettings):
        raise HTTPException(503, "Ingestion identity configuration unavailable")
    binding = require_user_binding(identity.payload(), config=policy)
    if not any(
        (
            g.issuer,
            g.client_id,
            g.tenant_id,
            g.subject_id,
            g.service,
            g.scope,
            g.permission,
        )
        == (
            binding.issuer,
            binding.client_id,
            identity.tenant_id,
            identity.user_id,
            "ingestion-service",
            "service_runtime",
            "ingestion.read_runtime",
        )
        for g in policy.INGESTION_RUNTIME_READERS
    ):
        raise HTTPException(
            403, "Explicit service-wide runtime reader permission required"
        )
    raw = request.scope.get("raw_path")
    if (
        request.scope.get("root_path")
        or not isinstance(raw, bytes)
        or raw != path.encode("ascii")
    ):
        raise HTTPException(403, "Ambiguous ingestion runtime read target")
    for name, expected in {
        "x-tenant-id": identity.tenant_id,
        "x-realm": binding.issuer.rsplit("/realms/", 1)[1],
    }.items():
        values = request.headers.getlist(name)
        if len(values) > 1 or values and values[0] != expected:
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
    # Global runtime metrics are explicitly service-wide, never selected by a tenant hint.
    if len(request.scope.get("query_string", b"")) > 64:
        raise HTTPException(400, "Runtime read query too large")
    query = request.query_params
    if query and (
        path != "/metrics"
        or set(query) != {"format"}
        or query.getlist("format") != ["prometheus"]
    ):
        raise HTTPException(400, "Unsupported or ambiguous runtime read query")
    if (
        request.headers.get("content-length", "0") != "0"
        or "transfer-encoding" in request.headers
    ):
        raise HTTPException(400, "Runtime read body is unsupported")
    return RuntimeReadContext(
        UUID(identity.tenant_id),
        UUID(identity.user_id),
        "ingestion.read_runtime",
        "service_runtime",
    )


async def verify_token_with_iam_agent(token: str) -> dict:
    """Legacy token-only helper cannot establish an owned operation contract."""
    raise HTTPException(503, "Owned ingestion request identity required")


async def get_current_tenant(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_BEARER_DOCUMENTATION),
) -> str:
    """Event writes need an owned workload contract; runtime readers cannot ingest."""
    raise HTTPException(503, "Owned ingestion workload and effect contract required")
