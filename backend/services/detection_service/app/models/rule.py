"""Database models for detection rules."""

from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base


class DetectionRule(Base):
    """Detection rule model."""
    __tablename__ = "detection_rules"
    __table_args__ = {"schema": "security_ops"}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(String(50), nullable=False)  # failed_logins, new_admin, suspicious_cloud, etc.
    pattern = Column(JSON, nullable=False)  # Rule configuration/pattern
    enabled = Column(Boolean, nullable=False, default=True)
    severity = Column(String(20), nullable=False, default="medium")  # low, medium, high, critical
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
