"""
App Catalog API endpoints.

Provides prebuilt app templates and one-click SSO setup.
"""

import logging
import re
import uuid
from typing import List, Optional
import json
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.api.request_context import get_tenant_session
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/apps/catalog", tags=["app-catalog"])
portal_router = APIRouter(prefix="/api/iam-portal/catalog/apps", tags=["app-catalog"])
SLUG_REGEX = re.compile(r"^[a-z0-9][a-z0-9-_]{2,63}$")


# ============================================================================
# Request/Response Models
# ============================================================================

class AppCatalogItem(BaseModel):
    """App catalog item response."""
    id: str
    name: str
    display_name: str
    description: Optional[str]
    app_type: str
    protocol: str
    icon_url: Optional[str]
    category: Optional[str]
    required_fields: List[str]
    optional_fields: List[str]
    default_config: dict
    setup_guide: Optional[str]


class AppCatalogListResponse(BaseModel):
    """App catalog list response."""
    items: List[AppCatalogItem]
    total: int


class ConnectAppRequest(BaseModel):
    """Connect app request."""
    catalog_app_id: str
    config: dict  # App-specific configuration


class ConnectAppResponse(BaseModel):
    """Connect app response."""
    success: bool
    app_id: str
    client_id: str
    message: str


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
    
    # Attach realm_name from issuer if present
    iss = result.get("payload", {}).get("iss", "")
    realm_name = iss.split("/realms/")[-1] if "/realms/" in iss else settings.KEYCLOAK_REALM
    result["realm_name"] = realm_name
    return result


def get_realm_for_tenant(tenant_id: str) -> str:
    """Get Keycloak realm name for tenant."""
    return settings.KEYCLOAK_REALM


def get_realm_from_token_data(token_data: dict) -> str:
    """Derive realm from token payload (fallback to default)."""
    return token_data.get("realm_name") or settings.KEYCLOAK_REALM


def _slugify(value: str) -> str:
    value = (value or "").lower().strip()
    value = re.sub(r'[^a-z0-9-_]+', '-', value)
    value = re.sub(r'-{2,}', '-', value).strip('-')
    return value or "app"


def _normalize_slug(value: str, fallback: str = "app") -> str:
    base = _slugify(value or fallback)
    base = base[:64]
    if len(base) < 3:
        base = (f"{base}-{fallback}")[:64]
    return base


def _validate_slug_or_400(slug: str, kind: str = "slug"):
    if not SLUG_REGEX.match(slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {kind}: must be 3-64 chars, lowercase letters/numbers/hyphen/underscore, starting alphanumeric.",
        )


def _prefixed_role(app_slug: str, ent: str) -> str:
    raw = _slugify(ent)
    if not raw:
        return ""
    if ":" in raw:
        return raw[:64]
    role = f"{app_slug}:{raw}"
    return role[:64]


def _auth_header(request: Request) -> str:
    """Return bearer token (without prefix) or empty string."""
    return request.headers.get("authorization", "").replace("Bearer ", "")


DEFAULT_CATALOG = [
    {
        "id": str(uuid.uuid4()),
        "name": "custom_byo_proxy",
        "display_name": "Bring Your Own App (Auth Proxy)",
        "description": "Front any homegrown app with an auth proxy (OIDC) and inject headers (X-User/X-Roles).",
        "app_type": "Custom",
        "protocol": "OIDC",
        "icon_url": None,
        "category": "Custom",
        "required_fields": ["redirect_uri"],
        "optional_fields": ["entitlements", "assign_groups", "assign_users"],
        "default_config": {
            "entitlements": "admin, user",
            "activation_mode": "draft",
            "redirect_uris": "https://app.example.com/oauth2/callback",
        },
        "setup_guide": "Use oauth2-proxy or nginx auth_request in front of your app. Configure issuer/client_id/secret from this entry, and trust X-User/X-Email/X-Roles headers.",
    },
    {
        "id": str(uuid.uuid4()),
        "name": "gitlab",
        "display_name": "GitLab",
        "description": "Connect GitLab for SSO (SAML).",
        "app_type": "SaaS",
        "protocol": "SAML",
        "icon_url": None,
        "category": "Development",
        "required_fields": ["redirect_uri", "entity_id"],
        "optional_fields": ["name_id_format"],
        "default_config": {},
        "setup_guide": "GitLab SAML: configure ACS/Entity ID; map email as NameID.",
    },
]


# ============================================================================
# App Catalog Endpoints
# ============================================================================

@router.get("", response_model=AppCatalogListResponse)
async def list_app_catalog(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search apps"),
    db: Session = Depends(get_tenant_session),
    authorization: str = Depends(_auth_header)
):
    """
    List available apps in the catalog.
    
    Can filter by category and search by name/description.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    try:
        catalog_apps: list[dict] = []
        try:
            rows = db.execute(
                text(
                    """
                    SELECT id, name, display_name, description, app_type, protocol, icon_url, category,
                           required_fields, optional_fields, default_config, setup_guide, is_active
                    FROM app_catalog
                    WHERE is_active = true
                    """
                )
            ).fetchall()
            if rows:
                for row in rows:
                    catalog_apps.append(
                        {
                            "id": str(row.id),
                            "name": row.name,
                            "display_name": row.display_name,
                            "description": row.description,
                            "app_type": row.app_type,
                            "protocol": row.protocol,
                            "icon_url": row.icon_url,
                            "category": row.category,
                            "required_fields": row.required_fields or [],
                            "optional_fields": row.optional_fields or [],
                            "default_config": row.default_config or {},
                            "setup_guide": row.setup_guide,
                        }
                    )
            else:
                # seed defaults if table exists but empty
                for item in DEFAULT_CATALOG:
                    db.execute(
                        text(
                            """
                            INSERT INTO app_catalog (id, name, display_name, description, app_type, protocol, icon_url, category, required_fields, optional_fields, default_config, setup_guide, is_active)
                            VALUES (:id, :name, :display_name, :description, :app_type, :protocol, :icon_url, :category, :required_fields::jsonb, :optional_fields::jsonb, :default_config::jsonb, :setup_guide, true)
                            ON CONFLICT (name) DO NOTHING
                            """
                        ),
                        {
                            "id": item["id"],
                            "name": item["name"],
                            "display_name": item["display_name"],
                            "description": item.get("description"),
                            "app_type": item.get("app_type"),
                            "protocol": item.get("protocol"),
                            "icon_url": item.get("icon_url"),
                            "category": item.get("category"),
                            "required_fields": item.get("required_fields", []),
                            "optional_fields": item.get("optional_fields", []),
                            "default_config": item.get("default_config", {}),
                            "setup_guide": item.get("setup_guide"),
                        },
                    )
                db.commit()
                catalog_apps = DEFAULT_CATALOG.copy()
        except Exception as e:
            logger.warning(f"Falling back to static catalog (DB not available): {e}")
            catalog_apps = DEFAULT_CATALOG.copy()

        # Filter by category
        if category:
            catalog_apps = [app for app in catalog_apps if app.get("category") == category]

        # Search
        if search:
            search_lower = search.lower()
            catalog_apps = [
                app for app in catalog_apps
                if search_lower in (app.get("display_name") or "").lower() or
                   search_lower in (app.get("description") or "").lower()
            ]

        return AppCatalogListResponse(
            items=[
                AppCatalogItem(
                    id=app["id"],
                    name=app["name"],
                    display_name=app["display_name"],
                    description=app.get("description"),
                    app_type=app["app_type"],
                    protocol=app["protocol"],
                    icon_url=app.get("icon_url"),
                    category=app.get("category"),
                    required_fields=app.get("required_fields", []),
                    optional_fields=app.get("optional_fields", []),
                    default_config=app.get("default_config", {}),
                    setup_guide=app.get("setup_guide")
                )
                for app in catalog_apps
            ],
            total=len(catalog_apps)
        )

    except Exception as e:
        logger.error(f"Error listing app catalog: {e}")
        raise HTTPException(status_code=500, detail="Failed to list app catalog")


@portal_router.get("", response_model=AppCatalogListResponse)
async def list_app_catalog_portal(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search apps"),
    db: Session = Depends(get_tenant_session),
    authorization: str = Depends(_auth_header)
):
    """Portal prefix for app catalog (same as /api/v1/apps/catalog)."""
    return await list_app_catalog(category, search, db, authorization)


@router.get("/{app_id}", response_model=AppCatalogItem)
async def get_app_catalog_item(
    app_id: str,
    db: Session = Depends(get_tenant_session),
    authorization: str = Depends(_auth_header)
):
    """Get details for a specific app in the catalog."""
    await get_token_data(authorization)

    try:
        row = db.execute(
            text(
                """
                SELECT id, name, display_name, description, app_type, protocol, icon_url, category,
                       required_fields, optional_fields, default_config, setup_guide
                FROM app_catalog
                WHERE (id = :id OR name = :id) AND is_active = true
                LIMIT 1
                """
            ),
            {"id": app_id},
        ).fetchone()
        if row:
            return AppCatalogItem(
                id=str(row.id),
                name=row.name,
                display_name=row.display_name,
                description=row.description,
                app_type=row.app_type,
                protocol=row.protocol,
                icon_url=row.icon_url,
                category=row.category,
                required_fields=row.required_fields or [],
                optional_fields=row.optional_fields or [],
                default_config=row.default_config or {},
                setup_guide=row.setup_guide,
            )
    except Exception as exc:
        logger.warning(f"Catalog item DB lookup failed, falling back to defaults: {exc}")

    for app in DEFAULT_CATALOG:
        if app["name"] == app_id or app["id"] == app_id:
            return AppCatalogItem(
                id=app["id"],
                name=app["name"],
                display_name=app["display_name"],
                description=app.get("description"),
                app_type=app["app_type"],
                protocol=app["protocol"],
                icon_url=app.get("icon_url"),
                category=app.get("category"),
                required_fields=app.get("required_fields", []),
                optional_fields=app.get("optional_fields", []),
                default_config=app.get("default_config", {}),
                setup_guide=app.get("setup_guide")
            )

    raise HTTPException(status_code=404, detail="App not found")


@router.get("/{app_id}/setup-guide")
async def get_setup_guide(
    app_id: str,
    db: Session = Depends(get_tenant_session),
    authorization: str = Depends(_auth_header)
):
    """Get setup guide for an app."""
    await get_token_data(authorization)

    # Try DB first
    try:
        row = db.execute(
            text(
                """
                SELECT setup_guide FROM app_catalog
                WHERE (id = :id OR name = :id) AND is_active = true
                LIMIT 1
                """
            ),
            {"id": app_id},
        ).fetchone()
        if row and row[0]:
            return {
                "app_id": app_id,
                "setup_guide": row[0],
                "format": "markdown",
            }
    except Exception as exc:
        logger.warning(f"Setup guide DB lookup failed, falling back to defaults: {exc}")

    for app in DEFAULT_CATALOG:
        if app["name"] == app_id or app["id"] == app_id:
            return {
                "app_id": app_id,
                "setup_guide": app.get("setup_guide", ""),
                "format": "markdown",
            }

    raise HTTPException(status_code=404, detail="App not found")


@router.post("/{app_id}/connect", response_model=ConnectAppResponse)
async def connect_app(
    app_id: str,
    request: ConnectAppRequest,
    authorization: str = Depends(_auth_header),
    db: Session = Depends(get_tenant_session),
):
    """
    One-click connect for a prebuilt app.
    
    Creates Keycloak client and configures SSO based on app template.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_from_token_data(token_data)
    
    logger.info(f"Connecting app {app_id} for tenant {tenant_id}")
    
    try:
        cfg = request.config or {}
        # Resolve template metadata (protocol)
        template_protocol = None
        try:
            row = db.execute(text("SELECT protocol FROM app_catalog WHERE id = :id LIMIT 1"), {"id": app_id}).first()
            if row:
                template_protocol = row[0]
            else:
                tmpl = next((c for c in DEFAULT_CATALOG if c["id"] == app_id), None)
                if tmpl:
                    template_protocol = tmpl.get("protocol")
        except Exception:
            template_protocol = None
        # resolve tenant slug (tenant_short)
        tenant_row = db.execute(text("SELECT slug FROM tenants WHERE id = :id LIMIT 1"), {"id": tenant_id}).first()
        if not tenant_row:
            raise HTTPException(status_code=404, detail="Tenant not found")
        tenant_slug = tenant_row[0]
        _validate_slug_or_400(tenant_slug, "tenant slug")

        app_slug_input = cfg.get("app_slug") or cfg.get("app_name") or app_id
        app_slug = _normalize_slug(app_slug_input, "app")
        _validate_slug_or_400(app_slug, "app slug")

        protocol = (cfg.get("protocol") or template_protocol or (app_id.startswith("oidc") and "oidc" or "saml")).lower()
        redirect_uris = []
        if cfg.get("redirect_uris"):
            redirect_uris = [u.strip() for u in str(cfg.get("redirect_uris")).split(",") if u.strip()]
        if cfg.get("redirect_uri"):
            redirect_uris.append(cfg.get("redirect_uri"))
        acs_url = cfg.get("acs_url") or cfg.get("redirect_uri")
        requires_redirects = protocol == "oidc"
        requires_acs = protocol.startswith("saml")

        if requires_redirects and not redirect_uris:
            raise HTTPException(status_code=400, detail="Redirect URIs are required for OIDC apps.")
        if requires_acs and not acs_url:
            raise HTTPException(status_code=400, detail="ACS URL is required for SAML apps.")

        activation_mode = (cfg.get("activation_mode") or "draft").lower()

        client_id_base = f"{tenant_slug}_{app_slug}"
        client_id_base = client_id_base[:60]
        client_id = client_id_base

        client_data = {
            "clientId": client_id,
            "name": cfg.get("app_name") or app_id.replace("_", " ").title(),
            "protocol": "openid-connect" if protocol == "oidc" else "saml",
            "enabled": activation_mode == "active",
        }

        if protocol == "oidc":
            client_data.update({
                "publicClient": False,
                "bearerOnly": False,
                "standardFlowEnabled": True,
                "implicitFlowEnabled": False,
                "directAccessGrantsEnabled": False,
                "serviceAccountsEnabled": False,
                "attributes": {
                    "pkce.code.challenge.method": "S256" if cfg.get("pkce_required", True) else "plain",
                },
                "redirectUris": redirect_uris or ["https://example.com/callback"],
            })
            if cfg.get("refresh_tokens"):
                client_data["attributes"]["oauth2.device.authorization.grant.enabled"] = "true"
        else:
            client_data.update({
                "redirectUris": [acs_url] if acs_url else [],
                "attributes": {
                    "saml.assertion.signature": "true" if cfg.get("sign_assertions", True) else "false",
                    "saml.force.post.binding": "true",
                    "saml.server.signature": "true",
                    "saml.nameid.format": cfg.get("nameid_format") or "email",
                },
            })

        ent_str = cfg.get("entitlements") or ""
        entitlements = [_prefixed_role(app_slug, e) for e in ent_str.split(",") if e.strip()]
        entitlements = [e for e in entitlements if e]

        assign_groups = [g.strip() for g in str(cfg.get("assign_groups") or "").split(",") if g.strip()]
        assign_users = [u.strip() for u in str(cfg.get("assign_users") or "").split(",") if u.strip()]

        if activation_mode == "active":
            if not entitlements:
                raise HTTPException(status_code=400, detail="Define at least one entitlement before activating.")
            if not (assign_groups or assign_users):
                raise HTTPException(status_code=400, detail="Assign at least one group or user before activating.")

        async with KeycloakAdminClient() as kc:
            # Create client with collision handling
            created_client_uuid = None
            for attempt in range(0, 3):
                try:
                    response = await kc._make_request(
                        "POST",
                        f"/realms/{realm}/clients",
                        json_data=client_data
                    )
                    response.raise_for_status()
                    created_client_uuid = response.headers.get("Location", "").split("/")[-1]
                    break
                except Exception as e:
                    # If conflict, add short suffix and retry
                    if hasattr(e, "response") and getattr(e.response, "status_code", None) == 409:
                        client_data["clientId"] = f"{client_id_base}-{uuid.uuid4().hex[:4]}"
                        continue
                    raise

            if not created_client_uuid:
                raise HTTPException(status_code=500, detail="Failed to create app client.")

            # Create client roles from entitlements (if provided)
            for ent in entitlements:
                await kc._make_request(
                    "POST",
                    f"/realms/{realm}/clients/{created_client_uuid}/roles",
                    json_data={"name": ent, "description": f"Entitlement for {app_slug}"}
                )

            # Assign roles to groups/users (if provided)
            if entitlements and (assign_groups or assign_users):
                roles_resp = await kc._make_request("GET", f"/realms/{realm}/clients/{created_client_uuid}/roles")
                roles_resp.raise_for_status()
                role_objs = {r["name"]: r for r in roles_resp.json() if "name" in r}

                # Assign to groups
                for group_name in assign_groups:
                    grp_resp = await kc._make_request("GET", f"/realms/{realm}/groups", params={"search": group_name})
                    grp_resp.raise_for_status()
                    groups = grp_resp.json() or []
                    target_group = next((g for g in groups if g.get("name") == group_name), None)
                    if not target_group:
                        continue
                    for ent in entitlements:
                        role = role_objs.get(ent)
                        if role:
                            await kc._make_request(
                                "POST",
                                f"/realms/{realm}/groups/{target_group['id']}/role-mappings/clients/{created_client_uuid}",
                                json_data=[role],
                            )

                # Assign to users (by username/email)
                for user_token in assign_users:
                    user_resp = await kc._make_request("GET", f"/realms/{realm}/users", params={"search": user_token})
                    user_resp.raise_for_status()
                    users = user_resp.json() or []
                    target_user = next(
                        (u for u in users if u.get("username") == user_token or u.get("email") == user_token),
                        None,
                    )
                    if not target_user:
                        continue
                    for ent in entitlements:
                        role = role_objs.get(ent)
                        if role:
                            await kc._make_request(
                                "POST",
                                f"/realms/{realm}/users/{target_user['id']}/role-mappings/clients/{created_client_uuid}",
                                json_data=[role],
                            )

            logger.info(f"App {app_id} connected successfully, client_id: {client_data['clientId']}")
            # Persist to apps inventory table for tenant
            try:
                db.execute(
                    text(
                        """
                        INSERT INTO apps (id, tenant_id, name, display_name, description, app_type, icon_url, is_active, config)
                        VALUES (CAST(:id AS uuid), CAST(:tenant_id AS uuid), :name, :display_name, :description, :app_type, :icon_url, :is_active, CAST(:config AS jsonb))
                        ON CONFLICT (tenant_id, name) DO UPDATE SET
                          display_name = EXCLUDED.display_name,
                          description = EXCLUDED.description,
                          app_type = EXCLUDED.app_type,
                          icon_url = EXCLUDED.icon_url,
                          is_active = EXCLUDED.is_active,
                          config = EXCLUDED.config,
                          updated_at = now()
                        """
                    ),
                    {
                        "id": created_client_uuid,
                        "tenant_id": tenant_id,
                        "name": app_slug,
                        "display_name": cfg.get("app_name") or app_slug,
                        "description": cfg.get("description") or "",
                        "app_type": template_protocol or "Custom",
                        "icon_url": None,
                        "is_active": activation_mode == "active",
                        "config": json.dumps({
                            "client_id": client_data["clientId"],
                            "realm": realm,
                            "redirect_uris": redirect_uris,
                            "acs_url": acs_url,
                            "entitlements": entitlements,
                            "assign_groups": assign_groups,
                            "assign_users": assign_users,
                            "protocol": protocol,
                        }),
                    },
                )
                db.commit()
            except Exception as db_err:
                logger.warning(f"App created in Keycloak but failed to persist inventory: {db_err}")
            return ConnectAppResponse(
                success=True,
                app_id=created_client_uuid,
                client_id=client_data["clientId"],
                message="App connected successfully"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting app: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to connect app: {str(e)}")


@portal_router.post("/{app_id}/connect", response_model=ConnectAppResponse)
async def connect_app_portal(
    app_id: str,
    request: ConnectAppRequest,
    authorization: str = Depends(_auth_header),
    db: Session = Depends(get_tenant_session),
):
    """Portal prefix for connect app (same as /api/v1/apps/catalog/{id}/connect)."""
    return await connect_app(app_id, request, authorization, db)
