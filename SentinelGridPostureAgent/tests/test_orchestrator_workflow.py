"""Integration tests for analyzer orchestrator workflow."""

import pytest
from fastapi.testclient import TestClient
import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../services/analyzer-orchestrator')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def client():
    """Create test client for orchestrator."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def test_tenant_id():
    """Generate test tenant ID."""
    return str(uuid.uuid4())


class TestOrchestratorEndpoints:
    """Test orchestrator API endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "analyzer-orchestrator"
        assert data["status"] == "healthy"
        assert "registered_analyzers" in data
    
    def test_health_endpoint(self, client):
        """Test health check."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_list_analyzers(self, client):
        """Test list all analyzers."""
        response = client.get("/api/v1/analyzers")
        
        assert response.status_code == 200
        data = response.json()
        assert "analyzers" in data
        assert "stats" in data
        assert len(data["analyzers"]) >= 5  # We registered 5 analyzers
        
        # Verify expected analyzers are present
        analyzer_names = [a["name"] for a in data["analyzers"]]
        assert "prowler-aws-cspm" in analyzer_names
        assert "zap-dast" in analyzer_names
        assert "trivy-vuln-scan" in analyzer_names
        assert "checkov-iac" in analyzer_names
        assert "gitleaks-secrets" in analyzer_names
    
    def test_list_analyzers_by_observable_type(self, client):
        """Test filtering analyzers by observable type."""
        response = client.get("/api/v1/analyzers?observable_type=web_application")
        
        assert response.status_code == 200
        data = response.json()
        assert "analyzers" in data
        assert data["observable_type"] == "web_application"
        
        # Should only return ZAP for web applications
        analyzer_names = [a["name"] for a in data["analyzers"]]
        assert "zap-dast" in analyzer_names
    
    def test_list_observable_types(self, client):
        """Test list supported observable types."""
        response = client.get("/api/v1/observable-types")
        
        assert response.status_code == 200
        data = response.json()
        assert "observable_types" in data
        assert "count" in data
        
        # Verify expected types
        types = data["observable_types"]
        assert "web_application" in types
        assert "aws_account" in types
        assert "docker_image" in types
        assert "git_repository" in types
    
    def test_list_tags(self, client):
        """Test list analyzer tags."""
        response = client.get("/api/v1/tags")
        
        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        assert "count" in data
        
        tags = data["tags"]
        assert "cspm" in tags
        assert "dast" in tags
        assert "critical" in tags


class TestAnalyzeWorkflow:
    """Test the analyze observable workflow."""
    
    def test_analyze_web_application(self, client, test_tenant_id):
        """Test analyzing a web application."""
        request_data = {
            "tenant_id": test_tenant_id,
            "observable_type": "web_application",
            "observable_value": "https://example.com"
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "analyzers_scheduled" in data
        assert "status" in data
        assert data["status"] == "running"
        assert "zap-dast" in data["analyzers_scheduled"]
    
    def test_analyze_aws_account(self, client, test_tenant_id):
        """Test analyzing an AWS account."""
        request_data = {
            "tenant_id": test_tenant_id,
            "observable_type": "aws_account",
            "observable_value": "123456789012"
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "prowler-aws-cspm" in data["analyzers_scheduled"]
    
    def test_analyze_docker_image(self, client, test_tenant_id):
        """Test analyzing a Docker image."""
        request_data = {
            "tenant_id": test_tenant_id,
            "observable_type": "docker_image",
            "observable_value": "nginx:latest"
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "trivy-vuln-scan" in data["analyzers_scheduled"]
    
    def test_analyze_git_repository_with_iac(self, client, test_tenant_id):
        """Test analyzing a Git repository with IaC files."""
        request_data = {
            "tenant_id": test_tenant_id,
            "observable_type": "git_repository",
            "observable_value": "https://github.com/org/repo",
            "metadata": {
                "has_terraform": True,
                "has_kubernetes_manifests": True
            }
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        # Should trigger both Checkov and Gitleaks
        assert "checkov-iac" in data["analyzers_scheduled"]
        assert "gitleaks-secrets" in data["analyzers_scheduled"]
    
    def test_analyze_git_repository_without_iac(self, client, test_tenant_id):
        """Test analyzing a Git repository without IaC files."""
        request_data = {
            "tenant_id": test_tenant_id,
            "observable_type": "git_repository",
            "observable_value": "https://github.com/org/repo",
            "metadata": {
                "has_terraform": False
            }
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        # Checkov should not run (no IaC), but Gitleaks should
        assert "checkov-iac" not in data["analyzers_scheduled"]
        assert "gitleaks-secrets" in data["analyzers_scheduled"]
    
    def test_analyze_with_analyzer_tags_filter(self, client, test_tenant_id):
        """Test filtering analyzers by tags."""
        request_data = {
            "tenant_id": test_tenant_id,
            "observable_type": "aws_account",
            "observable_value": "123456789012",
            "analyzer_tags": ["cspm"]
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        # Only CSPM-tagged analyzers should be scheduled
        assert "prowler-aws-cspm" in data["analyzers_scheduled"]
    
    def test_analyze_with_specific_analyzers(self, client, test_tenant_id):
        """Test specifying exact analyzers to run."""
        request_data = {
            "tenant_id": test_tenant_id,
            "observable_type": "git_repository",
            "observable_value": "https://github.com/org/repo",
            "analyzer_names": ["gitleaks-secrets"]
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["analyzers_scheduled"] == ["gitleaks-secrets"]
    
    def test_analyze_unsupported_observable_type(self, client, test_tenant_id):
        """Test analyzing unsupported observable type."""
        request_data = {
            "tenant_id": test_tenant_id,
            "observable_type": "unsupported_type",
            "observable_value": "test-value"
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        
        assert response.status_code == 404
        assert "No analyzers found" in response.json()["detail"]
    
    def test_get_job_status(self, client, test_tenant_id):
        """Test getting job status."""
        # First create a job
        request_data = {
            "tenant_id": test_tenant_id,
            "observable_type": "web_application",
            "observable_value": "https://example.com"
        }
        
        analyze_response = client.post("/api/v1/analyze", json=request_data)
        assert analyze_response.status_code == 200
        job_id = analyze_response.json()["job_id"]
        
        # Then get job status
        response = client.get(f"/api/v1/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert data["tenant_id"] == test_tenant_id
        assert "status" in data
    
    def test_get_nonexistent_job(self, client):
        """Test getting status of non-existent job."""
        fake_job_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/jobs/{fake_job_id}")
        
        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]


class TestValidation:
    """Test request validation."""
    
    def test_analyze_missing_tenant_id(self, client):
        """Test analyze request missing tenant_id."""
        request_data = {
            "observable_type": "web_application",
            "observable_value": "https://example.com"
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_analyze_missing_observable_type(self, client, test_tenant_id):
        """Test analyze request missing observable_type."""
        request_data = {
            "tenant_id": test_tenant_id,
            "observable_value": "https://example.com"
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        assert response.status_code == 422
    
    def test_analyze_missing_observable_value(self, client, test_tenant_id):
        """Test analyze request missing observable_value."""
        request_data = {
            "tenant_id": test_tenant_id,
            "observable_type": "web_application"
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

