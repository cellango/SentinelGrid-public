"""
Hardened Images API

Provides endpoints for managing and retrieving hardened OS images.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date, datetime
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    get_tenant_session,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/hardened-images", tags=["hardened-images"])

# ============================================================================
# Request/Response Models
# ============================================================================

class HardenedImageResponse(BaseModel):
    """Response for hardened image information."""
    id: str
    os_name: str
    os_version: str
    cloud_provider: str
    image_id: str
    image_name: str
    region: Optional[str] = None
    hardening_level: str
    cis_benchmark_version: Optional[str] = None
    agent_version: str
    agent_installed: bool
    build_date: date
    status: str
    metadata: Optional[Dict[str, Any]] = None
    download_url: Optional[str] = None
    documentation_url: Optional[str] = None


class HardenedImageListResponse(BaseModel):
    """Response for listing hardened images."""
    images: List[HardenedImageResponse]
    total: int
    page: int
    page_size: int


class HardenedImageFilter(BaseModel):
    """Filter criteria for hardened images."""
    os_name: Optional[str] = None
    os_version: Optional[str] = None
    cloud_provider: Optional[str] = None
    hardening_level: Optional[str] = None
    region: Optional[str] = None
    status: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("", response_model=HardenedImageListResponse)
async def list_hardened_images(
    os_name: Optional[str] = Query(None, description="Filter by OS name"),
    os_version: Optional[str] = Query(None, description="Filter by OS version"),
    cloud_provider: Optional[str] = Query(None, description="Filter by cloud provider"),
    hardening_level: Optional[str] = Query(None, description="Filter by hardening level"),
    region: Optional[str] = Query(None, description="Filter by region"),
    status: Optional[str] = Query("active", description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """
    List available hardened images with filtering and pagination.
    """
    _ = request_context
    try:
        # Build WHERE clause
        where_conditions = []
        params = {}
        
        if os_name:
            where_conditions.append("os_name = :os_name")
            params["os_name"] = os_name
        
        if os_version:
            where_conditions.append("os_version = :os_version")
            params["os_version"] = os_version
        
        if cloud_provider:
            where_conditions.append("cloud_provider = :cloud_provider")
            params["cloud_provider"] = cloud_provider
        
        if hardening_level:
            where_conditions.append("hardening_level = :hardening_level")
            params["hardening_level"] = hardening_level
        
        if region:
            where_conditions.append("region = :region")
            params["region"] = region
        
        if status:
            where_conditions.append("status = :status")
            params["status"] = status
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Count total
        count_query = f"""
            SELECT COUNT(*) as total
            FROM hardened_images
            WHERE {where_clause}
        """
        
        if db:
            count_result = db.execute(text(count_query), params)
            total = count_result.fetchone()[0]
        else:
            # Mock data for development
            total = 5
        
        # Get images
        offset = (page - 1) * page_size
        query = f"""
            SELECT 
                id, os_name, os_version, cloud_provider, image_id, image_name,
                region, hardening_level, cis_benchmark_version, agent_version,
                agent_installed, build_date, status, metadata
            FROM hardened_images
            WHERE {where_clause}
            ORDER BY build_date DESC, os_name, os_version
            LIMIT :limit OFFSET :offset
        """
        params["limit"] = page_size
        params["offset"] = offset
        
        if db:
            result = db.execute(text(query), params)
            rows = result.fetchall()
            
            images = []
            for row in rows:
                images.append(HardenedImageResponse(
                    id=str(row[0]),
                    os_name=row[1],
                    os_version=row[2],
                    cloud_provider=row[3],
                    image_id=row[4],
                    image_name=row[5],
                    region=row[6],
                    hardening_level=row[7],
                    cis_benchmark_version=row[8],
                    agent_version=row[9],
                    agent_installed=row[10],
                    build_date=row[11],
                    status=row[12],
                    metadata=row[13] if row[13] else {}
                ))
        else:
            # Mock data for development
            images = [
                HardenedImageResponse(
                    id="1",
                    os_name="Amazon Linux 2",
                    os_version="2.0",
                    cloud_provider="aws",
                    image_id="ami-1234567890abcdef0",
                    image_name="sentinelgrid-amazon-linux-2-hardened-20241130",
                    region="us-east-1",
                    hardening_level="CIS Level 1",
                    cis_benchmark_version="2.0.0",
                    agent_version="1.0.0",
                    agent_installed=True,
                    build_date=date.today(),
                    status="active",
                    metadata={"instance_type": "t3.medium"}
                ),
                HardenedImageResponse(
                    id="2",
                    os_name="Ubuntu",
                    os_version="22.04",
                    cloud_provider="aws",
                    image_id="ami-abcdef1234567890",
                    image_name="sentinelgrid-ubuntu-22.04-hardened-20241130",
                    region="us-east-1",
                    hardening_level="CIS Level 1",
                    cis_benchmark_version="1.0.0",
                    agent_version="1.0.0",
                    agent_installed=True,
                    build_date=date.today(),
                    status="active"
                ),
                HardenedImageResponse(
                    id="3",
                    os_name="Ubuntu",
                    os_version="22.04",
                    cloud_provider="gcp",
                    image_id="projects/sentinelgrid/global/images/sentinelgrid-ubuntu-22-04-hardened-20241130",
                    image_name="sentinelgrid-ubuntu-22-04-hardened-20241130",
                    region="us-east1",
                    hardening_level="CIS Level 1",
                    cis_benchmark_version="1.0.0",
                    agent_version="1.0.0",
                    agent_installed=True,
                    build_date=date.today(),
                    status="active"
                ),
                HardenedImageResponse(
                    id="4",
                    os_name="Amazon Linux 2",
                    os_version="2.0",
                    cloud_provider="azure",
                    image_id="/subscriptions/xxx/resourceGroups/packer-images/providers/Microsoft.Compute/images/sentinelgrid-amazon-linux-2-hardened-20241130",
                    image_name="sentinelgrid-amazon-linux-2-hardened-20241130",
                    region="East US",
                    hardening_level="CIS Level 1",
                    cis_benchmark_version="2.0.0",
                    agent_version="1.0.0",
                    agent_installed=True,
                    build_date=date.today(),
                    status="active"
                ),
                HardenedImageResponse(
                    id="5",
                    os_name="Windows Server",
                    os_version="2022",
                    cloud_provider="aws",
                    image_id="ami-windows2022abcdef",
                    image_name="sentinelgrid-windows-server-2022-hardened-20241130",
                    region="us-east-1",
                    hardening_level="CIS Level 1",
                    cis_benchmark_version="1.0.0",
                    agent_version="1.0.0",
                    agent_installed=True,
                    build_date=date.today(),
                    status="active"
                )
            ]
        
        return HardenedImageListResponse(
            images=images,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing hardened images: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list hardened images: {str(e)}")


@router.get("/recommendations/list", response_model=List[HardenedImageResponse])
async def get_recommended_images(
    cloud_provider: str = Query(..., description="Cloud provider"),
    region: Optional[str] = Query(None, description="Region"),
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """
    Get recommended hardened images for a cloud provider and region.
    """
    _ = request_context
    try:
        # Build query for recommended images
        where_conditions = ["cloud_provider = :cloud_provider", "status = 'active'"]
        params = {"cloud_provider": cloud_provider}
        
        if region:
            where_conditions.append("(region = :region OR region IS NULL)")
            params["region"] = region
        
        where_clause = " AND ".join(where_conditions)
        
        # Use existing schema columns (os_type, os_version, etc.) and alias to the response names
        query = f"""
            SELECT 
                id,
                os_type AS os_name,
                os_version,
                cloud_provider,
                image_id,
                image_name,
                region,
                hardening_level,
                COALESCE(metadata->>'cis_benchmark_version', '') AS cis_benchmark_version,
                agent_version,
                FALSE AS agent_installed,
                build_date,
                status,
                metadata
            FROM hardened_images
            WHERE {where_clause}
            ORDER BY 
                CASE os_type
                    WHEN 'Ubuntu' THEN 1
                    WHEN 'Amazon Linux' THEN 2
                    WHEN 'RHEL' THEN 3
                    WHEN 'Debian' THEN 4
                    WHEN 'Windows Server' THEN 5
                    ELSE 6
                END,
                build_date DESC
            LIMIT 10
        """
        
        if db:
            result = db.execute(text(query), params)
            rows = result.fetchall()
            
            images = []
            for row in rows:
                images.append(HardenedImageResponse(
                    id=str(row[0]),
                    os_name=row[1],
                    os_version=row[2],
                    cloud_provider=row[3],
                    image_id=row[4],
                    image_name=row[5],
                    region=row[6],
                    hardening_level=row[7],
                    cis_benchmark_version=row[8],
                    agent_version=row[9],
                    agent_installed=row[10],
                    build_date=row[11],
                    status=row[12],
                    metadata=row[13] if row[13] else {}
                ))
            
            return images
        else:
            # Mock data for development
            mock_images = [
                HardenedImageResponse(
                    id="1",
                    os_name="Ubuntu",
                    os_version="22.04",
                    cloud_provider=cloud_provider,
                    image_id=f"ami-{cloud_provider}123456",
                    image_name=f"sentinelgrid-ubuntu-22.04-hardened-latest",
                    region=region or "us-east-1",
                    hardening_level="CIS Level 1",
                    cis_benchmark_version="1.0.0",
                    agent_version="1.0.0",
                    agent_installed=True,
                    build_date=date.today(),
                    status="active"
                ),
                HardenedImageResponse(
                    id="2",
                    os_name="Amazon Linux 2",
                    os_version="2.0",
                    cloud_provider=cloud_provider,
                    image_id=f"ami-{cloud_provider}abcdef",
                    image_name=f"sentinelgrid-amazon-linux-2-hardened-latest",
                    region=region or "us-east-1",
                    hardening_level="CIS Level 1",
                    cis_benchmark_version="2.0.0",
                    agent_version="1.0.0",
                    agent_installed=True,
                    build_date=date.today(),
                    status="active"
                )
            ]
            
            return mock_images
        
    except Exception as e:
        logger.error(f"Error getting recommended images: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get recommended images: {str(e)}")


@router.get("/{image_id}", response_model=HardenedImageResponse)
async def get_hardened_image(
    image_id: str,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """
    Get details for a specific hardened image.
    """
    _ = request_context
    try:
        query = """
            SELECT 
                id, os_name, os_version, cloud_provider, image_id, image_name,
                region, hardening_level, cis_benchmark_version, agent_version,
                agent_installed, build_date, status, metadata
            FROM hardened_images
            WHERE id = :image_id OR image_id = :image_id
        """
        
        if db:
            result = db.execute(text(query), {"image_id": image_id})
            row = result.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Hardened image not found")
            
            return HardenedImageResponse(
                id=str(row[0]),
                os_name=row[1],
                os_version=row[2],
                cloud_provider=row[3],
                image_id=row[4],
                image_name=row[5],
                region=row[6],
                hardening_level=row[7],
                cis_benchmark_version=row[8],
                agent_version=row[9],
                agent_installed=row[10],
                build_date=row[11],
                status=row[12],
                metadata=row[13] if row[13] else {}
            )
        else:
            # Mock data for development
            raise HTTPException(status_code=404, detail="Hardened image not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting hardened image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get hardened image: {str(e)}")
