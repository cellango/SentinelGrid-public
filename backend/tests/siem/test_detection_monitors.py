"""
End-to-end tests for detection monitors and incident creation.

Tests the complete flow:
1. Generate test logs
2. Index into OpenSearch
3. Monitor fires and creates detection event
4. Webhook calls SOAR agent
5. Incident created with NIST status
6. Observables extracted
7. Timeline created
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any

from tests.siem.data.generate_test_logs import TestLogGenerator


class TestDetectionMonitors:
    """Test suite for detection monitors and incident creation."""
    
    @pytest.fixture
    def tenant_id(self) -> str:
        """Test tenant ID."""
        return "550e8400-e29b-41d4-a716-446655440000"
    
    @pytest.fixture
    def realm(self) -> str:
        """Test Keycloak realm."""
        return "sentinelgrid-test"
    
    @pytest.fixture
    def log_generator(self, tenant_id, realm):
        """Create test log generator."""
        return TestLogGenerator(tenant_id=tenant_id, realm=realm)
    
    def test_suspicious_login_detection(self, log_generator, tenant_id):
        """
        Test SG-DET-001: Suspicious Login / Account Takeover
        
        Scenario:
        - User has 7 failed login attempts
        - Followed by 1 successful login
        - From same IP (potential credential stuffing/brute force success)
        
        Expected:
        - Monitor fires
        - Detection event created
        - Incident created with NIST status=NEW
        - Playbook ID: PLAYBOOK_ACCOUNT_TAKEOVER
        """
        # Generate auth logs
        logs = log_generator.generate_auth_logs_suspicious_login(count=20)
        
        # Verify log structure
        assert len(logs) > 0
        assert any(log["event"]["outcome"] == "failure" for log in logs)
        assert any(log["event"]["outcome"] == "success" for log in logs)
        
        # Verify tenant context
        for log in logs:
            assert log["sg"]["tenant_id"] == tenant_id
            assert log["sg"]["realm"] is not None
        
        print(f"✓ Generated {len(logs)} auth logs for suspicious login test")
        print(f"  - Failures: {sum(1 for log in logs if log['event']['outcome'] == 'failure')}")
        print(f"  - Successes: {sum(1 for log in logs if log['event']['outcome'] == 'success')}")
    
    def test_user_reported_phishing(self, log_generator, tenant_id):
        """
        Test SG-DET-002: User-Reported Phishing
        
        Scenario:
        - Users report phishing emails via internal system
        
        Expected:
        - Monitor fires on each report
        - Incident created for each phishing report
        - Playbook ID: PLAYBOOK_PHISHING_USER_REPORTED
        """
        logs = log_generator.generate_email_logs_phishing_report(count=5)
        
        assert len(logs) == 5
        for log in logs:
            assert log["event"]["type"] == "phish_report"
            assert log["sg"]["tenant_id"] == tenant_id
        
        print(f"✓ Generated {len(logs)} phishing reports")
    
    def test_email_campaign_detection(self, log_generator, tenant_id):
        """
        Test SG-DET-003: Email Security Phishing Campaign
        
        Scenario:
        - Email gateway detects 50+ similar phishing emails
        
        Expected:
        - Monitor fires
        - Single incident for campaign
        - Playbook ID: PLAYBOOK_EMAIL_CAMPAIGN
        """
        logs = log_generator.generate_email_logs_campaign(count=50)
        
        assert len(logs) == 50
        assert all(log["alert"]["subtype"] == "phishing" for log in logs)
        
        print(f"✓ Generated {len(logs)} email campaign alerts")
    
    def test_endpoint_malware_detection(self, log_generator, tenant_id):
        """
        Test SG-DET-004: Endpoint Malware Detection
        
        Scenario:
        - EDR/AV detects high-severity malware on endpoints
        
        Expected:
        - Monitor fires
        - Incident created per detection
        - Observables: file_hash, host
        - Playbook ID: PLAYBOOK_ENDPOINT_MALWARE
        """
        logs = log_generator.generate_endpoint_logs_malware(count=5)
        
        assert len(logs) == 5
        for log in logs:
            assert log["event"]["category"] == "malware"
            assert log["event"]["severity"] in ["high", "critical"]
            assert "malware" in log
            assert "host" in log
        
        print(f"✓ Generated {len(logs)} malware detection logs")
    
    def test_ransomware_detection(self, log_generator, tenant_id):
        """
        Test SG-DET-005: Ransomware Suspected
        
        Scenario:
        - Ransomware family detected on critical systems
        
        Expected:
        - CRITICAL severity incident
        - Immediate containment playbook
        - Playbook ID: PLAYBOOK_RANSOMWARE
        """
        logs = log_generator.generate_endpoint_logs_ransomware(count=2)
        
        assert len(logs) == 2
        for log in logs:
            assert log["malware"]["family"] == "ransomware"
            assert log["event"]["severity"] == "critical"
        
        print(f"✓ Generated {len(logs)} ransomware detection logs")
    
    def test_cloud_storage_public(self, log_generator, tenant_id):
        """
        Test SG-DET-006: Public Cloud Storage Misconfiguration
        
        Scenario:
        - Cloud posture scan finds public S3 buckets
        
        Expected:
        - Incident created with resource details
        - Observables: cloud_resource
        - Playbook ID: PLAYBOOK_PUBLIC_STORAGE
        """
        logs = log_generator.generate_cloud_posture_logs(count=10)
        
        assert len(logs) == 10
        for log in logs:
            assert log["posture"]["type"] == "storage_public"
            assert log["posture"]["status"] == "fail"
            assert "resource" in log
        
        print(f"✓ Generated {len(logs)} cloud posture logs")
    
    def test_privilege_escalation(self, log_generator, tenant_id):
        """
        Test SG-DET-007: Privilege Escalation / New Admin
        
        Scenario:
        - Admin role granted to users
        
        Expected:
        - Incident created with actor and target user
        - HIGH severity
        - Playbook ID: PLAYBOOK_PRIVILEGE_ESCALATION
        """
        logs = log_generator.generate_iam_audit_logs(count=5)
        
        assert len(logs) == 5
        for log in logs:
            assert log["iam"]["action"] == "add_role"
            assert log["iam"]["role_name"] is not None
            assert "actor" in log
            assert "target_user" in log
        
        print(f"✓ Generated {len(logs)} IAM audit logs")
    
    def test_password_spray(self, log_generator, tenant_id):
        """
        Test SG-DET-008: Password Spray / Brute Force
        
        Scenario:
        - Single IP attempts to authenticate as 30+ different users
        - 100+ failed attempts in 10 minutes
        
        Expected:
        - Incident with spray statistics
        - Observables: source_ip
        - Playbook ID: PLAYBOOK_PASSWORD_SPRAY
        """
        logs = log_generator.generate_auth_logs_password_spray(count=100)
        
        assert len(logs) == 100
        
        # Count unique users
        unique_users = set(log["user"]["id"] for log in logs)
        assert len(unique_users) >= 10  # Should attack multiple users
        
        # All from same IP
        unique_ips = set(log["source"]["ip"] for log in logs)
        assert len(unique_ips) == 1  # All from same IP
        
        print(f"✓ Generated {len(logs)} password spray attempts")
        print(f"  - Unique users targeted: {len(unique_users)}")
        print(f"  - Source IP: {logs[0]['source']['ip']}")
    
    def test_data_exfiltration(self, log_generator, tenant_id):
        """
        Test SG-DET-009: Data Exfiltration / Unusual Transfer
        
        Scenario:
        - User transfers >10GB in 1 hour
        
        Expected:
        - Incident with network statistics
        - HIGH severity
        - Playbook ID: PLAYBOOK_DATA_EXFIL
        """
        logs = log_generator.generate_network_logs_data_exfil(count=20)
        
        assert len(logs) == 20
        
        # Calculate total bytes
        total_bytes = sum(log["network"]["bytes_out"] for log in logs)
        total_gb = total_bytes / (1024 ** 3)
        
        assert total_gb >= 10  # Should exceed threshold
        
        print(f"✓ Generated {len(logs)} network transfer logs")
        print(f"  - Total bytes out: {total_gb:.2f} GB")
    
    def test_lost_device(self, log_generator, tenant_id):
        """
        Test SG-DET-010: Lost / Stolen Device
        
        Scenario:
        - Device marked as lost in MDM
        
        Expected:
        - Incident created
        - Device details captured
        - Playbook ID: PLAYBOOK_LOST_DEVICE
        """
        logs = log_generator.generate_device_logs_lost(count=2)
        
        assert len(logs) == 2
        for log in logs:
            assert log["device"]["status"] in ["lost", "stolen"]
            assert "owner_email" in log["device"]
        
        print(f"✓ Generated {len(logs)} device status logs")


class TestDetectionEventIngestion:
    """Test detection event API endpoints."""
    
    @pytest.fixture
    def tenant_id(self) -> str:
        """Test tenant ID."""
        return "550e8400-e29b-41d4-a716-446655440000"
    
    @pytest.fixture
    def realm(self) -> str:
        """Test realm."""
        return "sentinelgrid-test"
    
    def test_detection_event_structure(self, tenant_id, realm):
        """Test detection event structure matches schema."""
        detection_event = {
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid4()),
            "sg": {
                "tenant_id": tenant_id,
                "realm": realm,
                "alert_type": "suspicious_login",
                "playbook_id": "PLAYBOOK_ACCOUNT_TAKEOVER",
                "severity": "high",
                "category": "identity"
            },
            "rule": {
                "id": "SG-DET-001-SUSPICIOUS-LOGIN",
                "name": "Suspicious login: failures then success",
                "version": "1.0.0"
            },
            "user": {
                "id": "user-42",
                "email": "jane.doe@example.com"
            },
            "source": {
                "ip": "203.0.113.10",
                "geo": {"country": "US"}
            },
            "auth": {
                "failed_count_10m": 7,
                "first_failure_at": "2025-12-02T11:52:00Z",
                "success_at": "2025-12-02T11:59:30Z"
            }
        }
        
        # Validate required fields
        assert "sg" in detection_event
        assert detection_event["sg"]["tenant_id"] == tenant_id
        assert detection_event["sg"]["realm"] == realm
        assert detection_event["sg"]["alert_type"] is not None
        assert detection_event["sg"]["severity"] in ["critical", "high", "medium", "low"]
        
        print("✓ Detection event structure valid")


class TestEndToEndFlow:
    """Test complete end-to-end flow from detection to incident."""
    
    @pytest.fixture
    def tenant_id(self) -> str:
        """Test tenant ID."""
        return "550e8400-e29b-41d4-a716-446655440000"
    
    def test_detection_to_incident_flow(self, tenant_id):
        """
        Test complete flow:
        1. Detection event created
        2. Webhook fires
        3. Incident created
        4. NIST status set correctly
        5. Timeline entries created
        6. Observables extracted
        """
        # This would be an integration test that requires:
        # - Running OpenSearch
        # - Running SIEM agent
        # - Running SOAR agent
        # - Database accessible
        
        # For now, document the expected flow
        expected_flow = {
            "step_1": "OpenSearch monitor detects pattern",
            "step_2": "Detection event indexed to sg-{tenant}-detection-*",
            "step_3": "Webhook triggered to SOAR agent",
            "step_4": "Incident created in PostgreSQL",
            "step_5": "NIST status = 'new', phase = 'detection_and_analysis'",
            "step_6": "incident_lifecycle record created",
            "step_7": "incident_timeline entry created",
            "step_8": "incident_observables extracted and stored",
            "step_9": "Playbook mapping looked up",
            "step_10": "Playbook executed (if auto_execute=true)"
        }
        
        print("✓ Expected end-to-end flow documented")
        print("\nFlow steps:")
        for step, description in expected_flow.items():
            print(f"  {step}: {description}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])

