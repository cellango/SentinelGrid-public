"""Entitlement data model."""

from sqlalchemy import Column, String, DateTime, Integer, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Entitlement(Base):
    """Entitlement model representing fine-grained access permissions."""
    
    __tablename__ = "entitlements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(255), nullable=False, index=True)  # '*' for wildcard
    action = Column(String(50), nullable=False)
    granted_to_type = Column(String(50), nullable=False)  # 'user', 'role', 'group'
    granted_to_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    granted_to_name = Column(String(255))  # Denormalized for performance
    status = Column(String(20), nullable=False, default='active', index=True)  # 'active', 'expired', 'revoked', 'pending_review'
    granted_by = Column(UUID(as_uuid=True), nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    usage_count_90d = Column(Integer, default=0)
    metadata_json = Column("metadata", JSON, default={})  # Column name in DB is 'metadata', but Python attribute avoids SQLAlchemy conflict
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        {'schema': 'public', 'postgresql_partition_by': None},  # Add partitioning later if needed
    )

