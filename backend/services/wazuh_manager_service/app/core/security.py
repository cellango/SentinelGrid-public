"""Wazuh HTTP source admission; no header-only, shared-token or body authority."""

from dataclasses import dataclass
from uuid import UUID
from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from app.core.principal_policy import WazuhPrincipalSettings
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.request_credentials import request_bearer_token
from sg_core.security import get_verified_request_identity
from sg_core.user_principals import require_user_binding

LIST_PATH = "/api/v1/wazuh/agents"
_BEARER_DOCUMENTATION = HTTPBearer(auto_error=False)
_PUBLIC = frozenset({("GET", "/", "app.api.health", "root")})
MAX_SKIP = 10000
MAX_LIMIT = 100


class WazuhInventoryQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    skip: int = Field(default=0, ge=0, le=MAX_SKIP)
    limit: int = Field(default=100, ge=1, le=MAX_LIMIT)


@dataclass(frozen=True)
class WazuhReadContext:
    """Constructing this object is not authentication or action authority."""

    tenant_id: UUID
    subject_id: UUID
    permission: str


def require_wazuh_request(request: Request) -> WazuhReadContext | None:
    endpoint = request.scope.get("endpoint")
    path = request.scope.get("path", "")
    owner = (getattr(endpoint, "__module__", None), getattr(endpoint, "__name__", None))
    if (request.method, path, *owner) in _PUBLIC:
        return None
    listing = path == LIST_PATH and owner == ("app.api.agents", "list_agents")
    if request.method != "GET" or not listing:
        raise HTTPException(
            503,
            "Wazuh operation requires an owned enrollment, provider or action contract",
        )
    request_bearer_token(request)
    if not isinstance(
        getattr(request.app.state, "iam_verification_settings", None),
        IAMVerificationSettings,
    ):
        raise HTTPException(503, "Wazuh verifier configuration unavailable")
    identity = get_verified_request_identity(request)
    policy = getattr(request.app.state, "wazuh_principal_settings", None)
    if not isinstance(policy, WazuhPrincipalSettings):
        raise HTTPException(503, "Wazuh identity configuration unavailable")
    binding = require_user_binding(identity.payload(), config=policy)
    if not any(
        (b.issuer, b.client_id, b.tenant_id, b.subject_id, b.permission)
        == (
            binding.issuer,
            binding.client_id,
            identity.tenant_id,
            identity.user_id,
            "wazuh.read_owned_inventory",
        )
        for b in policy.WAZUH_INVENTORY_READERS
    ):
        raise HTTPException(403, "Owned Wazuh reader permission required")
    raw = request.scope.get("raw_path")
    try:
        encoded = path.encode("ascii")
    except UnicodeError:
        raise HTTPException(403, "Ambiguous Wazuh read target") from None
    if (
        request.scope.get("root_path")
        or not isinstance(raw, bytes)
        or raw != encoded
        or b"%" in raw
        or b"\\" in raw
    ):
        raise HTTPException(403, "Ambiguous Wazuh read target")
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
    if len(request.scope.get("query_string", b"")) > 64:
        raise HTTPException(400, "Wazuh inventory read query too large")
    query = request.query_params
    allowed = {"skip", "limit"}
    if any(name not in allowed or len(query.getlist(name)) != 1 for name in query):
        raise HTTPException(400, "Unsupported or ambiguous Wazuh read query")
    if listing:
        try:
            WazuhInventoryQuery.model_validate(dict(query))
        except ValidationError:
            raise HTTPException(422, "Invalid Wazuh read query") from None
    if (
        request.headers.get("content-length", "0") != "0"
        or "transfer-encoding" in request.headers
    ):
        raise HTTPException(400, "Wazuh inventory read body is unsupported")
    return WazuhReadContext(
        UUID(identity.tenant_id), UUID(identity.user_id), "wazuh.read_owned_inventory"
    )


def get_current_tenant(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(_BEARER_DOCUMENTATION),
) -> UUID:
    context = require_wazuh_request(request)
    if context is None:
        raise HTTPException(503, "Tenant-scoped Wazuh operation required")
    return context.tenant_id


def require_owned_wazuh_operation():
    """Raw UUIDs, stored sensor labels, cached tokens and provider secrets grant no authority."""
    raise HTTPException(
        503, "Owned Wazuh enrollment, workload and provider contract required"
    )
