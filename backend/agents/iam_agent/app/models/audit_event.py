"""Additive IAM audit events; independent of incompatible legacy audit tables."""
import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class IAMAuditEvent(Base):
    __tablename__ = "iam_audit_events"
    __table_args__ = (
        CheckConstraint("actor_type IN ('user', 'internal_service')", name="iam_audit_actor_type"),
        CheckConstraint("actor_type <> 'user' OR performed_by IS NOT NULL", name="iam_audit_user_actor"),
        CheckConstraint("decision IS NULL OR decision IN ('allow', 'deny')", name="iam_audit_decision"),
        Index("ix_iam_audit_tenant_created", "tenant_id", "created_at"),
        {"schema": "public"},
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(String(50), nullable=False)
    entitlement_id = Column(UUID(as_uuid=True))
    performed_by = Column(UUID(as_uuid=True))
    actor_type = Column(String(30), nullable=False, default="user", server_default="user")
    subject_id = Column(UUID(as_uuid=True))
    decision = Column(String(10))
    performed_by_name = Column(String(255))
    changes = Column(JSONB, nullable=False, default=dict, server_default="{}")
    reason = Column(Text)
    campaign_id = Column(UUID(as_uuid=True))
    certification_id = Column(UUID(as_uuid=True))
    metadata_json = Column("metadata", JSONB, nullable=False, default=dict, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
