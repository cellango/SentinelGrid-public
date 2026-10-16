"""Tenant management router (from tenant_service)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_current_tenant, get_tenant_session

router = APIRouter()


def _enforce_same_tenant(path_tenant_id: str, current_tenant: str) -> None:
    if str(path_tenant_id) != str(current_tenant):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied",
        )


@router.get("/")
async def list_tenants(
    limit: int = 50,
    offset: int = 0,
    current_tenant: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """List tenants."""
    return {"items": [{"id": current_tenant, "status": "stub"}], "total": 1}


@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    current_tenant: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Get tenant by ID."""
    _enforce_same_tenant(tenant_id, current_tenant)
    return {"id": tenant_id, "status": "stub"}


@router.post("/")
async def create_tenant(
    tenant: dict,
    current_tenant: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Create new tenant."""
    requested_tenant = tenant.get("tenant_id") or tenant.get("id")
    if requested_tenant:
        _enforce_same_tenant(str(requested_tenant), current_tenant)
    return {"id": current_tenant, "status": "created"}
