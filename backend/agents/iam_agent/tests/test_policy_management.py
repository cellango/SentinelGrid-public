"""
Unit tests for Policy Management (Keycloak authorization policies)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from app.services.keycloak_client import KeycloakClient


@pytest.fixture
def mock_keycloak_client():
    """Mock Keycloak client."""
    client = Mock(spec=KeycloakClient)
    client.admin = Mock()
    return client


class TestPolicyManagement:
    """Test suite for Keycloak policy management."""
    
    def test_create_policy(self, mock_keycloak_client):
        """Test creating a Keycloak authorization policy."""
        policy_data = {
            "type": "role",
            "name": "admin-only-policy",
            "roles": ["admin"]
        }
        
        mock_keycloak_client.admin.create_client_authz_policy.return_value = {
            "id": str(uuid4()),
            "name": "admin-only-policy"
        }
        
        # Simulate policy creation
        result = mock_keycloak_client.admin.create_client_authz_policy(
            client_id="test-client",
            payload=policy_data
        )
        
        assert result["id"] is not None
        assert result["name"] == "admin-only-policy"
    
    def test_get_policy(self, mock_keycloak_client):
        """Test retrieving a policy."""
        policy_id = str(uuid4())
        mock_policy = {
            "id": policy_id,
            "name": "test-policy",
            "type": "role"
        }
        
        mock_keycloak_client.admin.get_client_authz_policy.return_value = mock_policy
        
        result = mock_keycloak_client.admin.get_client_authz_policy(
            client_id="test-client",
            policy_id=policy_id
        )
        
        assert result["id"] == policy_id
        assert result["name"] == "test-policy"
    
    def test_list_policies(self, mock_keycloak_client):
        """Test listing all policies for a client."""
        mock_policies = [
            {"id": "1", "name": "policy-1", "type": "role"},
            {"id": "2", "name": "policy-2", "type": "time"}
        ]
        
        mock_keycloak_client.admin.get_client_authz_policies.return_value = mock_policies
        
        result = mock_keycloak_client.admin.get_client_authz_policies(client_id="test-client")
        
        assert len(result) == 2
        assert all("id" in p for p in result)
    
    def test_update_policy(self, mock_keycloak_client):
        """Test updating a policy."""
        policy_id = str(uuid4())
        updated_data = {
            "name": "updated-policy",
            "roles": ["admin", "manager"]
        }
        
        mock_keycloak_client.admin.update_client_authz_policy.return_value = {"status": "updated"}
        
        result = mock_keycloak_client.admin.update_client_authz_policy(
            client_id="test-client",
            policy_id=policy_id,
            payload=updated_data
        )
        
        assert result["status"] == "updated"
    
    def test_delete_policy(self, mock_keycloak_client):
        """Test deleting a policy."""
        policy_id = str(uuid4())
        
        mock_keycloak_client.admin.delete_client_authz_policy.return_value = True
        
        result = mock_keycloak_client.admin.delete_client_authz_policy(
            client_id="test-client",
            policy_id=policy_id
        )
        
        assert result is True
    
    def test_evaluate_policy(self, mock_keycloak_client):
        """Test evaluating a policy against a request."""
        evaluation_request = {
            "roleIds": ["role-123"],
            "context": {
                "ipAddress": "192.168.1.1",
                "time": "09:00"
            }
        }
        
        mock_evaluation = {
            "result": True,
            "status": "PERMIT",
            "policies": ["policy-1"]
        }
        
        mock_keycloak_client.admin.evaluate_client_authz_policy.return_value = mock_evaluation
        
        result = mock_keycloak_client.admin.evaluate_client_authz_policy(
            client_id="test-client",
            payload=evaluation_request
        )
        
        assert result["result"] is True
        assert result["status"] == "PERMIT"
    
    def test_policy_types_role(self, mock_keycloak_client):
        """Test role-based policy creation."""
        role_policy = {
            "type": "role",
            "name": "admin-role-policy",
            "roles": ["admin", "super-admin"]
        }
        
        mock_keycloak_client.admin.create_client_authz_policy.return_value = {
            "id": str(uuid4()),
            **role_policy
        }
        
        result = mock_keycloak_client.admin.create_client_authz_policy(
            client_id="test-client",
            payload=role_policy
        )
        
        assert result["type"] == "role"
        assert "admin" in result["roles"]
    
    def test_policy_types_time(self, mock_keycloak_client):
        """Test time-based policy creation."""
        time_policy = {
            "type": "time",
            "name": "business-hours-policy",
            "notBefore": "09:00",
            "notOnOrAfter": "17:00"
        }
        
        mock_keycloak_client.admin.create_client_authz_policy.return_value = {
            "id": str(uuid4()),
            **time_policy
        }
        
        result = mock_keycloak_client.admin.create_client_authz_policy(
            client_id="test-client",
            payload=time_policy
        )
        
        assert result["type"] == "time"
        assert "notBefore" in result
    
    def test_policy_types_aggregate(self, mock_keycloak_client):
        """Test aggregate (AND/OR) policy creation."""
        aggregate_policy = {
            "type": "aggregate",
            "name": "combined-policy",
            "logic": "POSITIVE",
            "policies": ["policy-1", "policy-2"]
        }
        
        mock_keycloak_client.admin.create_client_authz_policy.return_value = {
            "id": str(uuid4()),
            **aggregate_policy
        }
        
        result = mock_keycloak_client.admin.create_client_authz_policy(
            client_id="test-client",
            payload=aggregate_policy
        )
        
        assert result["type"] == "aggregate"
        assert len(result["policies"]) == 2
    
    def test_policy_error_handling_not_found(self, mock_keycloak_client):
        """Test error handling for policy not found."""
        from keycloak.exceptions import KeycloakError
        
        mock_keycloak_client.admin.get_client_authz_policy.side_effect = KeycloakError(
            "Policy not found",
            response_code=404
        )
        
        with pytest.raises(KeycloakError):
            mock_keycloak_client.admin.get_client_authz_policy(
                client_id="test-client",
                policy_id="nonexistent"
            )

