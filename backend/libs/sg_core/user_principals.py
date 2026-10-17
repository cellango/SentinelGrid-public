"""An explicit provider/client/tenant contract for user-facing dependencies.

No workload delegation or action capabilities are issued here. Operator-owned
bindings and provider-issued claims are both necessary; neither is sufficient.
"""

from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

USER_CONTRACT = "keycloak-user-v1"


class UserClientBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, hide_input_in_errors=True)
    issuer: str
    client_id: str
    tenant_id: str
    # Admission attests this owned registration policy; it does not inspect a live
    # provider or turn user-editable attributes into trusted principal claims.
    contract: Literal["keycloak-user-v1"]
    service_accounts_enabled: Literal[False]
    token_exchange_enabled: Literal[False]

    @field_validator("service_accounts_enabled", "token_exchange_enabled", mode="before")
    @classmethod
    def disabled_grants(cls, value):
        if value is not False:
            raise ValueError("Machine grants and exchange must be explicitly disabled")
        return value

    @model_validator(mode="after")
    def validate_binding(self):
        p = urlsplit(self.issuer)
        if (p.scheme not in {"http", "https"} or not p.hostname or p.username is not None
            or p.password is not None or p.query or p.fragment or "?" in self.issuer or "#" in self.issuer
            or "\\" in self.issuer or "%" in self.issuer or self.issuer != self.issuer.strip()
            or any(ord(c) < 33 or ord(c) == 127 for c in self.issuer)
            or "/realms/" not in p.path):
            raise ValueError("Expected an exact owned Keycloak issuer")
        if p.port == 0:
            raise ValueError("Invalid issuer port")
        realm = p.path.rsplit("/realms/", 1)[1]
        if not realm or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for c in realm) or realm in {".", ".."}:
            raise ValueError("Invalid issuer realm")
        if not self.client_id or "*" in self.client_id or len(self.client_id) > 128 or any(ord(c) < 33 or ord(c) == 127 for c in self.client_id):
            raise ValueError("Invalid client ID")
        if str(UUID(self.tenant_id)) != self.tenant_id or UUID(self.tenant_id).int == 0:
            raise ValueError("Expected canonical non-nil tenant UUID")
        return self


class UserPrincipalSettings(BaseSettings):
    ENVIRONMENT: str = "development"
    IAM_USER_CLIENT_BINDINGS: tuple[UserClientBinding, ...] = Field(default=(), max_length=256)
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore",
                                      frozen=True, hide_input_in_errors=True)

    @model_validator(mode="after")
    def unique_clients(self):
        # Exact registrations only; shared realms can bind several named tenants.
        keys = [(b.issuer, b.client_id, b.tenant_id) for b in self.IAM_USER_CLIENT_BINDINGS]
        if len(set(keys)) != len(keys):
            raise ValueError("Ambiguous user-client registration")
        if self.ENVIRONMENT.strip().lower() not in {"development", "test"}:
            if any(urlsplit(b.issuer).scheme != "https" for b in self.IAM_USER_CLIENT_BINDINGS):
                raise ValueError("User issuers require HTTPS outside local development")
        return self


@lru_cache(maxsize=1)
def get_user_principal_settings():
    return UserPrincipalSettings()


def require_user_binding(payload: dict, config: UserPrincipalSettings | None = None) -> UserClientBinding:
    try:
        config = config if config is not None else get_user_principal_settings()
    except (ValueError, TypeError, OSError):
        raise HTTPException(503, "User identity configuration unavailable") from None
    if not isinstance(config, UserPrincipalSettings) or not config.IAM_USER_CLIENT_BINDINGS:
        raise HTTPException(503, "User identity configuration unavailable")
    # These claims must come through the verified receipt, never a request header,
    # username, body principal field, session marker, or operator-asserted user ID.
    if (payload.get("sg_principal_type") != "user" or payload.get("sg_identity_contract") != USER_CONTRACT
        or payload.get("typ") != "Bearer" or any(k in payload for k in ("act", "may_act", "client_id"))):
        raise HTTPException(403, "User identity required")
    for binding in config.IAM_USER_CLIENT_BINDINGS:
        if (payload.get("iss"), payload.get("azp"), payload.get("tenant_id")) == (
            binding.issuer, binding.client_id, binding.tenant_id
        ):
            return binding
    raise HTTPException(403, "User identity required")
