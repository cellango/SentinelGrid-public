"""Bounded SCIM User observations and durable read/blocked-operation audits.

Provisioning, PATCH, Groups and filters are not admitted. No provider effects are
implemented; the only outbound POST acquires the deployment's directory-read token.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import re
import secrets
from threading import Lock
import time
from urllib.parse import quote, urlsplit
from uuid import UUID
from fastapi import Header, HTTPException
import httpx
from app.core.config import settings
from app.services.audit_logger import AuditLogger
from app.services.role_directory_service import RoleDirectoryService

ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"
USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
LIST_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"


class SCIMError(HTTPException):
    def __init__(self, status, detail, scim_type=None, headers=None):
        super().__init__(status, detail, headers)
        self.scim_type = scim_type


@dataclass(frozen=True)
class SCIMContext:
    client_id: UUID
    tenant_id: UUID
    realm: str
    permissions: frozenset[str]
    credential_digest: str = field(repr=False)


_rate_limit_state = {}
_rate_lock = Lock()


def _rate_limit(client_id):
    window = int(time.monotonic() // 60)
    with _rate_lock:
        valid = set(settings.SCIM_CLIENT_BINDINGS)
        for old in list(_rate_limit_state):
            if old not in valid:
                del _rate_limit_state[old]
        prior_window, count = _rate_limit_state.get(client_id, (window, 0))
        count = count + 1 if prior_window == window else 1
        _rate_limit_state[client_id] = (window, count)
        if count > settings.SCIM_RATE_LIMIT_PER_MINUTE:
            raise SCIMError(
                429, "SCIM client rate limit exceeded", headers={"Retry-After": "60"}
            )


def verify_scim_token(authorization: str | None = Header(None)):
    invalid = SCIMError(
        401, "Invalid SCIM bearer credential", headers={"WWW-Authenticate": "Bearer"}
    )
    if not authorization or not authorization[:7].lower() == "bearer ":
        raise invalid
    token = authorization[7:]
    if not 32 <= len(token) <= 512 or not re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", token):
        raise invalid
    digest = hashlib.sha256(token.encode()).hexdigest()
    matches = []
    # Unauthenticated values never become rate-cache keys, tenant UUIDs or realms.
    for client, binding in settings.SCIM_CLIENT_BINDINGS.items():
        if secrets.compare_digest(digest, binding.credential_digest.get_secret_value()):
            matches.append((client, binding))
    if len(matches) != 1:
        raise invalid
    client, binding = matches[0]
    _rate_limit(client)
    return SCIMContext(
        UUID(client), binding.tenant_id, binding.realm, binding.permissions, digest
    )


def current_binding(context):
    binding = settings.SCIM_CLIENT_BINDINGS.get(str(context.client_id))
    if (
        binding is None
        or binding.tenant_id != context.tenant_id
        or binding.realm != context.realm
        or binding.permissions != context.permissions
        or not secrets.compare_digest(
            binding.credential_digest.get_secret_value(), context.credential_digest
        )
    ):
        raise SCIMError(403, "SCIM client binding changed or is unavailable")


def query_parameters(pairs):
    params = {}
    for key, value in pairs:
        if (
            key in params
            or key not in {"startIndex", "count", "filter"}
            or len(value) > 512
        ):
            raise SCIMError(400, "Unsupported or ambiguous SCIM query", "invalidSyntax")
        params[key] = value
    if "filter" in params:
        raise SCIMError(400, "SCIM filters are not supported", "invalidFilter")

    def integer(name, default):
        value = params.get(name, str(default))
        if not re.fullmatch(r"[+-]?[0-9]{1,10}", value) or abs(int(value)) > 2147483647:
            raise SCIMError(400, "Invalid SCIM pagination", "invalidSyntax")
        return int(value)

    return max(1, integer("startIndex", 1)), min(100, max(0, integer("count", 100)))


def resource_uuid(value):
    try:
        result = UUID(value)
        if str(result) != value.lower():
            raise ValueError()
        return result
    except (ValueError, TypeError, AttributeError):
        raise SCIMError(400, "A resource UUID is required", "invalidValue")


def provider_unavailable():
    raise SCIMError(503, "SCIM directory unavailable or unverified")


class SCIMDirectoryService(RoleDirectoryService):
    def _base(self, context):
        parsed = urlsplit(settings.KEYCLOAK_URL)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or context.realm in {".", ".."}
            or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", context.realm)
        ):
            provider_unavailable()
        return (
            settings.KEYCLOAK_URL.rstrip("/")
            + "/admin/realms/"
            + quote(context.realm, safe="")
        )

    def _membership(self, user):
        try:
            identity = resource_uuid(user["id"])
            if type(user["enabled"]) is not bool:
                provider_unavailable()
            return identity, self._tenant(user)
        except (KeyError, TypeError, HTTPException):
            provider_unavailable()

    def _resource(self, user):
        # Only known provider fields are projected; credentials/roles/attributes
        # never pass through. No invented externalId or modification timestamp.
        username = user.get("username")
        if not isinstance(username, str) or not username.strip() or len(username) > 255:
            provider_unavailable()
        result = dict(
            schemas=[USER_SCHEMA],
            id=str(resource_uuid(user["id"])),
            userName=username,
            active=user["enabled"],
            meta={"resourceType": "User"},
        )
        name = {}
        for source, target in [("firstName", "givenName"), ("lastName", "familyName")]:
            value = user.get(source)
            if value is not None:
                if not isinstance(value, str) or len(value) > 255:
                    provider_unavailable()
                if value:
                    name[target] = value
        if name:
            result["name"] = name
            result["displayName"] = " ".join(name.values())
        email = user.get("email")
        if email is not None and (not isinstance(email, str) or len(email) > 320):
            provider_unavailable()
        if email:
            result["emails"] = [{"value": email, "primary": True}]
        created = user.get("createdTimestamp")
        if created is not None:
            if type(created) is not int or created < 0:
                provider_unavailable()
            try:
                result["meta"]["created"] = datetime.fromtimestamp(
                    created / 1000, timezone.utc
                ).isoformat()
            except (OverflowError, ValueError, OSError):
                provider_unavailable()
        return result

    async def read(self, context, identity=None):
        base = self._base(context)
        async with httpx.AsyncClient(
            transport=self.transport,
            verify=settings.KEYCLOAK_VERIFY_TLS,
            timeout=10.0,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            headers = await self._token(client)
            if identity is not None:
                user = await self._json(
                    client,
                    "GET",
                    f"{base}/users/{identity}",
                    allow_missing=True,
                    headers=headers,
                )
                observed, tenant = self._membership(user)
                if observed != identity:
                    provider_unavailable()
                if tenant != context.tenant_id:
                    raise SCIMError(404, "User not found")
                return [self._resource(user)]
            ids, resources, first = set(), [], 0
            while True:
                page = await self._json(
                    client,
                    "GET",
                    f"{base}/users",
                    headers=headers,
                    params={"first": first, "max": 50, "briefRepresentation": "false"},
                )
                if not isinstance(page, list):
                    provider_unavailable()
                if not page:
                    break
                for user in page:
                    observed, tenant = self._membership(user)
                    if observed in ids:
                        provider_unavailable()
                    ids.add(observed)
                    if len(ids) > 100:
                        raise SCIMError(
                            400,
                            "SCIM directory observation exceeds 100 accounts",
                            "tooMany",
                        )
                    if tenant == context.tenant_id:
                        resources.append(self._resource(user))
                first += len(page)
            return sorted(resources, key=lambda user: user["id"])


class SCIMService:
    def __init__(self, db, context, *, directory=None):
        self.db, self.context = db, context
        self.directory = directory if directory is not None else SCIMDirectoryService()

    def _audit(self, operation, status, subject, count=0):
        try:
            AuditLogger(self.db).log_entitlement_event(
                "scim_read" if status == 200 else "scim_rejected",
                None,
                self.context.tenant_id,
                None,
                actor_type="internal_service",
                subject_id=subject,
                decision="allow" if status == 200 else "deny",
                changes={
                    "operation": operation,
                    "status": status,
                    "returned_count": count,
                    "provider_effects": [],
                },
                metadata={
                    "scim_client_id": str(self.context.client_id),
                    "directory_realm": self.context.realm,
                },
            )
            self.db.commit()
        except Exception as error:
            try:
                self.db.rollback()
            except Exception:
                pass
            raise SCIMError(503, "SCIM audit could not be confirmed") from error

    async def handle(self, operation, *, identity=None, query=()):
        subject, count = None, 0
        try:
            current_binding(self.context)
            if identity is not None:
                subject = resource_uuid(identity)
            if operation not in {"list_users", "get_user"}:
                raise SCIMError(
                    501, "SCIM provisioning and Group operations are not implemented"
                )
            if "users.read" not in self.context.permissions:
                raise SCIMError(403, "SCIM User read permission required")
            if subject is not None and query:
                raise SCIMError(
                    400, "Unsupported single-resource query", "invalidSyntax"
                )
            start, limit = query_parameters(query)
            users = await self.directory.read(self.context, subject)
            current_binding(self.context)
            if subject is None:
                page = users[start - 1 : start - 1 + limit]
                result = dict(
                    schemas=[LIST_SCHEMA],
                    totalResults=len(users),
                    itemsPerPage=len(page),
                    startIndex=start,
                    Resources=page,
                )
                count = len(page)
            else:
                if len(users) != 1:
                    provider_unavailable()
                result, count = users[0], 1
        except HTTPException as error:
            code = (
                error.status_code if error.status_code in {400, 403, 404, 501} else 503
            )
            self._audit(operation, code, subject)
            if isinstance(error, SCIMError):
                raise
            raise SCIMError(
                code,
                "User not found"
                if code == 404
                else "SCIM directory unavailable or unverified",
            ) from error
        except Exception as error:
            self._audit(operation, 503, subject)
            raise SCIMError(503, "SCIM directory unavailable or unverified") from error
        self._audit(operation, 200, subject, count)
        return result
