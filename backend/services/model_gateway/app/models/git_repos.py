"""Minimal Git repository models for knowledge ingestion."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class GitRepository(Base):
    __tablename__ = "git_repositories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=True)
    branch = Column(String, nullable=True)
    status = Column(String, default="active")
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GitIngestionJob(Base):
    __tablename__ = "git_ingestion_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String, default="pending")
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
