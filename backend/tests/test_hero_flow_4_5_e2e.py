"""
End-to-End Integration Tests for Hero Flow 4 & 5

Test Scenarios:
1. High-Severity Alert → Automated Response
2. Compliance Violation → Remediation
3. Multi-Step Workflow
"""

import pytest
import httpx
import os
import time
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
SOAR_AGENT_URL = os.getenv(
    "SOAR_AGENT_URL", "http://localhost:8004"
)
DETECTION_SERVICE_URL = os.getenv(
    "DETECTION_SERVICE_URL", "http://localhost:8006"
)
IAM_AGENT_URL = os.getenv(
    "IAM_AGENT_URL", "http://localhost:8005"
)
POSTURE_AGENT_URL = os.getenv(
    "POSTURE_AGENT_URL", "http://localhost:8010"
)

# Test configuration
TEST_TENANT_ID = os.getenv("TEST_TENANT_ID", str(uuid4()))
INTERNAL_SERVICE_TOKEN = os.getenv(
    "INTERNAL_SERVICE_TOKEN", "internal-service-token-change-in-production"
)


@pytest.fixture
def headers():
    """Create headers with tenant ID and auth token."""
    return {
        "X-Tenant-ID": TEST_TENANT_ID,
        "Authorization": f"Bearer {INTERNAL_SERVICE_TOKEN}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def test_playbook(headers):
    """Create a test playbook for automated response."""
    playbook_data = {
        "name": f"Test Automated Response Playbook {uuid4()}",
        "description": "Test playbook for automated response",
        "category": "suspicious_login",
        "workflow": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "position": {"x": 0, "y": 0},
                },
                {
                    "id": "action1",
                    "type": "action",
                    "data": {"action": "notify_user"},
                    "position": {"x": 200, "y": 0},
                },
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "start",
                    "target": "action1",
                }
            ],
        },
        "is_enabled": True,
        "auto_trigger_enabled": True,
        "trigger_conditions": {
            "severity": ["high", "critical"],
            "category": ["suspicious_login"],
        },
        "trigger_priority": 10,
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{SOAR_AGENT_URL}/soar/playbooks",
            json=playbook_data,
            headers=headers,
        )
        if response.status_code == 201:
            return response.json()
        else:
            pytest.skip(f"Could not create test playbook: {response.status_code} - {response.text}")


@pytest.fixture
def test_alert(headers):
    """Create a test alert for automated response."""
    alert_data = {
        "title": "Test High-Severity Alert",
        "description": "Test alert for automated response",
        "severity": "high",
        "category": "suspicious_login",
        "source": "siem_agent",
        "status": "open",
        "metadata": {
            "user_id": "test-user-123",
            "ip_address": "192.168.1.100",
        },
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{DETECTION_SERVICE_URL}/api/v1/alerts",
            json=alert_data,
            headers=headers,
        )
        if response.status_code == 201:
            return response.json()
        else:
            pytest.skip(f"Could not create test alert: {response.status_code} - {response.text}")


@pytest.fixture
def test_iam_finding(headers):
    """Create a test IAM finding for compliance remediation."""
    finding_data = {
        "identity_id": str(uuid4()),
        "finding_type": "excessive_permissions",
        "severity": "high",
        "description": "Test IAM finding for compliance remediation",
        "recommendation": "Review and reduce permissions",
        "status": "open",
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{IAM_AGENT_URL}/api/v1/iam/findings",
            json=finding_data,
            headers=headers,
        )
        if response.status_code == 201:
            return response.json()
        else:
            pytest.skip(f"Could not create test IAM finding: {response.status_code} - {response.text}")


class TestAutomatedResponseE2E:
    """Test Scenario 1: High-Severity Alert → Automated Response"""

    def test_alert_trigger_evaluation(self, headers, test_alert, test_playbook):
        """Test that alert triggers are evaluated correctly."""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{test_alert['id']}/evaluate",
                headers=headers,
            )
            assert response.status_code == 200
            result = response.json()
            assert "matching_playbooks" in result
            assert len(result["matching_playbooks"]) > 0
            # Verify our test playbook is in the results
            playbook_ids = [p["playbook_id"] for p in result["matching_playbooks"]]
            assert test_playbook["id"] in playbook_ids

    def test_auto_trigger_playbook(self, headers, test_alert, test_playbook):
        """Test that playbooks are automatically triggered for matching alerts."""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{test_alert['id']}/auto-trigger",
                headers=headers,
            )
            assert response.status_code == 200
            result = response.json()
            assert result["triggered"] is True
            assert result["playbooks_triggered"] > 0
            # Verify execution was created
            assert any(
                r.get("execution_id") for r in result.get("results", [])
            )

    def test_orchestrator_alert_response(self, headers, test_alert):
        """Test orchestrator coordinates automated response."""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{ORCHESTRATOR_URL}/api/v1/orchestrator/alerts/{test_alert['id']}/orchestrate",
                json={"response_type": "automated_response"},
                headers=headers,
            )
            assert response.status_code == 200
            result = response.json()
            assert result["status"] in ["orchestrated", "no_triggers"]
            if result["status"] == "orchestrated":
                assert result["playbooks_triggered"] > 0
                assert len(result["playbooks"]) > 0

    def test_execution_status_tracking(self, headers, test_alert, test_playbook):
        """Test that execution status is tracked correctly."""
        # First trigger the playbook
        with httpx.Client(timeout=30.0) as client:
            trigger_response = client.post(
                f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{test_alert['id']}/auto-trigger",
                headers=headers,
            )
            assert trigger_response.status_code == 200
            trigger_result = trigger_response.json()
            
            # Get execution ID
            execution_id = None
            for result in trigger_result.get("results", []):
                if result.get("execution_id"):
                    execution_id = result["execution_id"]
                    break
            
            if execution_id:
                # Check execution status
                status_response = client.get(
                    f"{SOAR_AGENT_URL}/soar/executions/{execution_id}",
                    headers=headers,
                )
                assert status_response.status_code == 200
                execution = status_response.json()
                assert "status" in execution
                assert execution["status"] in ["pending", "running", "completed", "failed"]


class TestComplianceRemediationE2E:
    """Test Scenario 2: Compliance Violation → Remediation"""

    def test_enhance_finding_with_compliance(self, headers, test_iam_finding):
        """Test that findings are enhanced with compliance metadata."""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{COMPLIANCE_SERVICE_URL}/api/v1/compliance/findings/{test_iam_finding['id']}/enhance",
                json={"finding_type": "iam_finding"},
                headers=headers,
            )
            assert response.status_code == 200
            result = response.json()
            assert result["finding_id"] == test_iam_finding["id"]
            # Should have NIST control ID
            assert "nist_control_id" in result or result.get("nist_control_id") is not None
            # Should have remediation plan
            assert "remediation_plan" in result

    def test_create_remediation_plan(self, headers, test_iam_finding):
        """Test that remediation plans are created correctly."""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{COMPLIANCE_SERVICE_URL}/api/v1/compliance/findings/{test_iam_finding['id']}/remediation-plan",
                json={"finding_type": "iam_finding"},
                headers=headers,
            )
            assert response.status_code == 200
            result = response.json()
            assert "plan" in result
            plan = result["plan"]
            assert "steps" in plan
            assert len(plan["steps"]) > 0
            assert "estimated_time" in plan

    def test_execute_remediation(self, headers, test_iam_finding, test_playbook):
        """Test that remediation is executed via playbook."""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{COMPLIANCE_SERVICE_URL}/api/v1/compliance/findings/{test_iam_finding['id']}/remediate",
                json={
                    "playbook_id": test_playbook["id"],
                    "auto_approve": False,
                },
                params={"finding_type": "iam_finding"},
                headers=headers,
            )
            assert response.status_code == 200
            result = response.json()
            assert "remediation_id" in result
            assert "execution_id" in result
            assert result["status"] in ["pending", "in_progress", "completed"]

    def test_orchestrator_remediation(self, headers, test_iam_finding, test_playbook):
        """Test orchestrator coordinates compliance remediation."""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{ORCHESTRATOR_URL}/api/v1/orchestrator/findings/{test_iam_finding['id']}/orchestrate",
                json={"playbook_id": test_playbook["id"]},
                params={"finding_type": "iam_finding"},
                headers=headers,
            )
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "orchestrated"
            assert "remediation_id" in result
            assert "execution_id" in result


class TestMultiStepWorkflowE2E:
    """Test Scenario 3: Multi-Step Workflow"""

    def test_alert_to_containment_to_remediation(self, headers, test_alert, test_playbook):
        """Test complete workflow: Alert → Containment → Remediation."""
        # Step 1: Alert detected and evaluated
        with httpx.Client(timeout=30.0) as client:
            eval_response = client.post(
                f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{test_alert['id']}/evaluate",
                headers=headers,
            )
            assert eval_response.status_code == 200
            eval_result = eval_response.json()
            assert len(eval_result["matching_playbooks"]) > 0

            # Step 2: Trigger containment playbook
            trigger_response = client.post(
                f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{test_alert['id']}/auto-trigger",
                headers=headers,
            )
            assert trigger_response.status_code == 200
            trigger_result = trigger_response.json()
            assert trigger_result["triggered"] is True

            # Step 3: Wait for execution (if async)
            time.sleep(2)

            # Step 4: Check execution status
            execution_id = None
            for result in trigger_result.get("results", []):
                if result.get("execution_id"):
                    execution_id = result["execution_id"]
                    break

            if execution_id:
                status_response = client.get(
                    f"{SOAR_AGENT_URL}/soar/executions/{execution_id}",
                    headers=headers,
                )
                assert status_response.status_code == 200
                execution = status_response.json()
                assert "status" in execution

    def test_remediation_status_tracking(self, headers, test_iam_finding):
        """Test that remediation status is tracked throughout the workflow."""
        with httpx.Client(timeout=30.0) as client:
            # Enhance finding
            enhance_response = client.post(
                f"{COMPLIANCE_SERVICE_URL}/api/v1/compliance/findings/{test_iam_finding['id']}/enhance",
                json={"finding_type": "iam_finding"},
                headers=headers,
            )
            assert enhance_response.status_code == 200

            # Get remediation status
            status_response = client.get(
                f"{COMPLIANCE_SERVICE_URL}/api/v1/compliance/findings/{test_iam_finding['id']}/remediation-status",
                params={"finding_type": "iam_finding"},
                headers=headers,
            )
            # May return 404 if no remediation started yet
            if status_response.status_code == 200:
                status = status_response.json()
                assert "status" in status
                assert status["status"] in ["pending", "in_progress", "completed", "failed"]


@pytest.mark.integration
class TestServiceHealth:
    """Test that all services are healthy and accessible."""

    def test_automated_response_service_health(self):
        """Test Automated Response Service health."""
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{AUTOMATED_RESPONSE_SERVICE_URL}/health")
            assert response.status_code == 200

    def test_compliance_service_health(self):
        """Test Compliance Service health."""
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{COMPLIANCE_SERVICE_URL}/health")
            assert response.status_code == 200

    def test_orchestrator_health(self):
        """Test Orchestrator health."""
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{ORCHESTRATOR_URL}/health")
            assert response.status_code == 200
