"""Step-CA provider implementation."""

import logging
import httpx
import hashlib
from typing import Optional
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

from app.providers.base import CAProvider, IssueCertRequest, IssueCertResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class StepCAProvider(CAProvider):
    """Step-CA provider using Smallstep Certificates."""
    
    def __init__(self, ca_url: str, provisioner_name: str, provisioner_password: Optional[str] = None):
        self.ca_url = ca_url.rstrip('/')
        self.provisioner_name = provisioner_name
        self.provisioner_password = provisioner_password
        self._token: Optional[str] = None
    
    def _get_token(self) -> str:
        """Get authentication token from Step-CA."""
        if self._token:
            return self._token
        
        # Step-CA uses OIDC or JWK provisioners
        # For simplicity, we'll use the provisioner password if available
        # In production, use proper OIDC authentication
        if self.provisioner_password:
            # This is a simplified approach - Step-CA typically uses OIDC
            # For V1, we'll assume token-based auth or configure Step-CA with a service account
            self._token = self.provisioner_password
            return self._token
        
        raise ValueError("Step-CA authentication not configured")
    
    def issue_cert(self, request: IssueCertRequest) -> IssueCertResult:
        """Issue a certificate via Step-CA API."""
        try:
            token = self._get_token()
            
            # Prepare certificate request
            cert_data = {
                "csr": request.csr_pem,
                "notAfter": None,  # Step-CA will use default or provisioner TTL
            }
            
            if request.ttl_hours:
                expires = datetime.utcnow() + timedelta(hours=request.ttl_hours)
                cert_data["notAfter"] = expires.isoformat() + "Z"
            
            # Call Step-CA API
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.ca_url}/1.0/sign",
                    json=cert_data,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                result = response.json()
            
            certificate_pem = result.get("crt") or result.get("cert")
            ca_chain_pem = result.get("ca", "")
            serial_number = self._extract_serial_number(certificate_pem)
            expires_at = self._extract_expiry(certificate_pem)
            spki_fingerprint = self._calculate_spki_fingerprint(certificate_pem)
            
            return IssueCertResult(
                certificate_pem=certificate_pem,
                private_key_pem=None,  # Step-CA doesn't return private keys
                ca_chain_pem=ca_chain_pem,
                serial_number=serial_number,
                expires_at=expires_at,
                spki_fingerprint=spki_fingerprint
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Step-CA API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to issue certificate: {e.response.text}")
        except Exception as e:
            logger.error(f"Error issuing certificate via Step-CA: {e}")
            raise
    
    def renew_cert(self, certificate_id: str, serial_number: str) -> IssueCertResult:
        """Renew a certificate via Step-CA."""
        # Step-CA renewal is typically done by issuing a new certificate
        # We'll need the original CSR or generate a new one
        # For now, this is a placeholder - actual implementation depends on how renewal is handled
        raise NotImplementedError("Certificate renewal via Step-CA requires CSR")
    
    def revoke_cert(self, serial_number: str, reason: str = "unspecified") -> bool:
        """Revoke a certificate via Step-CA API."""
        try:
            token = self._get_token()
            
            revoke_data = {
                "serial": serial_number,
                "reason": reason
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.ca_url}/1.0/revoke",
                    json=revoke_data,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
            
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Step-CA revocation error: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Error revoking certificate via Step-CA: {e}")
            return False
    
    def get_ca_chain(self) -> str:
        """Get the CA certificate chain."""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.ca_url}/1.0/roots")
                response.raise_for_status()
                roots = response.json()
                
                # Return the root CA certificate
                if roots and len(roots) > 0:
                    return roots[0].get("crt", "")
            
            # Fallback: read from file if configured
            if settings.STEP_CA_ROOT_CA_PATH:
                try:
                    with open(settings.STEP_CA_ROOT_CA_PATH, 'r') as f:
                        return f.read()
                except Exception as e:
                    logger.warning(f"Failed to read root CA from file: {e}")
            
            return ""
            
        except Exception as e:
            logger.error(f"Error getting CA chain: {e}")
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

