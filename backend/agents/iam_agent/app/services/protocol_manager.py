"""Compatibility facade: provider operations remain unavailable."""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Any, Optional
from enum import Enum
from fastapi import HTTPException

if TYPE_CHECKING:
    from app.services.keycloak_client import KeycloakClient


class ProtocolType(str, Enum):
    """Supported protocol types."""

    SAML2 = "saml2"
    OAUTH2 = "oauth2"
    OIDC = "oidc"
    SCIM2 = "scim2"
    LDAP = "ldap"
    KERBEROS = "kerberos"


class ProtocolManager:
    """Service for managing authentication and identity protocols."""

    def __init__(self, keycloak_client: KeycloakClient):
        self.keycloak_client = keycloak_client

    def configure_saml_identity_provider(
        self,
        alias: str,
        entity_id: str,
        sso_url: str,
        certificate: str,
        tenant_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Protocol configuration, storage and connection testing are not qualified",
        )

    def configure_oauth2_client(
        self,
        client_id: str,
        client_secret: Optional[str],
        redirect_uris: List[str],
        tenant_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Protocol configuration, storage and connection testing are not qualified",
        )

    def configure_scim_client(
        self,
        scim_endpoint: str,
        bearer_token: str,
        tenant_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Protocol configuration, storage and connection testing are not qualified",
        )

    def configure_ldap_federation(
        self,
        provider_name: str,
        connection_url: str,
        bind_dn: str,
        bind_credential: str,
        users_dn: str,
        tenant_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Protocol configuration, storage and connection testing are not qualified",
        )

    def list_protocol_configurations(
        self,
        protocol_type: Optional[ProtocolType] = None,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        raise HTTPException(
            status_code=501,
            detail="Protocol configuration, storage and connection testing are not qualified",
        )

    def get_protocol_configuration(
        self, config_id: str, tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        raise HTTPException(
            status_code=501,
            detail="Protocol configuration, storage and connection testing are not qualified",
        )

    def update_protocol_configuration(
        self, config_id: str, updates: Dict[str, Any], tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Protocol configuration, storage and connection testing are not qualified",
        )

    def delete_protocol_configuration(
        self, config_id: str, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Protocol configuration, storage and connection testing are not qualified",
        )

    def test_protocol_connection(
        self,
        config_id: str,
        protocol_type: ProtocolType,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Protocol configuration, storage and connection testing are not qualified",
        )
