"""Mappings for the unchanged, separate IAM database V3 contract."""
import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.database import Base


class AccessRequest(Base):
    __tablename__ = "access_requests"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'denied', 'cancelled')", name="valid_status"),
        CheckConstraint("resource_id != ''", name="valid_resource_id"),
        {"schema": "public"},
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    requested_by = Column(UUID(as_uuid=True), nullable=False)
    requested_for = Column(UUID(as_uuid=True), nullable=True)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(255), nullable=False)
    action = Column(String(50), nullable=False)
    justification = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default='pending', server_default=text("'pending'"))
    reviewer_id = Column(UUID(as_uuid=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_comments = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    entitlement_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


Index('idx_access_requests_tenant', AccessRequest.tenant_id)
Index('idx_access_requests_requested_by', AccessRequest.requested_by)
Index('idx_access_requests_status', AccessRequest.status)
Index('idx_access_requests_reviewer', AccessRequest.reviewer_id)
Index('idx_access_requests_created_at', AccessRequest.created_at.desc())


class AccessRequestHistory(Base):
    __tablename__ = "access_request_history"
    __table_args__ = {"schema": "public"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    request_id = Column(UUID(as_uuid=True), ForeignKey('public.access_requests.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(String(50), nullable=False)
    performed_by = Column(UUID(as_uuid=True), nullable=False)
    performed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    comments = Column(Text, nullable=True)
    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    metadata_json = Column("metadata", JSONB, default=dict, server_default=text("'{}'::jsonb"))


Index('idx_access_request_history_request_id', AccessRequestHistory.request_id)
Index('idx_access_request_history_performed_at', AccessRequestHistory.performed_at.desc())
