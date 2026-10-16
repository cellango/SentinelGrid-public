"""Pydantic schemas for Certificate Service."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class IssueCertRequest(BaseModel):
    """Request to issue a certificate."""
    service_id: Optional[str] = None
    service_type: Optional[str] = None  # 'siem-agent', 'iam-agent', etc.
    tenant_id: Optional[UUID] = None
    agent_id: Optional[str] = None
    subject_cn: str
    dns_names: List[str] = Field(default_factory=list)
    ip_addresses: List[str] = Field(default_factory=list)
    ttl_hours: Optional[int] = None
    csr_pem: Optional[str] = None  # If provided, use this CSR instead of generating keypair


class IssueCertResponse(BaseModel):
    """Response with issued certificate."""
    certificate_id: UUID
    certificate_pem: str
    private_key_pem: Optional[str] = None  # Only if Cert Service generated the keypair
    ca_chain_pem: str
    serial_number: str
    expires_at: datetime
    spki_fingerprint: str


class RenewCertRequest(BaseModel):
    """Request to renew a certificate."""
    certificate_id: Optional[UUID] = None  # If provided, renew this cert
    # If not provided, will use client certificate for mTLS


class RenewCertResponse(BaseModel):
    """Response with renewed certificate."""
    certificate_id: UUID
    certificate_pem: str
    ca_chain_pem: str
    serial_number: str
    expires_at: datetime


class RevokeCertRequest(BaseModel):
    """Request to revoke a certificate."""
    reason: str = "unspecified"  # 'unspecified', 'key_compromise', 'superseded', etc.


class RevokeCertResponse(BaseModel):
    """Response after revoking certificate."""
    certificate_id: UUID
    status: str
    revoked_at: datetime


class CertificateResponse(BaseModel):
    """Certificate metadata response."""
    id: UUID
    serial_number: str
    tenant_id: Optional[UUID]
    subject_cn: str
    dns_names: List[str]
    ip_addresses: List[str]
    usage: str
    service_type: Optional[str]
    agent_id: Optional[str]
    issued_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime]
    revocation_reason: Optional[str]
    status: str

    class Config:
        from_attributes = True


class CertificateRequestSubmission(BaseModel):
    """User-facing certificate request payload."""
    common_name: str
    subject_alternative_names: Optional[List[str]] = None
    certificate_type: str = Field(..., pattern="^(private|public)$")
    ca_authority_id: Optional[str] = None
    validity_days: Optional[int] = Field(None, ge=1, le=365)


class CertificateRequestAck(BaseModel):
    """Acknowledgement after submitting a certificate request."""
    request_id: UUID
    status: str
    tenant_id: Optional[UUID]
    common_name: str
    certificate_type: str
    ca_authority_id: Optional[str]
    submitted_at: datetime


class CreateBootstrapTokenRequest(BaseModel):
    """Request to create an agent bootstrap token."""
    # Note: tenant_id is NOT in request - it comes from JWT token for security
    agent_id: Optional[str] = None
    ttl_hours: Optional[int] = None


class CreateBootstrapTokenResponse(BaseModel):
    """Response with bootstrap token."""
    token: str  # One-time token (only shown once)
    token_id: UUID
    expires_at: datetime


class EnrollAgentRequest(BaseModel):
    """Request from agent to enroll and get certificate."""
    bootstrap_token: str
    agent_id: str
    hostname: str
    ip: Optional[str] = None
    dns_names: Optional[List[str]] = None


class EnrollAgentResponse(BaseModel):
    """Response with agent certificate."""
    certificate_id: UUID
    certificate_pem: str
    private_key_pem: str  # Agent certs always include private key
    ca_chain_pem: str
    serial_number: str
    expires_at: datetime


class CAAuthorityResponse(BaseModel):
    """CA Authority configuration response."""
    id: UUID
    name: str
    type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
