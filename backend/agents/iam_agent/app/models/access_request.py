"""Access Request data model."""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class AccessRequest(Base):
    """Access Request model for entitlement requests."""
    
    __tablename__ = "access_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    requested_by = Column(UUID(as_uuid=True), nullable=False, index=True)  # User requesting access
    requested_for = Column(UUID(as_uuid=True), nullable=True)  # User to grant access to (can be same as requested_by)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=False)  # '*' for wildcard
    action = Column(String(50), nullable=False)
    justification = Column(Text, nullable=False)  # Why access is needed
    status = Column(String(50), nullable=False, default='pending', index=True)  # 'pending', 'approved', 'denied', 'cancelled'
    reviewer_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Manager/admin who reviews
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_comments = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration for requested access
    entitlement_id = Column(UUID(as_uuid=True), nullable=True)  # Created entitlement ID (if approved)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class AccessRequestHistory(Base):
    """Access Request History model for audit trail."""
    
    __tablename__ = "access_request_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey('access_requests.id', ondelete='CASCADE'), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # 'created', 'submitted', 'approved', 'denied', 'cancelled', 'comment'
    performed_by = Column(UUID(as_uuid=True), nullable=False)
    performed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    comments = Column(Text, nullable=True)
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    metadata_json = Column("metadata", Text, default='{}')  # JSON stored as text

