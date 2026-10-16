"""Certificate Service business logic."""

import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import Certificate, CAAuthority, CertificateRequest, AgentBootstrapToken
from app.providers.base import CAProvider, IssueCertRequest
from app.providers.step_ca import StepCAProvider
from app.providers.ejbca import EJBCAProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class CertificateService:
    """Service for managing certificates with tenant isolation."""
    
    def __init__(self, db: Session, tenant_id: Optional[UUID] = None, ca_provider: Optional[CAProvider] = None):
        """
        Initialize certificate service.
        
        Args:
            db: Database session
            tenant_id: Tenant ID for tenant isolation (required for user-facing operations)
            ca_provider: Optional CA provider (will use default if not provided)
        """
        self.db = db
        self.tenant_id = tenant_id  # Store tenant_id for tenant isolation
        self.ca_provider = ca_provider or self._get_default_provider()
    
    def _get_default_provider(self) -> CAProvider:
        """Get the default CA provider based on configuration and tenant."""
        # Get CA authority for tenant (per-tenant CA or shared CA)
        ca_authority = self._get_ca_for_tenant()
        
        if not ca_authority:
            # Create default CA authority if none exists
            ca_authority = self._create_default_ca_authority()
        
        # Initialize provider based on type
        if ca_authority.type == "ejbca":
            config = ca_authority.config
            return EJBCAProvider(
                ejbca_url=config.get("url", settings.EJBCA_URL),
                ejbca_username=config.get("username", settings.EJBCA_USERNAME),
                ejbca_password=config.get("password", settings.EJBCA_PASSWORD),
                ca_name=config.get("ca_name", settings.EJBCA_CA_NAME),
                certificate_profile=config.get("certificate_profile", settings.EJBCA_CERTIFICATE_PROFILE),
                verify_ssl=config.get("verify_ssl", settings.EJBCA_VERIFY_SSL)
            )
        elif ca_authority.type == "step-ca":
            config = ca_authority.config
            return StepCAProvider(
                ca_url=config.get("url", settings.STEP_CA_URL),
                provisioner_name=config.get("provisioner_name", settings.STEP_CA_PROVISIONER_NAME),
                provisioner_password=config.get("provisioner_password", settings.STEP_CA_PROVISIONER_PASSWORD)
            )
        else:
            raise ValueError(f"Unsupported CA type: {ca_authority.type}")
    
    def _get_ca_for_tenant(self) -> Optional[CAAuthority]:
        """
        Get CA authority for tenant with isolation.
        
        Priority:
        1. Per-tenant CA (tenant_id matches)
        2. Shared CA (tenant_id is NULL)
        
        Returns:
            CAAuthority or None if not found
        """
        if self.tenant_id:
            # Try per-tenant CA first
            ca = self.db.query(CAAuthority).filter(
                CAAuthority.tenant_id == self.tenant_id,
                CAAuthority.status == "active"
            ).first()
            
            if ca:
                logger.debug(f"Using per-tenant CA for tenant {self.tenant_id}: {ca.name}")
                return ca
        
        # Fall back to shared CA (tenant_id is NULL)
        ca = self.db.query(CAAuthority).filter(
            CAAuthority.tenant_id.is_(None),  # Shared CA
            CAAuthority.status == "active"
        ).first()
        
        if ca:
            logger.debug(f"Using shared CA: {ca.name}")
            return ca
        
        return None
    
    def _create_default_ca_authority(self) -> CAAuthority:
        """Create default CA authority configuration based on CA_BACKEND_TYPE."""
        ca_type = settings.CA_BACKEND_TYPE.lower()
        
        if ca_type == "ejbca":
            ca_authority = CAAuthority(
                name="default-ejbca",
                type="ejbca",
                config={
                    "url": settings.EJBCA_URL,
                    "username": settings.EJBCA_USERNAME,
                    "password": settings.EJBCA_PASSWORD,
                    "ca_name": settings.EJBCA_CA_NAME,
                    "certificate_profile": settings.EJBCA_CERTIFICATE_PROFILE,
                    "verify_ssl": settings.EJBCA_VERIFY_SSL,
                },
                status="active"
            )
            logger.info("Created default EJBCA authority")
        elif ca_type == "step-ca":
            ca_authority = CAAuthority(
                name="default-step-ca",
                type="step-ca",
                config={
                    "url": settings.STEP_CA_URL,
                    "provisioner_name": settings.STEP_CA_PROVISIONER_NAME,
                    "provisioner_password": settings.STEP_CA_PROVISIONER_PASSWORD,
                },
                status="active"
            )
            logger.info("Created default Step-CA authority")
        else:
            raise ValueError(f"Unsupported CA_BACKEND_TYPE: {ca_type}")
        
        self.db.add(ca_authority)
        self.db.commit()
        self.db.refresh(ca_authority)
        return ca_authority
    
    def enroll_service(
        self,
        service_id: str,
        service_type: str,
        subject_cn: str,
        dns_names: List[str] = None,
        ip_addresses: List[str] = None,
        ttl_hours: Optional[int] = None,
        csr_pem: Optional[str] = None
    ) -> dict:
        """Enroll a service and issue a certificate."""
        dns_names = dns_names or []
        ip_addresses = ip_addresses or []
        ttl_hours = ttl_hours or settings.SERVICE_CERT_TTL_HOURS
        
        # Create certificate request
        cert_request = CertificateRequest(
            tenant_id=self.tenant_id,
            requestor_type="service",
            requestor_id=service_id,
            dns_names=dns_names,
            ip_addresses=ip_addresses,
            ttl_hours=ttl_hours,
            csr_pem=csr_pem,
            status="pending"
        )
        self.db.add(cert_request)
        self.db.flush()
        
        try:
            # Issue certificate via CA provider
            issue_request = IssueCertRequest(
                subject_cn=subject_cn,
                dns_names=dns_names,
                ip_addresses=ip_addresses,
                ttl_hours=ttl_hours,
                csr_pem=csr_pem
            )
            
            result = self.ca_provider.issue_cert(issue_request)
            
            # Get CA authority scoped to the service tenant when available
            ca_authority = self._get_ca_for_tenant()

            # Store certificate in database
            certificate = Certificate(
                serial_number=result.serial_number,
                tenant_id=self.tenant_id,
                subject_cn=subject_cn,
                dns_names=dns_names,
                ip_addresses=ip_addresses,
                spki_fingerprint=result.spki_fingerprint,
                usage="service",
                service_type=service_type,
                ca_authority_id=ca_authority.id,
                issued_at=datetime.utcnow(),
                expires_at=result.expires_at,
                status="issued"
            )
            self.db.add(certificate)
            self.db.flush()
            
            # Link request to certificate
            cert_request.certificate_id = certificate.id
            cert_request.status = "issued"
            
            self.db.commit()
            self.db.refresh(certificate)
            
            return {
                "certificate_id": certificate.id,
                "certificate_pem": result.certificate_pem,
                "private_key_pem": result.private_key_pem,
                "ca_chain_pem": result.ca_chain_pem,
                "serial_number": result.serial_number,
                "expires_at": result.expires_at,
                "spki_fingerprint": result.spki_fingerprint
            }
            
        except Exception as e:
            cert_request.status = "rejected"
            cert_request.error_message = str(e)
            self.db.commit()
            logger.error(f"Failed to enroll service {service_id}: {e}")
            raise
    
    def enroll_agent(
        self,
        tenant_id: UUID,
        agent_id: str,
        hostname: str,
        ip: Optional[str] = None,
        dns_names: Optional[List[str]] = None,
        bootstrap_token: str = None
    ) -> dict:
        """Enroll an agent and issue a certificate."""
        # Validate bootstrap token
        if bootstrap_token:
            token_hash = hashlib.sha256(bootstrap_token.encode()).hexdigest()
            token_record = self.db.query(AgentBootstrapToken).filter(
                and_(
                    AgentBootstrapToken.token_hash == token_hash,
                    AgentBootstrapToken.tenant_id == tenant_id,
                    AgentBootstrapToken.expires_at > datetime.utcnow(),
                    AgentBootstrapToken.used_at.is_(None)
                )
            ).first()
            
            if not token_record:
                raise ValueError("Invalid or expired bootstrap token")
            
            # Mark token as used
            token_record.used_at = datetime.utcnow()
        
        dns_names = dns_names or [hostname]
        if ip:
            ip_addresses = [ip]
        else:
            ip_addresses = []
        
        subject_cn = f"{agent_id}.{hostname}"
        ttl_hours = settings.AGENT_CERT_TTL_HOURS
        
        # Create certificate request
        cert_request = CertificateRequest(
            tenant_id=tenant_id,
            requestor_type="agent",
            requestor_id=agent_id,
            dns_names=dns_names,
            ip_addresses=ip_addresses,
            ttl_hours=ttl_hours,
            status="pending"
        )
        self.db.add(cert_request)
        self.db.flush()
        
        try:
            # Issue certificate via CA provider
            # For agents, we generate the keypair server-side (V1 simplification)
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.backends import default_backend
            import ipaddress
            
            # Generate keypair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # Create CSR
            csr = x509.CertificateSigningRequestBuilder().subject_name(
                x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject_cn)])
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(dns) for dns in dns_names
                ] + ([x509.IPAddress(ipaddress.ip_address(ip))] if ip else [])),
                critical=False
            ).sign(private_key, hashes.SHA256(), default_backend())
            
            csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode('utf-8')
            
            issue_request = IssueCertRequest(
                subject_cn=subject_cn,
                dns_names=dns_names,
                ip_addresses=ip_addresses,
                ttl_hours=ttl_hours,
                csr_pem=csr_pem
            )
            
            result = self.ca_provider.issue_cert(issue_request)
            
            # Get CA authority
            ca_authority = self.db.query(CAAuthority).filter(
                CAAuthority.status == "active"
            ).first()
            
            # Store certificate in database
            certificate = Certificate(
                serial_number=result.serial_number,
                tenant_id=tenant_id,
                subject_cn=subject_cn,
                dns_names=dns_names,
                ip_addresses=ip_addresses,
                spki_fingerprint=result.spki_fingerprint,
                usage="agent",
                agent_id=agent_id,
                ca_authority_id=ca_authority.id,
                issued_at=datetime.utcnow(),
                expires_at=result.expires_at,
                status="issued"
            )
            self.db.add(certificate)
            self.db.flush()
            
            # Link request to certificate
            cert_request.certificate_id = certificate.id
            cert_request.status = "issued"
            
            self.db.commit()
            self.db.refresh(certificate)
            
            # Serialize private key
            private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
            
            return {
                "certificate_id": certificate.id,
                "certificate_pem": result.certificate_pem,
                "private_key_pem": private_key_pem,
                "ca_chain_pem": result.ca_chain_pem,
                "serial_number": result.serial_number,
                "expires_at": result.expires_at,
                "spki_fingerprint": result.spki_fingerprint
            }
            
        except Exception as e:
            cert_request.status = "rejected"
            cert_request.error_message = str(e)
            self.db.commit()
            logger.error(f"Failed to enroll agent {agent_id}: {e}")
            raise
    
    def renew_certificate(self, certificate_id: UUID) -> dict:
        """
        Renew an existing certificate - tenant-scoped.
        
        Args:
            certificate_id: Certificate UUID
            
        Returns:
            Dict with renewed certificate details
            
        Raises:
            ValueError: If certificate not found or doesn't belong to tenant
        """
        # Use get_certificate which enforces tenant isolation
        certificate = self.get_certificate(certificate_id)
        
        if not certificate:
            raise ValueError(f"Certificate {certificate_id} not found")
        
        if certificate.status != "issued":
            raise ValueError(f"Certificate {certificate_id} is not in issued status")
        
        # Renew via CA provider (requires CSR - simplified for V1)
        # For now, we'll issue a new certificate with same parameters
        issue_request = IssueCertRequest(
            subject_cn=certificate.subject_cn,
            dns_names=certificate.dns_names or [],
            ip_addresses=[str(ip) for ip in (certificate.ip_addresses or [])],
            ttl_hours=settings.SERVICE_CERT_TTL_HOURS if certificate.usage == "service" else settings.AGENT_CERT_TTL_HOURS
        )
        
        result = self.ca_provider.issue_cert(issue_request)
        
        # Update certificate record
        certificate.serial_number = result.serial_number
        certificate.issued_at = datetime.utcnow()
        certificate.expires_at = result.expires_at
        certificate.spki_fingerprint = result.spki_fingerprint
        certificate.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(certificate)
        
        return {
            "certificate_id": certificate.id,
            "certificate_pem": result.certificate_pem,
            "ca_chain_pem": result.ca_chain_pem,
            "serial_number": result.serial_number,
            "expires_at": result.expires_at
        }
    
    def revoke_certificate(self, certificate_id: UUID, reason: str = "unspecified") -> dict:
        """
        Revoke a certificate - tenant-scoped.
        
        Args:
            certificate_id: Certificate UUID
            reason: Revocation reason
            
        Returns:
            Dict with revocation details
            
        Raises:
            ValueError: If certificate not found or doesn't belong to tenant
        """
        # Use get_certificate which enforces tenant isolation
        certificate = self.get_certificate(certificate_id)
        
        if not certificate:
            raise ValueError(f"Certificate {certificate_id} not found")
        
        if certificate.status == "revoked":
            return {
                "certificate_id": certificate.id,
                "status": "revoked",
                "revoked_at": certificate.revoked_at
            }
        
        # Revoke via CA provider
        success = self.ca_provider.revoke_cert(certificate.serial_number, reason)
        
        if success:
            certificate.status = "revoked"
            certificate.revoked_at = datetime.utcnow()
            certificate.revocation_reason = reason
            certificate.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(certificate)
            
            logger.info(f"Revoked certificate {certificate_id} for tenant {self.tenant_id}")
            
            return {
                "certificate_id": certificate.id,
                "status": "revoked",
                "revoked_at": certificate.revoked_at
            }
        else:
            raise Exception("Failed to revoke certificate via CA")
    
    def get_certificate(self, certificate_id: UUID) -> Optional[Certificate]:
        """
        Get certificate by ID - tenant-scoped.
        
        Args:
            certificate_id: Certificate UUID
            
        Returns:
            Certificate if found and belongs to tenant, None otherwise
        """
        query = self.db.query(Certificate).filter(
            Certificate.id == certificate_id
        )
        
        # Enforce tenant isolation
        if self.tenant_id:
            query = query.filter(Certificate.tenant_id == self.tenant_id)
        
        return query.first()
    
    def list_certificates(
        self,
        status: Optional[str] = None,
        usage: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Certificate], int]:
        """
        List certificates - tenant-scoped.
        
        Args:
            status: Filter by status (issued, revoked, expired)
            usage: Filter by usage (service, agent)
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            Tuple of (certificates list, total count)
        """
        query = self.db.query(Certificate)
        
        # Enforce tenant isolation
        if self.tenant_id:
            query = query.filter(Certificate.tenant_id == self.tenant_id)
        
        if status:
            query = query.filter(Certificate.status == status)
        if usage:
            query = query.filter(Certificate.usage == usage)
        
        total = query.count()
        certificates = query.order_by(Certificate.created_at.desc()).offset(offset).limit(limit).all()
        
        return certificates, total
    
    def create_bootstrap_token(
        self,
        tenant_id: UUID,
        agent_id: Optional[str] = None,
        ttl_hours: Optional[int] = None,
        created_by: Optional[UUID] = None
    ) -> dict:
        """Create a bootstrap token for agent enrollment."""
        ttl_hours = ttl_hours or settings.BOOTSTRAP_TOKEN_TTL_HOURS
        
        # Generate token
        token = secrets.token_urlsafe(settings.BOOTSTRAP_TOKEN_LENGTH)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Create token record
        token_record = AgentBootstrapToken(
            tenant_id=tenant_id,
            token_hash=token_hash,
            agent_id=agent_id,
            expires_at=datetime.utcnow() + timedelta(hours=ttl_hours),
            created_by=created_by
        )
        self.db.add(token_record)
        self.db.commit()
        self.db.refresh(token_record)
        
        return {
            "token": token,  # Only shown once
            "token_id": token_record.id,
            "expires_at": token_record.expires_at
        }
