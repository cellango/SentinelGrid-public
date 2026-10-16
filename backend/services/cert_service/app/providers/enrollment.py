"""Enrollment protocol support (ACME, SCEP, EST)."""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class ACMEProvider:
    """ACME protocol provider for certificate enrollment."""
    
    def __init__(
        self,
        ejbca_url: str,
        ejbca_username: str,
        ejbca_password: str,
        alias: Optional[str] = None,
        verify_ssl: bool = False
    ):
        """
        Initialize ACME provider.
        
        Args:
            ejbca_url: EJBCA base URL
            ejbca_username: EJBCA admin username
            ejbca_password: EJBCA admin password
            alias: ACME alias name (optional, defaults to EJBCA default)
            verify_ssl: Whether to verify SSL certificates
        """
        self.ejbca_url = ejbca_url.rstrip('/')
        self.ejbca_username = ejbca_username
        self.ejbca_password = ejbca_password
        self.alias = alias
        self.verify_ssl = verify_ssl
    
    def get_directory_url(self) -> str:
        """
        Get ACME directory URL.
        
        Returns:
            ACME directory URL
        """
        if self.alias:
            return f"{self.ejbca_url}/ejbca/acme/{self.alias}/directory"
        return f"{self.ejbca_url}/ejbca/acme/directory"
    
    def get_account_url(self) -> str:
        """Get ACME account URL."""
        if self.alias:
            return f"{self.ejbca_url}/ejbca/acme/{self.alias}/newAccount"
        return f"{self.ejbca_url}/ejbca/acme/newAccount"
    
    def get_new_order_url(self) -> str:
        """Get ACME new order URL."""
        if self.alias:
            return f"{self.ejbca_url}/ejbca/acme/{self.alias}/newOrder"
        return f"{self.ejbca_url}/ejbca/acme/newOrder"


class SCEPProvider:
    """SCEP protocol provider for certificate enrollment."""
    
    def __init__(
        self,
        ejbca_url: str,
        ejbca_username: str,
        ejbca_password: str,
        ra_name: Optional[str] = None,
        verify_ssl: bool = False
    ):
        """
        Initialize SCEP provider.
        
        Args:
            ejbca_url: EJBCA base URL
            ejbca_username: EJBCA admin username
            ejbca_password: EJBCA admin password
            ra_name: SCEP RA name (optional)
            verify_ssl: Whether to verify SSL certificates
        """
        self.ejbca_url = ejbca_url.rstrip('/')
        self.ejbca_username = ejbca_username
        self.ejbca_password = ejbca_password
        self.ra_name = ra_name
        self.verify_ssl = verify_ssl
    
    def get_scep_endpoint_url(self) -> str:
        """
        Get SCEP endpoint URL.
        
        Returns:
            SCEP endpoint URL
        """
        if self.ra_name:
            return f"{self.ejbca_url}/ejbca/publicweb/apply/scep/{self.ra_name}/pkiclient.exe"
        return f"{self.ejbca_url}/ejbca/publicweb/apply/scep/pkiclient.exe"
    
    def get_ca_certificate_url(self) -> str:
        """Get SCEP CA certificate URL."""
        if self.ra_name:
            return f"{self.ejbca_url}/ejbca/publicweb/apply/scep/{self.ra_name}/pkiclient.exe?operation=GetCACert"
        return f"{self.ejbca_url}/ejbca/publicweb/apply/scep/pkiclient.exe?operation=GetCACert"


class ESTProvider:
    """EST (Enrollment over Secure Transport) protocol provider."""
    
    def __init__(
        self,
        ejbca_url: str,
        ejbca_username: str,
        ejbca_password: str,
        alias: Optional[str] = None,
        verify_ssl: bool = False
    ):
        """
        Initialize EST provider.
        
        Args:
            ejbca_url: EJBCA base URL
            ejbca_username: EJBCA admin username
            ejbca_password: EJBCA admin password
            alias: EST alias name (optional)
            verify_ssl: Whether to verify SSL certificates
        """
        self.ejbca_url = ejbca_url.rstrip('/')
        self.ejbca_username = ejbca_username
        self.ejbca_password = ejbca_password
        self.alias = alias
        self.verify_ssl = verify_ssl
    
    def get_cacerts_url(self) -> str:
        """Get EST CA certificates URL."""
        if self.alias:
            return f"{self.ejbca_url}/.well-known/est/{self.alias}/cacerts"
        return f"{self.ejbca_url}/.well-known/est/cacerts"
    
    def get_simpleenroll_url(self) -> str:
        """Get EST simple enroll URL."""
        if self.alias:
            return f"{self.ejbca_url}/.well-known/est/{self.alias}/simpleenroll"
        return f"{self.ejbca_url}/.well-known/est/simpleenroll"
    
    def get_simplereenroll_url(self) -> str:
        """Get EST simple re-enroll URL."""
        if self.alias:
            return f"{self.ejbca_url}/.well-known/est/{self.alias}/simplereenroll"
        return f"{self.ejbca_url}/.well-known/est/simplereenroll"

