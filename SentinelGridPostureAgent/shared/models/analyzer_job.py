"""AnalyzerJob model - track analyzer execution jobs."""

from sqlalchemy import Column, String, Text, Integer, TIMESTAMP, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
import enum
from . import Base


class JobStatus(str, enum.Enum):
    """Analyzer job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalyzerJob(Base):
    """Track analyzer execution jobs."""
    
    __tablename__ = 'analyzer_jobs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Job details
    job_type = Column(String(50), nullable=False)  # 'analyze_observable', 'scheduled_scan', etc.
    analyzer_name = Column(String(100), nullable=False, index=True)  # prowler-aws-cspm, zap-dast, etc.
    
    # Observable being analyzed
    observable_id = Column(UUID(as_uuid=True))
    observable_type = Column(String(100), index=True)
    observable_value = Column(String(1000))
    
    # Job configuration
    config = Column(JSONB)  # Analyzer-specific config
    
    # Execution status
    status = Column(SQLEnum(JobStatus, name='job_status_enum'), nullable=False, default=JobStatus.PENDING, index=True)
    progress_percent = Column(Integer, default=0)  # 0-100
    
    # Timing
    queued_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(TIMESTAMP(timezone=True))
    finished_at = Column(TIMESTAMP(timezone=True))
    duration_seconds = Column(Integer)
    
    # Results
    findings_count = Column(JSONB)  # {"critical": 2, "high": 5, "medium": 10, "low": 3}
    error_message = Column(Text)
    result_metadata = Column(JSONB)  # Tool-specific result metadata
    
    # Worker info
    worker_id = Column(String(100))
    worker_hostname = Column(String(255))
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_analyzer_jobs_tenant_status', 'tenant_id', 'status'),
        Index('idx_analyzer_jobs_observable', 'observable_type', 'observable_value'),
        Index('idx_analyzer_jobs_analyzer', 'analyzer_name', 'status'),
        Index('idx_analyzer_jobs_queued', 'queued_at'),
    )

