"""Owned service-wide runtime readers; no event ingestion or workload authority."""

from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sg_core.user_principals import UserClientBinding, UserPrincipalSettings


class RuntimeReader(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, hide_input_in_errors=True
    )
    issuer: str
    client_id: str
    tenant_id: str
    subject_id: str
    service: Literal["ingestion-service"]
    scope: Literal["service_runtime"]
    permission: Literal["ingestion.read_runtime"]

    @model_validator(mode="after")
    def exact_identity(self):
        UserClientBinding(
            issuer=self.issuer,
            client_id=self.client_id,
            tenant_id=self.tenant_id,
            contract="keycloak-user-v1",
            service_accounts_enabled=False,
            token_exchange_enabled=False,
        )
        subject = UUID(self.subject_id)
        if not subject.int or str(subject) != self.subject_id:
            raise ValueError("Expected a canonical non-nil runtime reader subject UUID")
        return self


class IngestionPrincipalSettings(UserPrincipalSettings):
    INGESTION_RUNTIME_READERS: tuple[RuntimeReader, ...] = Field(
        default=(), max_length=256
    )

    @model_validator(mode="after")
    def owned_runtime_readers(self):
        registrations = {
            (b.issuer, b.client_id, b.tenant_id) for b in self.IAM_USER_CLIENT_BINDINGS
        }
        grants = [
            (b.issuer, b.client_id, b.tenant_id, b.subject_id)
            for b in self.INGESTION_RUNTIME_READERS
        ]
        if len(grants) != len(set(grants)):
            raise ValueError("Duplicate runtime reader grant")
        if any(g[:3] not in registrations for g in grants):
            raise ValueError(
                "Runtime reader requires an owned user-client registration"
            )
        return self
