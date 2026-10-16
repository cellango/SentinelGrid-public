"""Integration tests for detection service."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db, get_tenant_session
from app.models.rule import DetectionRule
from uuid import uuid4, UUID


@pytest.fixture
def client(db_session):
    """Create test client with database override."""
    def override_get_db():
        yield db_session

    def override_get_tenant_session():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_tenant_session] = override_get_tenant_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(test_tenant_id):
    """Create auth headers for test requests."""
    return {
        "Authorization": "Bearer test-token",
        "X-Tenant-ID": test_tenant_id,
    }


@pytest.mark.asyncio
async def test_create_rule(client, auth_headers, test_tenant_id):
    """Test creating a detection rule via API."""
    rule_data = {
        "name": "Test Failed Logins Rule",
        "description": "Test rule",
        "rule_type": "failed_logins",
        "pattern": {
            "threshold": 5,
            "window_minutes": 15,
        },
        "severity": "medium",
        "enabled": True,
    }
    
    with patch("app.core.security.verify_token_with_iam_agent") as mock_verify:
        mock_verify.return_value = {
            "tenant_id": test_tenant_id,
            "roles": ["admin"],
        }
        
        response = client.post(
            "/api/v1/rules",
            json=rule_data,
            headers=auth_headers,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == rule_data["name"]
        assert data["rule_type"] == rule_data["rule_type"]
        assert data["severity"] == rule_data["severity"]


def test_list_rules(client, db_session, sample_failed_logins_rule, auth_headers, test_tenant_id):
    """Test listing detection rules via API."""
    with patch("app.core.security.verify_token_with_iam_agent") as mock_verify:
        mock_verify.return_value = {
            "tenant_id": test_tenant_id,
            "roles": ["admin"],
        }
        
        response = client.get(
            "/api/v1/rules",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


@pytest.mark.asyncio
async def test_evaluate_rule_endpoint(client, db_session, sample_failed_logins_rule, auth_headers, test_tenant_id, sample_events):
    """Test manual rule evaluation via API."""
    with patch("app.core.security.verify_token_with_iam_agent") as mock_verify:
        mock_verify.return_value = {
            "tenant_id": test_tenant_id,
            "roles": ["admin"],
        }
        
        # Mock event fetching
        with patch("app.rules.base.BaseRule.fetch_recent_events") as mock_fetch:
            failed_events = [e for e in sample_events if "login.failure" in e.get("event_type", "")]
            mock_fetch.return_value = failed_events
            
            # Mock alert creation
            with patch("app.services.alert_service.create_alerts") as mock_create:
                mock_create.return_value = {"created": 1, "failed": 0}
                
                response = client.post(
                    f"/api/v1/rules/{sample_failed_logins_rule.id}/evaluate",
                    params={"create_alerts_flag": True},
                    headers=auth_headers,
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "alerts_generated" in data
                assert data["alerts_generated"] >= 0


def test_update_rule(client, db_session, sample_failed_logins_rule, auth_headers, test_tenant_id):
    """Test updating a detection rule via API."""
    with patch("app.core.security.verify_token_with_iam_agent") as mock_verify:
        mock_verify.return_value = {
            "tenant_id": test_tenant_id,
            "roles": ["admin"],
        }
        
        update_data = {
            "severity": "high",
            "pattern": {
                "threshold": 10,
                "window_minutes": 30,
            },
        }
        
        response = client.patch(
            f"/api/v1/rules/{sample_failed_logins_rule.id}",
            json=update_data,
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["severity"] == "high"


def test_delete_rule(client, db_session, sample_failed_logins_rule, auth_headers, test_tenant_id):
    """Test deleting a detection rule via API."""
    rule_id = sample_failed_logins_rule.id
    
    with patch("app.core.security.verify_token_with_iam_agent") as mock_verify:
        mock_verify.return_value = {
            "tenant_id": test_tenant_id,
            "roles": ["admin"],
        }
        
        response = client.delete(
            f"/api/v1/rules/{rule_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 204
        
        # Verify rule is deleted
        response = client.get(
            f"/api/v1/rules/{rule_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404
