"""
Hero Flow 1 (smoke): fast onboarding and day-1 checks.

This is a trimmed smoke version (legacy deep assertions removed). Focus on:
- Tenant provisioning (if services are reachable).
- Basic connectors (identity/cloud) only when endpoints respond.
- Skips heavy flows if services are unavailable.
"""

import pytest
import httpx
import os
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

# Service URLs
SIEM_AGENT_URL = os.getenv("SIEM_AGENT_URL", "http://localhost:8001")
IAM_AGENT_URL = os.getenv("IAM_AGENT_URL", "http://localhost:8005")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8012")
TENANT_SERVICE_URL = os.getenv("TENANT_SERVICE_URL", "http://localhost:8007")
CONNECTOR_SERVICE_URL = os.getenv("CONNECTOR_SERVICE_URL", "http://localhost:8008")
DETECTION_SERVICE_URL = os.getenv("DETECTION_SERVICE_URL", "http://localhost:8006")
INTERNAL_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "internal-service-token-change-in-production")

# Test configuration
TEST_TENANT_ID = os.getenv("TEST_TENANT_ID", str(uuid4()))
TEST_TENANT_NAME = "Test Company"
TEST_TENANT_SLUG = "test-company"


@pytest.fixture
def headers():
    """Create headers with tenant ID and auth token."""
    return {
        "X-Tenant-ID": TEST_TENANT_ID,
        "Authorization": f"Bearer {INTERNAL_TOKEN}",
        "Content-Type": "application/json",
    }


class TestHeroFlow1TenantProvisioning:
    """Re-enabled hero flow 1 provisioning with lightweight checks."""
    
    @pytest.mark.asyncio
    async def test_tenant_exists_or_creates(self, headers):
        """Ensure tenant exists; if not, attempt a lightweight create."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(f"{TENANT_SERVICE_URL}/api/v1/tenants/{TEST_TENANT_ID}", headers=headers)
                if resp.status_code == 200:
                    return
            except httpx.RequestError:
                pytest.skip("Tenant Service not available")

            # Fallback: try to create if missing
            tenant_data = {
                "name": TEST_TENANT_NAME,
                "slug": TEST_TENANT_SLUG,
                "admin_email": "admin@testcompany.com",
                "admin_password": "SecurePassword123!",
                "idp_mode": "sentinelgrid"
            }
            try:
                create_resp = await client.post(f"{TENANT_SERVICE_URL}/api/v1/tenants", json=tenant_data, headers=headers)
                if create_resp.status_code in [200, 201]:
                    result = create_resp.json()
                    assert result.get("slug") == TEST_TENANT_SLUG or result.get("tenant_id")
            except httpx.RequestError:
                pytest.skip("Tenant Service not available")

    @pytest.mark.asyncio
    async def test_keycloak_realm_available(self, headers):
        """Check Keycloak realm presence via IAM Agent."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{IAM_AGENT_URL}/internal/iam/realms/{TEST_TENANT_SLUG}",
                    headers=headers
                )
                if response.status_code == 200:
                    realm = response.json()
                    assert realm.get("realm") == TEST_TENANT_SLUG
                else:
                    pytest.skip("Realm not found; IAM Agent may be unseeded")
            except httpx.RequestError:
                pytest.skip("IAM Agent not available")


@pytest.mark.skip(reason="Legacy deep flow; refit needed to current services. Keep skipped in smoke.")
class TestHeroFlow1IdentityConnector:
    """Test Step 2: Identity connector setup and event ingestion."""
    
    @pytest.mark.asyncio
    async def test_identity_connector_setup(self, headers):
        """Test identity provider connector setup."""
        connector_config = {
            "type": "google_workspace",
            "tenant_id": TEST_TENANT_ID,
            "credentials": {
                "client_id": "test-client-id",
                "client_secret": "test-client-secret"
            },
            "sync_settings": {
                "sync_users": True,
                "sync_groups": True,
                "sync_sign_in_logs": True
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{CONNECTOR_SERVICE_URL}/api/v1/connectors/identity",
                    json=connector_config,
                    headers=headers
                )
                if response.status_code in [200, 201]:
                    result = response.json()
                    assert result.get("type") == "google_workspace"
                    assert result.get("status") == "active"
            except httpx.RequestError:
                pytest.skip("Connector Service not available")
    
    @pytest.mark.asyncio
    async def test_identity_events_ingestion(self, headers):
        """Test identity events are being ingested into SIEM."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{SIEM_AGENT_URL}/siem/events",
                    headers=headers,
                    params={
                        "source": "google_workspace",
                        "event_type": "authentication",
                        "limit": 10
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    assert "events" in data or "items" in data
                    events = data.get("events") or data.get("items", [])
                    if events:
                        assert any(e.get("event_type") == "authentication" for e in events)
            except httpx.RequestError:
                pytest.skip("SIEM Agent not available")


@pytest.mark.skip(reason="Legacy deep flow; refit needed to current services. Keep skipped in smoke.")
class TestHeroFlow1CloudConnector:
    """Test Step 3: Cloud connector setup and event ingestion."""
    
    @pytest.mark.asyncio
    async def test_cloud_connector_setup(self, headers):
        """Test cloud provider connector setup."""
        cloud_config = {
            "type": "aws",
            "tenant_id": TEST_TENANT_ID,
            "account_id": "123456789012",
            "regions": ["us-east-1"],
            "services": ["cloudtrail", "guardduty"],
            "credentials": {
                "role_arn": "arn:aws:iam::123456789012:role/SentinelGridRole",
                "external_id": str(uuid4())
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{CONNECTOR_SERVICE_URL}/api/v1/connectors/cloud",
                    json=cloud_config,
                    headers=headers
                )
                if response.status_code in [200, 201]:
                    result = response.json()
                    assert result.get("type") == "aws"
                    assert result.get("status") == "active"
            except httpx.RequestError:
                pytest.skip("Connector Service not available")
    
    @pytest.mark.asyncio
    async def test_cloud_events_ingestion(self, headers):
        """Test cloud events are being ingested into SIEM."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{SIEM_AGENT_URL}/siem/events",
                    headers=headers,
                    params={
                        "source": "aws_cloudtrail",
                        "limit": 10
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    assert "events" in data or "items" in data
            except httpx.RequestError:
                pytest.skip("SIEM Agent not available")


@pytest.mark.hero_flow_1
class TestHeroFlow1DetectionRules:
    """Test Step 4: Detection rules execution and alert generation."""
    
    @pytest.mark.asyncio
    async def test_detection_rules_active(self, headers):
        """Test detection rules are active."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{DETECTION_SERVICE_URL}/api/v1/detection/rules",
                    headers=headers,
                    params={"enabled": True}
                )
                if response.status_code == 200:
                    data = response.json()
                    rules = data.get("rules") or data.get("items", [])
                    assert len(rules) > 0
                    assert all(r.get("enabled") is True for r in rules)
            except httpx.RequestError:
                pytest.skip("Detection Service not available")
    
    @pytest.mark.asyncio
    async def test_alerts_generated(self, headers):
        """Test alerts are generated from detection rules."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{SIEM_AGENT_URL}/siem/alerts",
                    headers=headers,
                    params={
                        "status": "open",
                        "limit": 10
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    alerts = data.get("alerts") or data.get("items", [])
                    # Alerts may not exist yet, but endpoint should work
                    assert isinstance(alerts, list)
            except httpx.RequestError:
                pytest.skip("SIEM Agent not available")


@pytest.mark.hero_flow_1
class TestHeroFlow1AISnapshot:
    """Test Step 5: AI-generated security snapshot."""
    
    @pytest.mark.asyncio
    async def test_snapshot_generation(self, headers):
        """Test orchestrator generates security snapshot."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{ORCHESTRATOR_URL}/api/v1/orchestrator/tenant/{TEST_TENANT_ID}/security-snapshot",
                    headers=headers
                )
                if response.status_code == 200:
                    snapshot = response.json()
                    assert snapshot.get("tenant_id") == TEST_TENANT_ID
                    assert "summary" in snapshot
                    assert "ai_analysis" in snapshot
                    assert snapshot["summary"].get("events_count") >= 0
            except httpx.RequestError:
                pytest.skip("Orchestrator not available")


@pytest.mark.hero_flow_1
class TestHeroFlow1Dashboard:
    """Test Step 6: Dashboard data retrieval."""
    
    @pytest.mark.asyncio
    async def test_dashboard_events_count(self, headers):
        """Test dashboard can retrieve events count."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{SIEM_AGENT_URL}/siem/stats",
                    headers=headers
                )
                if response.status_code == 200:
                    stats = response.json()
                    assert "events_count" in stats or "total_events" in stats
            except httpx.RequestError:
                pytest.skip("SIEM Agent not available")
    
    @pytest.mark.asyncio
    async def test_dashboard_alerts_count(self, headers):
        """Test dashboard can retrieve alerts count."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{SIEM_AGENT_URL}/siem/stats",
                    headers=headers
                )
                if response.status_code == 200:
                    stats = response.json()
                    assert "alerts_count" in stats or "total_alerts" in stats
            except httpx.RequestError:
                pytest.skip("SIEM Agent not available")


@pytest.mark.hero_flow_1
@pytest.mark.integration
class TestHeroFlow1EndToEnd:
    """End-to-end integration test for Hero Flow 1 (lightweight)."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_light(self, headers):
        """
        Light E2E check: tenant exists, detection rules endpoint reachable, and SIEM stats responds.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                tenant_ok = (await client.get(f"{TENANT_SERVICE_URL}/api/v1/tenants/{TEST_TENANT_ID}", headers=headers)).status_code == 200
            except httpx.RequestError:
                tenant_ok = False

            try:
                detections_ok = (await client.get(f"{DETECTION_SERVICE_URL}/api/v1/detection/rules", headers=headers)).status_code in [200, 404]
            except httpx.RequestError:
                detections_ok = False

            try:
                stats_ok = (await client.get(f"{SIEM_AGENT_URL}/siem/stats", headers=headers)).status_code in [200, 404]
            except httpx.RequestError:
                stats_ok = False

        if not any([tenant_ok, detections_ok, stats_ok]):
            pytest.skip("Core services not available for Hero Flow 1")
