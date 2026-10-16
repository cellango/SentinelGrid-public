"""Minimal database models to support training/adapter metadata."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class TenantTrainingData(Base):
    __tablename__ = "tenant_training_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    module = Column(String, nullable=True)
    data_type = Column(String, nullable=True)
    raw_data = Column(JSON, nullable=True)
    processed_data = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TenantModelAdapter(Base):
    __tablename__ = "tenant_model_adapters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    adapter_version = Column(String, nullable=True)
    adapter_path = Column(String, nullable=True)
    base_model_name = Column(String, nullable=True)
    base_model_version = Column(String, nullable=True)
    training_data_count = Column(Integer, default=0)
    training_config = Column(JSON, nullable=True)
    performance_metrics = Column(JSON, nullable=True)
    status = Column(String, default="active")
    trained_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AdapterVersionHistory(Base):
    __tablename__ = "adapter_version_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    adapter_version = Column(String, nullable=True)
    adapter_path = Column(String, nullable=True)
    base_model_name = Column(String, nullable=True)
    base_model_version = Column(String, nullable=True)
    training_data_count = Column(Integer, default=0)
    training_config = Column(JSON, nullable=True)
    performance_metrics = Column(JSON, nullable=True)
    status = Column(String, default="archived")
    trained_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow)


class AdapterTrainingJob(Base):
    __tablename__ = "adapter_training_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String, default="pending")
    error_message = Column(Text, nullable=True)
    config = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TrainingDataSnapshot(Base):
    __tablename__ = "training_data_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
