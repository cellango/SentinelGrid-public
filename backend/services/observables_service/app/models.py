"""Data models for Observables Service."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Index, JSON, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


# Enums
class ObservableType(str, Enum):
    """Types of observables supported."""
    USER_ID = "user_id"
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    HASH = "hash"
    EMAIL = "email"
    CVE = "cve"
    FILE_PATH = "file_path"
    PROCESS_NAME = "process_name"
    REGISTRY_KEY = "registry_key"


class EnrichmentStatus(str, Enum):
    """Status of enrichment process."""
    PENDING = "pending"
    ENRICHING = "enriching"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# SQLAlchemy Models
class Observable(Base):
    """Observable database model."""
    __tablename__ = "observables"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    observable_type = Column(String(50), nullable=False, index=True)
    value = Column(Text, nullable=False)
    source_event_id = Column(PGUUID(as_uuid=True), nullable=True)
    first_seen = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    tlp_level = Column(Integer, default=2)  # Traffic Light Protocol: 0=WHITE, 1=GREEN, 2=AMBER, 3=RED
    enrichment_status = Column(String(20), default="pending")
    enrichment_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    analyzers = relationship("ObservableAnalyzer", back_populates="observable", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_observables_tenant_type_value', 'tenant_id', 'observable_type', 'value', unique=True),
        Index('idx_observables_status', 'enrichment_status'),
    )


class ObservableAnalyzer(Base):
    """Observable analyzer job database model."""
    __tablename__ = "observable_analyzers"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    observable_id = Column(PGUUID(as_uuid=True), ForeignKey('observables.id'), nullable=False)
    analyzer_id = Column(String(100), nullable=False)
    cortex_job_id = Column(String(100), nullable=True)
    status = Column(String(20), default="pending")
    report = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    observable = relationship("Observable", back_populates="analyzers")
    
    __table_args__ = (
        Index('idx_analyzers_observable', 'observable_id'),
        Index('idx_analyzers_cortex_job', 'cortex_job_id'),
    )


# Pydantic Models (API)
class ObservableCreate(BaseModel):
    """Create observable request."""
    observable_type: ObservableType
    value: str
    source_event_id: Optional[UUID] = None
    tlp_level: int = Field(default=2, ge=0, le=3)
    auto_enrich: bool = True


class ObservableUpdate(BaseModel):
    """Update observable request."""
    tlp_level: Optional[int] = Field(default=None, ge=0, le=3)
    enrichment_status: Optional[EnrichmentStatus] = None
    enrichment_data: Optional[Dict[str, Any]] = None


class ObservableResponse(BaseModel):
    """Observable response."""
    id: UUID
    tenant_id: UUID
    observable_type: str
    value: str
    source_event_id: Optional[UUID]
    first_seen: datetime
    last_seen: datetime
    tlp_level: int
    enrichment_status: str
    enrichment_data: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AnalyzerJobResponse(BaseModel):
    """Analyzer job response."""
    id: UUID
    observable_id: UUID
    analyzer_id: str
    cortex_job_id: Optional[str]
    status: str
    report: Optional[Dict[str, Any]]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class EnrichmentRequest(BaseModel):
    """Request to enrich an observable."""
    observable_id: UUID
    analyzer_ids: Optional[List[str]] = None  # If None, use all applicable analyzers


class BulkObservableCreate(BaseModel):
    """Bulk create observables."""
    observables: List[ObservableCreate]


class ObservableSearchRequest(BaseModel):
    """Search observables."""
    observable_type: Optional[ObservableType] = None
    value: Optional[str] = None  # Partial match
    enrichment_status: Optional[EnrichmentStatus] = None
    source_event_id: Optional[UUID] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)

