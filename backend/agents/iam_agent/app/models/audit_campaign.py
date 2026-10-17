"""Legacy IAM V1 campaign storage, with V015's additive update timestamp."""

import uuid
from sqlalchemy import Column, String, DateTime, Text, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class AuditCampaign(Base):
    __tablename__ = "audit_campaigns"
    __table_args__ = (
        CheckConstraint(
            "campaign_type IN ('scheduled','on_demand','continuous','event_triggered')",
            name="valid_campaign_type",
        ),
        CheckConstraint(
            "status IN ('draft','scheduled','active','in_review','completed','cancelled')",
            name="valid_campaign_status",
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
    name = Column(String(255), nullable=False)
    description = Column(Text)
    campaign_type = Column(String(50), nullable=False)
    status = Column(
        String(50), nullable=False, default="draft", server_default=text("'draft'")
    )
    scope = Column(JSONB, nullable=False)
    review_config = Column(JSONB, nullable=False)
    schedule = Column(JSONB, nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    statistics = Column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index("idx_campaigns_tenant", AuditCampaign.tenant_id)
Index("idx_campaigns_status", AuditCampaign.status)
Index(
    "idx_campaigns_schedule",
    AuditCampaign.tenant_id,
    AuditCampaign.status,
    text("(schedule->>'start_date')"),
)
