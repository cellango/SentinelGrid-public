"""CloudAccount model - track connected cloud accounts."""

from sqlalchemy import Column, String, Text, Integer, Numeric, Boolean, TIMESTAMP, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
import enum
from . import Base


class CloudProvider(str, enum.Enum):
    """Cloud provider types."""
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    ALIBABA = "alibaba"
    ORACLE = "oracle"


class AccountStatus(str, enum.Enum):
    """Cloud account status."""
    PENDING = "pending"
    CONNECTED = "connected"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class CloudAccount(Base):
    """Connected cloud accounts for scanning."""
    
    __tablename__ = 'cloud_accounts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Provider details
    provider = Column(SQLEnum(CloudProvider, name='cloud_provider_enum'), nullable=False, index=True)
    account_id = Column(String(255), nullable=False, index=True)  # AWS Account ID, Azure Subscription ID, etc.
    account_name = Column(String(255))  # Friendly name
    
    # Authentication (AWS)
    role_arn = Column(String(512))  # For AWS cross-account role
    external_id = Column(String(255))  # External ID for AWS role assumption
    
    # Authentication (Azure/GCP)
    credentials_encrypted = Column(Text)  # Encrypted service principal credentials/key
    
    # Account metadata
    environment = Column(String(50))  # prod, staging, dev
    tags = Column(JSONB)
    regions = Column(JSONB)  # List of regions to scan
    
    # Status
    status = Column(SQLEnum(AccountStatus, name='account_status_enum'), nullable=False, default=AccountStatus.PENDING, index=True)
    status_message = Column(Text)
    last_connection_test = Column(TIMESTAMP(timezone=True))
    
    # Scanning
    scan_enabled = Column(Boolean, default=True)
    scan_schedule = Column(String(100))  # Cron expression
    last_scan_at = Column(TIMESTAMP(timezone=True), index=True)
    next_scan_at = Column(TIMESTAMP(timezone=True))
    
    # Statistics
    total_assets = Column(Integer, default=0)
    total_findings = Column(Integer, default=0)
    last_posture_score = Column(Numeric(5, 2))
    
    # Configuration
    scan_config = Column(JSONB)  # Provider-specific scan configuration
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_cloud_accounts_tenant_provider', 'tenant_id', 'provider'),
        Index('idx_cloud_accounts_unique', 'tenant_id', 'provider', 'account_id', unique=True),
        Index('idx_cloud_accounts_scan', 'scan_enabled', 'next_scan_at'),
    )

