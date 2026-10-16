"""
Adapter Management API
Manage per-tenant LoRA adapters
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from pydantic import BaseModel, Field
import logging
import os

from app.services.adapter_manager import AdapterManager

router = APIRouter(prefix="/internal/llm/adapters", tags=["adapters"])
logger = logging.getLogger(__name__)

adapter_manager = AdapterManager(
    adapter_storage_path=os.getenv("ADAPTER_STORAGE_PATH", "/models/adapters")
)


class AdapterInfo(BaseModel):
    """Adapter information model."""
    tenant_id: str
    version: str
    path: str
    metadata: dict


class AdapterListResponse(BaseModel):
    """List of adapters for a tenant."""
    tenant_id: str
    adapters: List[AdapterInfo]


@router.get("/{tenant_id}", response_model=AdapterListResponse, summary="List Tenant Adapters")
async def list_tenant_adapters(tenant_id: str):
    """List all adapter versions for a tenant."""
    try:
        adapters = adapter_manager.list_tenant_adapters(tenant_id)
        
        return AdapterListResponse(
            tenant_id=tenant_id,
            adapters=[
                AdapterInfo(
                    tenant_id=tenant_id,
                    version=adapter["version"],
                    path=adapter["path"],
                    metadata=adapter.get("metadata", {})
                )
                for adapter in adapters
            ]
        )
    except Exception as e:
        logger.error(f"Error listing adapters for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{tenant_id}/cache", summary="Clear Adapter Cache")
async def clear_adapter_cache(tenant_id: str):
    """Clear cached adapter for a tenant."""
    try:
        adapter_manager.unload_adapter(tenant_id)
        return {"status": "success", "message": f"Cache cleared for tenant {tenant_id}"}
    except Exception as e:
        logger.error(f"Error clearing cache for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

