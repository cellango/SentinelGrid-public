"""Exact action-record routes, using verified user context and owned destination."""

from uuid import UUID
from fastapi import APIRouter, Depends, Request
from app.core.config import settings
from app.core.proxy import proxy_request
from sg_core.security import get_current_tenant

router = APIRouter()


async def forward(request, tenant_id, path):
    return await proxy_request(
        request,
        origin=settings.CASE_RUNTIME_URL,
        prefix="/api/v1/cases/",
        path=path,
        tenant_id=tenant_id,
    )


@router.post("/{case_id}/action-proposals")
async def submit(
    case_id: UUID, request: Request, tenant_id: str = Depends(get_current_tenant)
):
    return await forward(request, tenant_id, f"{case_id}/action-proposals")


@router.get("/{case_id}/action-proposals/{proposal_id}")
async def inspect(
    case_id: UUID,
    proposal_id: UUID,
    request: Request,
    tenant_id: str = Depends(get_current_tenant),
):
    return await forward(
        request, tenant_id, f"{case_id}/action-proposals/{proposal_id}"
    )


@router.post("/{case_id}/action-proposals/{proposal_id}/approvals")
async def approve(
    case_id: UUID,
    proposal_id: UUID,
    request: Request,
    tenant_id: str = Depends(get_current_tenant),
):
    return await forward(
        request, tenant_id, f"{case_id}/action-proposals/{proposal_id}/approvals"
    )
