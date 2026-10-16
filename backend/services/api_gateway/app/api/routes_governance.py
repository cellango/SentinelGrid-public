"""Governance proxy routes for access-review campaigns and certifications."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
import httpx

from sg_core.security import get_current_tenant
from app.core.config import settings

router = APIRouter()


@router.api_route("", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@router.api_route("/", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_governance(
    request: Request,
    path: str = "",
    current_tenant_id: str = Depends(get_current_tenant),
):
    """Proxy governance requests to the IAM agent."""
    normalized_path = path.lstrip("/")
    target_url = f"{settings.IAM_AGENT_URL}/api/v1/governance/{normalized_path}"
    auth_header = request.headers.get("Authorization")

    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except Exception:
            body = None

    query_params = dict(request.query_params)

    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers={
                    "Authorization": auth_header,
                    "X-Tenant-ID": current_tenant_id,
                    "Content-Type": request.headers.get("Content-Type", "application/json"),
                },
                params=query_params,
                json=body if body else None,
            )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type"),
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to governance service: {str(exc)}",
        )
