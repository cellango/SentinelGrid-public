"""Repository model - track code repositories."""

from sqlalchemy import Column, String, Boolean, Integer, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from . import Base


class Repository(Base):
    """Code repositories for scanning."""
    
    __tablename__ = 'repositories'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Repository identification
    repo_url = Column(String(1000), nullable=False, index=True)
    repo_name = Column(String(500), nullable=False)
    provider = Column(String(50))  # github, gitlab, bitbucket, azure_devops
    
    # Repository details
    default_branch = Column(String(100), default='main')
    is_public = Column(Boolean, default=False)
    
    # Content detection (for smart analyzer selection)
    has_terraform = Column(Boolean, default=False)
    has_cloudformation = Column(Boolean, default=False)
    has_kubernetes_manifests = Column(Boolean, default=False)
    has_dockerfile = Column(Boolean, default=False)
    programming_languages = Column(JSONB)  # ["python", "javascript", "go"]
    
    # Scanning
    scan_enabled = Column(Boolean, default=True)
    scan_on_push = Column(Boolean, default=True)
    scan_schedule = Column(String(100))  # Cron expression for periodic scans
    last_scan_at = Column(TIMESTAMP(timezone=True), index=True)
    last_commit_sha = Column(String(40))
    
    # Statistics
    total_findings = Column(Integer, default=0)
    critical_findings = Column(Integer, default=0)
    secrets_found = Column(Integer, default=0)
    iac_issues = Column(Integer, default=0)
    
    # Metadata
    tags = Column(JSONB)
    metadata = Column(JSONB)  # Additional repo metadata
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_repositories_tenant', 'tenant_id'),
        Index('idx_repositories_unique', 'tenant_id', 'repo_url', unique=True),
        Index('idx_repositories_scan', 'scan_enabled', 'last_scan_at'),
        Index('idx_repositories_provider', 'provider'),
    )

