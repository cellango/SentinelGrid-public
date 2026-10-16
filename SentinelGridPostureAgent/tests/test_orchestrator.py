"""Integration tests for analyzer orchestrator."""

import pytest
import asyncio
from typing import Dict, Any
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analyzers.base_analyzer import BaseAnalyzer


class TestAnalyzer(BaseAnalyzer):
    """Test analyzer that returns mock findings."""
    name = "test-analyzer"
    description = "Test analyzer"
    supported_observable_types = ["test_type"]
    tags = ["test"]
    
    async def analyze(self, observable, config=None):
        return {
            "status": "success",
            "findings": [
                {
                    "source": "cspm",
                    "tool": "test-tool",
                    "title": "Test finding",
                    "description": "Test description",
                    "severity": "high",
                    "evidence": {"test": "data"},
                    "remediation": "Fix it"
                }
            ],
            "metadata": {"test": True}
        }


@pytest.mark.asyncio
async def test_analyzer_execution():
    """Test analyzer executes successfully."""
    analyzer = TestAnalyzer()
    
    observable = {
        "type": "test_type",
        "value": "test-value",
        "metadata": {}
    }
    
    result = await analyzer.analyze(observable)
    
    assert result["status"] == "success"
    assert len(result["findings"]) == 1
    assert result["findings"][0]["severity"] == "high"


@pytest.mark.asyncio
async def test_should_run():
    """Test should_run logic."""
    analyzer = TestAnalyzer()
    
    # Should run for supported type
    observable = {"type": "test_type", "value": "test"}
    assert analyzer.should_run(observable) is True
    
    # Should not run for unsupported type
    observable = {"type": "unsupported_type", "value": "test"}
    assert analyzer.should_run(observable) is False


def test_analyzer_metadata():
    """Test analyzer metadata."""
    analyzer = TestAnalyzer()
    
    assert analyzer.name == "test-analyzer"
    assert "test" in analyzer.tags
    assert "test_type" in analyzer.supported_observable_types


@pytest.mark.asyncio
async def test_parallel_execution():
    """Test running multiple analyzers in parallel."""
    analyzer1 = TestAnalyzer()
    analyzer2 = TestAnalyzer()
    
    observable = {"type": "test_type", "value": "test"}
    
    # Run in parallel
    results = await asyncio.gather(
        analyzer1.analyze(observable),
        analyzer2.analyze(observable)
    )
    
    assert len(results) == 2
    assert all(r["status"] == "success" for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

