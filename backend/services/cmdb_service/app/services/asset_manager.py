"""Asset management service."""

import logging
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime
from uuid import UUID

from app.models import Asset
from app.services.cloud_query_integration import CloudQueryIntegration

logger = logging.getLogger(__name__)


class AssetManager:
    """Service for managing CMDB assets."""
    
    def __init__(self):
        self.cloud_query = CloudQueryIntegration() if self._should_init_cloud_query() else None
    
    def _should_init_cloud_query(self) -> bool:
        """Check if CloudQuery integration should be initialized."""
        from app.core.config import settings
        return settings.CLOUDQUERY_ENABLED and settings.CLOUDQUERY_DB_URL
    
    def get_asset(
        self,
        db: Session,
        asset_id: str,
        tenant_id: Union[UUID, str]
    ) -> Optional[Asset]:
        """
        Get asset by asset_id.
        
        Args:
            db: Database session
            asset_id: Asset identifier
            tenant_id: Tenant ID
        
        Returns:
            Asset object or None
        """
        asset = db.query(Asset).filter(
            and_(
                Asset.asset_id == asset_id,
                Asset.tenant_id == tenant_id
            )
        ).first()
        
        return asset
    
    def create_asset(
        self,
        db: Session,
        tenant_id: Union[UUID, str],
        asset_data: Dict[str, Any]
    ) -> Asset:
        """
        Create a new asset.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            asset_data: Asset data dictionary
        
        Returns:
            Created Asset object
        """
        # Check if asset already exists
        existing = self.get_asset(db, asset_data["asset_id"], tenant_id)
        if existing:
            raise ValueError(f"Asset {asset_data['asset_id']} already exists")
        
        asset = Asset(
            tenant_id=tenant_id,
            **asset_data
        )
        
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        return asset
    
    def update_asset(
        self,
        db: Session,
        asset_id: str,
        tenant_id: Union[UUID, str],
        asset_data: Dict[str, Any]
    ) -> Asset:
        """
        Update an existing asset.
        
        Args:
            db: Database session
            asset_id: Asset identifier
            tenant_id: Tenant ID
            asset_data: Updated asset data
        
        Returns:
            Updated Asset object
        """
        asset = self.get_asset(db, asset_id, tenant_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        # Update fields
        for key, value in asset_data.items():
            if hasattr(asset, key) and key != "id" and key != "tenant_id":
                setattr(asset, key, value)
        
        asset.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(asset)
        
        return asset
    
    def delete_asset(
        self,
        db: Session,
        asset_id: str,
        tenant_id: Union[UUID, str]
    ) -> bool:
        """
        Delete an asset.
        
        Args:
            db: Database session
            asset_id: Asset identifier
            tenant_id: Tenant ID
        
        Returns:
            True if deleted, False if not found
        """
        asset = self.get_asset(db, asset_id, tenant_id)
        if not asset:
            return False
        
        db.delete(asset)
        db.commit()
        
        return True
    
    def search_assets(
        self,
        db: Session,
        tenant_id: Union[UUID, str],
        search_term: Optional[str] = None,
        asset_type: Optional[str] = None,
        hostname: Optional[str] = None,
        ip_address: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Asset]:
        """
        Search assets.
        
        Args:
            db: Database session
            tenant_id: Tenant ID
            search_term: Search term (name, hostname, asset_id)
            asset_type: Filter by asset type
            hostname: Filter by hostname
            ip_address: Filter by IP address
            limit: Maximum number of results
            offset: Offset for pagination
        
        Returns:
            List of Asset objects
        """
        query = db.query(Asset).filter(
            Asset.tenant_id == tenant_id
        )
        
        if search_term:
            query = query.filter(
                or_(
                    Asset.name.ilike(f"%{search_term}%"),
                    Asset.hostname.ilike(f"%{search_term}%"),
                    Asset.asset_id.ilike(f"%{search_term}%")
                )
            )
        
        if asset_type:
            query = query.filter(Asset.asset_type == asset_type)
        
        if hostname:
            query = query.filter(Asset.hostname == hostname)
        
        if ip_address:
            query = query.filter(Asset.ip_address == ip_address)
        
        return query.order_by(Asset.created_at.desc()).offset(offset).limit(limit).all()
    
    def link_vulnerability_to_asset(
        self,
        db: Session,
        asset_id: str,
        tenant_id: Union[UUID, str],
        cve_id: str
    ) -> Asset:
        """
        Link a vulnerability (CVE) to an asset.
        
        Args:
            db: Database session
            asset_id: Asset identifier
            tenant_id: Tenant ID
            cve_id: CVE identifier
        
        Returns:
            Updated Asset object
        """
        asset = self.get_asset(db, asset_id, tenant_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        # Get current vulnerabilities list
        vulnerabilities = asset.vulnerabilities or []
        
        # Add CVE if not already present
        if cve_id not in vulnerabilities:
            vulnerabilities.append(cve_id)
            asset.vulnerabilities = vulnerabilities
            asset.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(asset)
        
        return asset
    
    async def sync_cloud_assets(
        self,
        db: Session,
        tenant_id: Union[UUID, str]
    ) -> Dict[str, Any]:
        """
        Sync assets from CloudQuery (if enabled).
        
        Args:
            db: Database session
            tenant_id: Tenant ID
        
        Returns:
            Sync results
        """
        if not self.cloud_query:
            return {
                "status": "skipped",
                "reason": "CloudQuery integration not enabled"
            }
        
        try:
            # Fetch assets from CloudQuery
            cloud_assets = await self.cloud_query.fetch_assets(tenant_id)
            
            results = {
                "synced": [],
                "updated": [],
                "failed": []
            }
            
            for cloud_asset in cloud_assets:
                try:
                    asset_id = cloud_asset.get("asset_id")
                    if not asset_id:
                        continue
                    
                    # Check if exists
                    existing = self.get_asset(db, asset_id, tenant_id)
                    
                    if existing:
                        # Update existing
                        self.update_asset(db, asset_id, tenant_id, cloud_asset)
                        results["updated"].append(asset_id)
                    else:
                        # Create new
                        cloud_asset["tenant_id"] = tenant_id
                        cloud_asset["source"] = "cloud_query"
                        self.create_asset(db, tenant_id, cloud_asset)
                        results["synced"].append(asset_id)
                
                except Exception as e:
                    logger.error(f"Error syncing asset {cloud_asset.get('asset_id')}: {e}")
                    results["failed"].append(cloud_asset.get("asset_id", "unknown"))
            
            return {
                "status": "completed",
                "results": results,
                "summary": {
                    "total": len(cloud_assets),
                    "synced": len(results["synced"]),
                    "updated": len(results["updated"]),
                    "failed": len(results["failed"])
                }
            }
        
        except Exception as e:
            logger.error(f"Error syncing cloud assets: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }
