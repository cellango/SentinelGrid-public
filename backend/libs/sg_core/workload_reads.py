"""Request-bound workload reads using the existing authoritative IAM verifier.

This contract authenticates a machine reading its registered tenant's resources.
It neither delegates an end user nor authorizes writes, provider operations or
model/tool execution. No token issuer or live provider registration is supplied.
"""

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import re
import time
from types import MappingProxyType
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.routing import compile_path

from sg_core.iam_verification import IAMVerificationSettings, get_verification_settings
from sg_core.security import get_verified_request_identity

READ_CONTRACT = "keycloak-workload-read-v1"
ServiceID = Literal["ticketing_service", "scanner_orchestrator", "soar_service"]
Permission = Literal["ticketing.read", "scan.read_results", "playbook.read_catalog"]

# Owned operation selection, not caller-selected route/capability metadata. Only
# these existing read handlers are in this foundation. Every other operation is
# unavailable until its own authorization/effect contract is qualified.
# Scanner artifact-object ownership and SOAR shared-catalog tenancy are open;
# their adapters exist, but no read operation/registration is admitted here.
READ_OPERATIONS = MappingProxyType({
    ("ticketing_service", "/api/v1/tickets"): "ticketing.read",
    ("ticketing_service", "/api/v1/tickets/{ticket_id}"): "ticketing.read",
    ("ticketing_service", "/api/v1/tickets/{ticket_id}/tabs/{tab_name}"): "ticketing.read",
})


# Included FastAPI routers can retain their original relative path. Reconstruct
# only these server-owned prefixes, then require the concrete request path to
# match; an unreviewed prefix/alias cannot inherit admission.
_SERVICE_PREFIXES = {"ticketing_service": "/api/v1/tickets", "scanner_orchestrator": "", "soar_service": "/soar"}
_ROUTE_PATTERNS = {key: compile_path(key[1])[0] for key in READ_OPERATIONS}


def _uuid(value: str) -> UUID:
    if not isinstance(value, str):
        raise ValueError("Expected UUID")
    parsed = UUID(value)
    if not parsed.int or str(parsed) != value:
        raise ValueError("Expected canonical non-nil UUID")
    return parsed


def service_audience(service_id: str) -> str:
    if service_id not in {"ticketing_service", "scanner_orchestrator", "soar_service"}:
        raise ValueError("Unknown read service")
    return "urn:sentinelgrid:service:" + service_id


class WorkloadReadBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, hide_input_in_errors=True)
    issuer: str
    client_id: str
    subject_id: str
    tenant_id: str
    service_id: ServiceID
    permission: Permission
    contract: Literal["keycloak-workload-read-v1"]

    @model_validator(mode="after")
    def exact_registration(self):
        p = urlsplit(self.issuer)
        if (p.scheme not in {"http", "https"} or not p.hostname or p.username is not None
            or p.password is not None or p.query or p.fragment or "?" in self.issuer or "#" in self.issuer
            or "\\" in self.issuer or "%" in self.issuer or self.issuer != self.issuer.strip()
            or any(ord(c) < 33 or ord(c) == 127 for c in self.issuer) or p.port == 0
            or not re.fullmatch(r".*/realms/[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", p.path)):
            raise ValueError("Expected exact owned Keycloak issuer")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", self.client_id):
            raise ValueError("Expected exact client ID")
        _uuid(self.subject_id); _uuid(self.tenant_id)
        if self.permission not in {v for (service, _), v in READ_OPERATIONS.items() if service == self.service_id}:
            raise ValueError("Permission does not belong to service")
        return self


class WorkloadReadSettings(BaseSettings):
    ENVIRONMENT: str = "development"
    SERVICE_READ_WORKLOAD_BINDINGS: tuple[WorkloadReadBinding, ...] = Field(default=(), max_length=256)
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore",
                                      frozen=True, hide_input_in_errors=True)

    @model_validator(mode="after")
    def unique_registrations(self):
        keys = [(b.issuer, b.client_id, b.subject_id, b.tenant_id, b.service_id, b.permission)
                for b in self.SERVICE_READ_WORKLOAD_BINDINGS]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate workload read registration")
        if self.ENVIRONMENT.strip().lower() not in {"development", "test"}:
            if any(urlsplit(b.issuer).scheme != "https" for b in self.SERVICE_READ_WORKLOAD_BINDINGS):
                raise ValueError("Workload issuer requires HTTPS outside local development")
        return self


@lru_cache(maxsize=1)
def get_workload_read_settings():
    return WorkloadReadSettings()


@dataclass(frozen=True)
class WorkloadReadContext:
    """Created only after verification/admission; a constructed object grants nothing."""
    tenant_id: UUID
    workload_subject_id: UUID
    client_id: str
    service_id: str
    permission: str
    request_id: UUID
    expires_at: float


def get_workload_read_context(request: Request, service_id: str) -> WorkloadReadContext:
    route = request.scope.get("route")
    declared = getattr(route, "path", None)
    operation = (service_id, declared)
    if operation not in READ_OPERATIONS and isinstance(declared, str):
        operation = (service_id, _SERVICE_PREFIXES.get(service_id, "") + declared)
    permission = READ_OPERATIONS.get(operation)
    if (request.method != "GET" or permission is None
        or not _ROUTE_PATTERNS[operation].fullmatch(request.scope["path"])):
        raise HTTPException(503, "Service operation requires an owned action contract")
    # Credential syntax, signature/issuer/audience/time and receipt binding use
    # the common verifier. No response body, raw UUID or typed object authenticates.
    identity = get_verified_request_identity(request)
    payload = identity.payload()
    if (payload.get("typ") != "Bearer" or payload.get("sg_principal_type") != "workload"
        or payload.get("sg_identity_contract") != READ_CONTRACT
        or any(k in payload for k in ("act", "may_act", "sg_actor"))):
        raise HTTPException(403, "Workload read identity required")
    try:
        config = getattr(request.app.state, "workload_read_settings", None)
        if config is None:
            config = get_workload_read_settings()
        if not isinstance(config, WorkloadReadSettings) or not config.SERVICE_READ_WORKLOAD_BINDINGS:
            raise HTTPException(503, "Workload read configuration unavailable")
        verification = getattr(request.app.state, "iam_verification_settings", None)
        if verification is None:
            verification = get_verification_settings()
        if not isinstance(verification, IAMVerificationSettings):
            raise ValueError("Invalid verifier configuration")
        audiences = payload.get("aud")
        if isinstance(audiences, str): audiences = [audiences]
        expected_audiences = {verification.KEYCLOAK_CLIENT_ID, service_audience(service_id)}
        if not isinstance(audiences, list) or len(audiences) != len(set(audiences)) or set(audiences) != expected_audiences:
            raise HTTPException(403, "Workload audience mismatch")
        matching = [b for b in config.SERVICE_READ_WORKLOAD_BINDINGS if (
            b.issuer, b.client_id, b.subject_id, b.tenant_id, b.service_id, b.permission
        ) == (payload.get("iss"), payload.get("azp"), identity.user_id, identity.tenant_id, service_id, permission)]
        if len(matching) != 1 or payload.get("sg_permissions") != [permission]:
            raise HTTPException(403, "Workload read permission denied")
        if "client_id" in payload and payload["client_id"] != matching[0].client_id:
            raise HTTPException(403, "Conflicting workload client")
        now = time.time()
        if (payload["exp"] <= now or payload["iat"] > now or payload["exp"]-payload["iat"] > 60
            or now-payload["iat"] > 60):
            raise HTTPException(401, "Expired or invalid workload read token")
        try:
            request_id = _uuid(payload.get("jti"))
        except (ValueError, TypeError):
            raise HTTPException(403, "Invalid workload request ID") from None
        raw_path = request.scope.get("raw_path")
        path = request.scope["path"]
        if (request.scope.get("root_path") or not isinstance(raw_path, bytes)
            or raw_path != path.encode("ascii") or b"%" in raw_path or b"\\" in raw_path
            or "//" in path or any(part in {".", ".."} for part in path.split("/"))):
            raise HTTPException(403, "Ambiguous workload target")
        query = request.scope.get("query_string", b"")
        if len(query) > 8192:
            raise HTTPException(403, "Workload query too large")
        target = {"service_id": service_id, "method": "GET", "path": path,
                  "query_sha256": hashlib.sha256(query).hexdigest()}
        if payload.get("sg_request") != target:
            raise HTTPException(403, "Workload target mismatch")
        if request.headers.get("content-length", "0") != "0" or "transfer-encoding" in request.headers:
            raise HTTPException(403, "Workload read body is not supported")
        for name, expected in {"x-tenant-id": identity.tenant_id,
                               "x-realm": matching[0].issuer.rsplit("/realms/", 1)[1]}.items():
            supplied = request.headers.getlist(name)
            if len(supplied) > 1 or supplied and supplied[0] != expected:
                raise HTTPException(403, "Conflicting identity context")
        if any(name in request.headers for name in ("x-user-id", "x-roles", "x-internal-token", "x-internal-service-token")):
            raise HTTPException(403, "Conflicting identity context")
        return WorkloadReadContext(_uuid(identity.tenant_id), _uuid(identity.user_id), matching[0].client_id,
                                   service_id, permission, request_id, float(payload["exp"]))
    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError, OverflowError, OSError, UnicodeError):
        raise HTTPException(503, "Workload read configuration or identity unavailable") from None
