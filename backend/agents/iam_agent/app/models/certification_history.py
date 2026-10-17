"""Exact legacy V1 history; V015 additionally guards the certification/grant link."""

import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base


class CertificationHistory(Base):
    __tablename__ = "certification_history"
    __table_args__ = {"schema": "public"}
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    certification_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "public.certifications.id", name="fk_certification", ondelete="CASCADE"
        ),
        nullable=False,
    )
    entitlement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.entitlements.id", name="fk_entitlement", ondelete="CASCADE"),
        nullable=False,
    )
    previous_status = Column(String(50))
    new_status = Column(String(50))
    decision = Column(String(50))
    changed_by = Column(UUID(as_uuid=True), nullable=False)
    changed_by_name = Column(String(255))
    changed_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reason = Column(Text)


Index("idx_cert_history_certification", CertificationHistory.certification_id)
Index("idx_cert_history_entitlement", CertificationHistory.entitlement_id)
Index("idx_cert_history_changed_at", CertificationHistory.changed_at)
