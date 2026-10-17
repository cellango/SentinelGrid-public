"""Exact orchestrator HTTP source admission and owned user/read authority.

A read method, registered user, shared credential or constructed context does not
confer action authority. Required unavailable operations remain restoration work.
"""
from dataclasses import dataclass
from uuid import UUID
from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.routing import compile_path
from app.core.principal_policy import OrchestratorPrincipalSettings
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.request_credentials import request_bearer_token
from sg_core.security import get_verified_request_identity
from sg_core.user_principals import require_user_binding

HISTORY_PATH = "/api/v1/orchestrator/tenant/{tenant_id}/posture-score/history"
_HISTORY_PATTERN = compile_path(HISTORY_PATH)[0]
_BEARER_DOCUMENTATION = HTTPBearer(auto_error=False)
_PUBLIC = frozenset({("GET", "/", "app.main", "root"), ("GET", "/health", "app.main", "health_check")})


@dataclass(frozen=True)
class OrchestratorReadContext:
    """Only the verified request path creates authority; constructing this does not."""
    tenant_id: UUID
    subject_id: UUID
    permission: str


def require_orchestrator_request(request: Request) -> OrchestratorReadContext | None:
    endpoint = request.scope.get("endpoint")
    path = request.scope["path"]
    owner = (getattr(endpoint,"__module__",None),getattr(endpoint,"__name__",None))
    if (request.method,path,*owner) in _PUBLIC:
        return None
    if (request.method != "GET" or owner != ("app.api.posture","get_posture_score_history")
        or not _HISTORY_PATTERN.fullmatch(path)):
        raise HTTPException(503,"Orchestrator operation requires an owned data or action contract")
    request_bearer_token(request)  # Cookie-only/marker forms do not expand direct service authority.
    verification = getattr(request.app.state,"iam_verification_settings",None)
    if not isinstance(verification,IAMVerificationSettings):
        raise HTTPException(503,"Orchestrator verifier configuration unavailable")
    identity = get_verified_request_identity(request)
    policy = getattr(request.app.state,"orchestrator_principal_settings",None)
    if not isinstance(policy,OrchestratorPrincipalSettings):
        raise HTTPException(503,"Orchestrator identity configuration unavailable")
    payload = identity.payload()
    binding = require_user_binding(payload,config=policy)
    if not any((b.issuer,b.client_id,b.tenant_id,b.subject_id,b.permission)==(
        binding.issuer,binding.client_id,identity.tenant_id,identity.user_id,"posture.read_history")
        for b in policy.ORCHESTRATOR_POSTURE_HISTORY_READERS):
        raise HTTPException(403,"Posture history reader permission required")
    tenant = request.path_params.get("tenant_id")
    if not isinstance(tenant,str) or tenant != identity.tenant_id:
        raise HTTPException(403,"Access denied: Tenant mismatch")
    raw = request.scope.get("raw_path")
    if (request.scope.get("root_path") or not isinstance(raw,bytes) or raw != path.encode("ascii")
        or b"%" in raw or b"\\" in raw):
        raise HTTPException(403,"Ambiguous posture history target")
    for name,expected in {"x-tenant-id":identity.tenant_id,"x-realm":binding.issuer.rsplit("/realms/",1)[1]}.items():
        hints = request.headers.getlist(name)
        if len(hints)>1 or hints and hints[0]!=expected:
            raise HTTPException(403,"Conflicting identity context")
    if any(name in request.headers for name in ("x-user-id","x-roles","x-internal-token","x-internal-service-token")):
        raise HTTPException(403,"Conflicting identity context")
    if any(name!="limit" for name in request.query_params) or len(request.query_params.getlist("limit"))>1:
        raise HTTPException(400,"Unsupported or ambiguous posture history query")
    if request.headers.get("content-length","0")!="0" or "transfer-encoding" in request.headers:
        raise HTTPException(400,"Posture history read body is unsupported")
    return OrchestratorReadContext(UUID(identity.tenant_id),UUID(identity.user_id),"posture.read_history")


def get_current_tenant(
    request: Request, credentials: HTTPAuthorizationCredentials | None = Security(_BEARER_DOCUMENTATION),
) -> UUID:
    """Compatibility dependency: no raw header, role or shared-token authority."""
    context = require_orchestrator_request(request)
    if context is None:
        raise HTTPException(503,"Tenant-scoped orchestrator operation required")
    return context.tenant_id
