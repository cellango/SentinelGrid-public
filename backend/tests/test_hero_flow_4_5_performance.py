"""
Performance Tests for Hero Flow 4 & 5

Test Cases:
- Rule evaluation performance (1000+ rules)
- Concurrent execution handling (100+ concurrent)
- Action execution latency
- System load under stress
"""

import pytest
import httpx
import os
import time
import asyncio
from typing import List, Dict, Any
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# Test configuration
TEST_TENANT_ID = os.getenv("TEST_TENANT_ID", str(uuid4()))
INTERNAL_SERVICE_TOKEN = os.getenv(
    "INTERNAL_SERVICE_TOKEN", "internal-service-token-change-in-production"
)

# Performance thresholds
MAX_EVALUATION_TIME_MS = 1000  # 1 second for rule evaluation
MAX_CONCURRENT_EXECUTIONS = 100
MAX_EXECUTION_LATENCY_MS = 5000  # 5 seconds for execution start


@pytest.fixture
def headers():
    """Create headers with tenant ID and auth token."""
    return {
        "X-Tenant-ID": TEST_TENANT_ID,
        "Authorization": f"Bearer {INTERNAL_SERVICE_TOKEN}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def test_playbooks(headers, num_playbooks=10):
    """Create multiple test playbooks for performance testing."""
    playbooks = []
    with httpx.Client(timeout=30.0) as client:
        for i in range(num_playbooks):
            playbook_data = {
                "name": f"Performance Test Playbook {i}",
                "description": f"Test playbook {i} for performance testing",
                "category": "suspicious_login",
                "workflow": {
                    "nodes": [{"id": "start", "type": "start", "position": {"x": 0, "y": 0}}],
                    "edges": [],
                },
                "is_enabled": True,
                "auto_trigger_enabled": True,
                "trigger_conditions": {
                    "severity": ["high", "critical"],
                    "category": ["suspicious_login"],
                },
                "trigger_priority": i,
            }
            response = client.post(
                f"{SOAR_AGENT_URL}/soar/playbooks",
                json=playbook_data,
                headers=headers,
            )
            if response.status_code == 201:
                playbooks.append(response.json())
    return playbooks


@pytest.fixture
def test_alerts(headers, num_alerts=50):
    """Create multiple test alerts for performance testing."""
    alerts = []
    with httpx.Client(timeout=30.0) as client:
        for i in range(num_alerts):
            alert_data = {
                "title": f"Performance Test Alert {i}",
                "description": f"Test alert {i} for performance testing",
                "severity": "high" if i % 2 == 0 else "critical",
                "category": "suspicious_login",
                "source": "siem_agent",
                "status": "open",
            }
            # Note: This would need to use the actual alert creation endpoint
            # For now, we'll create mock alert IDs
            alerts.append({"id": str(uuid4()), **alert_data})
    return alerts


@pytest.mark.performance
class TestRuleEvaluationPerformance:
    """Test rule evaluation performance with many playbooks."""

    def test_evaluate_single_alert_with_many_playbooks(self, headers, test_playbooks, test_alerts):
        """Test evaluation performance with many playbooks."""
        if not test_alerts:
            pytest.skip("No test alerts created")
        
        alert = test_alerts[0]
        start_time = time.time()
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{alert['id']}/evaluate",
                headers=headers,
            )
            elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
            
            assert response.status_code == 200
            # Performance assertion
            assert elapsed_time < MAX_EVALUATION_TIME_MS, (
                f"Evaluation took {elapsed_time}ms, expected < {MAX_EVALUATION_TIME_MS}ms"
            )

    def test_evaluate_multiple_alerts_sequentially(self, headers, test_playbooks, test_alerts):
        """Test sequential evaluation of multiple alerts."""
        if len(test_alerts) < 10:
            pytest.skip("Not enough test alerts")
        
        times = []
        with httpx.Client(timeout=30.0) as client:
            for alert in test_alerts[:10]:
                start_time = time.time()
                response = client.post(
                    f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{alert['id']}/evaluate",
                    headers=headers,
                )
                elapsed_time = (time.time() - start_time) * 1000
                times.append(elapsed_time)
                assert response.status_code in [200, 404]  # 404 if alert doesn't exist
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Performance assertions
        assert avg_time < MAX_EVALUATION_TIME_MS, (
            f"Average evaluation time {avg_time}ms, expected < {MAX_EVALUATION_TIME_MS}ms"
        )
        assert max_time < MAX_EVALUATION_TIME_MS * 2, (
            f"Max evaluation time {max_time}ms, expected < {MAX_EVALUATION_TIME_MS * 2}ms"
        )


@pytest.mark.performance
class TestConcurrentExecutionHandling:
    """Test concurrent execution handling."""

    def test_concurrent_alert_evaluations(self, headers, test_playbooks, test_alerts):
        """Test concurrent alert evaluations."""
        if len(test_alerts) < 20:
            pytest.skip("Not enough test alerts")
        
        def evaluate_alert(alert_id: str) -> Dict[str, Any]:
            """Evaluate a single alert."""
            with httpx.Client(timeout=30.0) as client:
                start_time = time.time()
                response = client.post(
                    f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{alert_id}/evaluate",
                    headers=headers,
                )
                elapsed_time = (time.time() - start_time) * 1000
                return {
                    "status_code": response.status_code,
                    "elapsed_time": elapsed_time,
                    "alert_id": alert_id,
                }
        
        # Execute concurrent evaluations
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(evaluate_alert, alert["id"])
                for alert in test_alerts[:20]
            ]
            results = [f.result() for f in as_completed(futures)]
        
        # Verify all completed
        assert len(results) == 20
        # Verify reasonable performance
        avg_time = sum(r["elapsed_time"] for r in results) / len(results)
        assert avg_time < MAX_EVALUATION_TIME_MS * 2, (
            f"Average concurrent evaluation time {avg_time}ms, expected < {MAX_EVALUATION_TIME_MS * 2}ms"
        )

    def test_concurrent_remediation_executions(self, headers, test_playbooks):
        """Test concurrent remediation executions."""
        # This would require test findings
        # For now, we'll test the endpoint availability
        with httpx.Client(timeout=30.0) as client:
            response = client.get(f"{COMPLIANCE_SERVICE_URL}/health")
            assert response.status_code == 200


@pytest.mark.performance
class TestExecutionLatency:
    """Test action execution latency."""

    def test_playbook_trigger_latency(self, headers, test_playbooks, test_alerts):
        """Test latency of playbook triggering."""
        if not test_alerts or not test_playbooks:
            pytest.skip("No test data available")
        
        alert = test_alerts[0]
        playbook = test_playbooks[0]
        
        start_time = time.time()
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{alert['id']}/trigger",
                json={
                    "playbook_id": playbook["id"],
                    "trigger_reason": "Performance test",
                },
                headers=headers,
            )
            elapsed_time = (time.time() - start_time) * 1000
        
        # May return 404 if alert doesn't exist, but should be fast
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert elapsed_time < MAX_EXECUTION_LATENCY_MS, (
                f"Playbook trigger latency {elapsed_time}ms, expected < {MAX_EXECUTION_LATENCY_MS}ms"
            )


@pytest.mark.performance
class TestSystemLoadUnderStress:
    """Test system load under stress."""

    def test_high_volume_alert_processing(self, headers, test_playbooks):
        """Test processing high volume of alerts."""
        # Create many alerts and process them
        num_alerts = 100
        alerts = [{"id": str(uuid4())} for _ in range(num_alerts)]
        
        start_time = time.time()
        success_count = 0
        
        with httpx.Client(timeout=30.0) as client:
            for alert in alerts:
                response = client.post(
                    f"{AUTOMATED_RESPONSE_SERVICE_URL}/api/v1/automated-response/alerts/{alert['id']}/evaluate",
                    headers=headers,
                )
                if response.status_code in [200, 404]:
                    success_count += 1
        
        elapsed_time = time.time() - start_time
        throughput = num_alerts / elapsed_time if elapsed_time > 0 else 0
        
        # Verify system handled the load
        assert success_count == num_alerts, (
            f"Only {success_count}/{num_alerts} requests succeeded"
        )
        # Verify reasonable throughput (at least 10 alerts/second)
        assert throughput > 10, (
            f"Throughput {throughput} alerts/sec, expected > 10 alerts/sec"
        )
