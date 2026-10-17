"""Protocol and Integration API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any, Optional
from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    ensure_request_has_any_role,
)
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
    SyncResponse,
)
from app.services.protocol_manager import ProtocolManager
from app.services.integration_manager import IntegrationManager

router = APIRouter(prefix="/internal/iam/protocols", tags=["protocols"])


def _resolve_tenant_id(
    request_context: RequestContext, requested_tenant_id: Optional[str] = None
) -> str:
    authenticated_tenant_id = str(request_context.tenant_id)
    if (
        requested_tenant_id is not None
        and requested_tenant_id != authenticated_tenant_id
    ):
        raise HTTPException(status_code=403, detail="Access denied: Tenant mismatch")
    return authenticated_tenant_id


def get_protocol_manager() -> ProtocolManager:
    return ProtocolManager(None)


def get_integration_manager() -> IntegrationManager:
    return IntegrationManager(None)


@router.post("/saml", response_model=SAMLConfigResponse)
async def configure_saml(
    request: SAMLConfigRequest,
    request_context: RequestContext = Depends(get_current_request_context),
) -> SAMLConfigResponse:
    _resolve_tenant_id(request_context, request.tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity protocol and integration operations are not qualified",
    )


@router.post("/oauth2", response_model=OAuth2ConfigResponse)
async def configure_oauth2(
    request: OAuth2ConfigRequest,
    request_context: RequestContext = Depends(get_current_request_context),
) -> OAuth2ConfigResponse:
    _resolve_tenant_id(request_context, request.tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity protocol and integration operations are not qualified",
    )


@router.post("/scim", response_model=SCIMConfigResponse)
async def configure_scim(
    request: SCIMConfigRequest,
    request_context: RequestContext = Depends(get_current_request_context),
) -> SCIMConfigResponse:
    _resolve_tenant_id(request_context, request.tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity protocol and integration operations are not qualified",
    )


@router.post("/ldap", response_model=LDAPConfigResponse)
async def configure_ldap(
    request: LDAPConfigRequest,
    request_context: RequestContext = Depends(get_current_request_context),
) -> LDAPConfigResponse:
    _resolve_tenant_id(request_context, request.tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity protocol and integration operations are not qualified",
    )


@router.get("/configurations")
async def list_protocol_configurations(
    protocol_type: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
) -> Dict[str, Any]:
    _resolve_tenant_id(request_context, tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity protocol and integration operations are not qualified",
    )


@router.post("/test/{config_id}")
async def test_protocol_connection(
    config_id: str,
    protocol_type: str,
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
) -> Dict[str, Any]:
    _resolve_tenant_id(request_context, tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity protocol and integration operations are not qualified",
    )


@router.post("/integrations/active-directory", response_model=IntegrationResponse)
async def create_ad_integration(
    request: ADIntegrationRequest,
    request_context: RequestContext = Depends(get_current_request_context),
) -> IntegrationResponse:
    _resolve_tenant_id(request_context, request.tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity protocol and integration operations are not qualified",
    )


@router.post("/integrations/azure-ad", response_model=IntegrationResponse)
async def create_azure_ad_integration(
    request: AzureADIntegrationRequest,
    request_context: RequestContext = Depends(get_current_request_context),
) -> IntegrationResponse:
    _resolve_tenant_id(request_context, request.tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity protocol and integration operations are not qualified",
    )


@router.post("/integrations/okta", response_model=IntegrationResponse)
async def create_okta_integration(
    request: OktaIntegrationRequest,
    request_context: RequestContext = Depends(get_current_request_context),
) -> IntegrationResponse:
    _resolve_tenant_id(request_context, request.tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity protocol and integration operations are not qualified",
    )


@router.get("/integrations")
async def list_integrations(
    integration_type: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
) -> Dict[str, Any]:
    _resolve_tenant_id(request_context, tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity protocol and integration operations are not qualified",
    )


@router.post("/integrations/{integration_id}/sync", response_model=SyncResponse)
async def sync_integration(
    integration_id: str,
    sync_type: str = Query("full"),
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
) -> SyncResponse:
    _resolve_tenant_id(request_context, tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity protocol and integration operations are not qualified",
    )


@router.post("/integrations/{integration_id}/test")
async def test_integration(
    integration_id: str,
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
) -> Dict[str, Any]:
    _resolve_tenant_id(request_context, tenant_id)
    ensure_request_has_any_role(
        request_context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"
    )
    raise HTTPException(
        status_code=501,
        detail="Identity protocol and integration operations are not qualified",
    )
