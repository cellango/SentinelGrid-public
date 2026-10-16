"""API endpoints for asset management."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_query_tenant_session, resolve_query_tenant_id
from app.services.asset_manager import AssetManager
from sg_core.schemas import AssetResponse

logger = logging.getLogger(__name__)

router = APIRouter()
asset_manager = AssetManager()


class AssetCreate(BaseModel):
    """Asset creation schema."""
    asset_id: str
    asset_type: str
    name: str
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    hardware_specs: Optional[dict] = None
    operating_system: Optional[str] = None
    os_version: Optional[str] = None
    installed_software: Optional[List[dict]] = None
    installed_patches: Optional[List[str]] = None
    network_segment: Optional[str] = None
    vlan: Optional[str] = None
    firewall_rules: Optional[dict] = None
    owner: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    source: Optional[str] = "manual"


class AssetUpdate(BaseModel):
    """Asset update schema."""
    name: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    operating_system: Optional[str] = None
    os_version: Optional[str] = None
    installed_software: Optional[List[dict]] = None
    installed_patches: Optional[List[str]] = None
    owner: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    compliance_status: Optional[str] = None


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: str,
    tenant_id: str = Depends(resolve_query_tenant_id),
    db: Session = Depends(get_query_tenant_session)
):
    """Get asset by asset_id."""
    try:
        asset = asset_manager.get_asset(db, asset_id, tenant_id)
        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
        return asset
    except Exception as e:
        logger.error(f"Error getting asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("", response_model=AssetResponse)
async def create_asset(
    asset: AssetCreate,
    tenant_id: str = Depends(resolve_query_tenant_id),
    db: Session = Depends(get_query_tenant_session)
):
    """Create a new asset."""
    try:
        asset_data = asset.dict()
        created_asset = asset_manager.create_asset(db, tenant_id, asset_data)
        return created_asset
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating asset: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: str,
    asset: AssetUpdate,
    tenant_id: str = Depends(resolve_query_tenant_id),
    db: Session = Depends(get_query_tenant_session)
):
    """Update an existing asset."""
    try:
        asset_data = {k: v for k, v in asset.dict().items() if v is not None}
        updated_asset = asset_manager.update_asset(db, asset_id, tenant_id, asset_data)
        return updated_asset
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    tenant_id: str = Depends(resolve_query_tenant_id),
    db: Session = Depends(get_query_tenant_session)
):
    """Delete an asset."""
    try:
        deleted = asset_manager.delete_asset(db, asset_id, tenant_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
        return {"status": "deleted", "asset_id": asset_id}
    except Exception as e:
        logger.error(f"Error deleting asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=List[AssetResponse])
async def search_assets(
    search: Optional[str] = Query(None, description="Search term (name, hostname, asset_id)"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    hostname: Optional[str] = Query(None, description="Filter by hostname"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant_id: str = Depends(resolve_query_tenant_id),
    db: Session = Depends(get_query_tenant_session)
):
    """Search assets."""
    assets = asset_manager.search_assets(
        db=db,
        tenant_id=tenant_id,
        search_term=search,
        asset_type=asset_type,
        hostname=hostname,
        ip_address=ip_address,
        limit=limit,
        offset=offset
    )
    return assets


@router.post("/{asset_id}/vulnerabilities/{cve_id}")
async def link_vulnerability(
    asset_id: str,
    cve_id: str,
    tenant_id: str = Depends(resolve_query_tenant_id),
    db: Session = Depends(get_query_tenant_session)
):
    """Link a vulnerability (CVE) to an asset."""
    try:
        asset = asset_manager.link_vulnerability_to_asset(db, asset_id, tenant_id, cve_id)
        return {"status": "linked", "asset_id": asset_id, "cve_id": cve_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error linking vulnerability to asset: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sync/cloud")
async def sync_cloud_assets(
    tenant_id: str = Depends(resolve_query_tenant_id),
    db: Session = Depends(get_query_tenant_session)
):
    """Sync assets from CloudQuery."""
    try:
        results = await asset_manager.sync_cloud_assets(db, tenant_id)
        return results
    except Exception as e:
        logger.error(f"Error syncing cloud assets: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
