"""PostureScore model - calculated posture metrics."""

from sqlalchemy import Column, String, Integer, Numeric, Boolean, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from . import Base


class PostureScore(Base):
    """Calculated posture scores for different scopes."""
    
    __tablename__ = 'posture_scores'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Score scope
    scope_type = Column(String(50), nullable=False, index=True)  # tenant, cloud_account, repo, service, asset
    scope_id = Column(String(255), nullable=False, index=True)  # ID of the scope entity
    scope_name = Column(String(500))  # Friendly name
    
    # Score metrics
    score = Column(Numeric(5, 2), nullable=False)  # 0.00 - 100.00
    grade = Column(String(2))  # A, B, C, D, F
    
    # Findings breakdown
    findings_breakdown = Column(JSONB)  # {"critical": 2, "high": 5, "medium": 10, "low": 3, "info": 1}
    total_findings = Column(Integer, default=0)
    
    # Source breakdown (findings by source)
    source_breakdown = Column(JSONB)  # {"cspm": 10, "iac": 5, "secret_scan": 2, "dast": 3}
    
    # Risk indicators
    has_critical_findings = Column(Boolean, default=False)
    has_high_findings = Column(Boolean, default=False)
    
    # Trend data
    previous_score = Column(Numeric(5, 2))
    score_change = Column(Numeric(5, 2))  # Change since last calculation
    
    # Calculation metadata
    calculation_method = Column(String(50), default='weighted')  # weighted, simple, custom
    calculation_config = Column(JSONB)  # Config used for calculation
    
    # Timestamps
    calculated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_posture_scores_tenant_scope', 'tenant_id', 'scope_type', 'scope_id'),
        Index('idx_posture_scores_score', 'score'),
        Index('idx_posture_scores_grade', 'grade'),
        # Latest score per scope
        Index('idx_posture_scores_latest', 'tenant_id', 'scope_type', 'scope_id', 'calculated_at'),
    )

