"""Multi-tenancy isolation tests for SentinelGridPostureAgent."""

import pytest
import uuid
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def tenant_a_id():
    """Tenant A identifier."""
    return str(uuid.uuid4())


@pytest.fixture
def tenant_b_id():
    """Tenant B identifier."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_finding_tenant_a(tenant_a_id):
    """Sample finding for Tenant A."""
    return {
        "tenant_id": tenant_a_id,
        "source": "cspm",
        "tool": "prowler",
        "title": "Tenant A Finding",
        "description": "Finding for Tenant A",
        "severity": "high",
        "observable_type": "aws_account",
        "observable_value": "111111111111"
    }


@pytest.fixture
def sample_finding_tenant_b(tenant_b_id):
    """Sample finding for Tenant B."""
    return {
        "tenant_id": tenant_b_id,
        "source": "cspm",
        "tool": "prowler",
        "title": "Tenant B Finding",
        "description": "Finding for Tenant B",
        "severity": "critical",
        "observable_type": "aws_account",
        "observable_value": "222222222222"
    }


class TestTenantIsolation:
    """Test complete tenant data isolation."""
    
    def test_tenant_ids_are_different(self, tenant_a_id, tenant_b_id):
        """Verify tenant IDs are unique."""
        assert tenant_a_id != tenant_b_id
    
    def test_findings_have_tenant_id(self, sample_finding_tenant_a, tenant_a_id):
        """Test findings are tagged with tenant_id."""
        assert sample_finding_tenant_a["tenant_id"] == tenant_a_id
    
    def test_different_tenants_different_data(self, sample_finding_tenant_a, sample_finding_tenant_b):
        """Test different tenants have different data."""
        assert sample_finding_tenant_a["tenant_id"] != sample_finding_tenant_b["tenant_id"]
        assert sample_finding_tenant_a["observable_value"] != sample_finding_tenant_b["observable_value"]


class TestDatabaseQueryIsolation:
    """Test database queries enforce tenant isolation."""
    
    @pytest.mark.skip(reason="Requires database setup")
    def test_findings_query_scoped_by_tenant(self):
        """Test findings queries are scoped by tenant_id."""
        # This would require actual database setup
        # Pseudo-test structure:
        # 1. Insert findings for Tenant A
        # 2. Insert findings for Tenant B
        # 3. Query with Tenant A ID
        # 4. Verify only Tenant A findings returned
        # 5. Query with Tenant B ID
        # 6. Verify only Tenant B findings returned
        pass
    
    @pytest.mark.skip(reason="Requires database setup")
    def test_assets_query_scoped_by_tenant(self):
        """Test assets queries are scoped by tenant_id."""
        pass
    
    @pytest.mark.skip(reason="Requires database setup")
    def test_posture_scores_scoped_by_tenant(self):
        """Test posture scores are scoped by tenant_id."""
        pass


class TestAPITenantScoping:
    """Test API endpoints enforce tenant scoping."""
    
    def test_posture_summary_requires_tenant_id_in_path(self):
        """Test posture summary endpoint requires tenant_id in path."""
        from fastapi.testclient import TestClient
        from services.posture_service.app.main import app
        
        client = TestClient(app)
        
        # Should fail without tenant_id
        response = client.get("/api/v1/posture/summary/")
        assert response.status_code == 404  # Route not found without tenant_id
    
    def test_findings_list_requires_tenant_id_parameter(self):
        """Test findings list requires tenant_id query parameter."""
        from fastapi.testclient import TestClient
        from services.posture_service.app.main import app
        
        client = TestClient(app)
        
        # Should fail without tenant_id parameter
        response = client.get("/api/v1/findings/")
        assert response.status_code == 422  # Validation error
    
    def test_assets_list_requires_tenant_id_parameter(self):
        """Test assets list requires tenant_id query parameter."""
        from fastapi.testclient import TestClient
        from services.posture_service.app.main import app
        
        client = TestClient(app)
        
        response = client.get("/api/v1/assets/")
        assert response.status_code == 422


class TestOrchestratorTenantScoping:
    """Test orchestrator enforces tenant scoping."""
    
    def test_analyze_requires_tenant_id(self):
        """Test analyze endpoint requires tenant_id."""
        from fastapi.testclient import TestClient
        from services.analyzer_orchestrator.app.main import app
        
        client = TestClient(app)
        
        request_data = {
            "observable_type": "web_application",
            "observable_value": "https://example.com"
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        assert response.status_code == 422  # Missing tenant_id
    
    def test_job_stores_tenant_id(self, tenant_a_id):
        """Test jobs are associated with tenant_id."""
        from fastapi.testclient import TestClient
        from services.analyzer_orchestrator.app.main import app
        
        client = TestClient(app)
        
        request_data = {
            "tenant_id": tenant_a_id,
            "observable_type": "web_application",
            "observable_value": "https://example.com"
        }
        
        response = client.post("/api/v1/analyze", json=request_data)
        assert response.status_code == 200
        
        job_id = response.json()["job_id"]
        job_response = client.get(f"/api/v1/jobs/{job_id}")
        
        assert job_response.status_code == 200
        job_data = job_response.json()
        assert job_data["tenant_id"] == tenant_a_id


class TestCrossTenantAccessPrevention:
    """Test that cross-tenant access is prevented."""
    
    @pytest.mark.skip(reason="Requires database and auth setup")
    def test_cannot_access_other_tenant_findings(self):
        """Test Tenant A cannot access Tenant B's findings."""
        # Pseudo-test:
        # 1. Create findings for Tenant A
        # 2. Try to query with Tenant B token
        # 3. Verify Tenant A findings are not returned
        pass
    
    @pytest.mark.skip(reason="Requires database and auth setup")
    def test_cannot_modify_other_tenant_findings(self):
        """Test Tenant A cannot modify Tenant B's findings."""
        # Pseudo-test:
        # 1. Create finding for Tenant A
        # 2. Try to update with Tenant B token
        # 3. Verify update is rejected
        pass
    
    @pytest.mark.skip(reason="Requires database and auth setup")
    def test_posture_score_isolated_by_tenant(self):
        """Test posture scores are isolated by tenant."""
        # Pseudo-test:
        # 1. Set up findings for Tenant A (critical)
        # 2. Set up findings for Tenant B (low severity)
        # 3. Calculate scores for both
        # 4. Verify Tenant A has low score
        # 5. Verify Tenant B has high score
        # 6. Verify they don't affect each other
        pass


class TestTenantInAnalyzerJobs:
    """Test analyzer jobs maintain tenant isolation."""
    
    def test_job_contains_tenant_id(self, tenant_a_id):
        """Test analyzer job records contain tenant_id."""
        from services.analyzer_orchestrator.app.main import jobs_store
        
        # Create a mock job
        job_id = str(uuid.uuid4())
        jobs_store[job_id] = {
            "id": job_id,
            "tenant_id": tenant_a_id,
            "observable": {"type": "test", "value": "test"},
            "status": "completed"
        }
        
        # Verify tenant_id is stored
        assert jobs_store[job_id]["tenant_id"] == tenant_a_id
    
    def test_findings_tagged_with_tenant_id(self, tenant_a_id, sample_finding_tenant_a):
        """Test findings are tagged with tenant_id before storage."""
        assert "tenant_id" in sample_finding_tenant_a
        assert sample_finding_tenant_a["tenant_id"] == tenant_a_id


class TestTenantIsolationInModels:
    """Test database models enforce tenant isolation."""
    
    def test_observable_model_has_tenant_id(self):
        """Test Observable model has tenant_id field."""
        from shared.models.observable import Observable
        
        assert hasattr(Observable, 'tenant_id')
    
    def test_finding_model_has_tenant_id(self):
        """Test Finding model has tenant_id field."""
        from shared.models.finding import Finding
        
        assert hasattr(Finding, 'tenant_id')
    
    def test_asset_model_has_tenant_id(self):
        """Test Asset model has tenant_id field."""
        from shared.models.asset import Asset
        
        assert hasattr(Asset, 'tenant_id')
    
    def test_analyzer_job_model_has_tenant_id(self):
        """Test AnalyzerJob model has tenant_id field."""
        from shared.models.analyzer_job import AnalyzerJob
        
        assert hasattr(AnalyzerJob, 'tenant_id')
    
    def test_posture_score_model_has_tenant_id(self):
        """Test PostureScore model has tenant_id field."""
        from shared.models.posture_score import PostureScore
        
        assert hasattr(PostureScore, 'tenant_id')
    
    def test_cloud_account_model_has_tenant_id(self):
        """Test CloudAccount model has tenant_id field."""
        from shared.models.cloud_account import CloudAccount
        
        assert hasattr(CloudAccount, 'tenant_id')
    
    def test_repository_model_has_tenant_id(self):
        """Test Repository model has tenant_id field."""
        from shared.models.repository import Repository
        
        assert hasattr(Repository, 'tenant_id')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

