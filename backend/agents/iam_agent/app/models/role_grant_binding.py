"""Service-owned grant provenance. Request metadata cannot create ownership."""

import uuid
from sqlalchemy import (
    Column,
    ForeignKey,
    DateTime,
    UniqueConstraint,
    Index,
    CheckConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class RoleGrantBinding(Base):
    __tablename__ = "iam_role_grants"
    __table_args__ = (
        UniqueConstraint("entitlement_id", name="iam_role_grant_unique"),
        CheckConstraint(
            "jsonb_typeof(target)='object' AND jsonb_typeof(roles)='array' AND jsonb_typeof(pattern_ids)='array'",
            name="iam_role_grant_json",
        ),
        {"schema": "public"},
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    subject_id = Column(UUID(as_uuid=True), nullable=False)
    entitlement_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "public.entitlements.id",
            name="iam_role_grant_entitlement",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    target = Column(JSONB, nullable=False)
    roles = Column(JSONB, nullable=False)
    pattern_ids = Column(JSONB, nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "ix_iam_role_grant_subject", RoleGrantBinding.tenant_id, RoleGrantBinding.subject_id
)
