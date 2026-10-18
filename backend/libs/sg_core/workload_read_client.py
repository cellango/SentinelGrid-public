"""Disabled fixed-target machine read; no signing, provisioning, user delegation or writes.

The issuer owns static claims. The client never supplies request claims to the token
endpoint and checks the actual signed token with the existing IAM/read contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import hashlib
import json
import math
import re
import ssl
import time
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import HTTPException, Request
import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from sg_core.iam_verification import IAMVerificationSettings
from sg_core.workload_reads import (
    READ_CONTRACT,
    WorkloadReadBinding,
    WorkloadReadSettings,
    get_workload_read_context,
    service_audience,
)

if TYPE_CHECKING:
    from sg_core.workload_registration import (
        LocalCredentialLease,
        IssuerRegistrationReader,
    )

PATH = "/api/v1/tickets"
QUERY = b"status=open&limit=3"
_LIMIT = 131072


class FixedTicketReadSettings(BaseModel):
    """Operator configuration; never construct this from request/model arguments."""

    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, hide_input_in_errors=True
    )
    enabled: bool = False
    binding: WorkloadReadBinding
    service_origin: str
    timeout_seconds: float = Field(default=5.0, gt=0, le=10, allow_inf_nan=False)
    ca_bundle: str | None = None

    @model_validator(mode="after")
    def fixed_contract(self):
        b = self.binding
        if (
            b.service_id != "ticketing_service"
            or b.permission != "ticketing.read"
            or b.contract != READ_CONTRACT
        ):
            raise ValueError("Only the fixed ticket read is supported")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", b.client_id):
            raise ValueError("Expected an unambiguous client-credentials client ID")
        issuer = urlsplit(b.issuer)
        if issuer.scheme != "https":
            raise ValueError("Issuer transport requires HTTPS")
        p = urlsplit(self.service_origin)
        if (
            p.scheme != "https"
            or not p.hostname
            or p.port == 0
            or p.username is not None
            or p.password is not None
            or p.path not in {"", "/"}
            or p.query
            or p.fragment
            or "?" in self.service_origin
            or "#" in self.service_origin
            or "\\" in self.service_origin
            or "%" in self.service_origin
            or any(ord(c) < 33 or ord(c) == 127 for c in self.service_origin)
        ):
            raise ValueError("Expected an owned HTTPS service origin")
        if self.ca_bundle is not None and not self.ca_bundle.strip():
            raise ValueError("Expected an explicit CA file")
        return self


def keycloak_client_fragment(
    config: FixedTicketReadSettings, verifier_audience: str
) -> dict:
    """Review output only. Never imports/applies it or creates keys/credentials.

    Client stays disabled. Subject must be read back from the issuer-created service
    account and registered separately; it is never synthesized by a mapper.
    """
    if not isinstance(config, FixedTicketReadSettings) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", verifier_audience
    ):
        raise ValueError(
            "Owned fixed-read configuration and verifier audience required"
        )
    claims = {
        "tenant_id": config.binding.tenant_id,
        "sg_principal_type": "workload",
        "sg_identity_contract": READ_CONTRACT,
        "sg_permissions": ["ticketing.read"],
        "sg_request": {
            "service_id": "ticketing_service",
            "method": "GET",
            "path": PATH,
            "query_sha256": hashlib.sha256(QUERY).hexdigest(),
        },
    }
    mappers = []
    for name, value in claims.items():
        structured = isinstance(value, (dict, list))
        mappers.append(
            {
                "name": "sentinelgrid-" + name,
                "protocol": "openid-connect",
                "protocolMapper": "oidc-hardcoded-claim-mapper",
                "config": {
                    "claim.name": name,
                    "claim.value": json.dumps(
                        value, separators=(",", ":"), sort_keys=True
                    )
                    if structured
                    else value,
                    "jsonType.label": "JSON" if structured else "String",
                    "access.token.claim": "true",
                    "id.token.claim": "false",
                    "userinfo.token.claim": "false",
                    "access.tokenResponse.claim": "false",
                },
            }
        )
    for i, audience in enumerate(
        [verifier_audience, service_audience("ticketing_service")]
    ):
        mappers.append(
            {
                "name": "sentinelgrid-audience-" + str(i),
                "protocol": "openid-connect",
                "protocolMapper": "oidc-audience-mapper",
                "config": {
                    "included.custom.audience": audience,
                    "access.token.claim": "true",
                    "id.token.claim": "false",
                },
            }
        )
    return {
        "clientId": config.binding.client_id,
        "enabled": False,
        "protocol": "openid-connect",
        "publicClient": False,
        "clientAuthenticatorType": "client-secret",
        "bearerOnly": False,
        "serviceAccountsEnabled": True,
        "standardFlowEnabled": False,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "authorizationServicesEnabled": False,
        "fullScopeAllowed": False,
        "redirectUris": [],
        "webOrigins": [],
        "defaultClientScopes": [],
        "optionalClientScopes": [],
        "attributes": {
            "access.token.lifespan": "30",
            "use.refresh.tokens": "false",
            "client_credentials.use_refresh_token": "false",
            "standard.token.exchange.enabled": "false",
            "oauth2.jwt.authorization.grant.enabled": "false",
        },
        "protocolMappers": mappers,
    }


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise ValueError("Duplicate response field")
        result[key] = value
    return result


def _constant(_):
    raise ValueError("Non-finite response number")


def _float(value):
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("Non-finite response number")
    return parsed


def _response(response):
    if (
        response.status_code != 200
        or response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        != "application/json"
    ):
        raise ValueError("Upstream response unavailable")
    body = bytearray()
    for chunk in response.iter_bytes(chunk_size=8192):
        body.extend(chunk)
        if len(body) > _LIMIT:
            raise ValueError("Upstream response exceeds bounds")
    return json.loads(
        body, object_pairs_hook=_pairs, parse_constant=_constant, parse_float=_float
    )


class FixedTicketReadClient:
    """Machine-only reference caller. Fetch accepts no target, tenant or user input."""

    def __init__(
        self,
        config: FixedTicketReadSettings,
        secret: LocalCredentialLease,
        verifier: IAMVerificationSettings,
        *,
        registration: IssuerRegistrationReader | None = None,
    ):
        from sg_core.workload_registration import LocalCredentialLease

        if (
            not isinstance(config, FixedTicketReadSettings)
            or not isinstance(secret, LocalCredentialLease)
            or not isinstance(verifier, IAMVerificationSettings)
        ):
            raise ValueError("Typed owned caller configuration required")
        self._config = config
        self._credential_lease = secret
        self._registration = registration
        self._verifier = verifier

    def fetch(self) -> list[dict]:
        config = self._config
        if not config.enabled:
            raise HTTPException(503, "Fixed workload read is disabled")
        try:
            from sg_core.workload_registration import IssuerRegistrationReader

            if not isinstance(self._registration, IssuerRegistrationReader):
                raise ValueError("Owned issuer readback required")
            version, credential = self._credential_lease.snapshot(config.binding)
            observation = self._registration.inspect(config, self._verifier)
            if not observation.enabled:
                raise ValueError("Issuer client is disabled")
            self._credential_lease.require_current(config.binding, version)
            verify = (
                ssl.create_default_context(cafile=config.ca_bundle)
                if config.ca_bundle
                else True
            )
            with httpx.Client(
                timeout=httpx.Timeout(config.timeout_seconds, pool=1.0),
                verify=verify,
                trust_env=False,
                follow_redirects=False,
                limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
            ) as client:
                with client.stream(
                    "POST",
                    config.binding.issuer + "/protocol/openid-connect/token",
                    auth=httpx.BasicAuth(
                        config.binding.client_id, credential.get_secret_value()
                    ),
                    data={"grant_type": "client_credentials"},
                    headers={"Accept": "application/json"},
                ) as response:
                    value = _response(response)
                if (
                    not isinstance(value, dict)
                    or value.get("token_type") != "Bearer"
                    or type(value.get("expires_in")) is not int
                    or not 1 <= value["expires_in"] <= 60
                    or value.get("scope") not in (None, "")
                    or any(k in value for k in ("refresh_token", "id_token"))
                ):
                    raise ValueError("Unexpected machine token response")
                token = value.get("access_token")
                if (
                    not isinstance(token, str)
                    or not 1 <= len(token) <= 32768
                    or any(ord(c) > 127 for c in token)
                ):
                    raise ValueError("Machine token unavailable")
                state = SimpleNamespace(
                    iam_verification_settings=self._verifier,
                    workload_read_settings=WorkloadReadSettings(
                        _env_file=None,
                        ENVIRONMENT="production",
                        SERVICE_READ_WORKLOAD_BINDINGS=(config.binding,),
                    ),
                )
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": PATH,
                    "raw_path": PATH.encode("ascii"),
                    "query_string": QUERY,
                    "root_path": "",
                    "headers": [
                        (b"authorization", ("Bearer " + token).encode("ascii"))
                    ],
                    "app": SimpleNamespace(state=state),
                    "route": SimpleNamespace(path=PATH),
                }
                context = get_workload_read_context(Request(scope), "ticketing_service")
                if context.expires_at <= time.time() + 1:
                    raise ValueError("Machine token expires before dispatch")
                self._credential_lease.require_current(config.binding, version)
                client.cookies.clear()  # Issuer cookies must not cross into the data transport.
                with client.stream(
                    "GET",
                    config.service_origin.rstrip("/")
                    + PATH
                    + "?"
                    + QUERY.decode("ascii"),
                    headers={
                        "Accept": "application/json",
                        "Authorization": "Bearer " + token,
                    },
                ) as response:
                    result = _response(response)
                if not isinstance(result, list) or len(result) > 3:
                    raise ValueError("Unexpected ticket page")
                for row in result:
                    if (
                        not isinstance(row, dict)
                        or row.get("tenant_id") != config.binding.tenant_id
                    ):
                        raise ValueError("Unexpected ticket ownership")
                    resource = UUID(row.get("id"))
                    if not resource.int or str(resource) != row["id"]:
                        raise ValueError("Unexpected ticket identity")
                return result
        except (
            HTTPException,
            httpx.HTTPError,
            ValueError,
            TypeError,
            KeyError,
            OSError,
            OverflowError,
            RecursionError,
        ):
            raise HTTPException(503, "Fixed workload read unavailable") from None
