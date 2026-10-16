"""Router endpoint that receives OpenSearch monitor alerts and forwards to the tenant's SOAR destination.

This enables a shared-monitor model: monitors are deployed once (filtered by tenant_id), and the router
forwards to the correct tenant-specific destination using tenant bindings data.
"""

import json
import logging
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_tenant_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/router", tags=["router"])


def _get_tenant_destination(db: Session, tenant_id: str) -> Dict[str, Any]:
    """Fetch the tenant's stored destination and custom config (SOAR URL/token)."""
    row = db.execute(
        """
        SELECT opensearch_destination_id, custom_config
        FROM tenant_detection_monitors
        WHERE tenant_id = :tenant_id::uuid
          AND opensearch_destination_id IS NOT NULL
        LIMIT 1
        """,
        {"tenant_id": tenant_id},
    ).mappings().first()
    return dict(row) if row else {}


async def resolve_opensearch_router_tenant(request: Request) -> str:
    """Resolve the webhook tenant before opening a DB session."""
    payload = await request.json()
    tenant_id = (
        payload.get("tenant_id")
        or payload.get("tenant")
        or payload.get("sg", {}).get("tenant_id")
    )
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing tenant_id in alert payload",
        )
    return tenant_id


def get_opensearch_router_session(
    tenant_id: str = Depends(resolve_opensearch_router_tenant),
):
    """Open a tenant-scoped DB session for the webhook tenant."""
    yield from get_tenant_db(tenant_id)


@router.post("/opensearch-webhook")
async def opensearch_router(
    request: Request,
    tenant_id: str = Depends(resolve_opensearch_router_tenant),
    db: Session = Depends(get_opensearch_router_session),
):
    payload = await request.json()

    dest = _get_tenant_destination(db, tenant_id)
    if not dest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No destination for tenant"
        )

    custom = dest.get("custom_config") or {}
    if isinstance(custom, str):
        try:
            custom = json.loads(custom)
        except Exception:
            custom = {}

    soar_url = custom.get("soar_webhook_url")
    auth_token = custom.get("auth_token")
    if not soar_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Destination missing soar_webhook_url",
        )

    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    try:
        async with httpx.AsyncClient(
            verify=settings.UPSTREAM_TLS_VERIFY,
            timeout=30.0,
        ) as client:
            resp = await client.post(soar_url, json=payload, headers=headers)
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Router forward failed: %s %s",
            exc.response.status_code,
            exc.response.text,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Forward failed"
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Router forward error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Forward error"
        )

    return {"status": "ok"}
