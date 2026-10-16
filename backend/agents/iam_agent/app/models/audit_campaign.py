"""Audit Campaign data model."""

from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class AuditCampaign(Base):
    """Audit Campaign model for access review campaigns."""
    
    __tablename__ = "audit_campaigns"
    __table_args__ = {"schema": "public"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(50), nullable=False, default='pending', index=True)  # 'pending', 'in_progress', 'completed', 'cancelled'
    reviewer_type = Column(String(50), nullable=False)  # 'user', 'manager', 'admin'
    auto_revoke_days = Column(Integer, nullable=True)  # Days after end_date to auto-revoke
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

