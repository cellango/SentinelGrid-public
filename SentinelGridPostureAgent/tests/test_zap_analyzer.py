"""Unit tests for ZAP analyzer."""

import pytest
import sys
import os
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analyzers.webapp.zap_analyzer import ZAPAnalyzer


@pytest.fixture
def zap_analyzer():
    """Create ZAP analyzer instance."""
    return ZAPAnalyzer()


@pytest.fixture
def webapp_observable():
    """Create web application observable."""
    return {
        "type": "web_application",
        "value": "https://app.example.com",
        "metadata": {"environment": "prod", "requires_auth": True}
    }


@pytest.fixture
def mock_zap_results():
    """Mock ZAP scan results."""
    return {
        "alerts": [
            {
                "pluginid": "40012",
                "name": "Cross Site Scripting (Reflected)",
                "risk": "High",
                "confidence": "Medium",
                "description": "Cross-site Scripting (XSS) is possible",
                "url": "https://app.example.com/search",
                "method": "GET",
                "param": "q",
                "attack": "<script>alert(1)</script>",
                "evidence": "script tag found",
                "solution": "Sanitize user input",
                "cweid": "79",
                "tags": {"OWASP_2021": "A03"}
            },
            {
                "pluginid": "10202",
                "name": "Absence of Anti-CSRF Tokens",
                "risk": "Medium",
                "confidence": "Medium",
                "description": "No Anti-CSRF tokens found",
                "url": "https://app.example.com/form",
                "method": "POST",
                "solution": "Implement CSRF protection"
            }
        ],
        "urls_tested": 25,
        "duration": 450,
        "zap_version": "2.14.0",
        "scan_type": "full"
    }


class TestZAPAnalyzer:
    """Test suite for ZAP analyzer."""
    
    def test_analyzer_metadata(self, zap_analyzer):
        """Test analyzer metadata."""
        assert zap_analyzer.name == "zap-dast"
        assert "dast" in zap_analyzer.tags
        assert "webapp" in zap_analyzer.tags
        assert "web_application" in zap_analyzer.supported_observable_types
        assert "api_endpoint" in zap_analyzer.supported_observable_types
    
    def test_should_run_https_url(self, zap_analyzer):
        """Test should_run for HTTPS URL."""
        observable = {
            "type": "web_application",
            "value": "https://example.com"
        }
        assert zap_analyzer.should_run(observable) is True
    
    def test_should_run_http_url(self, zap_analyzer):
        """Test should_run for HTTP URL."""
        observable = {
            "type": "web_application",
            "value": "http://example.com"
        }
        assert zap_analyzer.should_run(observable) is True
    
    def test_should_run_invalid_url(self, zap_analyzer):
        """Test should_run for invalid URL."""
        observable = {
            "type": "web_application",
            "value": "ftp://example.com"
        }
        assert zap_analyzer.should_run(observable) is False
    
    def test_should_run_wrong_type(self, zap_analyzer):
        """Test should_run for wrong observable type."""
        observable = {
            "type": "aws_account",
            "value": "123456789012"
        }
        assert zap_analyzer.should_run(observable) is False
    
    def test_get_priority_prod_with_auth(self, zap_analyzer, webapp_observable):
        """Test priority for production app with auth."""
        priority = zap_analyzer.get_priority(webapp_observable)
        assert priority == 15  # Prod environment
    
    def test_get_priority_with_auth_only(self, zap_analyzer):
        """Test priority for app with auth but not prod."""
        observable = {
            "type": "web_application",
            "value": "https://app.example.com",
            "metadata": {"requires_auth": True}
        }
        priority = zap_analyzer.get_priority(observable)
        assert priority == 10
    
    def test_get_priority_basic(self, zap_analyzer):
        """Test priority for basic web app."""
        observable = {
            "type": "web_application",
            "value": "https://app.example.com",
            "metadata": {}
        }
        priority = zap_analyzer.get_priority(observable)
        assert priority == 5
    
    def test_estimate_duration_quick_scan(self, zap_analyzer):
        """Test duration estimate for quick scan."""
        observable = {
            "type": "web_application",
            "value": "https://app.example.com",
            "metadata": {"scan_type": "quick"}
        }
        duration = zap_analyzer.estimate_duration(observable)
        assert duration == 300  # 5 minutes
    
    def test_estimate_duration_full_scan(self, zap_analyzer):
        """Test duration estimate for full scan."""
        observable = {
            "type": "web_application",
            "value": "https://app.example.com",
            "metadata": {"scan_type": "full"}
        }
        duration = zap_analyzer.estimate_duration(observable)
        assert duration == 900  # 15 minutes
    
    @pytest.mark.asyncio
    async def test_analyze_success(self, zap_analyzer, webapp_observable, mock_zap_results):
        """Test successful ZAP analysis."""
        with patch('tools.zap.zap_wrapper.scan', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = mock_zap_results
            
            result = await zap_analyzer.analyze(webapp_observable)
            
            assert result["status"] == "success"
            assert len(result["findings"]) == 2
            assert result["findings"][0]["source"] == "dast"
            assert result["findings"][0]["tool"] == "zap"
            assert result["findings"][0]["severity"] == "high"
            assert result["metadata"]["urls_tested"] == 25
            assert result["metadata"]["zap_version"] == "2.14.0"
    
    @pytest.mark.asyncio
    async def test_analyze_with_config(self, zap_analyzer, webapp_observable, mock_zap_results):
        """Test analysis with custom configuration."""
        config = {
            "scan_type": "quick",
            "auth": {"username": "test", "password": "test"}
        }
        
        with patch('tools.zap.zap_wrapper.scan', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = mock_zap_results
            
            result = await zap_analyzer.analyze(webapp_observable, config)
            
            assert result["status"] == "success"
            mock_scan.assert_called_once()
            call_kwargs = mock_scan.call_args.kwargs
            assert call_kwargs["scan_type"] == "quick"
            assert call_kwargs["auth_config"] == config["auth"]
    
    @pytest.mark.asyncio
    async def test_analyze_failure(self, zap_analyzer, webapp_observable):
        """Test analyzer handles failures."""
        with patch('tools.zap.zap_wrapper.scan', new_callable=AsyncMock) as mock_scan:
            mock_scan.side_effect = Exception("ZAP connection failed")
            
            result = await zap_analyzer.analyze(webapp_observable)
            
            assert result["status"] == "failure"
            assert "error" in result
            assert "ZAP connection failed" in result["error"]
    
    def test_parse_zap_alert_high_severity(self, zap_analyzer):
        """Test parsing ZAP alert with high severity."""
        alert = {
            "pluginid": "40012",
            "name": "XSS Vulnerability",
            "risk": "High",
            "description": "XSS found",
            "url": "https://example.com",
            "method": "GET",
            "param": "q",
            "cweid": "79",
            "solution": "Sanitize input"
        }
        
        finding = zap_analyzer._parse_zap_alert(alert)
        
        assert finding["source"] == "dast"
        assert finding["tool"] == "zap"
        assert finding["severity"] == "high"
        assert finding["check_id"] == "40012"
        assert finding["title"] == "XSS Vulnerability"
        assert finding["framework_refs"]["cwe"] == ["79"]
    
    def test_parse_zap_alert_with_owasp(self, zap_analyzer):
        """Test parsing ZAP alert with OWASP mapping."""
        alert = {
            "pluginid": "40012",
            "name": "XSS",
            "risk": "High",
            "description": "XSS",
            "cweid": "79",
            "tags": {"OWASP_2021": "A03"},
            "solution": "Fix"
        }
        
        finding = zap_analyzer._parse_zap_alert(alert)
        
        assert "cwe" in finding["framework_refs"]
        assert "owasp_2021" in finding["framework_refs"]
        assert finding["framework_refs"]["owasp_2021"] == ["A03"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

