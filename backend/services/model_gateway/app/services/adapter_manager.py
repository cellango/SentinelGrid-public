"""
Adapter Manager Service
Manages per-tenant LoRA adapters for model personalization
"""

import logging
import os
from typing import Dict, Optional, Any
from pathlib import Path
import json

from app.services.peft_adapter_service import PEFTAdapterService

logger = logging.getLogger(__name__)


class AdapterManager:
    """Manages loading and switching of per-tenant LoRA adapters."""
    
    def __init__(self, adapter_storage_path: str):
        self.adapter_storage_path = Path(adapter_storage_path)
        self.adapter_storage_path.mkdir(parents=True, exist_ok=True)
        self.loaded_adapters: Dict[str, Any] = {}  # Cache loaded adapters
        self.max_cached_adapters = 10  # Keep 10 most recent adapters in memory
        self.peft_service = PEFTAdapterService()  # PEFT adapter service
    
    def get_adapter_path(self, tenant_id: str, version: Optional[str] = None) -> Optional[Path]:
        """
        Get path to tenant adapter.
        
        Args:
            tenant_id: Tenant ID
            version: Adapter version (defaults to latest)
            
        Returns:
            Path to adapter or None if not found
        """
        tenant_dir = self.adapter_storage_path / f"tenant-{tenant_id}"
        
        if not tenant_dir.exists():
            return None
        
        if version:
            adapter_file = tenant_dir / version / "adapter.bin"
        else:
            # Get latest version
            versions = sorted([d for d in tenant_dir.iterdir() if d.is_dir()], reverse=True)
            if versions:
                adapter_file = versions[0] / "adapter.bin"
            else:
                return None
        
        return adapter_file if adapter_file.exists() else None
    
    def load_adapter(self, tenant_id: str, version: Optional[str] = None) -> Optional[Any]:
        """
        Load tenant adapter into memory.
        
        Args:
            tenant_id: Tenant ID
            version: Adapter version (defaults to latest)
            
        Returns:
            Adapter object or None
        """
        # Check cache
        cache_key = f"{tenant_id}:{version or 'latest'}"
        if cache_key in self.loaded_adapters:
            return self.loaded_adapters[cache_key]
        
        adapter_path = self.get_adapter_path(tenant_id, version)
        if not adapter_path:
            logger.warning(f"Adapter not found for tenant {tenant_id}, version {version}")
            return None
        
        try:
            # Load adapter using PEFT library
            from peft import PeftModel
            
            # Note: This requires base model to be loaded first
            # In actual implementation, adapter would be merged with base model
            # adapter = PeftModel.from_pretrained(base_model, adapter_path)
            
            # For now, return adapter path/metadata
            adapter_info = {
                "tenant_id": tenant_id,
                "version": version or "latest",
                "path": str(adapter_path),
                "loaded_at": None
            }
            
            # Cache adapter
            self._cache_adapter(cache_key, adapter_info)
            
            logger.info(f"Loaded adapter for tenant {tenant_id}")
            return adapter_info
            
        except Exception as e:
            logger.error(f"Error loading adapter for tenant {tenant_id}: {e}")
            return None
    
    def unload_adapter(self, tenant_id: str):
        """Unload adapter from memory cache."""
        keys_to_remove = [k for k in self.loaded_adapters.keys() if k.startswith(f"{tenant_id}:")]
        for key in keys_to_remove:
            del self.loaded_adapters[key]
    
    def list_tenant_adapters(self, tenant_id: str) -> list:
        """List all adapter versions for a tenant."""
        tenant_dir = self.adapter_storage_path / f"tenant-{tenant_id}"
        
        if not tenant_dir.exists():
            return []
        
        versions = []
        for version_dir in tenant_dir.iterdir():
            if version_dir.is_dir():
                adapter_file = version_dir / "adapter.bin"
                if adapter_file.exists():
                    # Read metadata
                    metadata_file = version_dir / "metadata.json"
                    metadata = {}
                    if metadata_file.exists():
                        with open(metadata_file) as f:
                            metadata = json.load(f)
                    
                    versions.append({
                        "version": version_dir.name,
                        "path": str(adapter_file),
                        "metadata": metadata
                    })
        
        return sorted(versions, key=lambda x: x["version"], reverse=True)
    
    def deploy_adapter(
        self,
        tenant_id: str,
        adapter_data: bytes,
        version: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Deploy a new adapter version for a tenant.
        
        Args:
            tenant_id: Tenant ID
            adapter_data: Adapter binary data
            version: Version string (e.g., "v1", "v2")
            metadata: Adapter metadata (training info, etc.)
            
        Returns:
            True if successful
        """
        try:
            tenant_dir = self.adapter_storage_path / f"tenant-{tenant_id}"
            version_dir = tenant_dir / version
            version_dir.mkdir(parents=True, exist_ok=True)
            
            # Write adapter file
            adapter_file = version_dir / "adapter.bin"
            with open(adapter_file, "wb") as f:
                f.write(adapter_data)
            
            # Write metadata
            metadata_file = version_dir / "metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Deployed adapter {version} for tenant {tenant_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deploying adapter for tenant {tenant_id}: {e}")
            return False
    
    def _cache_adapter(self, cache_key: str, adapter_info: Any):
        """Cache adapter, evicting least recently used if needed."""
        if len(self.loaded_adapters) >= self.max_cached_adapters:
            # Remove oldest (simple FIFO, could use LRU)
            oldest_key = next(iter(self.loaded_adapters))
            del self.loaded_adapters[oldest_key]
        
        self.loaded_adapters[cache_key] = adapter_info

