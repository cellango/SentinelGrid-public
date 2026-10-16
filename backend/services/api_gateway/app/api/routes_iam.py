"""IAM Agent proxy routes."""

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from typing import Optional
import httpx
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.security import get_current_tenant
from sg_core.request_tracing import build_trace_headers
from app.core.config import settings

router = APIRouter()


def _build_dashboard_snapshot_headers(
    current_tenant_id: str,
    authorization: Optional[str],
) -> dict[str, str]:
    bearer = authorization or f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"
    return build_trace_headers(
        {
            "Authorization": bearer,
            "X-Tenant-ID": current_tenant_id,
        }
    )


@router.get("/dashboard-snapshot")
async def get_iam_dashboard_snapshot(
    current_tenant_id: str = Depends(get_current_tenant),
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """Get IAM dashboard snapshot."""

    try:
        async with httpx.AsyncClient(timeout=30.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
            response = await client.get(
                f"{settings.IAM_AGENT_URL}/api/v1/iam/dashboard-snapshot",
                headers=_build_dashboard_snapshot_headers(current_tenant_id, authorization),
            )
            response.raise_for_status()
            return response.json()
    
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"IAM Agent service error: {e.response.text}"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to IAM Agent service: {str(e)}"
        )


# Generic IAM portal proxy (covers /api/iam-portal/* such as users/apps/profiles/birthrights)
@router.api_route("/iam-portal/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_iam_portal(
    path: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant),
):
    """Transparent proxy to IAM Agent /api/iam-portal endpoints."""
    # Preserve query string if present
    query = f"?{request.url.query}" if request.url.query else ""
    url = f"{settings.IAM_AGENT_URL}/api/iam-portal/{path}{query}"

    # Forward original headers (minus host) plus tenant context
    headers = build_trace_headers(dict(request.headers))
    headers.pop("host", None)
    headers["X-Tenant-ID"] = tenant_id

    try:
        async with httpx.AsyncClient(timeout=30.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
            resp = await client.request(
                request.method,
                url,
                content=await request.body(),
                headers=headers,
            )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to reach IAM Agent: {str(e)}"
        )

    if resp.status_code >= 400:
        # Attempt to surface JSON error, otherwise raw text
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)

    # Return JSON if available, else raw text
    try:
        return resp.json()
    except Exception:
        return JSONResponse(content=resp.text, status_code=resp.status_code)
