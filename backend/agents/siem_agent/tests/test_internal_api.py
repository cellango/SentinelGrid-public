"""Tests for internal API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from uuid import UUID, uuid4
from datetime import datetime

from app.main import app
from app.models.alert import AlertCreate, Alert

client = TestClient(app)

# Test tenant ID
TEST_TENANT_ID = str(uuid4())
INTERNAL_TOKEN = "internal-service-token-change-in-production"


@pytest.fixture
def mock_opensearch():
    """Mock OpenSearch client."""
    with patch("app.core.opensearch.OpenSearchClient") as mock:
        yield mock


@pytest.fixture
def auth_headers():
    """Authorization headers for internal API."""
    return {
        "Authorization": f"Bearer {INTERNAL_TOKEN}",
        "X-Tenant-ID": TEST_TENANT_ID
    }


class TestInternalAlertCreation:
    """Test internal alert creation endpoint."""
    
    def test_create_alert_success(self, mock_opensearch, auth_headers):
        """Test successful alert creation via internal API."""
        # Mock OpenSearch client
        mock_client = Mock()
        mock_opensearch.return_value.client = mock_client
        mock_opensearch.return_value.get_index_name.return_value = f"sg-{TEST_TENANT_ID}-alerts-2025.01.28"
        mock_client.indices.exists.return_value = True
        mock_client.index.return_value = {"result": "created"}
        mock_client.indices.refresh.return_value = {}
        
        alert_data = {
            "severity": "high",
            "status": "open",
            "title": "Test Alert",
            "description": "Test alert description",
            "source": "detection_rule",
            "detection_rule_id": "rule-123",
            "user_id": "user-123",
            "source_ip": "192.168.1.100",
            "tags": ["test"],
            "count": 1
        }
        
        response = client.post(
            "/internal/siem/alerts/create",
            json=alert_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Alert"
        assert data["severity"] == "high"
        assert data["tenant_id"] == TEST_TENANT_ID
    
    def test_create_alert_missing_token(self):
        """Test alert creation fails without auth token."""
        alert_data = {
            "severity": "high",
            "status": "open",
            "title": "Test Alert",
            "description": "Test alert description",
            "source": "detection_rule"
        }
        
        response = client.post(
            "/internal/siem/alerts/create",
            json=alert_data,
            headers={"X-Tenant-ID": TEST_TENANT_ID}
        )
        
        assert response.status_code == 401
    
    def test_create_alert_invalid_token(self, auth_headers):
        """Test alert creation fails with invalid token."""
        headers = auth_headers.copy()
        headers["Authorization"] = "Bearer invalid-token"
        
        alert_data = {
            "severity": "high",
            "status": "open",
            "title": "Test Alert",
            "description": "Test alert description",
            "source": "detection_rule"
        }
        
        response = client.post(
            "/internal/siem/alerts/create",
            json=alert_data,
            headers=headers
        )
        
        assert response.status_code == 401
    
    def test_create_alert_missing_tenant_id(self):
        """Test alert creation fails without tenant ID."""
        alert_data = {
            "severity": "high",
            "status": "open",
            "title": "Test Alert",
            "description": "Test alert description",
            "source": "detection_rule"
        }
        
        response = client.post(
            "/internal/siem/alerts/create",
            json=alert_data,
            headers={"Authorization": f"Bearer {INTERNAL_TOKEN}"}
        )
        
        assert response.status_code == 422  # Validation error


class TestInternalAlertRetrieval:
    """Test internal alert retrieval endpoint."""
    
    def test_get_alert_success(self, mock_opensearch, auth_headers):
        """Test successful alert retrieval via internal API."""
        alert_id = str(uuid4())
        mock_client = Mock()
        mock_opensearch.return_value.client = mock_client
        mock_opensearch.return_value.search_indices.return_value = [f"sg-{TEST_TENANT_ID}-alerts-2025.01.28"]
        mock_client.get.return_value = {
            "_id": alert_id,
            "_source": {
                "id": alert_id,
                "tenant_id": TEST_TENANT_ID,
                "severity": "high",
                "status": "open",
                "title": "Test Alert",
                "description": "Test description",
                "timestamp": datetime.utcnow().isoformat(),
                "source": "detection_rule",
                "tags": [],
                "events": []
            },
            "found": True
        }
        
        response = client.get(
            f"/internal/siem/alerts/{alert_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == alert_id
        assert data["tenant_id"] == TEST_TENANT_ID
    
    def test_get_alert_not_found(self, mock_opensearch, auth_headers):
        """Test alert retrieval returns 404 for non-existent alert."""
        alert_id = str(uuid4())
        mock_client = Mock()
        mock_opensearch.return_value.client = mock_client
        mock_opensearch.return_value.search_indices.return_value = [f"sg-{TEST_TENANT_ID}-alerts-2025.01.28"]
        mock_client.get.side_effect = Exception("Not found")
        
        with patch("app.services.alert_service.AlertService.get_alert", return_value=None):
            response = client.get(
                f"/internal/siem/alerts/{alert_id}",
                headers=auth_headers
            )
            
            assert response.status_code == 404


class TestInternalAlertEnrichment:
    """Test internal alert enrichment endpoint."""
    
    def test_add_events_to_alert_success(self, mock_opensearch, auth_headers):
        """Test successful alert enrichment."""
        alert_id = str(uuid4())
        event_ids = ["event-1", "event-2", "event-3"]
        
        mock_client = Mock()
        mock_opensearch.return_value.client = mock_client
        mock_opensearch.return_value.search_indices.return_value = [f"sg-{TEST_TENANT_ID}-alerts-2025.01.28"]
        
        # Mock existing alert
        mock_alert = Alert(
            id=UUID(alert_id),
            tenant_id=UUID(TEST_TENANT_ID),
            severity="high",
            status="open",
            title="Test Alert",
            description="Test",
            timestamp=datetime.utcnow(),
            source="detection_rule",
            tags=[],
            events=[]
        )
        
        with patch("app.services.alert_service.AlertService.get_alert", return_value=mock_alert):
            mock_client.update.return_value = {"result": "updated"}
            mock_client.indices.refresh.return_value = {}
            
            response = client.post(
                f"/internal/siem/alerts/{alert_id}/events",
                json=event_ids,
                headers=auth_headers
            )
            
            assert response.status_code == 200


class TestInternalSearch:
    """Test internal search endpoints."""
    
    def test_search_events_success(self, mock_opensearch, auth_headers):
        """Test successful event search via internal API."""
        mock_client = Mock()
        mock_opensearch.return_value.client = mock_client
        mock_opensearch.return_value.search_indices.return_value = [f"sg-{TEST_TENANT_ID}-logs-2025.01.28"]
        
        mock_response = Mock()
        mock_response.hits.total.value = 5
        mock_response.hits = [Mock(to_dict=lambda: {
            "id": "event-1",
            "tenant_id": TEST_TENANT_ID,
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "authentication",
            "source": {}
        })]
        mock_response.timed_out = False
        
        with patch("app.services.search_service.SearchService.simple_search") as mock_search:
            mock_search.return_value = {
                "events": [],
                "total": 5,
                "took_ms": 10,
                "timed_out": False
            }
            
            response = client.get(
                "/internal/siem/search/events",
                params={"query": "login", "limit": 100},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "events" in data
            assert "total" in data

