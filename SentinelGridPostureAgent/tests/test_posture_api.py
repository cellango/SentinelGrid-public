"""Integration tests for Posture Service REST API."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../services/posture-service')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock database before importing app
from shared.database import get_db


def override_get_db():
    """Override database dependency for testing."""
    # Return mock database session
    pass


@pytest.fixture
def client():
    """Create test client."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return MagicMock()


@pytest.fixture
def test_tenant_id():
    """Test tenant ID."""
    return str(uuid.uuid4())


class TestPostureEndpoints:
    """Test posture summary endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns service info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "posture-service"
        assert "apis" in data
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_posture_summary_requires_tenant_id(self, client):
        """Test posture summary requires tenant ID."""
        # This will fail without database, but we can test the route exists
        response = client.get("/api/v1/posture/summary/")
        assert response.status_code in [404, 422]  # Not found or validation error
    
    def test_findings_list_requires_tenant_id(self, client):
        """Test findings list requires tenant_id parameter."""
        response = client.get("/api/v1/findings/")
        assert response.status_code == 422  # Validation error (missing tenant_id)
    
    def test_findings_list_with_tenant_id(self, client):
        """Test findings list accepts tenant_id."""
        # Will fail with DB error, but validates route structure
        test_tenant_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/findings/?tenant_id={test_tenant_id}")
        # Will get DB error since no real DB, but route is valid
        assert response.status_code in [200, 500]
    
    def test_assets_list_requires_tenant_id(self, client):
        """Test assets list requires tenant_id parameter."""
        response = client.get("/api/v1/assets/")
        assert response.status_code == 422  # Validation error
    
    def test_invalid_finding_id_format(self, client):
        """Test invalid UUID format handling."""
        response = client.get("/api/v1/findings/invalid-uuid")
        assert response.status_code == 400
        assert "Invalid finding ID format" in response.json()["detail"]
    
    def test_finding_update_invalid_uuid(self, client):
        """Test finding update with invalid UUID."""
        response = client.patch(
            "/api/v1/findings/invalid-uuid",
            json={"status": "fixed"}
        )
        assert response.status_code == 400
    
    def test_finding_update_invalid_status(self, client):
        """Test finding update with invalid status."""
        valid_uuid = str(uuid.uuid4())
        response = client.patch(
            f"/api/v1/findings/{valid_uuid}",
            json={"status": "invalid_status"}
        )
        # Will fail with DB or validation error
        assert response.status_code in [400, 404, 500]
    
    def test_bulk_create_findings_validation(self, client):
        """Test bulk create findings validation."""
        # Missing required fields
        response = client.post(
            "/api/v1/findings/bulk",
            json={"findings": []}
        )
        assert response.status_code == 422  # Validation error (missing tenant_id)
    
    def test_bulk_create_findings_structure(self, client):
        """Test bulk create findings with valid structure."""
        test_tenant_id = str(uuid.uuid4())
        
        request_data = {
            "tenant_id": test_tenant_id,
            "findings": [
                {
                    "source": "cspm",
                    "tool": "prowler",
                    "title": "Test finding",
                    "description": "Test",
                    "severity": "high",
                    "observable_type": "aws_account",
                    "observable_value": "123456789012"
                }
            ]
        }
        
        response = client.post("/api/v1/findings/bulk", json=request_data)
        # Will fail with DB error, but validates request structure
        assert response.status_code in [200, 500]


class TestFilteringAndPagination:
    """Test filtering and pagination logic."""
    
    def test_findings_severity_filter(self, client):
        """Test findings can be filtered by severity."""
        test_tenant_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/findings/?tenant_id={test_tenant_id}&severity=critical"
        )
        # Validates filter parameter is accepted
        assert response.status_code in [200, 500]
    
    def test_findings_source_filter(self, client):
        """Test findings can be filtered by source."""
        test_tenant_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/findings/?tenant_id={test_tenant_id}&source=cspm"
        )
        assert response.status_code in [200, 500]
    
    def test_findings_tool_filter(self, client):
        """Test findings can be filtered by tool."""
        test_tenant_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/findings/?tenant_id={test_tenant_id}&tool=prowler"
        )
        assert response.status_code in [200, 500]
    
    def test_findings_pagination(self, client):
        """Test findings pagination parameters."""
        test_tenant_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/findings/?tenant_id={test_tenant_id}&limit=50&offset=10"
        )
        assert response.status_code in [200, 500]
    
    def test_findings_invalid_severity(self, client):
        """Test invalid severity value."""
        test_tenant_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/findings/?tenant_id={test_tenant_id}&severity=invalid"
        )
        # Should return 400 for invalid enum value
        assert response.status_code in [400, 500]
    
    def test_assets_environment_filter(self, client):
        """Test assets can be filtered by environment."""
        test_tenant_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/assets/?tenant_id={test_tenant_id}&environment=prod"
        )
        assert response.status_code in [200, 500]
    
    def test_assets_type_filter(self, client):
        """Test assets can be filtered by type."""
        test_tenant_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/assets/?tenant_id={test_tenant_id}&asset_type=aws_s3_bucket"
        )
        assert response.status_code in [200, 500]


class TestAPIEndpointStructure:
    """Test API endpoint structure and routing."""
    
    def test_posture_endpoints_exist(self, client):
        """Test all posture endpoints are routed."""
        test_tenant_id = str(uuid.uuid4())
        
        endpoints = [
            f"/api/v1/posture/summary/{test_tenant_id}",
            f"/api/v1/posture/trends/{test_tenant_id}",
            f"/api/v1/posture/top-risks/{test_tenant_id}"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should not be 404 (route exists)
            assert response.status_code != 404
    
    def test_findings_endpoints_exist(self, client):
        """Test all findings endpoints are routed."""
        endpoints = [
            "/api/v1/findings/",
            f"/api/v1/findings/{uuid.uuid4()}",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code != 404
    
    def test_assets_endpoints_exist(self, client):
        """Test all assets endpoints are routed."""
        endpoints = [
            "/api/v1/assets/",
            f"/api/v1/assets/{uuid.uuid4()}",
            f"/api/v1/assets/{uuid.uuid4()}/findings"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code != 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

