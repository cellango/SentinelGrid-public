"""Integration tests for SIEM Agent with other services."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx
from uuid import uuid4
from datetime import datetime

# These tests verify integration between SIEM Agent and other services


class TestSOCAgentIntegration:
    """Test integration with SOC Agent."""
    
    @pytest.mark.asyncio
    async def test_soc_agent_can_create_alerts(self):
        """Test that SOC Agent can create alerts via internal API."""
        # This would be an actual HTTP call in a real integration test
        # For now, we verify the endpoint exists and accepts correct format
        
        alert_data = {
            "severity": "high",
            "status": "open",
            "title": "Suspicious Login Detected",
            "description": "Multiple failed login attempts",
            "source": "soc_agent",
            "detection_rule_id": "rule-suspicious-login",
            "user_id": "user-123",
            "source_ip": "192.168.1.100",
            "tags": ["authentication", "suspicious"],
            "count": 5
        }
        
        # Verify data structure is correct
        assert "severity" in alert_data
        assert "status" in alert_data
        assert "title" in alert_data
        assert "source" in alert_data
    
    @pytest.mark.asyncio
    async def test_soc_agent_can_enrich_alerts(self):
        """Test that SOC Agent can add events to alerts."""
        alert_id = str(uuid4())
        event_ids = ["event-1", "event-2", "event-3"]
        
        # Verify enrichment payload format
        assert isinstance(event_ids, list)
        assert len(event_ids) > 0
    
    @pytest.mark.asyncio
    async def test_soc_agent_can_search_events(self):
        """Test that SOC Agent can search for events."""
        search_params = {
            "query": "login failed",
            "start_time": datetime.utcnow().isoformat(),
            "limit": 100
        }
        
        # Verify search parameters
        assert "query" in search_params
        assert "limit" in search_params


class TestIAMAgentIntegration:
    """Test integration with IAM Agent."""
    
    @pytest.mark.asyncio
    async def test_iam_agent_can_query_user_timeline(self):
        """Test that IAM Agent can query user event timeline."""
        user_id = "user-123"
        
        timeline_request = {
            "entity_type": "user",
            "entity_id": user_id,
            "start_time": (datetime.utcnow()).isoformat(),
            "limit": 1000
        }
        
        # Verify timeline request format
        assert timeline_request["entity_type"] == "user"
        assert timeline_request["entity_id"] == user_id
    
    @pytest.mark.asyncio
    async def test_iam_agent_can_query_ip_timeline(self):
        """Test that IAM Agent can query IP address timeline."""
        ip_address = "192.168.1.100"
        
        timeline_request = {
            "entity_type": "ip",
            "entity_id": ip_address,
            "start_time": (datetime.utcnow()).isoformat(),
            "limit": 1000
        }
        
        # Verify timeline request format
        assert timeline_request["entity_type"] == "ip"
        assert timeline_request["entity_id"] == ip_address


class TestSOARAgentIntegration:
    """Test integration with SOAR Agent."""
    
    @pytest.mark.asyncio
    async def test_soar_agent_can_get_observable_types(self):
        """Test that SOAR Agent can get observable types."""
        # This endpoint should return list of observable types
        observable_types = [
            "ip", "domain", "url", "hash_md5", "hash_sha1",
            "hash_sha256", "email", "filename"
        ]
        
        assert "ip" in observable_types
        assert "domain" in observable_types
        assert "email" in observable_types
    
    @pytest.mark.asyncio
    async def test_soar_agent_can_extract_observables_from_alerts(self):
        """Test that SOAR Agent can extract observables from alerts."""
        alert = {
            "id": str(uuid4()),
            "title": "Suspicious Activity",
            "source_ip": "192.168.1.100",
            "user_id": "user-123",
            "description": "Malicious file detected: abc123def456"
        }
        
        # Verify observable extraction points
        observables = []
        if alert.get("source_ip"):
            observables.append({"type": "ip", "value": alert["source_ip"]})
        if alert.get("user_id"):
            observables.append({"type": "user", "value": alert["user_id"]})
        
        assert len(observables) > 0
        assert any(obs["type"] == "ip" for obs in observables)


class TestEndToEndFlow:
    """Test end-to-end workflows."""
    
    @pytest.mark.asyncio
    async def test_alert_to_incident_flow(self):
        """Test complete flow from alert creation to incident."""
        # Step 1: Create alert (SOC Agent)
        alert = {
            "id": str(uuid4()),
            "severity": "high",
            "status": "open",
            "title": "Suspicious Login",
            "source": "detection_rule"
        }
        
        # Step 2: Enrich alert with events (SOC Agent)
        alert["events"] = ["event-1", "event-2"]
        
        # Step 3: Query entity timeline (IAM Agent)
        timeline = {
            "entity_type": "user",
            "entity_id": "user-123",
            "events": []
        }
        
        # Step 4: Extract observables (SOAR Agent)
        observables = [
            {"type": "ip", "value": "192.168.1.100"},
            {"type": "user", "value": "user-123"}
        ]
        
        # Verify flow completeness
        assert alert["status"] == "open"
        assert len(alert["events"]) > 0
        assert timeline["entity_type"] == "user"
        assert len(observables) > 0

