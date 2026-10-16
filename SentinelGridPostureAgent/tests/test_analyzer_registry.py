"""Unit tests for analyzer registry."""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analyzers.registry import AnalyzerRegistry
from analyzers.base_analyzer import BaseAnalyzer


class MockAnalyzer1(BaseAnalyzer):
    """Mock analyzer for testing."""
    name = "mock-analyzer-1"
    description = "Test analyzer 1"
    supported_observable_types = ["web_application"]
    tags = ["test", "critical"]
    
    async def analyze(self, observable, config=None):
        return {"status": "success", "findings": []}


class MockAnalyzer2(BaseAnalyzer):
    """Another mock analyzer for testing."""
    name = "mock-analyzer-2"
    description = "Test analyzer 2"
    supported_observable_types = ["web_application", "aws_account"]
    tags = ["test", "cloud"]
    
    async def analyze(self, observable, config=None):
        return {"status": "success", "findings": []}


def test_registry_initialization():
    """Test registry initializes empty."""
    registry = AnalyzerRegistry()
    assert len(registry) == 0
    assert registry.list_observable_types() == []


def test_register_analyzer():
    """Test registering an analyzer."""
    registry = AnalyzerRegistry()
    registry.register(MockAnalyzer1)
    
    assert len(registry) == 1
    assert "web_application" in registry.list_observable_types()
    assert "test" in registry.list_tags()


def test_get_analyzers_for_observable():
    """Test getting analyzers for observable type."""
    registry = AnalyzerRegistry()
    registry.register(MockAnalyzer1)
    registry.register(MockAnalyzer2)
    
    # Get analyzers for web_application
    analyzers = registry.get_analyzers_for_observable("web_application")
    assert len(analyzers) == 2
    
    # Get analyzers for aws_account
    analyzers = registry.get_analyzers_for_observable("aws_account")
    assert len(analyzers) == 1
    assert analyzers[0].name == "mock-analyzer-2"


def test_filter_by_tags():
    """Test filtering analyzers by tags."""
    registry = AnalyzerRegistry()
    registry.register(MockAnalyzer1)
    registry.register(MockAnalyzer2)
    
    # Filter by "critical" tag
    analyzers = registry.get_analyzers_for_observable("web_application", tags=["critical"])
    assert len(analyzers) == 1
    assert analyzers[0].name == "mock-analyzer-1"
    
    # Filter by "cloud" tag
    analyzers = registry.get_analyzers_for_observable("web_application", tags=["cloud"])
    assert len(analyzers) == 1
    assert analyzers[0].name == "mock-analyzer-2"


def test_get_stats():
    """Test registry statistics."""
    registry = AnalyzerRegistry()
    registry.register(MockAnalyzer1)
    registry.register(MockAnalyzer2)
    
    stats = registry.get_stats()
    assert stats["total_analyzers"] == 2
    assert stats["observable_types"] == 2  # web_application, aws_account
    assert "web_application" in stats["analyzers_by_type"]
    assert stats["analyzers_by_type"]["web_application"] == 2


def test_unregister_analyzer():
    """Test unregistering an analyzer."""
    registry = AnalyzerRegistry()
    registry.register(MockAnalyzer1)
    registry.register(MockAnalyzer2)
    
    assert len(registry) == 2
    
    registry.unregister("mock-analyzer-1")
    assert len(registry) == 1
    
    analyzers = registry.get_analyzers_for_observable("web_application")
    assert len(analyzers) == 1
    assert analyzers[0].name == "mock-analyzer-2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

