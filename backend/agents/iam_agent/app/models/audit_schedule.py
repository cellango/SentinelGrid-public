"""Audit Schedule data model."""

from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class AuditSchedule(Base):
    """Audit Schedule model for automated campaign generation."""
    
    __tablename__ = "audit_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    entitlement_pattern = Column(Text, nullable=False)  # e.g., 'incident:*:write', 'alert:*:*'
    frequency = Column(String(50), nullable=False)  # 'daily', 'weekly', 'monthly', 'quarterly', 'annual'
    reviewer_type = Column(String(50), nullable=False)  # 'user', 'manager', 'admin'
    auto_revoke_days = Column(Integer, nullable=True)  # Default auto-revoke days
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

