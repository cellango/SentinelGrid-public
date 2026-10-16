"""Assets API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..')))

from shared.database import get_db
from shared.models.asset import Asset
from shared.models.finding import Finding
from sqlalchemy import and_
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/")
async def list_assets(
    tenant_id: str = Query(...),
    asset_type: Optional[str] = Query(None),
    cloud_account_id: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """
    List assets with filters.
    
    Args:
        tenant_id: Tenant identifier
        asset_type: Filter by asset type
        cloud_account_id: Filter by cloud account
        environment: Filter by environment (prod, staging, dev)
        limit: Max results
        offset: Pagination offset
        db: Database session
    
    Returns:
        List of assets
    """
    logger.info(f"Listing assets for tenant: {tenant_id}")
    
    # Build query
    query = db.query(Asset).filter(Asset.tenant_id == tenant_id)
    
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    
    if cloud_account_id:
        query = query.filter(Asset.cloud_account_id == cloud_account_id)
    
    if environment:
        query = query.filter(Asset.environment == environment)
    
    # Order by risk score (highest first)
    query = query.order_by(Asset.risk_score.desc(), Asset.name)
    
    # Pagination
    total_count = query.count()
    assets = query.offset(offset).limit(limit).all()
    
    return {
        "assets": [
            {
                "id": str(a.id),
                "tenant_id": str(a.tenant_id),
                "asset_id": a.asset_id,
                "asset_type": a.asset_type,
                "name": a.name,
                "cloud_account_id": a.cloud_account_id,
                "region": a.region,
                "environment": a.environment,
                "risk_score": a.risk_score,
                "critical_findings_count": a.critical_findings_count,
                "high_findings_count": a.high_findings_count,
                "tags": a.tags
            }
            for a in assets
        ],
        "total_count": total_count,
        "limit": limit,
        "offset": offset
    }


@router.get("/{asset_id}")
async def get_asset(
    asset_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed asset information.
    
    Args:
        asset_id: Asset identifier
        db: Database session
    
    Returns:
        Asset details
    """
    try:
        asset_uuid = uuid.UUID(asset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid asset ID format")
    
    asset = db.query(Asset).filter(Asset.id == asset_uuid).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    return {
        "id": str(asset.id),
        "tenant_id": str(asset.tenant_id),
        "asset_id": asset.asset_id,
        "asset_type": asset.asset_type,
        "name": asset.name,
        "cloud_account_id": asset.cloud_account_id,
        "region": asset.region,
        "owner_team": asset.owner_team,
        "environment": asset.environment,
        "tags": asset.tags,
        "metadata": asset.metadata,
        "risk_score": asset.risk_score,
        "critical_findings_count": asset.critical_findings_count,
        "high_findings_count": asset.high_findings_count,
        "medium_findings_count": asset.medium_findings_count,
        "low_findings_count": asset.low_findings_count,
        "first_seen_at": asset.first_seen_at.isoformat() if asset.first_seen_at else None,
        "last_seen_at": asset.last_seen_at.isoformat() if asset.last_seen_at else None
    }


@router.get("/{asset_id}/findings")
async def get_asset_findings(
    asset_id: str,
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get all findings for an asset.
    
    Args:
        asset_id: Asset identifier
        status: Filter by status
        severity: Filter by severity
        db: Database session
    
    Returns:
        List of findings for the asset
    """
    try:
        asset_uuid = uuid.UUID(asset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid asset ID format")
    
    # Verify asset exists
    asset = db.query(Asset).filter(Asset.id == asset_uuid).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Query findings
    query = db.query(Finding).filter(Finding.asset_id == asset_uuid)
    
    if status:
        query = query.filter(Finding.status == status)
    
    if severity:
        query = query.filter(Finding.severity == severity)
    
    findings = query.order_by(Finding.severity.desc()).all()
    
    return {
        "asset_id": str(asset_id),
        "asset_name": asset.name,
        "findings": [
            {
                "id": str(f.id),
                "title": f.title,
                "severity": f.severity.value,
                "status": f.status.value,
                "source": f.source.value,
                "tool": f.tool,
                "first_seen_at": f.first_seen_at.isoformat() if f.first_seen_at else None
            }
            for f in findings
        ],
        "count": len(findings)
    }

