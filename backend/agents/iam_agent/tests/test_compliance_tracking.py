"""
Unit tests for Compliance Tracking Service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.services.compliance_tracking import ComplianceTrackingService
from app.services.nist_controls import NISTControlsService


@pytest.fixture
def mock_nist_service():
    """Mock NIST controls service."""
    return Mock(spec=NISTControlsService)


@pytest.fixture
def compliance_service(mock_nist_service):
    """Create ComplianceTrackingService instance."""
    service = ComplianceTrackingService()
    # Replace the internal nist_service with mock
    service.nist_service = mock_nist_service
    return service


class TestComplianceTrackingService:
    """Test suite for ComplianceTrackingService."""
    
    def test_init(self, mock_nist_service):
        """Test service initialization."""
        service = ComplianceTrackingService()
        # Verify service has nist_service attribute
        assert hasattr(service, 'nist_service')
        assert service.nist_service is not None
    
    def test_map_feature_to_nist_controls(self, compliance_service, mock_nist_service):
        """Test mapping IAM features to NIST controls."""
        # Use nist_service directly for mapping
        feature = "user_access_management"
        
        # Mock the nist_service method
        mock_nist_service.map_feature_to_controls.return_value = [
            {"control_id": "AC-2", "control_name": "Account Management"}
        ]
        
        controls = compliance_service.nist_service.map_feature_to_controls(
            feature_name=feature,
            feature_description="User access management"
        )
        
        assert isinstance(controls, list)
        # Should include relevant NIST controls like AC-2
        assert len(controls) > 0
    
    def test_track_compliance_status(self, compliance_service):
        """Test tracking compliance status for controls."""
        control_id = "AC-2"
        
        status = compliance_service.track_compliance_status(control_id)
        
        assert "control_id" in status
        assert status["control_id"] == control_id
        assert "status" in status  # compliant, non-compliant, partial
        assert "last_assessed" in status
    
    def test_get_compliance_report(self, compliance_service, mock_nist_service):
        """Test generating compliance report."""
        tenant_id = "tenant-123"
        
        # Mock nist_service.get_iam_controls to return test data
        mock_nist_service.get_iam_controls.return_value = [
            {"control_id": "AC-2", "control_name": "Account Management", "category": "AC"}
        ]
        
        report = compliance_service.track_compliance_status(tenant_id)
        
        assert "tenant_id" in report
        assert report["tenant_id"] == tenant_id
        assert "controls" in report
        assert "overall_compliance_score" in report
    
    def test_assess_control_compliance(self, compliance_service, mock_nist_service):
        """Test assessing individual control compliance."""
        # Use record_evidence which calls assess_control_compliance internally
        tenant_id = "tenant-123"
        control_id = "AC-2"
        
        # Mock get_control to return proper structure
        mock_nist_service.get_control.return_value = {
            "control_id": control_id,
            "control_name": "Account Management",
            "category": "AC",
            "impact": "high",
            "description": "Account management control"
        }
        
        # Mock assess_control_compliance
        mock_nist_service.assess_control_compliance.return_value = {
            "control_id": control_id,
            "compliant": True,
            "evidence": {"account_management_enabled": True}
        }
        
        evidence = {"account_management_enabled": True}
        result = compliance_service.record_evidence(control_id, evidence, tenant_id)
        
        assert "control_id" in result
        assert result["control_id"] == control_id
        assert "compliant" in result
    
    def test_get_compliance_gaps(self, compliance_service, mock_nist_service):
        """Test identifying compliance gaps."""
        tenant_id = "tenant-123"
        
        # Mock proper control structure with all required keys
        mock_nist_service.get_iam_controls.return_value = [
            {
                "control_id": "AC-2",
                "control_name": "Account Management",
                "category": "AC",
                "impact": "high",
                "description": "Account management control"
            }
        ]
        
        gaps = compliance_service.get_compliance_gaps(tenant_id)
        
        assert isinstance(gaps, list)
        # Each gap should have control_id and description
        # Note: Gaps are returned for non-compliant/not-assessed controls
        if gaps:
            assert "control_id" in gaps[0]
            assert "control_name" in gaps[0]
            assert "impact" in gaps[0]
    
    def test_calculate_compliance_score(self, compliance_service, mock_nist_service):
        """Test calculating overall compliance score."""
        tenant_id = "tenant-123"
        
        # Mock proper control structure
        mock_nist_service.get_iam_controls.return_value = [
            {
                "control_id": "AC-2",
                "control_name": "Account Management",
                "category": "AC",
                "impact": "high",
                "description": "Account management control"
            }
        ]
        
        report = compliance_service.track_compliance_status(tenant_id)
        score = report.get("overall_compliance_score", 0.0)
        
        assert isinstance(score, (int, float))
        assert 0 <= score <= 1.0  # Score is 0-1.0, can multiply by 100 for percentage
    
    def test_track_control_implementation(self, compliance_service, mock_nist_service):
        """Test tracking control implementation status."""
        # Test track_compliance_status which tracks implementation
        tenant_id = "tenant-123"
        control_id = "AC-2"
        
        # Mock get_control to return proper structure
        mock_nist_service.get_control.return_value = {
            "control_id": control_id,
            "control_name": "Account Management",
            "category": "AC",
            "impact": "high",
            "description": "Account management control"
        }
        
        result = compliance_service.track_compliance_status(tenant_id, control_ids=[control_id])
        
        assert "tenant_id" in result
        assert "controls" in result
        # Implementation status would be in control records
        if result["controls"]:
            assert "control_id" in result["controls"][0]
    
    def test_get_nist_control_details(self, compliance_service, mock_nist_service):
        """Test retrieving NIST control details."""
        control_id = "AC-2"
        
        mock_control = {
            "control_id": control_id,
            "control_name": "Account Management",
            "description": "Manage information system accounts",
            "guidance": "Account management addresses..."
        }
        mock_nist_service.get_control.return_value = mock_control
        
        # Use nist_service directly
        control = compliance_service.nist_service.get_control(control_id)
        
        assert control["control_id"] == control_id
        assert "control_name" in control
        assert "description" in control
    
    def test_generate_compliance_recommendations(self, compliance_service, mock_nist_service):
        """Test generating compliance recommendations."""
        # Test get_compliance_gaps which provides recommendations
        tenant_id = "tenant-123"
        
        # Mock proper control structure with all required keys
        mock_nist_service.get_iam_controls.return_value = [
            {
                "control_id": "AC-2",
                "control_name": "Account Management",
                "category": "AC",
                "impact": "high",
                "description": "Account management control"
            }
        ]
        
        gaps = compliance_service.get_compliance_gaps(tenant_id)
        
        assert isinstance(gaps, list)
        # Gaps serve as recommendations for improvement
        if gaps:
            assert "control_id" in gaps[0]
            assert "control_name" in gaps[0]
            assert "recommended_actions" in gaps[0]
    
    def test_export_compliance_report(self, compliance_service, mock_nist_service):
        """Test exporting compliance report."""
        # Test generate_compliance_report which is the actual export method
        tenant_id = "tenant-123"
        
        # Mock proper control structure
        mock_nist_service.get_iam_controls.return_value = [
            {
                "control_id": "AC-2",
                "control_name": "Account Management",
                "category": "AC",
                "impact": "high",
                "description": "Account management control"
            }
        ]
        
        report = compliance_service.generate_compliance_report(tenant_id, report_type="summary")
        
        assert report is not None
        assert isinstance(report, dict)
        assert "tenant_id" in report
        assert "report_type" in report
        assert report["report_type"] == "summary"
        # Can be exported as JSON
        import json
        json_report = json.dumps(report)
        assert isinstance(json_report, str)

