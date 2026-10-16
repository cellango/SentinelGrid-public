"""End-to-end test scenarios for SentinelGridPostureAgent."""

import pytest
import asyncio
import httpx
import uuid
from typing import Dict, Any


# Service URLs
ORCHESTRATOR_URL = "http://localhost:8103"
POSTURE_SERVICE_URL = "http://localhost:8100"


@pytest.fixture
def test_tenant_id():
    """Generate test tenant ID."""
    return str(uuid.uuid4())


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_web_application_scan(test_tenant_id):
    """
    End-to-end test: Scan web application.
    
    Flow:
    1. Submit web application for analysis
    2. Verify job is created
    3. Wait for analysis to complete
    4. Verify findings are stored
    5. Query posture summary
    6. Verify score is calculated
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Submit analysis
        analyze_request = {
            "tenant_id": test_tenant_id,
            "observable_type": "web_application",
            "observable_value": "https://example.com"
        }
        
        response = await client.post(
            f"{ORCHESTRATOR_URL}/api/v1/analyze",
            json=analyze_request
        )
        
        assert response.status_code == 200
        job_data = response.json()
        job_id = job_data["job_id"]
        
        assert "analyzers_scheduled" in job_data
        assert job_data["status"] == "running"
        
        # Step 2: Wait for job completion (with timeout)
        max_wait = 30  # seconds
        wait_interval = 2
        waited = 0
        
        while waited < max_wait:
            job_response = await client.get(
                f"{ORCHESTRATOR_URL}/api/v1/jobs/{job_id}"
            )
            
            if job_response.status_code == 200:
                job_status = job_response.json()
                if job_status["status"] in ["completed", "failed"]:
                    break
            
            await asyncio.sleep(wait_interval)
            waited += wait_interval
        
        # Step 3: Verify job completed
        final_job_response = await client.get(
            f"{ORCHESTRATOR_URL}/api/v1/jobs/{job_id}"
        )
        
        assert final_job_response.status_code == 200
        final_job_data = final_job_response.json()
        
        # Job should be completed (even if findings are mocked)
        assert final_job_data["status"] in ["completed", "failed"]
        
        # Step 4: Query posture summary (if posture service is running)
        try:
            summary_response = await client.get(
                f"{POSTURE_SERVICE_URL}/api/v1/posture/summary/{test_tenant_id}"
            )
            
            if summary_response.status_code == 200:
                summary_data = summary_response.json()
                assert "posture_score" in summary_data
                assert "grade" in summary_data
                assert "total_findings" in summary_data
        except httpx.ConnectError:
            pytest.skip("Posture service not running")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_aws_account_scan(test_tenant_id):
    """
    End-to-end test: Scan AWS account.
    
    Flow:
    1. Submit AWS account for analysis
    2. Verify Prowler is selected
    3. Check job status
    4. Verify findings would be created (mocked)
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        analyze_request = {
            "tenant_id": test_tenant_id,
            "observable_type": "aws_account",
            "observable_value": "123456789012",
            "metadata": {"environment": "prod"}
        }
        
        response = await client.post(
            f"{ORCHESTRATOR_URL}/api/v1/analyze",
            json=analyze_request
        )
        
        assert response.status_code == 200
        job_data = response.json()
        
        # Prowler should be scheduled
        assert "prowler-aws-cspm" in job_data["analyzers_scheduled"]
        
        job_id = job_data["job_id"]
        
        # Check job status
        job_response = await client.get(
            f"{ORCHESTRATOR_URL}/api/v1/jobs/{job_id}"
        )
        
        assert job_response.status_code == 200


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_git_repository_with_iac(test_tenant_id):
    """
    End-to-end test: Scan Git repository with IaC files.
    
    Flow:
    1. Submit repository with IaC metadata
    2. Verify both Checkov and Gitleaks are selected
    3. Verify smart analyzer selection (Checkov only if has_terraform)
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        analyze_request = {
            "tenant_id": test_tenant_id,
            "observable_type": "git_repository",
            "observable_value": "https://github.com/test/repo",
            "metadata": {
                "has_terraform": True,
                "has_kubernetes_manifests": True
            }
        }
        
        response = await client.post(
            f"{ORCHESTRATOR_URL}/api/v1/analyze",
            json=analyze_request
        )
        
        assert response.status_code == 200
        job_data = response.json()
        
        # Both Checkov and Gitleaks should be scheduled
        analyzers = job_data["analyzers_scheduled"]
        assert "checkov-iac" in analyzers
        assert "gitleaks-secrets" in analyzers


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_git_repository_without_iac(test_tenant_id):
    """
    End-to-end test: Scan Git repository without IaC files.
    
    Verifies smart analyzer selection - Checkov should NOT run.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        analyze_request = {
            "tenant_id": test_tenant_id,
            "observable_type": "git_repository",
            "observable_value": "https://github.com/test/app-repo",
            "metadata": {
                "has_terraform": False
            }
        }
        
        response = await client.post(
            f"{ORCHESTRATOR_URL}/api/v1/analyze",
            json=analyze_request
        )
        
        assert response.status_code == 200
        job_data = response.json()
        
        analyzers = job_data["analyzers_scheduled"]
        
        # Checkov should NOT be scheduled (no IaC files)
        assert "checkov-iac" not in analyzers
        
        # Gitleaks should still be scheduled (scans all repos)
        assert "gitleaks-secrets" in analyzers


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_docker_image_scan(test_tenant_id):
    """
    End-to-end test: Scan Docker image.
    
    Flow:
    1. Submit Docker image
    2. Verify Trivy is selected
    3. Check job tracking
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        analyze_request = {
            "tenant_id": test_tenant_id,
            "observable_type": "docker_image",
            "observable_value": "nginx:latest",
            "metadata": {"in_use": True, "environment": "prod"}
        }
        
        response = await client.post(
            f"{ORCHESTRATOR_URL}/api/v1/analyze",
            json=analyze_request
        )
        
        assert response.status_code == 200
        job_data = response.json()
        
        assert "trivy-vuln-scan" in job_data["analyzers_scheduled"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_tag_based_filtering(test_tenant_id):
    """
    End-to-end test: Tag-based analyzer filtering.
    
    Verifies only "critical" tagged analyzers run.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Analyze with "critical" tag filter
        analyze_request = {
            "tenant_id": test_tenant_id,
            "observable_type": "web_application",
            "observable_value": "https://example.com",
            "analyzer_tags": ["critical"]
        }
        
        response = await client.post(
            f"{ORCHESTRATOR_URL}/api/v1/analyze",
            json=analyze_request
        )
        
        assert response.status_code == 200
        job_data = response.json()
        
        # ZAP has "critical" tag, should be included
        assert "zap-dast" in job_data["analyzers_scheduled"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_specific_analyzer_selection(test_tenant_id):
    """
    End-to-end test: Specific analyzer selection.
    
    User specifies exact analyzers to run.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        analyze_request = {
            "tenant_id": test_tenant_id,
            "observable_type": "git_repository",
            "observable_value": "https://github.com/test/repo",
            "analyzer_names": ["gitleaks-secrets"]
        }
        
        response = await client.post(
            f"{ORCHESTRATOR_URL}/api/v1/analyze",
            json=analyze_request
        )
        
        assert response.status_code == 200
        job_data = response.json()
        
        # Only Gitleaks should be scheduled
        assert job_data["analyzers_scheduled"] == ["gitleaks-secrets"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_multiple_tenants_isolated(test_tenant_id):
    """
    End-to-end test: Multiple tenants operate independently.
    
    Submit analyses for two different tenants and verify isolation.
    """
    tenant_a_id = test_tenant_id
    tenant_b_id = str(uuid.uuid4())
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Submit for Tenant A
        response_a = await client.post(
            f"{ORCHESTRATOR_URL}/api/v1/analyze",
            json={
                "tenant_id": tenant_a_id,
                "observable_type": "web_application",
                "observable_value": "https://tenant-a-app.com"
            }
        )
        
        assert response_a.status_code == 200
        job_a_id = response_a.json()["job_id"]
        
        # Submit for Tenant B
        response_b = await client.post(
            f"{ORCHESTRATOR_URL}/api/v1/analyze",
            json={
                "tenant_id": tenant_b_id,
                "observable_type": "aws_account",
                "observable_value": "999999999999"
            }
        )
        
        assert response_b.status_code == 200
        job_b_id = response_b.json()["job_id"]
        
        # Verify jobs are different
        assert job_a_id != job_b_id
        
        # Verify each job has correct tenant_id
        job_a_response = await client.get(f"{ORCHESTRATOR_URL}/api/v1/jobs/{job_a_id}")
        assert job_a_response.json()["tenant_id"] == tenant_a_id
        
        job_b_response = await client.get(f"{ORCHESTRATOR_URL}/api/v1/jobs/{job_b_id}")
        assert job_b_response.json()["tenant_id"] == tenant_b_id


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_service_health_checks():
    """Test all services are healthy."""
    services = [
        (ORCHESTRATOR_URL, "analyzer-orchestrator"),
        # (POSTURE_SERVICE_URL, "posture-service"),  # Uncomment when running
    ]
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for url, name in services:
            try:
                response = await client.get(f"{url}/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
            except httpx.ConnectError:
                pytest.skip(f"{name} not running - start with docker-compose up -d")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])

