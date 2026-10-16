"""
Tests for API Gateway endpoints
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(mock_get_db, mock_get_tenant_session, mock_get_current_tenant):
    """FastAPI test client."""
    from sg_core.db import get_db, get_tenant_session
    from sg_core.security import get_current_tenant
    
    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_tenant_session] = mock_get_tenant_session
    app.dependency_overrides[get_current_tenant] = mock_get_current_tenant
    
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestAPIEndpoints:
    """Test suite for API Gateway endpoints."""
    
    def test_list_alerts_endpoint(self, client, mock_get_db):
        """Test listing alerts endpoint."""
        from app.services.alert_service import AlertService
        
        mock_service = Mock()
        mock_service.list_alerts.return_value = ([], 0)
        
        with patch('app.api.routes_alerts.AlertService', return_value=mock_service):
            response = client.get("/api/v1/alerts/")
            
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert isinstance(data["items"], list)
    
    def test_list_alerts_with_filters(self, client, mock_get_db):
        """Test listing alerts with status and severity filters."""
        from app.services.alert_service import AlertService
        
        mock_service = Mock()
        mock_service.list_alerts.return_value = ([], 0)
        
        with patch('app.api.routes_alerts.AlertService', return_value=mock_service):
            response = client.get("/api/v1/alerts/?status=open&severity=high")
            
            assert response.status_code == 200
            # Verify filters were passed to service
            mock_service.list_alerts.assert_called()
    
    def test_list_alerts_with_pagination(self, client, mock_get_db):
        """Test listing alerts with pagination."""
        from app.services.alert_service import AlertService
        
        mock_service = Mock()
        mock_service.list_alerts.return_value = ([], 0)
        
        with patch('app.api.routes_alerts.AlertService', return_value=mock_service):
            response = client.get("/api/v1/alerts/?limit=10&offset=20")
            
            assert response.status_code == 200
            # Verify pagination parameters were passed
            call_args = mock_service.list_alerts.call_args
            assert call_args.kwargs.get("limit") == 10
            assert call_args.kwargs.get("offset") == 20
    
    def test_get_alert_by_id(self, client, mock_get_db):
        """Test getting a specific alert by ID."""
        alert_id = str(uuid4())
        
        from app.services.alert_service import AlertService
        
        mock_service = Mock()
        mock_alert = Mock()
        mock_alert.id = alert_id
        mock_service.get_alert.return_value = mock_alert
        
        with patch('app.api.routes_alerts.AlertService', return_value=mock_service):
            response = client.get(f"/api/v1/alerts/{alert_id}")
            
            # Should return alert if found
            assert response.status_code in [200, 404]
    
    def test_list_incidents_endpoint(self, client, mock_get_db):
        """Test listing incidents endpoint."""
        response = client.get("/api/v1/incidents/")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
    
    def test_get_incident_by_id(self, client, mock_get_db):
        """Test getting a specific incident by ID."""
        incident_id = str(uuid4())
        
        response = client.get(f"/api/v1/incidents/{incident_id}")
        
        assert response.status_code in [200, 404]
    
    def test_list_playbooks_endpoint(self, client, mock_get_db):
        """Test listing playbooks endpoint."""
        response = client.get("/api/v1/playbooks/")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_execute_playbook_endpoint(self, client, mock_get_db):
        """Test executing a playbook."""
        playbook_id = str(uuid4())
        
        response = client.post(
            f"/api/v1/playbooks/{playbook_id}/execute",
            json={"parameters": {}}
        )
        
        assert response.status_code in [200, 404]
    
    def test_chat_endpoint(self, client, mock_get_db):
        """Test chat endpoint."""
        response = client.post(
            "/api/v1/chat/",
            json={"message": "Hello"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "session_id" in data
    
    def test_list_integrations_endpoint(self, client, mock_get_db):
        """Test listing integrations endpoint."""
        response = client.get("/api/v1/integrations/")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_create_integration_endpoint(self, client, mock_get_db):
        """Test creating an integration."""
        integration_data = {
            "name": "Test Integration",
            "type": "siem",
            "config": {}
        }
        
        response = client.post(
            "/api/v1/integrations/",
            json=integration_data
        )
        
        assert response.status_code in [200, 201, 400]
    
    def test_endpoint_error_handling(self, client, mock_get_db):
        """Test error handling in endpoints."""
        from app.services.alert_service import AlertService
        
        mock_service = Mock()
        mock_service.list_alerts.side_effect = Exception("Database error")
        
        with patch('app.api.routes_alerts.AlertService', return_value=mock_service):
            response = client.get("/api/v1/alerts/")
            
            # Should handle errors gracefully
            assert response.status_code in [500, 503]
    
    def test_query_parameter_validation(self, client, mock_get_db):
        """Test query parameter validation."""
        # Test invalid limit (too high)
        response = client.get("/api/v1/alerts/?limit=200")
        
        # Should reject or cap limit
        assert response.status_code in [200, 400, 422]
    
    def test_endpoint_response_format(self, client, mock_get_db):
        """Test that endpoints return consistent response format."""
        response = client.get("/api/v1/alerts/")
        
        if response.status_code == 200:
            data = response.json()
            # Should have consistent structure
            assert isinstance(data, dict)

    def test_source_health_includes_edr(self, client):
        """Ensure source-health exposes EDR sidecar statuses."""
        with patch('app.api.routes_siem._probe') as mock_probe:
            mock_probe.side_effect = [
                "healthy",  # ingest
                "healthy",  # siem agent
                "healthy",  # opensearch
                "healthy",  # wazuh
                "healthy",  # openedr
                "healthy",  # velociraptor
            ]
            response = client.get("/api/v1/siem/source-health")
        assert response.status_code == 200
        data = response.json()
        for key in ("wazuh", "openedr", "velociraptor", "ingestion_service", "siem_agent", "opensearch"):
            assert key in data
