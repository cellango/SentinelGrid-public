"""SOAR proxy routes - forward /api/v1/soar/* through the gateway to SOAR Agent."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
import httpx
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))
from sg_core.security import get_current_tenant
from app.core.config import settings

router = APIRouter()


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_soar(
    path: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant),
):
    """
    Proxy SOAR routes via gateway, preserving auth and tenant context.
    Example: /api/v1/soar/playbooks -> http://soar_agent:8000/soar/playbooks
    """
    url = f"{settings.SOAR_AGENT_URL}/soar/{path}"

    # Capture body for non-GET methods
    try:
        body = await request.json() if request.method in ["POST", "PUT", "PATCH", "DELETE"] else None
    except Exception:
        body = None

    headers = {"Content-Type": "application/json", "X-Tenant-ID": tenant_id}
    auth_header = request.headers.get("authorization")
    if auth_header:
        headers["Authorization"] = auth_header

    try:
        async with httpx.AsyncClient(timeout=30.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
            resp = await client.request(
                method=request.method,
                url=url,
                params=dict(request.query_params),
                json=body,
                headers=headers,
            )
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"SOAR proxy failed: {e}")
