"""Public governance DTOs; storage retains the separate IAM V1 JSON contract."""

from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, BaseModel, Field, field_validator, model_validator


class CampaignCreate(BaseModel):
    tenant_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    start_date: AwareDatetime
    end_date: AwareDatetime
    reviewer_type: Literal["self", "manager", "admin"]
    auto_revoke_days: int | None = Field(None, ge=0, le=3650)
    entitlement_patterns: list[str] | None = Field(default_factory=list, max_length=100)

    @field_validator("name")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Name must be nonblank")
        return value

    @field_validator("entitlement_patterns")
    @classmethod
    def patterns(cls, values):
        for value in values or []:
            parts = value.split(":")
            if (
                len(value) > 500
                or len(parts) != 3
                or any(
                    not part.strip() or ("*" in part and part != "*") for part in parts
                )
            ):
                raise ValueError(
                    "Use resource_type:resource_id:action with whole-field * only"
                )
        return values or []

    @model_validator(mode="after")
    def dates(self):
        if self.end_date <= self.start_date:
            raise ValueError("End date must follow start date")
        return self


class CampaignUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    start_date: AwareDatetime | None = None
    end_date: AwareDatetime | None = None
    status: Literal["pending", "cancelled"] | None = None
    reviewer_type: Literal["self", "manager", "admin"] | None = None
    auto_revoke_days: int | None = Field(None, ge=0, le=3650)

    @model_validator(mode="after")
    def required_values(self):
        for field in self.model_fields_set - {"description", "auto_revoke_days"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        if self.name is not None:
            CampaignCreate.nonblank(self.name)
        return self


class CampaignResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str | None
    start_date: datetime
    end_date: datetime
    status: str
    reviewer_type: str
    auto_revoke_days: int | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class CertificationResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    entitlement_id: UUID
    user_id: UUID
    reviewer_id: UUID
    review_status: str
    review_date: datetime | None
    comments: str | None
    created_at: datetime
    updated_at: datetime


class CertificationDecision(BaseModel):
    decision: Literal["approved", "revoked", "retained"]
    comments: str | None = Field(None, max_length=10000)


class BulkCertificationDecision(CertificationDecision):
    certification_ids: list[UUID] = Field(min_length=1, max_length=500)

    @field_validator("certification_ids")
    @classmethod
    def distinct(cls, values):
        if len(values) != len(set(values)):
            raise ValueError("Certification IDs must be distinct")
        return values
