"""Asset model - physical and logical assets in infrastructure."""

from sqlalchemy import Column, String, Integer, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from . import Base


class Asset(Base):
    """Assets are concrete resources discovered in cloud/infrastructure."""
    
    __tablename__ = 'assets'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Asset identification
    asset_id = Column(String(512), nullable=False)  # External identifier (ARN, resource ID, etc.)
    asset_type = Column(String(100), nullable=False, index=True)  # aws_account, aws_s3_bucket, repo, image, etc.
    name = Column(String(500))
    
    # Location/ownership
    cloud_account_id = Column(String(255), index=True)
    region = Column(String(100))
    owner_team = Column(String(255))
    environment = Column(String(50))  # prod, staging, dev
    
    # Metadata
    tags = Column(JSONB)  # Cloud provider tags or custom tags
    metadata = Column(JSONB)  # Tool-specific data, properties
    
    # Risk scoring
    risk_score = Column(Integer, default=0)  # 0-100
    critical_findings_count = Column(Integer, default=0)
    high_findings_count = Column(Integer, default=0)
    medium_findings_count = Column(Integer, default=0)
    low_findings_count = Column(Integer, default=0)
    
    # Timestamps
    first_seen_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_assets_tenant_type', 'tenant_id', 'asset_type'),
        Index('idx_assets_unique', 'tenant_id', 'asset_type', 'asset_id', unique=True),
        Index('idx_assets_cloud_account', 'cloud_account_id'),
        Index('idx_assets_environment', 'environment'),
        Index('idx_assets_risk_score', 'risk_score'),
    )

