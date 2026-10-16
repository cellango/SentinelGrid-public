"""Finding model - unified security findings from all analyzers."""

from sqlalchemy import Column, String, Text, TIMESTAMP, Index, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from . import Base


class FindingSource(str, enum.Enum):
    """Source types for findings."""
    CSPM = "cspm"  # Cloud Security Posture Management
    IAC = "iac"  # Infrastructure as Code
    SECRET_SCAN = "secret_scan"  # Secrets detection
    SAST = "sast"  # Static Application Security Testing
    DAST = "dast"  # Dynamic Application Security Testing
    SCA = "sca"  # Software Composition Analysis
    IMAGE_SCAN = "image_scan"  # Container image scanning
    RUNTIME = "runtime"  # Runtime security (Falco, etc.)


class FindingSeverity(str, enum.Enum):
    """Finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingStatus(str, enum.Enum):
    """Finding status."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ACCEPTED = "accepted"  # Risk accepted
    FIXED = "fixed"
    FALSE_POSITIVE = "false_positive"


class Finding(Base):
    """Unified findings from all security analyzers/tools."""
    
    __tablename__ = 'findings'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Related asset
    asset_id = Column(UUID(as_uuid=True), ForeignKey('assets.id', ondelete='CASCADE'), index=True)
    
    # Finding identification
    finding_id = Column(String(512), nullable=False)  # Unique per tool
    source = Column(SQLEnum(FindingSource, name='finding_source_enum'), nullable=False, index=True)
    tool = Column(String(50), nullable=False, index=True)  # prowler, zap, trivy, etc.
    scan_id = Column(UUID(as_uuid=True), ForeignKey('analyzer_jobs.id', ondelete='SET NULL'))
    
    # Tool-specific identifiers
    check_id = Column(String(255))  # Tool-specific check/rule ID
    control_id = Column(String(255))  # Normalized control (optional)
    
    # Finding details
    title = Column(String(1000), nullable=False)
    description = Column(Text)
    severity = Column(SQLEnum(FindingSeverity, name='finding_severity_enum'), nullable=False, index=True)
    status = Column(SQLEnum(FindingStatus, name='finding_status_enum'), nullable=False, default=FindingStatus.OPEN, index=True)
    
    # Compliance & frameworks
    framework_refs = Column(JSONB)  # {"cis": ["1.1", "1.2"], "nist": ["AC-2"], "soc2": ["CC6.1"]}
    
    # Evidence & context
    evidence = Column(JSONB)  # Full tool output, resource details, etc.
    remediation = Column(Text)  # Remediation guidance
    
    # Observable context (for correlation)
    observable_type = Column(String(100))
    observable_value = Column(String(1000))
    
    # Timestamps
    first_seen_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    resolved_at = Column(TIMESTAMP(timezone=True))
    resolved_by = Column(UUID(as_uuid=True))  # User ID
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    asset = relationship("Asset", backref="findings")
    
    __table_args__ = (
        Index('idx_findings_tenant_severity', 'tenant_id', 'severity', 'status'),
        Index('idx_findings_source_tool', 'source', 'tool'),
        Index('idx_findings_unique', 'tenant_id', 'source', 'tool', 'finding_id', unique=True),
        Index('idx_findings_asset', 'asset_id'),
        Index('idx_findings_scan', 'scan_id'),
        Index('idx_findings_observable', 'observable_type', 'observable_value'),
    )

