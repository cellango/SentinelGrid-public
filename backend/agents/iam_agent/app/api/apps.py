"""
Application inventory and status endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
import logging

from app.api.app_catalog import get_token_data, get_realm_for_tenant
from app.api.app_catalog import get_realm_from_token_data
from app.api.request_context import get_tenant_session
from app.services.keycloak_admin_client import KeycloakAdminClient
from sqlalchemy.orm import Session
from sqlalchemy import text

router = APIRouter(prefix="/api/iam-portal/apps", tags=["apps"])
logger = logging.getLogger(__name__)


class AppStatusUpdate(BaseModel):
  is_active: bool


class AppOut(BaseModel):
  id: str
  client_id: str | None = None
  issuer: str | None = None
  name: str | None = None
  display_name: str | None = None
  description: str | None = None
  app_type: str | None = None
  protocol: str | None = None
  is_active: bool | None = None
  config: dict | None = None


def _auth_header(request: Request) -> str:
  return request.headers.get("authorization", "").replace("Bearer ", "")


@router.get("", response_model=list[AppOut])
async def list_apps(authorization: str = Depends(_auth_header), db: Session = Depends(get_tenant_session)):
  token_data = await get_token_data(authorization)
  tenant_id = token_data["tenant_id"]
  realm = get_realm_from_token_data(token_data)
  try:
    # Prefer DB inventory
    rows = db.execute(
      text(
        """
        SELECT id, tenant_id, name, display_name, description, app_type, icon_url, is_active, config
        FROM apps
        WHERE tenant_id = :tenant_id
        ORDER BY created_at DESC
        """
      ),
      {"tenant_id": tenant_id},
    ).fetchall()
    results: list[AppOut] = []
    for r in rows:
      cfg = r.config or {}
      results.append(
        AppOut(
          id=str(r.id),
          client_id=cfg.get("client_id"),
          issuer=cfg.get("issuer") or (cfg.get("realm") and f"{cfg.get('realm')}"),
          name=r.name,
          display_name=r.display_name,
          description=r.description,
          app_type=r.app_type,
          protocol=cfg.get("protocol") or "oidc",
          is_active=r.is_active,
          config=cfg,
        )
      )
    if results:
      return results
    # Fallback: fetch apps for this tenant from Keycloak
    async with KeycloakAdminClient() as kc:
      resp = await kc._make_request("GET", f"/realms/{realm}/clients")
      resp.raise_for_status()
      clients = resp.json() or []
      kc_results: list[AppOut] = []
      for c in clients:
        # Filter service/builtin clients
        if c.get("clientId", "").startswith("realm-management"):
          continue
        kc_results.append(
          AppOut(
            id=c.get("id"),
            client_id=c.get("clientId"),
            issuer=f"{kc.server_url}/realms/{realm}",
            name=c.get("name") or c.get("clientId"),
            display_name=c.get("name") or c.get("clientId"),
            app_type="Custom",
            protocol=c.get("protocol") or "oidc",
            is_active=c.get("enabled", False),
            config={
              "redirect_uris": c.get("redirectUris", []),
              "acs_url": (c.get("redirectUris") or [None])[0],
            },
          )
        )
      return kc_results
  except Exception as e:
    logger.error(f"Failed to list apps: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Failed to list apps")


@router.get("/{app_id}", response_model=AppOut)
async def get_app(app_id: str, authorization: str = Depends(_auth_header), db: Session = Depends(get_tenant_session)):
  token_data = await get_token_data(authorization)
  tenant_id = token_data["tenant_id"]
  realm = get_realm_from_token_data(token_data)
  try:
    row = db.execute(
      text(
        """
        SELECT id, tenant_id, name, display_name, description, app_type, icon_url, is_active, config
        FROM apps
        WHERE id = :id AND tenant_id = :tenant_id
        """
      ),
      {"id": app_id, "tenant_id": tenant_id},
    ).first()
    if row:
      cfg = row.config or {}
      return AppOut(
        id=str(row.id),
        client_id=cfg.get("client_id"),
        issuer=cfg.get("issuer") or (cfg.get("realm") and f"{cfg.get('realm')}"),
        name=row.name,
        display_name=row.display_name,
        description=row.description,
        app_type=row.app_type,
        protocol=cfg.get("protocol") or "oidc",
        is_active=row.is_active,
        config=cfg,
      )
  except Exception as e:
    logger.error(f"Failed to get app from DB {app_id}: {e}", exc_info=True)
    # fallback to KC below
  try:
    async with KeycloakAdminClient() as kc:
      resp = await kc._make_request("GET", f"/realms/{realm}/clients/{app_id}")
      resp.raise_for_status()
      c = resp.json()
      return AppOut(
        id=c.get("id"),
        client_id=c.get("clientId"),
        issuer=f"{kc.server_url}/realms/{realm}",
        name=c.get("name") or c.get("clientId"),
        display_name=c.get("name") or c.get("clientId"),
        app_type="Custom",
        protocol=c.get("protocol") or "oidc",
        is_active=c.get("enabled", False),
        config={
          "redirect_uris": c.get("redirectUris", []),
          "acs_url": (c.get("redirectUris") or [None])[0],
        },
      )
  except Exception as e:
    logger.error(f"Failed to get app {app_id}: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Failed to fetch app")


@router.post("/{app_id}/status")
async def set_app_status(app_id: str, body: AppStatusUpdate, authorization: str = Depends(_auth_header)):
  token_data = await get_token_data(authorization)
  tenant_id = token_data["tenant_id"]
  realm = get_realm_from_token_data(token_data)
  try:
    async with KeycloakAdminClient() as kc:
      # simple enable/disable on client
      resp = await kc._make_request("PUT", f"/realms/{realm}/clients/{app_id}", json_data={"enabled": body.is_active})
      resp.raise_for_status()
      return {"ok": True, "is_active": body.is_active}
  except Exception as e:
    logger.error(f"Failed to update app status {app_id}: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="Failed to update app status")
