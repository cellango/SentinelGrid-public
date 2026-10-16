"""Security event embedding model (vector store)."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class SecurityEventEmbedding(Base):
    __tablename__ = "security_event_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    source = Column(String, nullable=False, index=True)
    agent_id = Column(String, nullable=True)
    host_id = Column(String, nullable=True)
    os_id_ref = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    fields = Column(JSON, nullable=True)
    embedding = Column(Vector(dim=1024), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index(
            "idx_security_event_embeddings_unique",
            "tenant_id",
            "source",
            "os_id_ref",
            unique=True,
        ),
    )
