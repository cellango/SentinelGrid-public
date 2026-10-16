"""Database models for connectors."""

from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base


class ConnectorConfig(Base):
    """Connector configuration model."""
    __tablename__ = "connector_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # google_workspace, microsoft_entra, okta, aws
    name = Column(String(255), nullable=False)
    credentials = Column(JSON, nullable=False)  # Encrypted credentials
    sync_settings = Column(JSON, nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="active")  # active, error, paused
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

