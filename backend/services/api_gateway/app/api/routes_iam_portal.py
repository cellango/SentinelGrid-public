"""IAM Portal proxy routes - People, Apps, Access Profiles, etc."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from typing import Optional
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


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_iam_portal(
    path: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Proxy all IAM portal requests to IAM Agent.
    
    CRITICAL: tenant_id is REQUIRED for proper multi-tenant isolation.
    Requests without tenant_id will be rejected with 403.
    """
    # Forward the request to IAM Agent
    url = f"{IAM_AGENT_URL}/api/iam-portal/{path}"
    
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
    
    logger.info(f"🔄 Proxying {request.method} /api/iam-portal/{path} to IAM Agent (tenant_id={tenant_id})")
    logger.debug(f"🔍 [IAM Portal Proxy] tenant_id={tenant_id}, path={path}, query_params={query_params}, auth_header_present={bool(auth_header)}")
    
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

            # Gracefully handle unimplemented IAM portal endpoints (return empty list instead of surfacing 404)
            if response.status_code == 404 and path.startswith("policies"):
                return Response(content="[]", status_code=200, headers={"Content-Type": "application/json"})

            return Response(content=response.content, status_code=response.status_code, headers=dict(response.headers))
    except httpx.ConnectError:
        logger.error(f"❌ Could not connect to IAM Agent at {IAM_AGENT_URL}")
        raise HTTPException(status_code=503, detail="IAM Agent unavailable")
    except Exception as e:
        logger.error(f"❌ IAM Agent proxy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
