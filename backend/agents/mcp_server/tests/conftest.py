"""Pytest configuration and fixtures for MCP server tests."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx


@pytest.fixture
def mock_tenant_id():
    """Return a mock tenant ID."""
    return "tenant-123"


@pytest.fixture
def mock_user_id():
    """Return a mock user ID."""
    return "user-456"


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx AsyncClient."""
    client = AsyncMock(spec=httpx.AsyncClient)
    
    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.raise_for_status = Mock()
    mock_response.json = Mock(return_value={"status": "ok", "data": []})
    
    client.get = AsyncMock(return_value=mock_response)
    client.post = AsyncMock(return_value=mock_response)
    
    return client


@pytest.fixture
def mock_service_clients(mock_httpx_client):
    """Mock service clients."""
    with patch('app.core.service_clients.clients') as mock_clients:
        # Set all clients to mock
        mock_clients.siem_agent = mock_httpx_client
        mock_clients.soar_agent = mock_httpx_client
        mock_clients.iam_agent = mock_httpx_client
        mock_clients.posture_agent = mock_httpx_client
        mock_clients.observables_service = mock_httpx_client
        mock_clients.detection_service = mock_httpx_client
        mock_clients.compliance_service = mock_httpx_client
        mock_clients.vulnerability_service = mock_httpx_client
        mock_clients.ticketing_agent = mock_httpx_client
        mock_clients.framework_service = mock_httpx_client
        
        mock_clients.add_tenant_header = Mock(return_value={"X-Tenant-Id": "tenant-123"})
        
        yield mock_clients


@pytest.fixture
def mock_security_manager():
    """Mock security manager."""
    with patch('app.core.security.security_manager') as mock_mgr:
        mock_mgr.authorize_tool_call = AsyncMock(return_value=True)
        mock_mgr.audit_tool_call = AsyncMock()
        mock_mgr.is_high_risk_tool = Mock(return_value=False)
        mock_mgr.sanitize_tool_output = Mock(side_effect=lambda x: x)
        
        yield mock_mgr


@pytest.fixture
def sample_log_search_result():
    """Sample log search result."""
    return {
        "total": 2,
        "hits": [
            {
                "timestamp": "2024-12-02T10:00:00Z",
                "message": "Failed login attempt",
                "source_ip": "192.168.1.100",
                "user": "admin"
            },
            {
                "timestamp": "2024-12-02T10:01:00Z",
                "message": "Failed login attempt",
                "source_ip": "192.168.1.100",
                "user": "admin"
            }
        ]
    }


@pytest.fixture
def sample_incident():
    """Sample incident."""
    return {
        "id": "INC-123",
        "title": "Brute Force Attack",
        "description": "Multiple failed login attempts detected",
        "severity": "high",
        "status": "new",
        "created_at": "2024-12-02T10:00:00Z"
    }


@pytest.fixture
def sample_playbook():
    """Sample playbook."""
    return {
        "id": "PB-001",
        "name": "Phishing Containment",
        "description": "Automated response to phishing attacks",
        "category": "phishing",
        "steps": [
            {"action": "lock_account", "params": {"user_id": "{{user_id}}"}},
            {"action": "revoke_sessions", "params": {"user_id": "{{user_id}}"}},
            {"action": "notify_soc", "params": {"message": "User contained"}}
        ]
    }


@pytest.fixture
def sample_user():
    """Sample user."""
    return {
        "id": "user-789",
        "email": "john.doe@example.com",
        "name": "John Doe",
        "status": "active",
        "mfa_enabled": True,
        "last_login": "2024-12-02T09:00:00Z"
    }


@pytest.fixture
def sample_observable():
    """Sample observable."""
    return {
        "id": "obs-001",
        "tenant_id": "tenant-123",
        "observable_type": "ip",
        "value": "192.168.1.100",
        "enrichment_status": "completed",
        "enrichment_data": {
            "reputation": "malicious",
            "country": "US",
            "asn": "AS1234"
        }
    }

