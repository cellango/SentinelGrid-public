"""Deployment-owned SCIM client identities; no request can extend these grants."""

import re
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class SCIMClientBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    tenant_id: UUID
    realm: str = Field(min_length=1, max_length=100)
    credential_digest: SecretStr
    permissions: frozenset[Literal["users.read"]] = frozenset()

    @field_validator("realm")
    @classmethod
    def safe_realm(cls, value):
        if value in {".", ".."} or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", value):
            raise ValueError("SCIM realm must be an explicit safe realm name")
        return value

    @field_validator("credential_digest")
    @classmethod
    def sha256_digest(cls, value):
        if not re.fullmatch(r"[0-9a-f]{64}", value.get_secret_value()):
            raise ValueError("A SHA256 credential digest is required")
        return value


def validate_scim_bindings(value):
    if len(value) > 64:
        raise ValueError("At most 64 SCIM client bindings are supported")
    digests, realms = set(), {}
    for client, binding in value.items():
        if str(UUID(client)) != client:
            raise ValueError("SCIM client identifiers must be canonical UUID strings")
        digest = binding.credential_digest.get_secret_value()
        if digest in digests:
            raise ValueError("SCIM credentials must identify exactly one client")
        digests.add(digest)
        prior = realms.setdefault(binding.tenant_id, binding.realm)
        if prior != binding.realm:
            raise ValueError("SCIM clients for one tenant must bind the same realm")
    return value
