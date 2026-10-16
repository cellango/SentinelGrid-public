"""Devices proxy routes - forward to IAM Agent."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
import httpx
import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.security import get_current_tenant
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# IAM Agent URL
IAM_AGENT_URL = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")


@router.api_route("", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@router.api_route("/", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_devices_root(
    request: Request,
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Proxy /api/v1/devices root when no extra path is provided.
    """
    return await proxy_devices(path="", request=request, tenant_id=tenant_id)


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_devices(
    path: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Proxy all devices requests to IAM Agent.
    
    CRITICAL: tenant_id is REQUIRED for proper multi-tenant isolation.
    Requests without tenant_id will be rejected with 403.
    """
    # Forward the request to IAM Agent
    if path:
        url = f"{IAM_AGENT_URL}/api/v1/devices/{path}"
    else:
        url = f"{IAM_AGENT_URL}/api/v1/devices"
    
    # Get query params
    query_params = dict(request.query_params)
    
    # Get request body if present
    try:
        body = await request.json() if request.method in ["POST", "PUT", "PATCH"] else None
    except:
        body = None
    
    # Get authorization header
    auth_header = request.headers.get("authorization")
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json"
    } if auth_header else {"Content-Type": "application/json"}
    
    logger.info(f"🔄 Proxying {request.method} /api/v1/devices/{path} to IAM Agent (tenant_id={tenant_id})")
    logger.info(f"🔍 [Devices Proxy] tenant_id={tenant_id}, path={path}, query_params={query_params}, auth_header_present={bool(auth_header)}")
    logger.info(f"🔍 [Devices Proxy] Full URL: {url}, IAM_AGENT_URL={IAM_AGENT_URL}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=url,
                params=query_params,
                json=body,
                headers=headers
            )
            
            logger.info(f"✅ IAM Agent responded with {response.status_code}")
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
    except httpx.ConnectError:
        logger.error(f"❌ Could not connect to IAM Agent at {IAM_AGENT_URL}")
        raise HTTPException(status_code=503, detail="IAM Agent unavailable")
    except Exception as e:
        logger.error(f"❌ IAM Agent proxy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
