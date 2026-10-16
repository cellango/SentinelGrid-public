"""Role Entitlement Pattern data model."""

from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class RoleEntitlementPattern(Base):
    """Role Entitlement Pattern model for mapping roles to entitlement patterns."""
    
    __tablename__ = "role_entitlement_patterns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_name = Column(String(255), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # NULL for global roles
    entitlement_pattern = Column(Text, nullable=False)  # e.g., 'alert:*:read', 'incident:*:write'
    auto_grant = Column(Boolean, nullable=False, default=True)  # Whether to auto-grant when role is assigned
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

