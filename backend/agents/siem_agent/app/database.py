"""Database models for SIEM Agent metadata."""

from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class AlertMetadata(Base):
    """Alert metadata cache (denormalized from OpenSearch)."""
    __tablename__ = "siem_alert_metadata"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    alert_id = Column(String(255), nullable=False)  # OpenSearch document ID
    severity = Column(String(20), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    title = Column(Text, nullable=False)
    detection_rule_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(String(255), nullable=True)
    source_ip = Column(String(45), nullable=True)  # IPv6 compatible
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    assigned_to = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class QueryHistory(Base):
    """Query history for analytics."""
    __tablename__ = "siem_query_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    query_type = Column(String(50), nullable=False)
    query_params = Column(JSON, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    result_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())

