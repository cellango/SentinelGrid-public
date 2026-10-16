"""
External Identity Provider Integration API endpoints.

Supports connecting Microsoft 365, Google Workspace, and other external IdPs.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import httpx
import re

from app.api.request_context import (
    RequestContext,
    ensure_request_has_any_role,
    get_current_request_context,
)
from app.services.keycloak_admin_client import KeycloakAdminClient
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/idp", tags=["external-idp"])


# ============================================================================
# Request/Response Models
# ============================================================================

class MicrosoftConnectRequest(BaseModel):
    """Microsoft 365 connection request."""
    tenant_id: str  # Azure AD tenant ID
    client_id: str  # Azure AD application client ID
    client_secret: str  # Azure AD application secret
    sync_users: bool = True
    sync_groups: bool = False


class GoogleConnectRequest(BaseModel):
    """Google Workspace connection request."""
    domain: str  # Google Workspace domain
    client_id: str  # Google OAuth client ID
    client_secret: str  # Google OAuth client secret
    sync_users: bool = True
    sync_groups: bool = False


class IdPProviderResponse(BaseModel):
    """IdP provider response."""
    alias: str
    provider_id: str
    display_name: str
    provider_type: str  # 'microsoft', 'google', 'saml', 'oidc'
    enabled: bool
    first_broker_login_flow_alias: Optional[str]
    post_broker_login_flow_alias: Optional[str]
    config: dict
    created_at: Optional[str]


class OIDCDiscoveryTestRequest(BaseModel):
    """Test an OIDC discovery endpoint (optionally token call)."""
    discovery_url: str
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    scope: str = "openid email profile"


class OIDCDiscoveryTestResponse(BaseModel):
    discovery_ok: bool
    token_ok: bool
    issuer: Optional[str] = None
    auth_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None
    error: Optional[str] = None


class SAMLMetadataTestRequest(BaseModel):
    """Test a SAML metadata URL."""
    metadata_url: str


class SAMLMetadataTestResponse(BaseModel):
    metadata_ok: bool
    entity_id: Optional[str] = None
    error: Optional[str] = None


class GatewayEndpointsResponse(BaseModel):
    """Public gateway endpoints for IdP config."""
    acs_url: str
    saml_metadata_url: str
    oidc_authorize_url: str
    oidc_callback_url: str
    oidc_logout_url: str
    tenant_param: str


class OIDCIdPCreateRequest(BaseModel):
    """Create external OIDC IdP in Keycloak (per-tenant)."""
    display_name: str
    discovery_url: str
    client_id: str
    client_secret: str
    scopes: List[str] = ["openid", "email", "profile"]
    prompt: Optional[str] = None
    allowed_domains: List[str] = []
    default_role: Optional[str] = None
    claim_mappings: List[dict] = []
    link_only: bool = False
    store_token: bool = False
    trust_email: bool = True
    group_role_mappings: List[dict] = []


class SAMLIdPCreateRequest(BaseModel):
    """Create external SAML IdP in Keycloak (per-tenant)."""
    display_name: str
    metadata_url: str
    authn_contexts: List[str] = []
    allowed_domains: List[str] = []
    default_role: Optional[str] = None
    claim_mappings: List[dict] = []
    force_authn: bool = False
    post_binding_response: bool = True
    post_binding_logout: bool = True
    validate_signature: bool = True
    group_role_mappings: List[dict] = []


# ============================================================================
# Helper Functions
# ============================================================================

async def get_token_data(credentials: str) -> dict:
    """Extract and validate token, return token data with tenant_id."""
    from app.services.token_validator import TokenValidator
    from app.services.keycloak_client import KeycloakClient
    
    keycloak_client = KeycloakClient()
    validator = TokenValidator(keycloak_client)
    result = validator.validate_token(credentials)
    
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if not result.get("tenant_id"):
        raise HTTPException(status_code=403, detail="No tenant_id in token")
    
    return result


def require_idp_admin_request_context(
    request_context: RequestContext = Depends(get_current_request_context),
) -> RequestContext:
    """Require an authenticated admin identity for IdP diagnostics and configuration."""
    ensure_request_has_any_role(request_context, "TENANT_ADMIN", "PLATFORM_ADMIN")
    return request_context


def get_realm_for_tenant(tenant_id: str) -> str:
    """Get Keycloak realm name for tenant."""
    return settings.KEYCLOAK_REALM


def _sanitize_alias(name: str, tenant_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip()).strip("-").lower()
    return f"{safe}-{tenant_id}"


def _ensure_https(url: str, field: str):
    if not url.lower().startswith("https://"):
        raise HTTPException(status_code=400, detail=f"{field} must be https://")


async def _add_claim_mappers(kc: KeycloakAdminClient, realm: str, alias: str, mappings: List[dict], kind: str):
    """
    Add claim/attribute mappers for OIDC/SAML.
    kind: 'oidc' or 'saml'
    """
    for mapping in mappings or []:
        source = mapping.get("claim") or mapping.get("attribute") or mapping.get("from")
        target = mapping.get("to") or mapping.get("user_attribute") or mapping.get("attribute_name") or mapping.get("attr")
        if not source or not target:
            continue
        if kind == "oidc":
            mapper = {
                "identityProviderAlias": alias,
                "name": f"claim-{source}",
                "identityProviderMapper": "oidc-user-attribute-idp-mapper",
                "config": {"claim": source, "user.attribute": target},
            }
        else:
            mapper = {
                "identityProviderAlias": alias,
                "name": f"claim-{source}",
                "identityProviderMapper": "saml-user-attribute-idp-mapper",
                "config": {
                    "attribute.name": source,
                    "user.attribute": target,
                },
            }
        await kc._make_request(
            "POST",
            f"/realms/{realm}/identity-provider/instances/{alias}/mappers",
            json_data=mapper,
        )


async def _add_default_role(kc: KeycloakAdminClient, realm: str, alias: str, role: Optional[str], kind: str):
    """Attach a hardcoded role mapper if default_role provided."""
    if not role:
        return
    mapper_type = "oidc-hardcoded-role-idp-mapper" if kind == "oidc" else "saml-hardcoded-role-idp-mapper"
    mapper = {
        "identityProviderAlias": alias,
        "name": f"default-role-{role}",
        "identityProviderMapper": mapper_type,
        "config": {"role": role},
    }
    await kc._make_request(
        "POST",
        f"/realms/{realm}/identity-provider/instances/{alias}/mappers",
        json_data=mapper,
    )


# ============================================================================
# External IdP Endpoints
# ============================================================================


@router.get("/gateway/endpoints", response_model=GatewayEndpointsResponse)
async def get_gateway_endpoints(
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Return public gateway endpoints (ACS/redirect) to share with customer IdPs.
    Keycloak stays private; all callbacks go through our gateway.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    base = settings.PUBLIC_AUTH_BASE_URL.rstrip("/")
    tenant_param = f"tenant_id={tenant_id}"

    return GatewayEndpointsResponse(
        acs_url=f"{base}/auth/saml/acs?{tenant_param}",
        saml_metadata_url=f"{base}/auth/saml/metadata?{tenant_param}",
        oidc_authorize_url=f"{base}/auth/oidc/authorize?{tenant_param}",
        oidc_callback_url=f"{base}/auth/oidc/callback?{tenant_param}",
        oidc_logout_url=f"{base}/auth/oidc/logout?{tenant_param}",
        tenant_param=tenant_param,
    )


@router.post("/test/oidc", response_model=OIDCDiscoveryTestResponse)
async def test_oidc_discovery(
    payload: OIDCDiscoveryTestRequest,
    request_context: RequestContext = Depends(require_idp_admin_request_context),
):
    """
    Validate OIDC discovery endpoint and optionally perform client_credentials token call.
    """
    try:
        _ = request_context
        async with httpx.AsyncClient(timeout=10.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
            disc_resp = await client.get(payload.discovery_url)
            disc_resp.raise_for_status()
            discovery = disc_resp.json()
            token_endpoint = discovery.get("token_endpoint")
            auth_endpoint = discovery.get("authorization_endpoint")

            token_ok = False
            if payload.client_id and payload.client_secret and token_endpoint:
                token_resp = await client.post(
                    token_endpoint,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": payload.client_id,
                        "client_secret": payload.client_secret,
                        "scope": payload.scope,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                token_ok = token_resp.status_code == 200

            return OIDCDiscoveryTestResponse(
                discovery_ok=True,
                token_ok=token_ok,
                issuer=discovery.get("issuer"),
                auth_endpoint=auth_endpoint,
                token_endpoint=token_endpoint,
                error=None,
            )
    except Exception as exc:
        logger.warning(f"OIDC discovery test failed: {exc}")
        return OIDCDiscoveryTestResponse(
            discovery_ok=False,
            token_ok=False,
            issuer=None,
            auth_endpoint=None,
            token_endpoint=None,
            error=str(exc),
        )


@router.post("/test/saml", response_model=SAMLMetadataTestResponse)
async def test_saml_metadata(
    payload: SAMLMetadataTestRequest,
    request_context: RequestContext = Depends(require_idp_admin_request_context),
):
    """
    Fetch and sanity-check SAML metadata URL.
    """
    try:
        _ = request_context
        async with httpx.AsyncClient(timeout=10.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
            resp = await client.get(payload.metadata_url)
            resp.raise_for_status()
            text = resp.text
            entity_id = None
            match = re.search(r'entityID="([^"]+)"', text)
            if match:
                entity_id = match.group(1)
            return SAMLMetadataTestResponse(
                metadata_ok=True,
                entity_id=entity_id,
                error=None,
            )
    except Exception as exc:
        logger.warning(f"SAML metadata test failed: {exc}")
        return SAMLMetadataTestResponse(
            metadata_ok=False,
            entity_id=None,
            error=str(exc),
        )


@router.post("/oidc", summary="Create external OIDC IdP for this tenant")
async def create_oidc_idp(
    payload: OIDCIdPCreateRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Create an OIDC identity provider in Keycloak for this tenant.
    Keycloak stays private; redirect/ACS go through the gateway host.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    alias = _sanitize_alias(payload.display_name, tenant_id)

    # Basic validation
    _ensure_https(payload.discovery_url, "discovery_url")

    try:
        async with KeycloakAdminClient() as kc:
            idp_config = {
                "alias": alias,
                "displayName": payload.display_name,
                "providerId": "oidc",
                "enabled": True,
                "trustEmail": payload.trust_email,
                "storeToken": payload.store_token,
                "linkOnly": payload.link_only,
                "firstBrokerLoginFlowAlias": "first broker login",
                "config": {
                    "clientId": payload.client_id,
                    "clientSecret": payload.client_secret,
                    "useJwksUrl": "true",
                    "authorizationUrl": None,  # derived from discovery
                    "tokenUrl": None,
                    "logoutUrl": None,
                    "defaultScope": " ".join(payload.scopes),
                    "prompt": payload.prompt or "",
                    "validateSignature": "true",
                    "backchannelSupported": "true",
                    "syncMode": "IMPORT",
                    "allowedDomains": ",".join(payload.allowed_domains),
                    "discoveryEndpoint": payload.discovery_url,
                },
            }

            # Create identity provider
            resp = await kc._make_request(
                "POST", f"/realms/{realm}/identity-provider/instances", json_data=idp_config
            )
            resp.raise_for_status()

            # Basic mapper to pull email/subject
            mapper = {
                "identityProviderAlias": alias,
                "name": "email",
                "identityProviderMapper": "oidc-user-attribute-idp-mapper",
                "config": {"claim": "email", "user.attribute": "email"},
            }
            await kc._make_request(
                "POST", f"/realms/{realm}/identity-provider/instances/{alias}/mappers", json_data=mapper
            )

            await _add_default_role(kc, realm, alias, payload.default_role, "oidc")
            await _add_claim_mappers(kc, realm, alias, payload.claim_mappings, "oidc")

            # Optional group->role mappers (maps token group to realm role)
            for mapping in payload.group_role_mappings:
                group_value = mapping.get("group") or mapping.get("value")
                role_value = mapping.get("role")
                if not group_value or not role_value:
                    continue
                role_mapper = {
                    "identityProviderAlias": alias,
                    "name": f"role-{group_value}",
                    "identityProviderMapper": "oidc-role-idp-mapper",
                    "config": {
                        "claim": "groups",
                        "claim.value": group_value,
                        "role": role_value,
                    },
                }
                await kc._make_request(
                    "POST",
                    f"/realms/{realm}/identity-provider/instances/{alias}/mappers",
                    json_data=role_mapper,
                )

            return {"success": True, "alias": alias, "message": "OIDC IdP created"}
    except Exception as exc:
        logger.error(f"Failed to create OIDC IdP: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create OIDC IdP: {exc}")


@router.post("/saml", summary="Create external SAML IdP for this tenant")
async def create_saml_idp(
    payload: SAMLIdPCreateRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Create a SAML identity provider in Keycloak for this tenant.
    Keycloak stays private; ACS goes through the gateway host.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    alias = _sanitize_alias(payload.display_name, tenant_id)

    _ensure_https(payload.metadata_url, "metadata_url")

    try:
        async with KeycloakAdminClient() as kc:
            idp_config = {
                "alias": alias,
                "displayName": payload.display_name,
                "providerId": "saml",
                "enabled": True,
                "storeToken": False,
                "linkOnly": False,
                "firstBrokerLoginFlowAlias": "first broker login",
                "config": {
                    "validateSignature": "true" if payload.validate_signature else "false",
                    "wantAuthnRequestsSigned": "false",
                    "forceAuthn": "true" if payload.force_authn else "false",
                    "singleSignOnServiceUrl": None,  # derived from metadata
                    "singleLogoutServiceUrl": None,
                    "postBindingResponse": "true" if payload.post_binding_response else "false",
                    "postBindingLogout": "true" if payload.post_binding_logout else "false",
                    "nameIDPolicyFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                    "syncMode": "IMPORT",
                    "allowedDomains": ",".join(payload.allowed_domains),
                    "authnContextClassRefs": " ".join(payload.authn_contexts),
                    "metadataUrl": payload.metadata_url,
                },
            }

            resp = await kc._make_request(
                "POST", f"/realms/{realm}/identity-provider/instances", json_data=idp_config
            )
            resp.raise_for_status()

            # Basic mapper to pull email
            mapper = {
                "identityProviderAlias": alias,
                "name": "email",
                "identityProviderMapper": "saml-user-attribute-idp-mapper",
                "config": {"attribute.name": "email", "user.attribute": "email"},
            }
            await kc._make_request(
                "POST", f"/realms/{realm}/identity-provider/instances/{alias}/mappers", json_data=mapper
            )

            await _add_default_role(kc, realm, alias, payload.default_role, "saml")
            await _add_claim_mappers(kc, realm, alias, payload.claim_mappings, "saml")

            # Optional group->role mappers (maps SAML attribute to realm role)
            for mapping in payload.group_role_mappings:
                group_value = mapping.get("group") or mapping.get("value")
                role_value = mapping.get("role")
                if not group_value or not role_value:
                    continue
                role_mapper = {
                    "identityProviderAlias": alias,
                    "name": f"role-{group_value}",
                    "identityProviderMapper": "saml-role-idp-mapper",
                    "config": {
                        "attribute.name": "memberOf",
                        "attribute.friendly.name": "memberOf",
                        "attribute.value": group_value,
                        "role": role_value,
                    },
                }
                await kc._make_request(
                    "POST",
                    f"/realms/{realm}/identity-provider/instances/{alias}/mappers",
                    json_data=role_mapper,
                )

            return {"success": True, "alias": alias, "message": "SAML IdP created"}
    except Exception as exc:
        logger.error(f"Failed to create SAML IdP: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create SAML IdP: {exc}")


@router.post("/microsoft/connect")
async def connect_microsoft(
    request: MicrosoftConnectRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Connect Microsoft 365 as external Identity Provider.
    
    Creates Keycloak identity provider for Azure AD.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    logger.info(f"Connecting Microsoft 365 for tenant {tenant_id}")
    
    try:
        async with KeycloakAdminClient() as kc:
            # Create Microsoft identity provider
            idp_alias = f"microsoft-{tenant_id}"
            
            idp_config = {
                "alias": idp_alias,
                "providerId": "microsoft",
                "enabled": True,
                "updateProfileFirstLoginMode": "on",
                "trustEmail": True,
                "storeToken": False,
                "addReadTokenRoleOnCreate": False,
                "authenticateByDefault": False,
                "linkOnly": False,
                "firstBrokerLoginFlowAlias": "first broker login",
                "config": {
                    "clientId": request.client_id,
                    "clientSecret": request.client_secret,
                    "defaultScope": "openid email profile",
                    "tenant": request.tenant_id,
                    "syncMode": "IMPORT" if request.sync_users else "LEGACY",
                }
            }
            
            # Create identity provider
            response = await kc._make_request(
                "POST",
                f"/realms/{realm}/identity-provider/instances",
                json_data=idp_config
            )
            response.raise_for_status()
            
            logger.info(f"Microsoft 365 connected successfully for tenant {tenant_id}")
            
            return {
                "success": True,
                "alias": idp_alias,
                "message": "Microsoft 365 connected successfully",
                "sync_enabled": request.sync_users
            }
            
    except Exception as e:
        logger.error(f"Error connecting Microsoft 365: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to connect Microsoft 365: {str(e)}")


@router.post("/google/connect")
async def connect_google(
    request: GoogleConnectRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Connect Google Workspace as external Identity Provider.
    
    Creates Keycloak identity provider for Google OAuth.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    logger.info(f"Connecting Google Workspace for tenant {tenant_id}")
    
    try:
        async with KeycloakAdminClient() as kc:
            # Create Google identity provider
            idp_alias = f"google-{tenant_id}"
            
            idp_config = {
                "alias": idp_alias,
                "providerId": "google",
                "enabled": True,
                "updateProfileFirstLoginMode": "on",
                "trustEmail": True,
                "storeToken": False,
                "addReadTokenRoleOnCreate": False,
                "authenticateByDefault": False,
                "linkOnly": False,
                "firstBrokerLoginFlowAlias": "first broker login",
                "config": {
                    "clientId": request.client_id,
                    "clientSecret": request.client_secret,
                    "defaultScope": "openid email profile",
                    "hostedDomain": request.domain,
                    "syncMode": "IMPORT" if request.sync_users else "LEGACY",
                }
            }
            
            # Create identity provider
            response = await kc._make_request(
                "POST",
                f"/realms/{realm}/identity-provider/instances",
                json_data=idp_config
            )
            response.raise_for_status()
            
            logger.info(f"Google Workspace connected successfully for tenant {tenant_id}")
            
            return {
                "success": True,
                "alias": idp_alias,
                "message": "Google Workspace connected successfully",
                "sync_enabled": request.sync_users
            }
            
    except Exception as e:
        logger.error(f"Error connecting Google Workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to connect Google Workspace: {str(e)}")


@router.get("/providers", response_model=List[IdPProviderResponse])
async def list_idp_providers(
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """List connected identity providers for the tenant."""
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            response = await kc._make_request(
                "GET",
                f"/realms/{realm}/identity-provider/instances"
            )
            response.raise_for_status()
            providers = response.json()
            
            # Filter to tenant's providers (by alias pattern)
            tenant_providers = [
                p for p in providers
                if tenant_id in p.get("alias", "")
            ]
            
            return [
                IdPProviderResponse(
                    alias=provider.get("alias", ""),
                    provider_id=provider.get("providerId", ""),
                    display_name=provider.get("displayName", provider.get("alias", "")),
                    provider_type=provider.get("providerId", ""),
                    enabled=provider.get("enabled", False),
                    first_broker_login_flow_alias=provider.get("firstBrokerLoginFlowAlias"),
                    post_broker_login_flow_alias=provider.get("postBrokerLoginFlowAlias"),
                    config=provider.get("config", {}),
                    created_at=None
                )
                for provider in tenant_providers
            ]
            
    except Exception as e:
        logger.error(f"Error listing IdP providers: {e}")
        raise HTTPException(status_code=500, detail="Failed to list identity providers")


@router.delete("/providers/{alias}")
async def disconnect_idp(
    alias: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """Disconnect an identity provider."""
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    # Verify alias belongs to tenant
    if tenant_id not in alias:
        raise HTTPException(status_code=404, detail="Identity provider not found")
    
    try:
        async with KeycloakAdminClient() as kc:
            await kc._make_request(
                "DELETE",
                f"/realms/{realm}/identity-provider/instances/{alias}"
            )
            
            logger.info(f"Identity provider {alias} disconnected for tenant {tenant_id}")
            
            return {"success": True, "message": "Identity provider disconnected"}
            
    except Exception as e:
        logger.error(f"Error disconnecting IdP: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect identity provider")
