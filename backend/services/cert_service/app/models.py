"""Certificate Service database models."""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, Integer, DateTime, ForeignKey, ARRAY, JSON,
    Index, Boolean
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from app.core.database import Base


class CAAuthority(Base):
    """Certificate Authority backend configuration."""
    __tablename__ = "ca_authorities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    type = Column(String(50), nullable=False)  # 'ejbca', 'step-ca', 'aws-acm-pca', etc.
    # For now, leave tenant_id nullable; older DBs may not have this column. We don't enforce FK here to avoid dependency on external metadata during startup.
    tenant_id = Column(UUID(as_uuid=True), nullable=True)  # NULL = shared CA
    ca_name = Column(String(255))  # EJBCA CA name (e.g., "SentinelGrid-Issuing-CA")
    certificate_profile = Column(String(100))  # Certificate profile name (e.g., "service-tls")
    config = Column(JSON, nullable=False)  # URLs, ARNs, credentials, etc.
    enrollment_protocols = Column(JSON)  # ['acme', 'scep', 'est']
    status = Column(String(50), nullable=False, default="active")  # 'active', 'disabled'
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    certificates = relationship("Certificate", back_populates="ca_authority")

    __table_args__ = (
        Index("idx_ca_authorities_name", "name"),
        Index("idx_ca_authorities_type", "type"),
        Index("idx_ca_authorities_status", "status"),
        Index("idx_ca_authorities_tenant_id", "tenant_id"),
    )


class Certificate(Base):
    """Issued X.509 certificate with metadata."""
    __tablename__ = "certificates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    serial_number = Column(String(255), nullable=False, unique=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    subject_cn = Column(String(255), nullable=False)
    dns_names = Column(ARRAY(Text), default=[])
    ip_addresses = Column(ARRAY(INET), default=[])
    spki_fingerprint = Column(String(255))  # SHA-256 fingerprint of public key
    usage = Column(String(50), nullable=False)  # 'service', 'agent'
    service_type = Column(String(100))  # 'siem-agent', 'iam-agent', 'orchestrator', etc.
    agent_id = Column(String(255))  # For agent certificates
    ca_authority_id = Column(UUID(as_uuid=True), ForeignKey("ca_authorities.id"), nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revocation_reason = Column(String(100))  # 'unspecified', 'key_compromise', 'superseded', etc.
    status = Column(String(50), nullable=False, default="issued")  # 'issued', 'revoked', 'expired'
    meta = Column("metadata", JSON)  # Additional metadata (CSR info, etc.)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    ca_authority = relationship("CAAuthority", back_populates="certificates")
    requests = relationship("CertificateRequest", back_populates="certificate")

    __table_args__ = (
        Index("idx_certificates_serial_number", "serial_number"),
        Index("idx_certificates_tenant_id", "tenant_id"),
        Index("idx_certificates_subject_cn", "subject_cn"),
        Index("idx_certificates_status", "status"),
        Index("idx_certificates_expires_at", "expires_at"),
        Index("idx_certificates_usage", "usage"),
        Index("idx_certificates_service_type", "service_type"),
        Index("idx_certificates_agent_id", "agent_id"),
        Index("idx_certificates_ca_authority_id", "ca_authority_id"),
    )


class CertificateRequest(Base):
    """Certificate enrollment requests for audit and tracking."""
    __tablename__ = "certificate_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certificate_id = Column(UUID(as_uuid=True), ForeignKey("certificates.id", ondelete="SET NULL"), nullable=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    requestor_type = Column(String(50), nullable=False)  # 'service', 'agent', 'admin'
    requestor_id = Column(String(255))  # Service name, agent ID, or user ID
    csr_pem = Column(Text)  # Certificate Signing Request (optional, for audit)
    dns_names = Column(ARRAY(Text), default=[])
    ip_addresses = Column(ARRAY(INET), default=[])
    ttl_hours = Column(Integer)  # Requested TTL
    status = Column(String(50), nullable=False, default="pending")  # 'pending', 'approved', 'rejected', 'issued'
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    certificate = relationship("Certificate", back_populates="requests")

    __table_args__ = (
        Index("idx_certificate_requests_certificate_id", "certificate_id"),
        Index("idx_certificate_requests_tenant_id", "tenant_id"),
        Index("idx_certificate_requests_status", "status"),
        Index("idx_certificate_requests_requestor", "requestor_type", "requestor_id"),
    )


class AgentBootstrapToken(Base):
    """One-time tokens for agent certificate enrollment."""
    __tablename__ = "agent_bootstrap_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False, unique=True)  # SHA-256 hash of token
    agent_id = Column(String(255))  # Optional: pre-assigned agent ID
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)  # When token was used for enrollment
    created_by = Column(UUID(as_uuid=True))  # User ID who created the token
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_agent_bootstrap_tokens_tenant_id", "tenant_id"),
        Index("idx_agent_bootstrap_tokens_token_hash", "token_hash"),
        Index("idx_agent_bootstrap_tokens_expires_at", "expires_at"),
    )
