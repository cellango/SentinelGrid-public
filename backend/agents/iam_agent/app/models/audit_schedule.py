"""Exact IAM V1 schedule mapping; no scheduler is enabled by this model."""

import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Integer,
    CheckConstraint,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class AuditSchedule(Base):
    __tablename__ = "audit_schedules"
    __table_args__ = (
        UniqueConstraint("tenant_id", "entitlement_pattern", name="unique_schedule"),
        CheckConstraint(
            "frequency IN ('monthly','quarterly','annual','continuous')",
            name="valid_frequency",
        ),
        CheckConstraint(
            "reviewer_type IN ('self','manager','admin')", name="valid_reviewer_type"
        ),
        {"schema": "public"},
    )
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    entitlement_pattern = Column(String(500), nullable=False)
    frequency = Column(String(50), nullable=False)
    reviewer_type = Column(String(50), nullable=False)
    auto_revoke_days = Column(
        Integer, nullable=False, default=30, server_default=text("30")
    )
    notification_config = Column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    enabled = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index("idx_schedules_tenant", AuditSchedule.tenant_id)
Index(
    "idx_schedules_enabled",
    AuditSchedule.tenant_id,
    AuditSchedule.enabled,
    postgresql_where=AuditSchedule.enabled == True,
)  # noqa: E712
