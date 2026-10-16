"""Certificate Service API endpoints."""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sg_core.service_security import verify_internal_service_token
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import get_db, get_tenant_db, get_tenant_session
from app.core.auth import get_current_tenant, require_role
from app.services.cert_service import CertificateService
from app.schemas import (
    IssueCertRequest, IssueCertResponse,
    RenewCertRequest, RenewCertResponse,
    RevokeCertRequest, RevokeCertResponse,
    CertificateResponse, CAAuthorityResponse,
    CertificateRequestSubmission, CertificateRequestAck,
    EnrollAgentRequest, EnrollAgentResponse,
    CreateBootstrapTokenRequest, CreateBootstrapTokenResponse
)
from app.core.config import settings
from app.models import AgentBootstrapToken, Certificate, CAAuthority

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_service_token(
    authorization: Optional[str] = Header(None),
    x_internal_service_token: Optional[str] = Header(None, alias="X-Internal-Service-Token"),
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token"),
) -> str:
    """
    Verify service authentication token for internal service-to-service calls.
    
    Note: This is for internal services only. User-facing endpoints use JWT tokens.
    """
    return verify_internal_service_token(
        settings.INTERNAL_SERVICE_TOKEN,
        authorization=authorization,
        x_internal_service_token=x_internal_service_token,
        x_internal_token=x_internal_token,
        missing_detail="Missing authorization header",
        invalid_detail="Invalid service token",
    )


def resolve_service_enrollment_tenant(
    request: IssueCertRequest,
    _token: str = Depends(verify_service_token),
) -> UUID:
    """Resolve tenant scope for internal service enrollment requests."""
    if not request.tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required for service enrollment")
    return request.tenant_id


def get_service_enrollment_tenant_session(
    tenant_id: UUID = Depends(resolve_service_enrollment_tenant),
):
    """Tenant-scoped DB dependency for internal service enrollment."""
    yield from get_tenant_db(tenant_id)


def resolve_agent_enrollment_tenant(
    request: EnrollAgentRequest,
    db: Session = Depends(get_db),
) -> UUID:
    """Resolve tenant scope from a bootstrap token before enrollment."""
    import hashlib
    from datetime import datetime

    token_hash = hashlib.sha256(request.bootstrap_token.encode()).hexdigest()
    token_record = db.query(AgentBootstrapToken).filter(
        and_(
            AgentBootstrapToken.token_hash == token_hash,
            AgentBootstrapToken.expires_at > datetime.utcnow(),
            AgentBootstrapToken.used_at.is_(None),
        )
    ).first()

    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid or expired bootstrap token")

    return token_record.tenant_id


def get_agent_enrollment_tenant_session(
    tenant_id: UUID = Depends(resolve_agent_enrollment_tenant),
):
    """Tenant-scoped DB dependency for bootstrap-token enrollment."""
    yield from get_tenant_db(tenant_id)


@router.get("/v1/ca", response_model=List[CAAuthorityResponse])
async def list_ca_authorities(
    tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """
    List Certificate Authorities available to the tenant (tenant-specific or shared).
    Ensures a default CA record exists on first access.
    """
    try:
        # Initialize service to ensure default CA is created if missing
        CertificateService(db, tenant_id=tenant_id)
    except Exception as e:
        logger.warning(f"CA provider initialization failed (continuing to list CA records): {e}")

    cas = db.query(CAAuthority).filter(
        CAAuthority.status == "active",
        (CAAuthority.tenant_id == tenant_id) | (CAAuthority.tenant_id.is_(None))
    ).all()

    return [
        CAAuthorityResponse(
            id=ca.id,
            name=ca.name,
            type=ca.type,
            status=ca.status,
            created_at=ca.created_at,
        )
        for ca in cas
    ]


@router.post("/v1/certificates/request", response_model=CertificateRequestAck)
async def request_certificate(
    request: CertificateRequestSubmission,
    tenant_id: UUID = Depends(get_current_tenant),
):
    """
    Accept a certificate request and acknowledge receipt.
    (Placeholder implementation; issuance workflow not yet wired to a CA.)
    """
    request_id = uuid4()
    now = datetime.utcnow()
    return CertificateRequestAck(
        request_id=request_id,
        status="pending",
        tenant_id=tenant_id,
        common_name=request.common_name,
        certificate_type=request.certificate_type,
        ca_authority_id=request.ca_authority_id,
        submitted_at=now,
    )


@router.post("/v1/certificates/enroll-service", response_model=IssueCertResponse)
async def enroll_service(
    request: IssueCertRequest,
    tenant_id: UUID = Depends(resolve_service_enrollment_tenant),
    db: Session = Depends(get_service_enrollment_tenant_session),
):
    """Enroll a service and issue a certificate."""
    try:
        service = CertificateService(db, tenant_id=tenant_id)
        result = service.enroll_service(
            service_id=request.service_id or "unknown",
            service_type=request.service_type or "unknown",
            subject_cn=request.subject_cn,
            dns_names=request.dns_names,
            ip_addresses=request.ip_addresses,
            ttl_hours=request.ttl_hours,
            csr_pem=request.csr_pem
        )
        return IssueCertResponse(**result)
    except Exception as e:
        logger.error(f"Error enrolling service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/certificates/enroll-agent", response_model=EnrollAgentResponse)
async def enroll_agent(
    request: EnrollAgentRequest,
    tenant_id: UUID = Depends(resolve_agent_enrollment_tenant),
    db: Session = Depends(get_agent_enrollment_tenant_session),
):
    """Enroll an agent and issue a certificate using bootstrap token."""
    try:
        service = CertificateService(db, tenant_id=tenant_id)
        result = service.enroll_agent(
            tenant_id=tenant_id,
            agent_id=request.agent_id,
            hostname=request.hostname,
            ip=request.ip,
            dns_names=request.dns_names,
            bootstrap_token=request.bootstrap_token
        )
        return EnrollAgentResponse(**result)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error enrolling agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/certificates/renew", response_model=RenewCertResponse)
async def renew_certificate(
    request: RenewCertRequest,
    tenant_id: UUID = Depends(get_current_tenant),  # Extract from JWT token
    db: Session = Depends(get_tenant_session)
):
    """
    Renew an existing certificate - tenant-scoped.
    
    Only allows renewal of certificates belonging to the tenant from the JWT token.
    """
    if not request.certificate_id:
        raise HTTPException(status_code=400, detail="certificate_id is required")
    
    try:
        service = CertificateService(db, tenant_id=tenant_id)
        result = service.renew_certificate(request.certificate_id)
        return RenewCertResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error renewing certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/certificates/{certificate_id}/revoke", response_model=RevokeCertResponse)
async def revoke_certificate(
    certificate_id: UUID,
    request: RevokeCertRequest,
    tenant_id: UUID = Depends(get_current_tenant),  # Extract from JWT token
    _roles: dict = Depends(require_role(["TENANT_ADMIN", "SOC_MANAGER"])),  # Require admin role
    db: Session = Depends(get_tenant_session)
):
    """
    Revoke a certificate - tenant-scoped.
    
    Only allows revocation of certificates belonging to the tenant from the JWT token.
    Requires TENANT_ADMIN or SOC_MANAGER role.
    """
    try:
        service = CertificateService(db, tenant_id=tenant_id)
        result = service.revoke_certificate(certificate_id, request.reason)
        return RevokeCertResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error revoking certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/certificates", response_model=List[CertificateResponse])
async def list_certificates(
    status: Optional[str] = Query(None, description="Filter by status: issued|revoked|expired"),
    usage: Optional[str] = Query(None, description="Filter by usage: service|agent"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    tenant_id: UUID = Depends(get_current_tenant),  # Extract from JWT token
    db: Session = Depends(get_tenant_session)
):
    """
    List certificates for the current tenant.
    
    All certificates are filtered by tenant_id from the JWT token.
    """
    try:
        service = CertificateService(db, tenant_id=tenant_id)
        certificates, total = service.list_certificates(
            status=status,
            usage=usage,
            limit=limit,
            offset=offset
        )
        
        return [
            CertificateResponse(
                id=cert.id,
                serial_number=cert.serial_number,
                tenant_id=cert.tenant_id,
                subject_cn=cert.subject_cn,
                dns_names=cert.dns_names or [],
                ip_addresses=[str(ip) for ip in (cert.ip_addresses or [])],
                usage=cert.usage,
                service_type=cert.service_type,
                agent_id=cert.agent_id,
                issued_at=cert.issued_at,
                expires_at=cert.expires_at,
                revoked_at=cert.revoked_at,
                revocation_reason=cert.revocation_reason,
                status=cert.status
            )
            for cert in certificates
        ]
    except Exception as e:
        logger.error(f"Error listing certificates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/certificates/{certificate_id}", response_model=CertificateResponse)
async def get_certificate(
    certificate_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant),  # Extract from JWT token
    db: Session = Depends(get_tenant_session)
):
    """
    Get certificate metadata by ID - tenant-scoped.
    
    Only returns certificate if it belongs to the tenant from the JWT token.
    """
    try:
        service = CertificateService(db, tenant_id=tenant_id)
        certificate = service.get_certificate(certificate_id)
        
        if not certificate:
            raise HTTPException(status_code=404, detail="Certificate not found")
        
        return CertificateResponse(
            id=certificate.id,
            serial_number=certificate.serial_number,
            tenant_id=certificate.tenant_id,
            subject_cn=certificate.subject_cn,
            dns_names=certificate.dns_names or [],
            ip_addresses=[str(ip) for ip in (certificate.ip_addresses or [])],
            usage=certificate.usage,
            service_type=certificate.service_type,
            agent_id=certificate.agent_id,
            issued_at=certificate.issued_at,
            expires_at=certificate.expires_at,
            revoked_at=certificate.revoked_at,
            revocation_reason=certificate.revocation_reason,
            status=certificate.status
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/bootstrap-tokens", response_model=CreateBootstrapTokenResponse)
async def create_bootstrap_token(
    request: CreateBootstrapTokenRequest,
    tenant_id: UUID = Depends(get_current_tenant),  # Extract from JWT token
    _roles: dict = Depends(require_role(["TENANT_ADMIN", "SOC_MANAGER"])),  # Require admin role
    db: Session = Depends(get_tenant_session)
):
    """
    Create a bootstrap token for agent enrollment - tenant-scoped.
    
    The tenant_id from the JWT token is used (not from request body) for security.
    Requires TENANT_ADMIN or SOC_MANAGER role.
    """
    try:
        # Override request.tenant_id with token tenant_id (security)
        service = CertificateService(db, tenant_id=tenant_id)
        result = service.create_bootstrap_token(
            tenant_id=tenant_id,  # Use token tenant_id, not request
            agent_id=request.agent_id,
            ttl_hours=request.ttl_hours
        )
        return CreateBootstrapTokenResponse(**result)
    except Exception as e:
        logger.error(f"Error creating bootstrap token: {e}")
        raise HTTPException(status_code=500, detail=str(e))
