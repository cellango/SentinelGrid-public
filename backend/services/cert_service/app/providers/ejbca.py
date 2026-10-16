"""EJBCA provider implementation."""

import logging
import httpx
import hashlib
from typing import Optional, List
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

from app.providers.base import CAProvider, IssueCertRequest, IssueCertResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class EJBCAProvider(CAProvider):
    """EJBCA provider using REST API."""
    
    def __init__(
        self,
        ejbca_url: str,
        ejbca_username: str,
        ejbca_password: str,
        ca_name: str = None,
        certificate_profile: str = None,
        verify_ssl: bool = False
    ):
        """
        Initialize EJBCA provider.
        
        Args:
            ejbca_url: EJBCA base URL (e.g., https://ejbca:8443)
            ejbca_username: EJBCA admin username
            ejbca_password: EJBCA admin password
            ca_name: CA name in EJBCA (e.g., "SentinelGrid-Issuing-CA")
            certificate_profile: Certificate profile name (e.g., "service-tls")
            verify_ssl: Whether to verify SSL certificates
        """
        self.ejbca_url = ejbca_url.rstrip('/')
        self.ejbca_username = ejbca_username
        self.ejbca_password = ejbca_password
        self.ca_name = ca_name or settings.EJBCA_CA_NAME
        self.certificate_profile = certificate_profile or settings.EJBCA_CERTIFICATE_PROFILE
        self.verify_ssl = verify_ssl
        self._session: Optional[httpx.Client] = None
        self._auth_token: Optional[str] = None
    
    def _get_session(self) -> httpx.Client:
        """Get authenticated HTTP session with EJBCA."""
        if self._session and self._auth_token:
            return self._session
        
        # Create session
        self._session = httpx.Client(
            base_url=self.ejbca_url,
            verify=self.verify_ssl,
            timeout=30.0
        )
        
        # Authenticate and get token
        try:
            auth_response = self._session.post(
                "/ejbca/ejbca-rest-api/v1/certificate/ca",
                auth=(self.ejbca_username, self.ejbca_password)
            )
            auth_response.raise_for_status()
            
            # EJBCA REST API uses basic auth, so we'll use it for all requests
            # Store credentials for subsequent requests
            self._auth_token = None  # Not needed with basic auth
            
            logger.info(f"Authenticated with EJBCA at {self.ejbca_url}")
            return self._session
            
        except httpx.HTTPStatusError as e:
            logger.error(f"EJBCA authentication failed: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to authenticate with EJBCA: {e.response.text}")
        except Exception as e:
            logger.error(f"Error authenticating with EJBCA: {e}")
            raise
    
    def issue_cert(self, request: IssueCertRequest) -> IssueCertResult:
        """Issue a certificate via EJBCA REST API."""
        try:
            session = self._get_session()
            
            # EJBCA REST API endpoint for certificate enrollment
            # Using PKCS10 enrollment (CSR-based)
            if not request.csr_pem:
                raise ValueError("CSR is required for EJBCA certificate issuance")
            
            # Prepare enrollment request
            enrollment_data = {
                "certificate_request": request.csr_pem,
                "certificate_profile_name": self.certificate_profile,
                "end_entity_profile_name": "EMPTY",  # Default profile
                "certificate_authority_name": self.ca_name,
                "username": request.subject_cn.replace(".", "_"),  # EJBCA username from CN
                "password": "dummy",  # Not used for PKCS10 enrollment
                "include_chain": True
            }
            
            # Add subject alternative names if provided
            if request.dns_names:
                enrollment_data["subject_alt_name"] = ",".join([
                    f"DNS:{dns}" for dns in request.dns_names
                ])
            
            # Call EJBCA REST API
            response = session.post(
                "/ejbca/ejbca-rest-api/v1/certificate/pkcs10enroll",
                json=enrollment_data,
                auth=(self.ejbca_username, self.ejbca_password)
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract certificate from response
            certificate_pem = result.get("certificate") or result.get("certificate_data")
            if not certificate_pem:
                raise Exception("EJBCA did not return certificate")
            
            # Extract CA chain if provided
            ca_chain_pem = result.get("ca_chain", "")
            if isinstance(ca_chain_pem, list):
                ca_chain_pem = "\n".join(ca_chain_pem)
            
            # Extract serial number and expiry
            serial_number = self._extract_serial_number(certificate_pem)
            expires_at = self._extract_expiry(certificate_pem)
            spki_fingerprint = self._calculate_spki_fingerprint(certificate_pem)
            
            logger.info(f"Issued certificate via EJBCA: serial={serial_number}, CN={request.subject_cn}")
            
            return IssueCertResult(
                certificate_pem=certificate_pem,
                private_key_pem=None,  # EJBCA doesn't return private keys
                ca_chain_pem=ca_chain_pem,
                serial_number=serial_number,
                expires_at=expires_at,
                spki_fingerprint=spki_fingerprint
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"EJBCA API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to issue certificate via EJBCA: {e.response.text}")
        except Exception as e:
            logger.error(f"Error issuing certificate via EJBCA: {e}")
            raise
    
    def renew_cert(self, certificate_id: str, serial_number: str) -> IssueCertResult:
        """Renew a certificate via EJBCA."""
        # EJBCA renewal requires a new CSR
        # For now, this is a placeholder - actual implementation depends on renewal workflow
        raise NotImplementedError("Certificate renewal via EJBCA requires CSR")
    
    def revoke_cert(self, serial_number: str, reason: str = "unspecified") -> bool:
        """Revoke a certificate via EJBCA REST API."""
        try:
            session = self._get_session()
            
            # Map revocation reason
            ejbca_reason_map = {
                "unspecified": 0,
                "key_compromise": 1,
                "cacompromise": 2,
                "affiliation_changed": 3,
                "superseded": 4,
                "cessation_of_operation": 5,
                "certificate_hold": 6,
                "remove_from_crl": 8,
                "privilege_withdrawn": 9,
                "aa_compromise": 10
            }
            ejbca_reason = ejbca_reason_map.get(reason.lower(), 0)
            
            # Revoke certificate
            # EJBCA REST API requires issuer DN and certificate serial number
            # For now, we'll use a simplified approach
            revoke_data = {
                "issuer_dn": f"CN={self.ca_name}",
                "certificate_serial_number": serial_number,
                "reason": ejbca_reason
            }
            
            response = session.post(
                "/ejbca/ejbca-rest-api/v1/certificate/revoke",
                json=revoke_data,
                auth=(self.ejbca_username, self.ejbca_password)
            )
            response.raise_for_status()
            
            logger.info(f"Revoked certificate via EJBCA: serial={serial_number}, reason={reason}")
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"EJBCA revocation error: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Error revoking certificate via EJBCA: {e}")
            return False
    
    def get_ca_chain(self) -> str:
        """Get the CA certificate chain."""
        try:
            session = self._get_session()
            
            # Get CA certificate
            response = session.get(
                f"/ejbca/ejbca-rest-api/v1/ca/{self.ca_name}/certificate",
                auth=(self.ejbca_username, self.ejbca_password)
            )
            response.raise_for_status()
            result = response.json()
            
            ca_cert = result.get("certificate") or result.get("certificate_data")
            if ca_cert:
                return ca_cert
            
            return ""
            
        except httpx.HTTPStatusError as e:
            logger.error(f"EJBCA CA chain error: {e.response.status_code} - {e.response.text}")
            return ""
        except Exception as e:
            logger.error(f"Error getting CA chain from EJBCA: {e}")
            return ""
    
    def _extract_serial_number(self, cert_pem: str) -> str:
        """Extract serial number from certificate."""
        try:
            cert = x509.load_pem_x509_certificate(
                cert_pem.encode('utf-8'),
                default_backend()
            )
            return str(cert.serial_number)
        except Exception as e:
            logger.error(f"Error extracting serial number: {e}")
            return ""
    
    def _extract_expiry(self, cert_pem: str) -> datetime:
        """Extract expiry date from certificate."""
        try:
            cert = x509.load_pem_x509_certificate(
                cert_pem.encode('utf-8'),
                default_backend()
            )
            return cert.not_valid_after.replace(tzinfo=None)
        except Exception as e:
            logger.error(f"Error extracting expiry: {e}")
            return datetime.utcnow() + timedelta(days=30)
    
    def _calculate_spki_fingerprint(self, cert_pem: str) -> str:
        """Calculate SPKI fingerprint (SHA-256) of certificate."""
        try:
            cert = x509.load_pem_x509_certificate(
                cert_pem.encode('utf-8'),
                default_backend()
            )
            public_key = cert.public_key()
            public_key_bytes = public_key.public_bytes(
                encoding=x509.serialization.Encoding.DER,
                format=x509.serialization.PublicFormat.SubjectPublicKeyInfo
            )
            fingerprint = hashlib.sha256(public_key_bytes).hexdigest()
            return fingerprint
        except Exception as e:
            logger.error(f"Error calculating SPKI fingerprint: {e}")
            return ""

