"""Unit tests for Prowler analyzer."""

import pytest
import sys
import os
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analyzers.cloud.prowler_analyzer import ProwlerAWSAnalyzer


@pytest.fixture
def prowler_analyzer():
    """Create Prowler analyzer instance."""
    return ProwlerAWSAnalyzer()


@pytest.fixture
def aws_account_observable():
    """Create AWS account observable."""
    return {
        "type": "aws_account",
        "value": "123456789012",
        "metadata": {"environment": "prod"}
    }


@pytest.fixture
def s3_bucket_observable():
    """Create S3 bucket observable."""
    return {
        "type": "aws_s3_bucket",
        "value": "arn:aws:s3:::my-bucket",
        "metadata": {"environment": "staging"}
    }


@pytest.fixture
def mock_prowler_results():
    """Mock Prowler scan results."""
    return {
        "checks": [
            {
                "check_id": "s3_bucket_public_access",
                "check_title": "S3 Bucket has public access",
                "check_description": "S3 bucket allows public access",
                "status": "FAIL",
                "severity": "high",
                "service": "s3",
                "resource_id": "arn:aws:s3:::my-bucket",
                "region": "us-east-1",
                "compliance": {"CIS": ["2.1.1"], "NIST": ["AC-3"]},
                "remediation": "Disable public access on the bucket"
            },
            {
                "check_id": "s3_bucket_encryption",
                "check_title": "S3 Bucket encryption is not enabled",
                "check_description": "S3 bucket does not have encryption enabled",
                "status": "FAIL",
                "severity": "medium",
                "service": "s3",
                "resource_id": "arn:aws:s3:::my-bucket",
                "region": "us-east-1",
                "compliance": {"CIS": ["2.1.2"]},
                "remediation": "Enable default encryption on the bucket"
            }
        ],
        "resources_scanned": 1,
        "duration": 45,
        "prowler_version": "3.0.0"
    }


class TestProwlerAnalyzer:
    """Test suite for Prowler analyzer."""
    
    def test_analyzer_metadata(self, prowler_analyzer):
        """Test analyzer metadata is correct."""
        assert prowler_analyzer.name == "prowler-aws-cspm"
        assert "cspm" in prowler_analyzer.tags
        assert "aws" in prowler_analyzer.tags
        assert "critical" in prowler_analyzer.tags
        assert "aws_account" in prowler_analyzer.supported_observable_types
        assert "aws_s3_bucket" in prowler_analyzer.supported_observable_types
    
    def test_should_run_valid_observable(self, prowler_analyzer, aws_account_observable):
        """Test should_run returns True for valid observable."""
        assert prowler_analyzer.should_run(aws_account_observable) is True
    
    def test_should_run_invalid_observable(self, prowler_analyzer):
        """Test should_run returns False for invalid observable."""
        invalid_observable = {
            "type": "web_application",
            "value": "https://example.com"
        }
        assert prowler_analyzer.should_run(invalid_observable) is False
    
    def test_get_priority_prod_environment(self, prowler_analyzer, aws_account_observable):
        """Test higher priority for production environment."""
        priority = prowler_analyzer.get_priority(aws_account_observable)
        assert priority == 20  # Production should be high priority
    
    def test_get_priority_staging_environment(self, prowler_analyzer, s3_bucket_observable):
        """Test medium priority for staging environment."""
        priority = prowler_analyzer.get_priority(s3_bucket_observable)
        assert priority == 10  # Staging should be medium priority
    
    def test_get_priority_dev_environment(self, prowler_analyzer):
        """Test lower priority for dev environment."""
        dev_observable = {
            "type": "aws_account",
            "value": "123456789012",
            "metadata": {"environment": "dev"}
        }
        priority = prowler_analyzer.get_priority(dev_observable)
        assert priority == 5  # Dev should be lower priority
    
    def test_estimate_duration_account(self, prowler_analyzer, aws_account_observable):
        """Test duration estimate for account scan."""
        duration = prowler_analyzer.estimate_duration(aws_account_observable)
        assert duration == 600  # 10 minutes for full account
    
    def test_estimate_duration_resource(self, prowler_analyzer, s3_bucket_observable):
        """Test duration estimate for resource scan."""
        duration = prowler_analyzer.estimate_duration(s3_bucket_observable)
        assert duration == 60  # 1 minute for single resource
    
    @pytest.mark.asyncio
    async def test_analyze_success(self, prowler_analyzer, aws_account_observable, mock_prowler_results):
        """Test successful analysis."""
        with patch('tools.prowler.prowler_wrapper.scan_account', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = mock_prowler_results
            
            result = await prowler_analyzer.analyze(aws_account_observable)
            
            assert result["status"] == "success"
            assert len(result["findings"]) == 2
            assert result["findings"][0]["source"] == "cspm"
            assert result["findings"][0]["tool"] == "prowler"
            assert result["findings"][0]["severity"] == "high"
            assert result["metadata"]["checks_run"] == 2
    
    @pytest.mark.asyncio
    async def test_analyze_with_config(self, prowler_analyzer, aws_account_observable, mock_prowler_results):
        """Test analysis with custom configuration."""
        config = {
            "role_arn": "arn:aws:iam::123456789012:role/SentinelGridRole",
            "external_id": "sentinel-external-id",
            "regions": ["us-east-1", "us-west-2"]
        }
        
        with patch('tools.prowler.prowler_wrapper.scan_account', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = mock_prowler_results
            
            result = await prowler_analyzer.analyze(aws_account_observable, config)
            
            assert result["status"] == "success"
            mock_scan.assert_called_once()
            call_args = mock_scan.call_args
            assert call_args.kwargs["role_arn"] == config["role_arn"]
            assert call_args.kwargs["external_id"] == config["external_id"]
    
    @pytest.mark.asyncio
    async def test_analyze_failure(self, prowler_analyzer, aws_account_observable):
        """Test analyzer handles failures gracefully."""
        with patch('tools.prowler.prowler_wrapper.scan_account', new_callable=AsyncMock) as mock_scan:
            mock_scan.side_effect = Exception("Prowler scan failed")
            
            result = await prowler_analyzer.analyze(aws_account_observable)
            
            assert result["status"] == "failure"
            assert "error" in result
            assert "Prowler scan failed" in result["error"]
            assert result["findings"] == []
    
    def test_parse_prowler_check(self, prowler_analyzer):
        """Test Prowler check parsing."""
        check = {
            "check_id": "test_check",
            "check_title": "Test Check",
            "check_description": "Test description",
            "status": "FAIL",
            "severity": "critical",
            "service": "s3",
            "resource_id": "arn:aws:s3:::bucket",
            "region": "us-east-1",
            "compliance": {"CIS": ["1.1"], "NIST": ["AC-2"]},
            "remediation": "Fix it"
        }
        
        finding = prowler_analyzer._parse_prowler_check(check)
        
        assert finding["source"] == "cspm"
        assert finding["tool"] == "prowler"
        assert finding["severity"] == "critical"
        assert finding["check_id"] == "test_check"
        assert finding["title"] == "Test Check"
        assert finding["framework_refs"]["cis"] == ["1.1"]
        assert finding["framework_refs"]["nist"] == ["AC-2"]
    
    def test_severity_mapping(self, prowler_analyzer):
        """Test Prowler severity mapping."""
        test_cases = [
            ("critical", "critical"),
            ("high", "high"),
            ("medium", "medium"),
            ("low", "low"),
            ("informational", "info"),
            ("unknown", "medium")  # Default
        ]
        
        for prowler_severity, expected_severity in test_cases:
            check = {
                "check_id": "test",
                "check_title": "Test",
                "check_description": "Test",
                "status": "FAIL",
                "severity": prowler_severity,
                "service": "test"
            }
            
            finding = prowler_analyzer._parse_prowler_check(check)
            assert finding["severity"] == expected_severity


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

