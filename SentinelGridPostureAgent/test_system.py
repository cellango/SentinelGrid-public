#!/usr/bin/env python3
"""
End-to-end test for SentinelGrid Posture Agent.

Tests the complete observable-analyzer workflow.
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any

# Configuration
ANALYZER_ORCHESTRATOR_URL = "http://localhost:8103"
POSTURE_SERVICE_URL = "http://localhost:8100"
TEST_TENANT_ID = "test-tenant-123"


async def test_analyzer_orchestrator():
    """Test analyzer orchestrator service."""
    print("\n" + "="*60)
    print("TEST 1: Analyzer Orchestrator")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        # Test 1: Health check
        print("\n1. Health check...")
        response = await client.get(f"{ANALYZER_ORCHESTRATOR_URL}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        # Test 2: List analyzers
        print("\n2. List available analyzers...")
        response = await client.get(f"{ANALYZER_ORCHESTRATOR_URL}/api/v1/analyzers")
        data = response.json()
        print(f"   Total analyzers: {len(data.get('analyzers', []))}")
        for analyzer in data.get('analyzers', []):
            print(f"   - {analyzer['name']}: {analyzer['description']}")
            print(f"     Types: {analyzer['supported_types']}")
            print(f"     Tags: {analyzer['tags']}")
        
        # Test 3: List observable types
        print("\n3. List supported observable types...")
        response = await client.get(f"{ANALYZER_ORCHESTRATOR_URL}/api/v1/observable-types")
        data = response.json()
        print(f"   Supported types: {data.get('observable_types', [])}")
        
        # Test 4: Analyze a web application
        print("\n4. Analyze web application...")
        analyze_request = {
            "tenant_id": TEST_TENANT_ID,
            "observable_type": "web_application",
            "observable_value": "https://example.com",
            "analyzer_tags": ["dast"]
        }
        response = await client.post(
            f"{ANALYZER_ORCHESTRATOR_URL}/api/v1/analyze",
            json=analyze_request
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            job_id = data.get("job_id")
            print(f"   Job ID: {job_id}")
            print(f"   Analyzers scheduled: {data.get('analyzers_scheduled')}")
            
            # Wait a bit and check job status
            print("\n5. Check job status...")
            await asyncio.sleep(2)
            response = await client.get(f"{ANALYZER_ORCHESTRATOR_URL}/api/v1/jobs/{job_id}")
            if response.status_code == 200:
                job_data = response.json()
                print(f"   Job status: {job_data.get('status')}")
                print(f"   Findings count: {job_data.get('findings_count', 0)}")
                print(f"   Completed analyzers: {job_data.get('completed_analyzers', [])}")
        else:
            print(f"   Error: {response.text}")
        
        # Test 5: Analyze AWS account
        print("\n6. Analyze AWS account...")
        analyze_request = {
            "tenant_id": TEST_TENANT_ID,
            "observable_type": "aws_account",
            "observable_value": "123456789012"
        }
        response = await client.post(
            f"{ANALYZER_ORCHESTRATOR_URL}/api/v1/analyze",
            json=analyze_request
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Job ID: {data.get('job_id')}")
            print(f"   Analyzers scheduled: {data.get('analyzers_scheduled')}")
        
        # Test 6: Analyze Git repository
        print("\n7. Analyze Git repository...")
        analyze_request = {
            "tenant_id": TEST_TENANT_ID,
            "observable_type": "git_repository",
            "observable_value": "https://github.com/example/repo",
            "metadata": {
                "has_terraform": True,
                "has_kubernetes_manifests": True
            }
        }
        response = await client.post(
            f"{ANALYZER_ORCHESTRATOR_URL}/api/v1/analyze",
            json=analyze_request
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Job ID: {data.get('job_id')}")
            print(f"   Analyzers scheduled: {data.get('analyzers_scheduled')}")
            print(f"   Expected: Checkov and Gitleaks (repo has IaC files)")


async def test_posture_service():
    """Test posture service endpoints."""
    print("\n" + "="*60)
    print("TEST 2: Posture Service")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        # Test 1: Health check
        print("\n1. Health check...")
        try:
            response = await client.get(f"{POSTURE_SERVICE_URL}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except httpx.ConnectError:
            print(f"   ⚠️  Posture service not running at {POSTURE_SERVICE_URL}")
            print(f"   Start with: docker-compose up -d posture-service")
            return
        
        # Test 2: Get posture summary
        print("\n2. Get posture summary...")
        try:
            response = await client.get(
                f"{POSTURE_SERVICE_URL}/api/v1/posture/summary/{TEST_TENANT_ID}"
            )
            if response.status_code == 200:
                data = response.json()
                print(f"   Posture score: {data.get('posture_score')}")
                print(f"   Grade: {data.get('grade')}")
                print(f"   Total findings: {data.get('total_findings')}")
                print(f"   Critical: {data.get('critical_findings')}")
                print(f"   High: {data.get('high_findings')}")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Error: {str(e)}")
        
        # Test 3: List findings
        print("\n3. List findings...")
        try:
            response = await client.get(
                f"{POSTURE_SERVICE_URL}/api/v1/findings/",
                params={"tenant_id": TEST_TENANT_ID, "limit": 10}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"   Total findings: {data.get('total_count', 0)}")
                for finding in data.get('findings', [])[:3]:
                    print(f"   - {finding['title']} ({finding['severity']})")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Error: {str(e)}")
        
        # Test 4: List assets
        print("\n4. List assets...")
        try:
            response = await client.get(
                f"{POSTURE_SERVICE_URL}/api/v1/assets/",
                params={"tenant_id": TEST_TENANT_ID, "limit": 10}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"   Total assets: {data.get('total_count', 0)}")
                for asset in data.get('assets', [])[:3]:
                    print(f"   - {asset['name']} ({asset['asset_type']})")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Error: {str(e)}")


async def main():
    """Run all tests."""
    print("\n🚀 SentinelGrid Posture Agent - End-to-End Test")
    print("="*60)
    
    # Test analyzer orchestrator
    await test_analyzer_orchestrator()
    
    # Test posture service
    await test_posture_service()
    
    print("\n" + "="*60)
    print("✅ Tests Complete")
    print("="*60)
    print("\nNext Steps:")
    print("1. Implement tool wrappers to actually run Prowler, ZAP, etc.")
    print("2. Start posture-service: docker-compose up -d posture-service")
    print("3. Run database migrations: cd database && alembic upgrade head")
    print("4. Test with real cloud accounts")


if __name__ == "__main__":
    asyncio.run(main())

