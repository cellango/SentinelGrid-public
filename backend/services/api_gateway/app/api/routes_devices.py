"""Bounded devices forwarding preserving root and path route identities."""
from fastapi import APIRouter, Depends, Request
from sg_core.security import get_current_tenant
from app.core.config import settings
from app.core.proxy import proxy_request

router = APIRouter()

@router.api_route("", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@router.api_route("/", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_devices_root(request: Request, tenant_id: str = Depends(get_current_tenant)):
    return await proxy_devices(path="", request=request, tenant_id=tenant_id)

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_devices(path: str, request: Request, tenant_id: str = Depends(get_current_tenant)):
    return await proxy_request(request, origin=settings.IAM_AGENT_URL, prefix="/api/v1/devices/", path=path, tenant_id=tenant_id)
