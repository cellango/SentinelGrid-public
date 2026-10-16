"""Observable model - entities that can be analyzed."""

from sqlalchemy import Column, String, Integer, TIMESTAMP, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
import enum
from . import Base


class ObservableType(str, enum.Enum):
    """Types of observables that can be analyzed."""
    
    # Cloud assets
    AWS_ACCOUNT = "aws_account"
    AWS_S3_BUCKET = "aws_s3_bucket"
    AWS_EC2_INSTANCE = "aws_ec2_instance"
    AWS_IAM_ROLE = "aws_iam_role"
    AWS_RDS_INSTANCE = "aws_rds_instance"
    AWS_LAMBDA_FUNCTION = "aws_lambda_function"
    
    AZURE_SUBSCRIPTION = "azure_subscription"
    AZURE_RESOURCE_GROUP = "azure_resource_group"
    AZURE_VM = "azure_vm"
    AZURE_STORAGE_ACCOUNT = "azure_storage_account"
    
    GCP_PROJECT = "gcp_project"
    GCP_COMPUTE_INSTANCE = "gcp_compute_instance"
    GCP_STORAGE_BUCKET = "gcp_storage_bucket"
    
    # Code & repos
    GIT_REPOSITORY = "git_repository"
    DOCKER_IMAGE = "docker_image"
    
    # Applications
    WEB_APPLICATION = "web_application"
    API_ENDPOINT = "api_endpoint"
    
    # Kubernetes
    K8S_CLUSTER = "k8s_cluster"
    K8S_NAMESPACE = "k8s_namespace"
    K8S_WORKLOAD = "k8s_workload"
    K8S_POD = "k8s_pod"


class Observable(Base):
    """An observable is any entity that can be analyzed by security tools."""
    
    __tablename__ = 'observables'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Observable identification
    observable_type = Column(
        SQLEnum(ObservableType, name='observable_type_enum'),
        nullable=False,
        index=True
    )
    observable_value = Column(String(1000), nullable=False)  # URL, ARN, image name, etc.
    
    # Observable metadata (type-specific data)
    metadata = Column(JSONB)  # e.g., {"environment": "prod", "region": "us-east-1"}
    tags = Column(JSONB)  # e.g., ["critical", "pci-scope", "prod"]
    
    # Analysis tracking
    last_analyzed_at = Column(TIMESTAMP(timezone=True))
    analysis_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    __table_args__ = (
        Index('idx_observables_tenant_type', 'tenant_id', 'observable_type'),
        Index('idx_observables_value', 'observable_value'),
        Index('idx_observables_last_analyzed', 'last_analyzed_at'),
    )

