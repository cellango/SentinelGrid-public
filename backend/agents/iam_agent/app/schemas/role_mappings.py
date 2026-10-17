from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def parse_pattern(value):
    parts = value.split(":")
    if (
        len(value) > 500
        or len(parts) != 3
        or any(
            not p.strip() or ("*" in p and p != "*") or "{" in p or "}" in p
            for p in parts
        )
    ):
        raise ValueError("Use resource_type:resource_id:action with whole-field * only")
    if any(len(p) > limit for p, limit in zip(parts, (100, 255, 50))):
        raise ValueError("Pattern field exceeds grant storage")
    return tuple(parts)


class RolePatternCreate(BaseModel):
    role_name: str = Field(min_length=1, max_length=100)
    tenant_id: UUID | None = None
    entitlement_pattern: str
    auto_grant: bool = True
    created_by: UUID | None = None  # Compatibility input, never actor authority.

    @field_validator("role_name")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Role must be nonblank")
        return value

    @field_validator("entitlement_pattern")
    @classmethod
    def pattern(cls, value):
        parse_pattern(value)
        return value


class RolePatternUpdate(BaseModel):
    entitlement_pattern: str | None = None
    auto_grant: bool | None = None
    enabled: bool | None = None

    @model_validator(mode="after")
    def explicit(self):
        for name in self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError("Explicit null is unsupported")
        if self.entitlement_pattern is not None:
            parse_pattern(self.entitlement_pattern)
        return self


class RolePatternResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    role_name: str
    tenant_id: UUID | None
    entitlement_pattern: str
    auto_grant: bool
    enabled: bool
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime


class SyncUserRolesRequest(BaseModel):
    user_id: UUID
    tenant_id: UUID
    granted_by: UUID | None = None


class SyncRoleRequest(BaseModel):
    role_name: str = Field(min_length=1, max_length=100)
    tenant_id: UUID | None = None
    granted_by: UUID | None = None
