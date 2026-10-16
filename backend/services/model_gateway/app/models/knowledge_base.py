"""Cybersecurity knowledge base model for RAG."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class CybersecurityKnowledgeBase(Base):
    __tablename__ = "cybersecurity_knowledge_base"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    category = Column(String, nullable=False)
    subcategory = Column(String, nullable=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    # pgvector column for similarity search
    embedding = Column(Vector(dim=384))
    metadata_json = Column("metadata", JSON, nullable=True)
    source_url = Column(String, nullable=True)
    framework_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
