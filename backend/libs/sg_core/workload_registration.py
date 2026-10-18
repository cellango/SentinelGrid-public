"""Read-only owned issuer observations and process-local credential leases.

No provider provisioning/enablement/rotation/revocation, secret-store persistence or
snapshot-as-authority API. Every enabled caller must obtain a fresh observation.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import secrets
from threading import Lock
import ssl
import time
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import HTTPException
import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from sg_core.iam_verification import IAMVerificationSettings, verify_iam_token
from sg_core.workload_reads import WorkloadReadBinding
from sg_core.workload_read_client import (
    FixedTicketReadSettings,
    keycloak_client_fragment,
    _response,
)

MANAGEMENT_CONTRACT = "keycloak-registration-read-v1"
MANAGEMENT_PERMISSION = "iam.read_workload_registration"


def _uuid(value):
    parsed = UUID(value)
    if not parsed.int or str(parsed) != value:
        raise ValueError("Canonical non-nil UUID required")
    return parsed


def _secret(value, *, limit=32768):
    if not isinstance(value, SecretStr):
        raise ValueError("Protected credential required")
    raw = value.get_secret_value()
    if not 1 <= len(raw) <= limit or any(ord(c) < 33 or ord(c) > 126 for c in raw):
        raise ValueError("Protected credential unavailable")
    return value


def _expiry(value):
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
        or value <= datetime.now(timezone.utc)
    ):
        raise ValueError("Future timezone-aware lease expiry required")
    return value


class LocalCredentialLease:
    """Local CAS/expiry/terminal revocation only; constructing one grants no permission."""

    def __init__(
        self,
        binding: WorkloadReadBinding,
        secret: SecretStr,
        *,
        version: int,
        expires_at: datetime,
    ):
        if (
            not isinstance(binding, WorkloadReadBinding)
            or type(version) is not int
            or not 1 <= version < 2**31
        ):
            raise ValueError("Owned credential lease required")
        self._binding = binding
        self._secret = _secret(secret, limit=4096)
        self._expires_at = _expiry(expires_at)
        self._version = version
        self._revoked = False
        self._lock = Lock()

    def _current(self, binding, version=None):
        if (
            binding != self._binding
            or self._revoked
            or self._secret is None
            or self._expires_at <= datetime.now(timezone.utc)
            or version is not None
            and (type(version) is not int or version != self._version)
        ):
            raise HTTPException(503, "Local credential lease unavailable")

    def snapshot(self, binding):
        with self._lock:
            self._current(binding)
            return self._version, self._secret

    def require_current(self, binding, version):
        with self._lock:
            self._current(binding, version)

    def revoke_locally(self, *, expected_version: int):
        with self._lock:
            if (
                self._revoked
                or type(expected_version) is not int
                or expected_version != self._version
            ):
                raise HTTPException(503, "Local credential version unavailable")
            self._version += 1
            self._revoked = True
            self._secret = None
            return self._version

    def replace_locally(
        self, secret: SecretStr, *, expected_version: int, expires_at: datetime
    ):
        secret = _secret(secret, limit=4096)
        expires_at = _expiry(expires_at)
        with self._lock:
            if (
                self._revoked
                or type(expected_version) is not int
                or expected_version != self._version
                or secrets.compare_digest(
                    secret.get_secret_value(), self._secret.get_secret_value()
                )
            ):
                raise HTTPException(503, "Fresh local credential version required")
            self._version += 1
            self._secret = secret
            self._expires_at = expires_at
            return self._version


class IssuerReadbackSettings(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, hide_input_in_errors=True
    )
    enabled: bool = False
    target: FixedTicketReadSettings
    client_uuid: str
    management_issuer: str
    management_client_id: str
    management_subject_id: str
    expected_client_enabled: bool = False
    timeout_seconds: float = Field(default=5.0, gt=0, le=10, allow_inf_nan=False)
    ca_bundle: str | None = None

    @model_validator(mode="after")
    def exact_owner(self):
        b = self.target.binding
        _uuid(self.client_uuid)
        _uuid(self.management_subject_id)
        # Reuse canonical issuer/client/subject validation without granting read authority.
        WorkloadReadBinding(
            issuer=self.management_issuer,
            client_id=self.management_client_id,
            subject_id=self.management_subject_id,
            tenant_id=b.tenant_id,
            service_id="ticketing_service",
            permission="ticketing.read",
            contract=b.contract,
        )
        if (
            self.management_issuer != b.issuer
            or self.management_client_id == b.client_id
            or self.management_subject_id == b.subject_id
            or "//" in urlsplit(b.issuer).path
            or any(p in {".", ".."} for p in urlsplit(b.issuer).path.split("/"))
        ):
            raise ValueError("Distinct same-issuer management registration required")
        if self.ca_bundle is not None and not self.ca_bundle.strip():
            raise ValueError("Explicit CA file required")
        return self


@dataclass(frozen=True)
class RegistrationObservation:
    client_uuid: str
    subject_id: str
    enabled: bool
    observed_at: float
    policy_sha256: str


def _mappers(value):
    if not isinstance(value, list) or len(value) > 20:
        raise ValueError("Mapper set unavailable")
    result = {}
    for row in value:
        if not isinstance(row, dict):
            raise ValueError("Mapper unavailable")
        if set(row) - {
            "id",
            "name",
            "protocol",
            "protocolMapper",
            "config",
            "consentRequired",
            "consentText",
        }:
            raise ValueError("Unreviewed mapper fields")
        if "id" in row:
            _uuid(row["id"])
        if row.get("consentRequired", False) is not False or row.get(
            "consentText"
        ) not in (None, ""):
            raise ValueError("Unreviewed mapper consent")
        name = row.get("name")
        config = row.get("config")
        if (
            not isinstance(name, str)
            or name in result
            or not isinstance(config, dict)
            or any(
                not isinstance(k, str) or not isinstance(v, str)
                for k, v in config.items()
            )
        ):
            raise ValueError("Ambiguous mapper")
        result[name] = {
            "protocol": row.get("protocol"),
            "protocolMapper": row.get("protocolMapper"),
            "config": config,
        }
    return result


def _empty_roles(value):
    if not isinstance(value, dict) or set(value) - {"realmMappings", "clientMappings"}:
        raise ValueError("Role mappings unavailable")
    if value.get("realmMappings", []) != [] or value.get("clientMappings", {}) != {}:
        raise ValueError("Unexpected role grants")


class IssuerRegistrationReader:
    """Exact authenticated GETs only. No mutable client lookup/name inference or fallback."""

    def __init__(
        self,
        config: IssuerReadbackSettings,
        management_token: SecretStr,
        verifier: IAMVerificationSettings,
    ):
        if not isinstance(config, IssuerReadbackSettings) or not isinstance(
            verifier, IAMVerificationSettings
        ):
            raise ValueError("Owned readback configuration required")
        if urlsplit(verifier.IAM_AGENT_URL).scheme != "https":
            raise ValueError("Readback verifier requires HTTPS")
        self._config = config
        self._token = _secret(management_token)
        self._verifier = verifier

    def inspect(
        self, target: FixedTicketReadSettings, verifier: IAMVerificationSettings
    ):
        c = self._config
        b = c.target.binding
        if not c.enabled or target != c.target or verifier != self._verifier:
            raise HTTPException(503, "Owned issuer readback unavailable")
        try:
            token = self._token.get_secret_value()
            p = verify_iam_token(token, config=verifier)
            now = time.time()
            aud = p.get("aud")
            aud = [aud] if isinstance(aud, str) else aud
            expected_target = {
                "issuer": b.issuer,
                "client_uuid": c.client_uuid,
                "client_id": b.client_id,
                "subject_id": b.subject_id,
                "tenant_id": b.tenant_id,
            }
            roles = p.get("resource_access", {})
            if (
                p.get("iss") != c.management_issuer
                or p.get("azp") != c.management_client_id
                or p.get("sub") != c.management_subject_id
                or p.get("tenant_id") != b.tenant_id
                or p.get("typ") != "Bearer"
                or p.get("sg_principal_type") != "workload"
                or p.get("sg_identity_contract") != MANAGEMENT_CONTRACT
                or p.get("sg_permissions") != [MANAGEMENT_PERMISSION]
                or p.get("sg_registration_target") != expected_target
                or any(k in p for k in ("act", "may_act", "sg_actor", "client_id"))
                or not isinstance(aud, list)
                or len(aud) != 2
                or set(aud) != {verifier.KEYCLOAK_CLIENT_ID, "realm-management"}
                or p.get("roles") != []
                or p.get("scope") not in (None, "")
                or roles
                != {"realm-management": {"roles": ["view-clients", "view-users"]}}
                or p["exp"] - p["iat"] > 60
                or now - p["iat"] > 60
                or p["exp"] <= now + 1
            ):
                raise ValueError("Management identity unavailable")
            _uuid(p.get("jti"))
            base, realm = b.issuer.rsplit("/realms/", 1)
            prefix = base + "/admin/realms/" + realm
            client_path = "/clients/" + c.client_uuid
            user_path = "/users/" + b.subject_id
            verify = (
                ssl.create_default_context(cafile=c.ca_bundle) if c.ca_bundle else True
            )
            with httpx.Client(
                timeout=httpx.Timeout(c.timeout_seconds, pool=1.0),
                verify=verify,
                trust_env=False,
                follow_redirects=False,
                limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
            ) as client:

                def get(path):
                    if p["exp"] <= time.time() + 1:
                        raise ValueError("Management credential expired")
                    client.cookies.clear()
                    with client.stream(
                        "GET",
                        prefix + path,
                        headers={
                            "Accept": "application/json",
                            "Authorization": "Bearer " + token,
                        },
                    ) as r:
                        return _response(r)

                actual = get(client_path)
                expected = keycloak_client_fragment(
                    c.target, verifier.KEYCLOAK_CLIENT_ID
                )
                expected["enabled"] = c.expected_client_enabled
                if not isinstance(actual, dict) or actual.get("id") != c.client_uuid:
                    raise ValueError("Client identity unavailable")
                for name, value in expected.items():
                    if name == "protocolMappers":
                        continue
                    if (
                        name not in actual
                        or type(actual[name]) is not type(value)
                        or actual[name] != value
                    ):
                        raise ValueError("Client policy drift")
                if actual.get(
                    "authenticationFlowBindingOverrides", {}
                ) != {} or actual.get("authorizationSettings") not in (None, {}):
                    raise ValueError("Unreviewed client policy")
                mappers = get(client_path + "/protocol-mappers/models")
                if _mappers(mappers) != _mappers(expected["protocolMappers"]):
                    raise ValueError("Mapper drift")
                if "protocolMappers" in actual and _mappers(
                    actual["protocolMappers"]
                ) != _mappers(mappers):
                    raise ValueError("Conflicting mapper snapshots")
                # Never call /service-account-user: stock24 can create an account on GET.
                # Require provider-observed association; UUID/name alone is not proof.
                # Stock24 user GET omits this field and therefore fails closed.
                user = get(user_path)
                if (
                    not isinstance(user, dict)
                    or user.get("id") != b.subject_id
                    or user.get("enabled") is not True
                    or user.get("serviceAccountClientId") != b.client_id
                    or user.get("username") != "service-account-" + b.client_id
                ):
                    raise ValueError("Service-account ownership unavailable")
                attrs = user.get("attributes", {})
                if not isinstance(attrs, dict) or attrs.get(
                    "tenant_id", [b.tenant_id]
                ) != [b.tenant_id]:
                    raise ValueError("Conflicting tenant attribution")
                for path in [
                    client_path + "/default-client-scopes",
                    client_path + "/optional-client-scopes",
                    user_path + "/groups",
                    user_path + "/role-mappings/realm/composite",
                ]:
                    if get(path) != []:
                        raise ValueError("Unexpected inherited scopes or roles")
                _empty_roles(get(client_path + "/scope-mappings"))
                _empty_roles(get(user_path + "/role-mappings"))
                if p["exp"] <= time.time() + 1:
                    raise ValueError("Expired readback")
            digest = hashlib.sha256(
                json.dumps(
                    {
                        "client_uuid": c.client_uuid,
                        "subject_id": b.subject_id,
                        "policy": expected,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            return RegistrationObservation(
                c.client_uuid,
                b.subject_id,
                c.expected_client_enabled,
                time.time(),
                digest,
            )
        except (
            HTTPException,
            httpx.HTTPError,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            OSError,
            OverflowError,
            RecursionError,
        ):
            raise HTTPException(503, "Owned issuer readback unavailable") from None
