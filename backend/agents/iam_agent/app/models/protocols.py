"""Models for protocol and integration management."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ProtocolType(str, Enum):
    """Protocol types."""
    SAML2 = "saml2"
    OAUTH2 = "oauth2"
    OIDC = "oidc"
    SCIM2 = "scim2"
    LDAP = "ldap"
    KERBEROS = "kerberos"


class IntegrationType(str, Enum):
    """Integration types."""
    ACTIVE_DIRECTORY = "active_directory"
    AZURE_AD = "azure_ad"
    OKTA = "okta"
    GOOGLE_WORKSPACE = "google_workspace"
    AWS_IAM = "aws_iam"
    GITHUB = "github"
    CUSTOM = "custom"


class SAMLConfigRequest(BaseModel):
    """Request to configure SAML identity provider."""
    alias: str
    entity_id: str
    sso_url: str
    certificate: str
    tenant_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class SAMLConfigResponse(BaseModel):
    """Response from SAML configuration."""
    alias: str
    protocol: str
    status: str
    entity_id: str
    sso_url: str
    tenant_id: Optional[str] = None
    configured_at: datetime


class OAuth2ConfigRequest(BaseModel):
    """Request to configure OAuth 2.0 client."""
    client_id: str
    client_secret: Optional[str] = None
    redirect_uris: List[str]
    tenant_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class OAuth2ConfigResponse(BaseModel):
    """Response from OAuth 2.0 configuration."""
    client_id: str
    protocol: str
    status: str
    redirect_uris: List[str]
    tenant_id: Optional[str] = None
    configured_at: datetime


class SCIMConfigRequest(BaseModel):
    """Request to configure SCIM client."""
    scim_endpoint: str
    bearer_token: str
    tenant_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class SCIMConfigResponse(BaseModel):
    """Response from SCIM configuration."""
    scim_endpoint: str
    protocol: str
    status: str
    tenant_id: Optional[str] = None
    configured_at: datetime


class LDAPConfigRequest(BaseModel):
    """Request to configure LDAP federation."""
    provider_name: str
    connection_url: str
    bind_dn: str
    bind_credential: str
    users_dn: str
    tenant_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class LDAPConfigResponse(BaseModel):
    """Response from LDAP configuration."""
    provider_name: str
    protocol: str
    status: str
    connection_url: str
    users_dn: str
    tenant_id: Optional[str] = None
    configured_at: datetime


class ADIntegrationRequest(BaseModel):
    """Request to create Active Directory integration."""
    name: str
    domain: str
    ldap_url: str
    bind_dn: str
    bind_password: str
    users_dn: str
    tenant_id: Optional[str] = None
    sync_config: Optional[Dict[str, Any]] = None


class AzureADIntegrationRequest(BaseModel):
    """Request to create Azure AD integration."""
    name: str
    tenant_id_azure: str
    client_id: str
    client_secret: str
    tenant_id: Optional[str] = None
    sync_config: Optional[Dict[str, Any]] = None


class OktaIntegrationRequest(BaseModel):
    """Request to create Okta integration."""
    name: str
    okta_domain: str
    client_id: str
    client_secret: str
    tenant_id: Optional[str] = None
    sync_config: Optional[Dict[str, Any]] = None


class IntegrationResponse(BaseModel):
    """Response with integration information."""
    integration_id: str
    name: str
    type: str
    status: str
    tenant_id: Optional[str] = None
    created_at: datetime


class SyncRequest(BaseModel):
    """Request to sync an integration."""
    integration_id: str
    sync_type: str = Field("full", description="full, incremental, users, or groups")
    tenant_id: Optional[str] = None


class SyncResponse(BaseModel):
    """Response from sync operation."""
    integration_id: str
    sync_type: str
    status: str
    synced_at: datetime
    result: Dict[str, Any]

