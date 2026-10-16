"""Certification data model."""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Certification(Base):
    """Certification model for entitlement reviews."""
    
    __tablename__ = "certifications"
    __table_args__ = {"schema": "public"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey('public.audit_campaigns.id', ondelete='CASCADE'), nullable=False, index=True)
    entitlement_id = Column(UUID(as_uuid=True), ForeignKey('public.entitlements.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # The user whose entitlement is being certified
    reviewer_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # The user performing the review
    review_status = Column(String(50), nullable=False, default='pending', index=True)  # 'pending', 'approved', 'revoked', 'retained'
    review_date = Column(DateTime(timezone=True), nullable=True)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

