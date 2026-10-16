"""Base CA Provider interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class IssueCertRequest:
    """Request to issue a certificate."""
    def __init__(
        self,
        subject_cn: str,
        dns_names: list = None,
        ip_addresses: list = None,
        ttl_hours: int = None,
        csr_pem: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.subject_cn = subject_cn
        self.dns_names = dns_names or []
        self.ip_addresses = ip_addresses or []
        self.ttl_hours = ttl_hours
        self.csr_pem = csr_pem
        self.metadata = metadata or {}


class IssueCertResult:
    """Result of certificate issuance."""
    def __init__(
        self,
        certificate_pem: str,
        private_key_pem: Optional[str],
        ca_chain_pem: str,
        serial_number: str,
        expires_at: datetime,
        spki_fingerprint: str
    ):
        self.certificate_pem = certificate_pem
        self.private_key_pem = private_key_pem
        self.ca_chain_pem = ca_chain_pem
        self.serial_number = serial_number
        self.expires_at = expires_at
        self.spki_fingerprint = spki_fingerprint


class CAProvider(ABC):
    """Base interface for CA providers."""
    
    @abstractmethod
    def issue_cert(self, request: IssueCertRequest) -> IssueCertResult:
        """Issue a new certificate."""
        pass
    
    @abstractmethod
    def renew_cert(self, certificate_id: str, serial_number: str) -> IssueCertResult:
        """Renew an existing certificate."""
        pass
    
    @abstractmethod
    def revoke_cert(self, serial_number: str, reason: str = "unspecified") -> bool:
        """Revoke a certificate."""
        pass
    
    @abstractmethod
    def get_ca_chain(self) -> str:
        """Get the CA certificate chain."""
        pass

