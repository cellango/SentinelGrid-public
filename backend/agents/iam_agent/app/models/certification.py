"""Exact legacy IAM V1 certification storage; API aliases live in the adapter."""

import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class Certification(Base):
    __tablename__ = "certifications"
    __table_args__ = (
        UniqueConstraint("campaign_id", "entitlement_id", name="unique_certification"),
        CheckConstraint(
            "certifier_type IN ('self','manager','admin','delegated')",
            name="valid_certifier_type",
        ),
        CheckConstraint(
            "status IN ('pending','approved','revoked','questioned','deferred')",
            name="valid_certification_status",
        ),
        CheckConstraint(
            "decision IN ('approve','revoke','question','defer','modify') OR decision IS NULL",
            name="valid_decision",
        ),
        {"schema": "public"},
    )
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.audit_campaigns.id", name="fk_campaign", ondelete="CASCADE"),
        nullable=False,
    )
    entitlement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.entitlements.id", name="fk_entitlement", ondelete="CASCADE"),
        nullable=False,
    )
    certifier_id = Column(UUID(as_uuid=True), nullable=False)
    certifier_type = Column(String(50), nullable=False)
    certifier_name = Column(String(255))
    status = Column(
        String(50), nullable=False, default="pending", server_default=text("'pending'")
    )
    decision = Column(String(50))
    justification = Column(Text)
    decision_date = Column(DateTime(timezone=True))
    deadline = Column(DateTime(timezone=True), nullable=False)
    escalated_to = Column(UUID(as_uuid=True))
    escalation_reason = Column(Text)
    metadata_json = Column(
        "metadata", JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index("idx_certifications_campaign", Certification.campaign_id)
Index("idx_certifications_certifier", Certification.certifier_id, Certification.status)
Index(
    "idx_certifications_deadline",
    Certification.status,
    Certification.deadline,
    postgresql_where=Certification.status == "pending",
)
Index("idx_certifications_entitlement", Certification.entitlement_id)
