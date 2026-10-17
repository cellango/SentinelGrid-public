"""Owned user registrations and exact connector metadata reader grants, not issuance."""

from uuid import UUID
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sg_core.user_principals import UserClientBinding, UserPrincipalSettings


class ConnectorReader(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, hide_input_in_errors=True
    )
    issuer: str
    client_id: str
    tenant_id: str
    subject_id: str
    permission: Literal["connector.read_owned"]

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
            raise ValueError("Expected a canonical non-nil reader subject UUID")
        return self


class ConnectorPrincipalSettings(UserPrincipalSettings):
    CONNECTOR_METADATA_READERS: tuple[ConnectorReader, ...] = Field(
        default=(), max_length=256
    )

    @model_validator(mode="after")
    def owned_reader_registrations(self):
        registrations = {
            (b.issuer, b.client_id, b.tenant_id) for b in self.IAM_USER_CLIENT_BINDINGS
        }
        grants = [
            (b.issuer, b.client_id, b.tenant_id, b.subject_id)
            for b in self.CONNECTOR_METADATA_READERS
        ]
        if len(grants) != len(set(grants)):
            raise ValueError("Duplicate playbook reader grant")
        if any(grant[:3] not in registrations for grant in grants):
            raise ValueError("Reader requires an owned user-client registration")
        return self
