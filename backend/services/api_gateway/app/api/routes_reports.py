"""Reporting service proxy routes."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from typing import Optional
import httpx
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.security import get_current_tenant
from app.core.config import settings

router = APIRouter()


@router.api_route("", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@router.api_route("/", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_reports(
    request: Request,
    path: str = "",
    current_tenant_id: str = Depends(get_current_tenant)
):
    """
    Proxy requests to reporting service.
    All reporting endpoints are proxied through API Gateway for consistency.
    """
    # Build target URL (avoid double slashes)
    normalized_path = path.lstrip("/")
    target_url = f"{settings.REPORTING_SERVICE_URL}/api/v1/reports/{normalized_path}"
    auth_header = request.headers.get("Authorization")
    
    # Get request body if present
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except:
            body = None
    
    # Get query parameters
    query_params = dict(request.query_params)
    
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            # Forward request to reporting service
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
            
            # Return response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )
    
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to reporting service: {str(e)}"
        )
