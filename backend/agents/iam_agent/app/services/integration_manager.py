"""Compatibility facade: provider operations remain unavailable."""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Any, Optional
from enum import Enum
from fastapi import HTTPException

if TYPE_CHECKING:
    from app.services.keycloak_client import KeycloakClient


class IntegrationType(str, Enum):
    """Types of integrations."""

    ACTIVE_DIRECTORY = "active_directory"
    AZURE_AD = "azure_ad"
    OKTA = "okta"
    GOOGLE_WORKSPACE = "google_workspace"
    AWS_IAM = "aws_iam"
    GITHUB = "github"
    CUSTOM = "custom"


class IntegrationStatus(str, Enum):
    """Integration status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    SYNCING = "syncing"


class IntegrationManager:
    """Service for managing external system integrations."""

    def __init__(self, keycloak_client: KeycloakClient):
        self.keycloak_client = keycloak_client

    def create_active_directory_integration(
        self,
        name: str,
        domain: str,
        ldap_url: str,
        bind_dn: str,
        bind_password: str,
        users_dn: str,
        tenant_id: Optional[str] = None,
        sync_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Identity integration configuration, storage and synchronization are not qualified",
        )

    def create_azure_ad_integration(
        self,
        name: str,
        tenant_id_azure: str,
        client_id: str,
        client_secret: str,
        tenant_id: Optional[str] = None,
        sync_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Identity integration configuration, storage and synchronization are not qualified",
        )

    def create_okta_integration(
        self,
        name: str,
        okta_domain: str,
        client_id: str,
        client_secret: str,
        tenant_id: Optional[str] = None,
        sync_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Identity integration configuration, storage and synchronization are not qualified",
        )

    def sync_integration(
        self,
        integration_id: str,
        sync_type: str = "full",
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Identity integration configuration, storage and synchronization are not qualified",
        )

    def list_integrations(
        self,
        integration_type: Optional[IntegrationType] = None,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        raise HTTPException(
            status_code=501,
            detail="Identity integration configuration, storage and synchronization are not qualified",
        )

    def get_integration(
        self, integration_id: str, tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        raise HTTPException(
            status_code=501,
            detail="Identity integration configuration, storage and synchronization are not qualified",
        )

    def update_integration(
        self,
        integration_id: str,
        updates: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Identity integration configuration, storage and synchronization are not qualified",
        )

    def delete_integration(
        self, integration_id: str, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Identity integration configuration, storage and synchronization are not qualified",
        )

    def test_integration_connection(
        self, integration_id: str, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Identity integration configuration, storage and synchronization are not qualified",
        )

    def _sync_ldap_users(self, integration: Dict[str, Any]) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Identity integration configuration, storage and synchronization are not qualified",
        )

    def _sync_azure_ad_users(self, integration: Dict[str, Any]) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Identity integration configuration, storage and synchronization are not qualified",
        )

    def _test_ldap_connection(self, integration: Dict[str, Any]) -> Dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Identity integration configuration, storage and synchronization are not qualified",
        )

    def _generate_integration_id(self) -> str:
        raise HTTPException(
            status_code=501,
            detail="Identity integration configuration, storage and synchronization are not qualified",
        )
