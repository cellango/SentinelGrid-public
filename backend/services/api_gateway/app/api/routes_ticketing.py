"""Ticketing proxy routes."""

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sg_core.security import get_current_tenant
import httpx
from app.core.config import settings

router = APIRouter()


def _ticket_headers(tenant_id: str, x_realm: str | None) -> dict:
    headers = {"X-Tenant-ID": tenant_id}
    if x_realm:
        headers["X-Realm"] = x_realm
    return headers


async def _proxy_ticket_request(method: str, path: str, tenant_id: str, x_realm: str | None, params: dict | None = None, payload: dict | None = None):
    headers = _ticket_headers(tenant_id, x_realm)
    url = f"{settings.TICKETING_SERVICE_URL}{path}"
    async with httpx.AsyncClient(timeout=30.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
        resp = await client.request(method, url, headers=headers, params=params, json=payload)
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)
    try:
        return resp.json()
    except Exception:
        return resp.text


@router.get("/tickets")
async def list_tickets(
    status: str | None = None,
    severity: str | None = None,
    category: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(get_current_tenant),
    x_realm: str | None = Header(None, alias="X-Realm"),
):
    params = {
        "tenant_id": tenant_id,
        "status": status,
        "severity": severity,
        "category": category,
        "limit": limit,
        "offset": offset,
    }
    params = {k: v for k, v in params.items() if v is not None}
    return await _proxy_ticket_request("GET", "/api/v1/tickets", tenant_id, x_realm, params=params)


@router.post("/tickets")
async def create_ticket(
    payload: dict,
    tenant_id: str = Depends(get_current_tenant),
    x_realm: str | None = Header(None, alias="X-Realm"),
):
    params = {"tenant_id": tenant_id}
    return await _proxy_ticket_request("POST", "/api/v1/tickets", tenant_id, x_realm, params=params, payload=payload)


@router.get("/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    tenant_id: str = Depends(get_current_tenant),
    x_realm: str | None = Header(None, alias="X-Realm"),
):
    params = {"tenant_id": tenant_id}
    return await _proxy_ticket_request("GET", f"/api/v1/tickets/{ticket_id}", tenant_id, x_realm, params=params)


@router.put("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    payload: dict,
    tenant_id: str = Depends(get_current_tenant),
    x_realm: str | None = Header(None, alias="X-Realm"),
):
    params = {"tenant_id": tenant_id}
    return await _proxy_ticket_request("PUT", f"/api/v1/tickets/{ticket_id}", tenant_id, x_realm, params=params, payload=payload)


@router.post("/tickets/{ticket_id}/comments")
async def add_ticket_comment(
    ticket_id: str,
    payload: dict,
    tenant_id: str = Depends(get_current_tenant),
    x_realm: str | None = Header(None, alias="X-Realm"),
):
    params = {"tenant_id": tenant_id}
    return await _proxy_ticket_request(
        "POST",
        f"/api/v1/tickets/{ticket_id}/comments",
        tenant_id,
        x_realm,
        params=params,
        payload=payload,
    )


@router.get("/tickets/{ticket_id}/tabs/{tab_name}")
async def get_ticket_tab(
    ticket_id: str,
    tab_name: str,
    tenant_id: str = Depends(get_current_tenant),
    x_realm: str | None = Header(None, alias="X-Realm"),
):
    params = {"tenant_id": tenant_id}
    return await _proxy_ticket_request("GET", f"/api/v1/tickets/{ticket_id}/tabs/{tab_name}", tenant_id, x_realm, params=params)
