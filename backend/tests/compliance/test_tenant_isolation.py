import os
import sys
import tempfile
import pytest

# Make model_gateway app importable for service classes
MODEL_GATEWAY_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "services", "model_gateway")
)
if MODEL_GATEWAY_ROOT not in sys.path:
    sys.path.insert(0, MODEL_GATEWAY_ROOT)

from app.services.rag_service import RAGService  # type: ignore
from app.services.adapter_manager import AdapterManager  # type: ignore
from app.services.knowledge_base_loader import KnowledgeBaseLoader  # type: ignore


def test_rag_search_requires_tenant_returns_empty():
    rag = RAGService(db_session=None)
    results = rag.search("test without tenant", tenant_id=None)
    assert results == []


def test_adapter_cache_is_tenant_scoped():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = AdapterManager(adapter_storage_path=tmpdir)
        mgr._cache_adapter("tenant-a:latest", {"tenant_id": "tenant-a"})
        mgr._cache_adapter("tenant-b:latest", {"tenant_id": "tenant-b"})
        assert set(mgr.loaded_adapters.keys()) == {"tenant-a:latest", "tenant-b:latest"}
        assert mgr.loaded_adapters["tenant-a:latest"]["tenant_id"] != mgr.loaded_adapters["tenant-b:latest"]["tenant_id"]


def test_soc2_sample_content_includes_criteria_and_schema():
    loader = KnowledgeBaseLoader(db_session=None)
    data = loader._get_sample_soc2_content()
    items = data.get("items", [])
    assert any(item.get("criteria_id") == "CC6.1" for item in items)
    assert any(item.get("criteria_id") == "REPORT_SCHEMA" for item in items)
