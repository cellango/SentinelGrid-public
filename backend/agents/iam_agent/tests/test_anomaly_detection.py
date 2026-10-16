"""Tests for anomaly detection and automated response."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.anomaly_detection import AnomalyDetectionService


@pytest.fixture
def client():
    """Create test client."""
    # Override token dependency to avoid real validation
    def _fake_token_dep():
        return "test-token"

    app.dependency_overrides = {
        # FastAPI doesn't expose the lambda dep directly; override via header accessor
        # by returning a dummy header extractor
    }
    return TestClient(app)


@pytest.fixture
def mock_token_data():
    """Mock token data with tenant_id."""
    return {
        "valid": True,
        "tenant_id": "test-tenant-123",
        "user_id": "user-123",
        "roles": ["TENANT_ADMIN"]
    }


@patch('app.api.anomalies.get_token_data')
@patch('app.api.anomalies.AnomalyDetectionService')
@patch('app.api.anomalies.AutomatedResponseService')
def test_list_anomalies(mock_auto, mock_service_class, mock_get_token, client, mock_token_data):
    """Test list anomalies endpoint."""
    mock_get_token.return_value = mock_token_data
    
    mock_service = Mock()
    mock_service.detect_anomalies = AsyncMock(return_value=[])
    mock_store = Mock()
    mock_store.list_anomalies.return_value = {
        "items": [
            {
                "id": "anomaly-1",
                "tenant_id": mock_token_data["tenant_id"],
                "user_id": mock_token_data["user_id"],
                "anomaly_type": "failed_logins",
                "severity": "high",
                "title": "Multiple Failed Login Attempts",
                "description": "5 failed login attempts detected",
                "risk_score": 75.0,
                "metadata": {"failed_count": 5},
                "status": "open",
                "detected_at": datetime.utcnow()
            }
        ],
        "total": 1
    }
    mock_service.store = mock_store
    mock_service_class.return_value = mock_service
    mock_auto.return_value = Mock()
    
    response = client.get(
        "/api/v1/security/anomalies",
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["anomaly_type"] == "failed_logins"


@patch('app.api.anomalies.AnomalyStore')
@patch('app.api.anomalies.get_token_data')
def test_acknowledge_anomaly(mock_get_token, mock_store_class, client, mock_token_data):
    """Test acknowledge anomaly endpoint."""
    mock_get_token.return_value = mock_token_data
    mock_store = Mock()
    mock_store.acknowledge.return_value = True
    mock_store_class.return_value = mock_store
    
    response = client.post(
        "/api/v1/security/anomalies/anomaly-123/acknowledge",
        json={"notes": "Reviewed and resolved"},
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@patch('app.api.anomalies.get_token_data')
@patch('app.api.anomalies.AnomalyDetectionService')
@patch('app.api.anomalies.AutomatedResponseService')
def test_trigger_anomaly_detection(mock_response_service, mock_detection_service, mock_get_token, client, mock_token_data):
    """Test manual anomaly detection trigger."""
    mock_get_token.return_value = mock_token_data
    
    mock_detection = Mock()
    mock_detection.detect_anomalies = AsyncMock(return_value=[
        {
            "anomaly_type": "unusual_device",
            "severity": "medium",
            "title": "Unusual Device Detected",
            "risk_score": 60.0
        }
    ])
    mock_detection_service.return_value = mock_detection
    
    mock_response = Mock()
    mock_response.respond_to_anomaly = AsyncMock(return_value=[])
    mock_response_service.return_value = mock_response
    
    response = client.post(
        "/api/v1/security/anomalies/detect",
        json={"time_window_hours": 24},
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["anomalies_detected"] == 1


def test_impossible_travel_detection():
    """Detector flags geo jumps that exceed speed threshold."""
    service = AnomalyDetectionService(store=Mock())
    now = datetime.utcnow()
    events = [
        {
            "user_id": "u1",
            "timestamp": now - timedelta(hours=2),
            "success": True,
            "ip_address": "1.1.1.1",
            "user_agent": "ua",
            "device_id": None,
            "geo": {"lat": 40.7128, "lon": -74.0060, "city": "New York", "country": "US"},
        },
        {
            "user_id": "u1",
            "timestamp": now - timedelta(minutes=30),
            "success": True,
            "ip_address": "2.2.2.2",
            "user_agent": "ua",
            "device_id": None,
            "geo": {"lat": 51.5074, "lon": -0.1278, "city": "London", "country": "UK"},
        },
    ]
    anomalies = service._detect_impossible_travel(events)
    assert anomalies, "Expected impossible travel anomaly"
    assert anomalies[0]["anomaly_type"] == "impossible_travel"


def test_failed_login_burst_detection():
    """Detector flags failed login spikes in a short window."""
    service = AnomalyDetectionService(store=Mock())
    base = datetime.utcnow()
    failures = [
        {"timestamp": base - timedelta(minutes=4), "success": False},
        {"timestamp": base - timedelta(minutes=3), "success": False},
        {"timestamp": base - timedelta(minutes=2), "success": False},
        {"timestamp": base - timedelta(minutes=1), "success": False},
        {"timestamp": base - timedelta(seconds=30), "success": False},
    ]
    anomalies = service._detect_failed_auth_spike(failures, base - timedelta(hours=1))
    assert anomalies, "Expected failed login burst anomaly"
    assert anomalies[0]["anomaly_type"] == "failed_logins"
