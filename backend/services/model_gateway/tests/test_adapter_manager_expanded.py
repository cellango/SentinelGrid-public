"""
Expanded tests for Adapter Manager Service
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.services.adapter_manager import AdapterManager


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return Mock()


@pytest.fixture
def adapter_manager(mock_db_session, tmp_path):
    """Create AdapterManager instance."""
    adapter_storage = tmp_path / "adapters"
    adapter_storage.mkdir(parents=True, exist_ok=True)
    return AdapterManager(adapter_storage_path=str(adapter_storage))


class TestAdapterManagerExpanded:
    """Expanded test suite for AdapterManager."""
    
    def test_load_adapter_caching(self, adapter_manager, tmp_path):
        """Test that adapters are cached after loading."""
        tenant_id = str(uuid.uuid4())
        
        # Create adapter file
        tenant_dir = tmp_path / "adapters" / f"tenant-{tenant_id}" / "v1.0.0"
        tenant_dir.mkdir(parents=True, exist_ok=True)
        (tenant_dir / "adapter.bin").touch()
        
        # Load adapter twice
        adapter1 = adapter_manager.load_adapter(tenant_id, "v1.0.0")
        adapter2 = adapter_manager.load_adapter(tenant_id, "v1.0.0")
        
        # Should return same adapter (cached)
        assert adapter1 is not None
        assert adapter1 == adapter2
        # Verify cache was used (check cache size)
        assert len(adapter_manager.loaded_adapters) == 1
    
    def test_cache_eviction_on_limit(self, adapter_manager, tmp_path):
        """Test that cache evicts oldest adapter when limit reached."""
        adapter_manager.max_cached_adapters = 3
        
        # Create adapter files for 4 different tenants
        for i in range(4):
            tenant_id = str(uuid.uuid4())
            tenant_dir = tmp_path / "adapters" / f"tenant-{tenant_id}" / "v1.0.0"
            tenant_dir.mkdir(parents=True, exist_ok=True)
            (tenant_dir / "adapter.bin").touch()
            
            adapter_manager.load_adapter(tenant_id, "v1.0.0")
        
        # Cache should only contain 3 adapters (FIFO eviction)
        assert len(adapter_manager.loaded_adapters) == 3
    
    def test_list_tenant_adapters(self, adapter_manager, tmp_path):
        """Test listing all adapter versions for a tenant."""
        tenant_id = str(uuid.uuid4())
        
        # Create multiple adapter versions
        tenant_dir = tmp_path / "adapters" / f"tenant-{tenant_id}"
        for version in ["v1.0.0", "v1.1.0", "v1.2.0"]:
            version_dir = tenant_dir / version
            version_dir.mkdir(parents=True, exist_ok=True)
            (version_dir / "adapter.bin").touch()
            (version_dir / "metadata.json").write_text('{"training_date": "2024-01-01"}')
        
        adapters = adapter_manager.list_tenant_adapters(tenant_id)
        
        assert len(adapters) == 3
        assert all("version" in a for a in adapters)
        # Should be sorted by version (newest first)
        assert adapters[0]["version"] == "v1.2.0"
    
    def test_get_adapter_path_with_version(self, adapter_manager, tmp_path):
        """Test getting adapter path with specific version."""
        tenant_id = str(uuid.uuid4())
        version = "v1.0.0"
        
        # Create adapter directory structure
        tenant_dir = tmp_path / "adapters" / f"tenant-{tenant_id}" / version
        tenant_dir.mkdir(parents=True, exist_ok=True)
        (tenant_dir / "adapter.bin").touch()
        
        path = adapter_manager.get_adapter_path(tenant_id, version)
        
        assert path is not None
        assert path.exists()
    
    def test_get_adapter_path_latest_version(self, adapter_manager, tmp_path):
        """Test getting adapter path for latest version."""
        tenant_id = str(uuid.uuid4())
        
        # Create multiple versions
        tenant_dir = tmp_path / "adapters" / f"tenant-{tenant_id}"
        (tenant_dir / "v1.0.0" / "adapter.bin").parent.mkdir(parents=True, exist_ok=True)
        (tenant_dir / "v1.0.0" / "adapter.bin").touch()
        (tenant_dir / "v1.1.0" / "adapter.bin").parent.mkdir(parents=True, exist_ok=True)
        (tenant_dir / "v1.1.0" / "adapter.bin").touch()
        
        path = adapter_manager.get_adapter_path(tenant_id)
        
        assert path is not None
        assert "v1.1.0" in str(path)  # Latest version
    
    def test_deploy_adapter(self, adapter_manager, tmp_path):
        """Test deploying an adapter version."""
        tenant_id = str(uuid.uuid4())
        version = "v1.0.0"
        adapter_data = b"fake adapter binary data"
        metadata = {
            "training_date": "2024-01-01",
            "training_samples": 100
        }
        
        result = adapter_manager.deploy_adapter(tenant_id, adapter_data, version, metadata)
        
        assert result is True
        
        # Verify adapter file was created
        adapter_file = tmp_path / "adapters" / f"tenant-{tenant_id}" / version / "adapter.bin"
        assert adapter_file.exists()
        
        # Verify metadata file was created
        metadata_file = tmp_path / "adapters" / f"tenant-{tenant_id}" / version / "metadata.json"
        assert metadata_file.exists()
    
    def test_tenant_isolation_in_cache(self, adapter_manager, tmp_path):
        """Test that adapter cache maintains tenant isolation."""
        tenant_1 = str(uuid.uuid4())
        tenant_2 = str(uuid.uuid4())
        
        # Create adapters for both tenants
        tenant1_dir = tmp_path / "adapters" / f"tenant-{tenant_1}" / "v1.0.0"
        tenant1_dir.mkdir(parents=True, exist_ok=True)
        (tenant1_dir / "adapter.bin").touch()
        
        tenant2_dir = tmp_path / "adapters" / f"tenant-{tenant_2}" / "v1.0.0"
        tenant2_dir.mkdir(parents=True, exist_ok=True)
        (tenant2_dir / "adapter.bin").touch()
        
        adapter1 = adapter_manager.load_adapter(tenant_1, "v1.0.0")
        adapter2 = adapter_manager.load_adapter(tenant_2, "v1.0.0")
        
        # Should load different adapters for different tenants
        assert adapter1 is not None
        assert adapter2 is not None
        assert adapter1["tenant_id"] == tenant_1
        assert adapter2["tenant_id"] == tenant_2
        assert len(adapter_manager.loaded_adapters) == 2

