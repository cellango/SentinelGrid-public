"""IAM-local registry contracts; inputs cannot choose tenant, owner or authority."""

from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

AccountStatus = Literal["active", "inactive", "deleted"]


class CreateServiceAccountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4096)
    rotation_days: int = Field(default=90, ge=1, le=365, strict=True)

    @field_validator("name")
    @classmethod
    def nonblank(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError("A nonblank printable account name is required")
        return value


class LifecycleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1, le=2147483646, strict=True)
    reason: str | None = Field(default=None, max_length=1000)


class ServiceAccountResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    client_id: str
    owner_user_id: UUID
    created_by: UUID
    status: AccountStatus
    rotation_days: int
    credential_version: int
    credential_expires_at: datetime | None
    credential_expired: bool
    created_at: datetime
    updated_at: datetime
    credential_scope: Literal["local_registry_only"] = "local_registry_only"
    provider_status: Literal["not_integrated"] = "not_integrated"


class IssuedCredentialResponse(ServiceAccountResponse):
    client_secret: str = Field(repr=False)
