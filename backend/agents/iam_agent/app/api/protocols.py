"""Protocol and Integration API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional

from app.api.request_context import RequestContext, get_current_request_context
from app.models.protocols import (
    SAMLConfigRequest,
    SAMLConfigResponse,
    OAuth2ConfigRequest,
    OAuth2ConfigResponse,
    SCIMConfigRequest,
    SCIMConfigResponse,
    LDAPConfigRequest,
    LDAPConfigResponse,
    ADIntegrationRequest,
    AzureADIntegrationRequest,
    OktaIntegrationRequest,
    IntegrationResponse,
    SyncRequest,
    SyncResponse,
    ProtocolType,
    IntegrationType
)
from app.services.protocol_manager import ProtocolManager, ProtocolType as ServiceProtocolType
from app.services.integration_manager import IntegrationManager, IntegrationType as ServiceIntegrationType
from app.services.keycloak_client import KeycloakClient
from app.api.auth import get_keycloak_client

router = APIRouter(prefix="/internal/iam/protocols", tags=["protocols"])


def _resolve_tenant_id(
    request_context: RequestContext,
    requested_tenant_id: Optional[str] = None,
) -> str:
    authenticated_tenant_id = str(request_context.tenant_id)
    if requested_tenant_id is not None and requested_tenant_id != authenticated_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied: Tenant mismatch")
    return authenticated_tenant_id


def get_protocol_manager(
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
) -> ProtocolManager:
    """Get protocol manager instance."""
    return ProtocolManager(keycloak_client)


def get_integration_manager(
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
) -> IntegrationManager:
    """Get integration manager instance."""
    return IntegrationManager(keycloak_client)


@router.post("/saml", response_model=SAMLConfigResponse)
async def configure_saml(
    request: SAMLConfigRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    protocol_manager: ProtocolManager = Depends(get_protocol_manager)
) -> SAMLConfigResponse:
    """Configure SAML 2.0 identity provider."""
    try:
        result = protocol_manager.configure_saml_identity_provider(
            alias=request.alias,
            entity_id=request.entity_id,
            sso_url=request.sso_url,
            certificate=request.certificate,
            tenant_id=_resolve_tenant_id(request_context, request.tenant_id),
            config=request.config
        )
        return SAMLConfigResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error configuring SAML: {str(e)}")


@router.post("/oauth2", response_model=OAuth2ConfigResponse)
async def configure_oauth2(
    request: OAuth2ConfigRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    protocol_manager: ProtocolManager = Depends(get_protocol_manager)
) -> OAuth2ConfigResponse:
    """Configure OAuth 2.0 client."""
    try:
        result = protocol_manager.configure_oauth2_client(
            client_id=request.client_id,
            client_secret=request.client_secret,
            redirect_uris=request.redirect_uris,
            tenant_id=_resolve_tenant_id(request_context, request.tenant_id),
            config=request.config
        )
        return OAuth2ConfigResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error configuring OAuth 2.0: {str(e)}")


@router.post("/scim", response_model=SCIMConfigResponse)
async def configure_scim(
    request: SCIMConfigRequest,
    request_context: RequestContext = Depends(get_current_request_context)
) -> SCIMConfigResponse:
    """Outbound SCIM configuration is unavailable until storage/provider admission."""
    _resolve_tenant_id(request_context, request.tenant_id)
    raise HTTPException(status_code=501, detail="Outbound SCIM configuration is not implemented")


@router.post("/ldap", response_model=LDAPConfigResponse)
async def configure_ldap(
    request: LDAPConfigRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    protocol_manager: ProtocolManager = Depends(get_protocol_manager)
) -> LDAPConfigResponse:
    """Configure LDAP user federation."""
    try:
        result = protocol_manager.configure_ldap_federation(
            provider_name=request.provider_name,
            connection_url=request.connection_url,
            bind_dn=request.bind_dn,
            bind_credential=request.bind_credential,
            users_dn=request.users_dn,
            tenant_id=_resolve_tenant_id(request_context, request.tenant_id),
            config=request.config
        )
        return LDAPConfigResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error configuring LDAP: {str(e)}")


@router.get("/configurations")
async def list_protocol_configurations(
    protocol_type: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
    protocol_manager: ProtocolManager = Depends(get_protocol_manager)
) -> Dict[str, Any]:
    """List all protocol configurations."""
    try:
        protocol_enum = ServiceProtocolType(protocol_type) if protocol_type else None
        configurations = protocol_manager.list_protocol_configurations(
            protocol_type=protocol_enum,
            tenant_id=_resolve_tenant_id(request_context, tenant_id)
        )
        return {
            "configurations": configurations,
            "total": len(configurations)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing configurations: {str(e)}")


@router.post("/test/{config_id}")
async def test_protocol_connection(
    config_id: str,
    protocol_type: str,
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
    protocol_manager: ProtocolManager = Depends(get_protocol_manager)
) -> Dict[str, Any]:
    """Test connection to a protocol endpoint."""
    try:
        protocol_enum = ServiceProtocolType(protocol_type)
        result = protocol_manager.test_protocol_connection(
            config_id=config_id,
            protocol_type=protocol_enum,
            tenant_id=_resolve_tenant_id(request_context, tenant_id)
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing connection: {str(e)}")


# Integration endpoints

@router.post("/integrations/active-directory", response_model=IntegrationResponse)
async def create_ad_integration(
    request: ADIntegrationRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    integration_manager: IntegrationManager = Depends(get_integration_manager)
) -> IntegrationResponse:
    """Create Active Directory integration."""
    try:
        result = integration_manager.create_active_directory_integration(
            name=request.name,
            domain=request.domain,
            ldap_url=request.ldap_url,
            bind_dn=request.bind_dn,
            bind_password=request.bind_password,
            users_dn=request.users_dn,
            tenant_id=_resolve_tenant_id(request_context, request.tenant_id),
            sync_config=request.sync_config
        )
        return IntegrationResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating AD integration: {str(e)}")


@router.post("/integrations/azure-ad", response_model=IntegrationResponse)
async def create_azure_ad_integration(
    request: AzureADIntegrationRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    integration_manager: IntegrationManager = Depends(get_integration_manager)
) -> IntegrationResponse:
    """Create Azure AD integration."""
    try:
        result = integration_manager.create_azure_ad_integration(
            name=request.name,
            tenant_id_azure=request.tenant_id_azure,
            client_id=request.client_id,
            client_secret=request.client_secret,
            tenant_id=_resolve_tenant_id(request_context, request.tenant_id),
            sync_config=request.sync_config
        )
        return IntegrationResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating Azure AD integration: {str(e)}")


@router.post("/integrations/okta", response_model=IntegrationResponse)
async def create_okta_integration(
    request: OktaIntegrationRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    integration_manager: IntegrationManager = Depends(get_integration_manager)
) -> IntegrationResponse:
    """Create Okta integration."""
    try:
        result = integration_manager.create_okta_integration(
            name=request.name,
            okta_domain=request.okta_domain,
            client_id=request.client_id,
            client_secret=request.client_secret,
            tenant_id=_resolve_tenant_id(request_context, request.tenant_id),
            sync_config=request.sync_config
        )
        return IntegrationResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating Okta integration: {str(e)}")


@router.get("/integrations")
async def list_integrations(
    integration_type: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
    integration_manager: IntegrationManager = Depends(get_integration_manager)
) -> Dict[str, Any]:
    """List all integrations."""
    try:
        integration_enum = ServiceIntegrationType(integration_type) if integration_type else None
        integrations = integration_manager.list_integrations(
            integration_type=integration_enum,
            tenant_id=_resolve_tenant_id(request_context, tenant_id)
        )
        return {
            "integrations": integrations,
            "total": len(integrations)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing integrations: {str(e)}")


@router.post("/integrations/{integration_id}/sync", response_model=SyncResponse)
async def sync_integration(
    integration_id: str,
    sync_type: str = Query("full"),
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
    integration_manager: IntegrationManager = Depends(get_integration_manager)
) -> SyncResponse:
    """Trigger a sync for an integration."""
    try:
        result = integration_manager.sync_integration(
            integration_id=integration_id,
            sync_type=sync_type,
            tenant_id=_resolve_tenant_id(request_context, tenant_id)
        )
        return SyncResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing integration: {str(e)}")


@router.post("/integrations/{integration_id}/test")
async def test_integration(
    integration_id: str,
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
    integration_manager: IntegrationManager = Depends(get_integration_manager)
) -> Dict[str, Any]:
    """Test connection to an integration."""
    try:
        result = integration_manager.test_integration_connection(
            integration_id=integration_id,
            tenant_id=_resolve_tenant_id(request_context, tenant_id)
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing integration: {str(e)}")
