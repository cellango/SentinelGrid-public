"""IAM routes using the shared bounded credential-preserving proxy."""
from fastapi import APIRouter, Depends, Request
from sg_core.security import get_current_tenant
from app.core.config import settings
from app.core.proxy import proxy_request

router = APIRouter()

@router.get("/dashboard-snapshot")
async def get_iam_dashboard_snapshot(request: Request, current_tenant_id: str = Depends(get_current_tenant)):
    return await proxy_request(request, origin=settings.IAM_AGENT_URL,
        prefix="/api/v1/iam/dashboard-snapshot", tenant_id=current_tenant_id)

@router.api_route("/iam-portal/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy_iam_portal(path: str, request: Request, tenant_id: str = Depends(get_current_tenant)):
    return await proxy_request(request, origin=settings.IAM_AGENT_URL,
        prefix="/api/iam-portal/", path=path, tenant_id=tenant_id)
