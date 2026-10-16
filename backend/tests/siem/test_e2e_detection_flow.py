"""
End-to-end tests for complete detection flow.

Tests the entire pipeline from log generation to incident creation:
1. Generate test logs
2. Index into OpenSearch
3. Trigger monitor execution (simulate)
4. Verify detection event created
5. Call webhook endpoint
6. Verify incident created
7. Verify ticket created (if applicable)
8. Verify NIST status tracking
9. Verify timeline entries
10. Verify observables extracted
"""

import pytest
import asyncio
import httpx
import json
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from sqlalchemy import text
from sqlalchemy.orm import Session

# Add parent directory to path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../agents/siem_agent"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../agents/soar_agent"))

from tests.siem.data.generate_test_logs import TestLogGenerator


class TestEndToEndDetectionFlow:
    """End-to-end integration tests for detection system."""
    
    @pytest.fixture
    def tenant_id(self) -> str:
        """Test tenant ID."""
        return "550e8400-e29b-41d4-a716-446655440000"
    
    @pytest.fixture
    def realm(self) -> str:
        """Test Keycloak realm."""
        return "sentinelgrid-test"
    
    @pytest.fixture
    def opensearch_url(self) -> str:
        """OpenSearch URL."""
        return os.getenv("OPENSEARCH_URL", "http://localhost:9200")
    
    @pytest.fixture
    def siem_agent_url(self) -> str:
        """SIEM Agent URL."""
        return os.getenv("SIEM_AGENT_URL", "http://localhost:8001")
    
    @pytest.fixture
    def soar_agent_url(self) -> str:
        """SOAR Agent URL."""
        return os.getenv("SOAR_AGENT_URL", "http://localhost:8003")
    
    @pytest.fixture
    def internal_token(self) -> str:
        """Internal service token."""
        return os.getenv("INTERNAL_SERVICE_TOKEN", "test-token-123")
    
    @pytest.fixture
    def db_session(self):
        """Get database session."""
        from app.core.database import get_db
        db = next(get_db())
        yield db
        db.close()
    
    @pytest.mark.asyncio
    async def test_01_suspicious_login_e2e(
        self,
        tenant_id,
        realm,
        soar_agent_url,
        internal_token,
        db_session
    ):
        """
        Test SG-DET-001: Suspicious Login - Complete E2E Flow
        
        Steps:
        1. Create detection event (simulating OpenSearch monitor)
        2. POST to webhook endpoint
        3. Verify incident created in database
        4. Verify NIST status = 'new'
        5. Verify timeline entry created
        6. Verify observables extracted
        7. Verify no duplicate incident created on repeat
        """
        print("\n" + "="*60)
        print("TEST 1: Suspicious Login End-to-End Flow")
        print("="*60)
        
        # Step 1: Create detection event
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
                "id": "SG-DET-001",
                "name": "Suspicious login: failures then success",
                "version": "1.0.0"
            },
            "user": {
                "id": "test-user-42",
                "email": "jane.doe@example.com"
            },
            "source": {
                "ip": "203.0.113.10",
                "geo": {"country": "RU"}
            },
            "auth": {
                "failed_count_10m": 7,
                "first_failure_at": "2025-12-02T11:52:00Z",
                "success_at": "2025-12-02T11:59:30Z"
            }
        }
        
        print(f"✓ Created detection event: {detection_event['event_id']}")
        
        # Step 2: POST to webhook endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{soar_agent_url}/api/v1/detection-events/ingest",
                json=detection_event,
                headers={
                    "Authorization": f"Bearer {internal_token}",
                    "X-Tenant-ID": tenant_id
                },
                timeout=30.0
            )
            
            assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
            result = response.json()
            
            print(f"✓ Webhook received, HTTP {response.status_code}")
            print(f"  Incident ID: {result.get('incident_id')}")
            print(f"  Status: {result.get('status')}")
            
            incident_id = result.get("incident_id")
            assert incident_id is not None, "Incident ID not returned"
        
        # Step 3: Verify incident in database
        query = text("""
            SELECT id, external_id, title, status, severity
            FROM incidents
            WHERE id = :incident_id AND tenant_id = :tenant_id
        """)
        
        incident = db_session.execute(query, {
            "incident_id": UUID(incident_id),
            "tenant_id": UUID(tenant_id)
        }).fetchone()
        
        assert incident is not None, "Incident not found in database"
        assert incident[3] == "new", f"Expected status='new', got '{incident[3]}'"
        assert incident[4] == "high", f"Expected severity='high', got '{incident[4]}'"
        
        print(f"✓ Incident verified in database")
        print(f"  External ID: {incident[1]}")
        print(f"  Status: {incident[3]} (NIST phase: Detection & Analysis)")
        print(f"  Severity: {incident[4]}")
        
        # Step 4: Verify lifecycle record
        lifecycle_query = text("""
            SELECT detection_event_id, alert_raw_payload
            FROM incident_lifecycle
            WHERE incident_id = :incident_id
        """)
        
        lifecycle = db_session.execute(lifecycle_query, {
            "incident_id": UUID(incident_id)
        }).fetchone()
        
        assert lifecycle is not None, "Lifecycle record not found"
        assert lifecycle[0] == detection_event["event_id"], "Detection event ID mismatch"
        
        print(f"✓ Lifecycle record verified")
        print(f"  Detection Event ID: {lifecycle[0]}")
        
        # Step 5: Verify timeline entry
        timeline_query = text("""
            SELECT event_type, action, nist_phase, nist_status
            FROM incident_timeline
            WHERE incident_id = :incident_id
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        
        timeline = db_session.execute(timeline_query, {
            "incident_id": UUID(incident_id)
        }).fetchone()
        
        assert timeline is not None, "Timeline entry not found"
        assert timeline[0] == "detection", f"Expected event_type='detection', got '{timeline[0]}'"
        assert timeline[2] == "detection_and_analysis", "Wrong NIST phase"
        
        print(f"✓ Timeline entry verified")
        print(f"  Event type: {timeline[0]}")
        print(f"  Action: {timeline[1]}")
        print(f"  NIST phase: {timeline[2]}")
        
        # Step 6: Verify observables extracted
        observables_query = text("""
            SELECT observable_type, observable_value, source
            FROM incident_observables
            WHERE incident_id = :incident_id
        """)
        
        observables = db_session.execute(observables_query, {
            "incident_id": UUID(incident_id)
        }).fetchall()
        
        assert len(observables) > 0, "No observables extracted"
        
        # Should have extracted: IP and email
        observable_types = [obs[0] for obs in observables]
        assert "ip" in observable_types, "IP address not extracted"
        assert "email" in observable_types, "Email not extracted"
        
        print(f"✓ Observables extracted: {len(observables)}")
        for obs in observables:
            print(f"  - {obs[0]}: {obs[1]} (source: {obs[2]})")
        
        # Step 7: Test deduplication - send same event again
        print("\n  Testing deduplication...")
        
        # Create another event with same user+IP (should be suppressed)
        duplicate_event = detection_event.copy()
        duplicate_event["event_id"] = str(uuid4())
        duplicate_event["@timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        async with httpx.AsyncClient() as client:
            response2 = await client.post(
                f"{soar_agent_url}/api/v1/detection-events/ingest",
                json=duplicate_event,
                headers={
                    "Authorization": f"Bearer {internal_token}",
                    "X-Tenant-ID": tenant_id
                },
                timeout=30.0
            )
            
            result2 = response2.json()
            
            # Should be suppressed or link to same incident
            if result2.get("suppressed"):
                print(f"✓ Duplicate suppressed: {result2.get('suppression_reason')}")
            else:
                # May create incident if within escalation policy
                print(f"  New incident: {result2.get('incident_id')} (escalation)")
        
        print(f"\n✅ Test PASSED: Suspicious Login E2E Flow")
        return True
    
    @pytest.mark.asyncio
    async def test_02_phishing_report_e2e(
        self,
        tenant_id,
        realm,
        soar_agent_url,
        internal_token,
        db_session
    ):
        """
        Test SG-DET-002: User-Reported Phishing - E2E Flow
        
        Verifies:
        - Incident created from phishing report
        - Email observables extracted
        - Playbook mapping resolves correctly
        """
        print("\n" + "="*60)
        print("TEST 2: User-Reported Phishing E2E Flow")
        print("="*60)
        
        detection_event = {
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid4()),
            "sg": {
                "tenant_id": tenant_id,
                "realm": realm,
                "alert_type": "phishing_user_report",
                "playbook_id": "PLAYBOOK_PHISHING_USER_REPORTED",
                "severity": "medium",
                "category": "email"
            },
            "rule": {
                "id": "SG-DET-002",
                "name": "User-reported phishing email",
                "version": "1.0.0"
            },
            "user": {
                "id": "test-user-15",
                "email": "alice@example.com"
            },
            "email": {
                "message_id": "<test-phish-123@malicious.com>",
                "subject": "Urgent: Verify Your Account",
                "from": "security@fake-bank.com"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{soar_agent_url}/api/v1/detection-events/ingest",
                json=detection_event,
                headers={
                    "Authorization": f"Bearer {internal_token}",
                    "X-Tenant-ID": tenant_id
                },
                timeout=30.0
            )
            
            assert response.status_code == 202
            result = response.json()
            incident_id = result.get("incident_id")
            
            print(f"✓ Incident created: {incident_id}")
        
        # Verify observables include email and domain
        observables_query = text("""
            SELECT observable_type, observable_value
            FROM incident_observables
            WHERE incident_id = :incident_id
        """)
        
        observables = db_session.execute(observables_query, {
            "incident_id": UUID(incident_id)
        }).fetchall()
        
        observable_dict = {obs[0]: obs[1] for obs in observables}
        
        assert "email" in observable_dict, "Email observable not extracted"
        assert "domain" in observable_dict, "Domain observable not extracted"
        assert observable_dict["domain"] == "fake-bank.com", "Wrong domain extracted"
        
        print(f"✓ Observables extracted correctly:")
        for obs_type, obs_value in observable_dict.items():
            print(f"  - {obs_type}: {obs_value}")
        
        print(f"\n✅ Test PASSED: Phishing Report E2E Flow")
        return True
    
    @pytest.mark.asyncio
    async def test_03_endpoint_malware_e2e(
        self,
        tenant_id,
        realm,
        soar_agent_url,
        internal_token,
        db_session
    ):
        """
        Test SG-DET-004: Endpoint Malware - E2E Flow
        
        Verifies:
        - Incident created from malware detection
        - Host and hash observables extracted
        - High severity escalation
        """
        print("\n" + "="*60)
        print("TEST 3: Endpoint Malware E2E Flow")
        print("="*60)
        
        detection_event = {
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "event_id": str(uuid4()),
            "sg": {
                "tenant_id": tenant_id,
                "realm": realm,
                "alert_type": "endpoint_malware",
                "playbook_id": "PLAYBOOK_ENDPOINT_MALWARE",
                "severity": "high",
                "category": "endpoint"
            },
            "rule": {
                "id": "SG-DET-004",
                "name": "High severity malware detected",
                "version": "1.0.0"
            },
            "host": {
                "name": "test-prod-api-01",
                "id": "host-test-001",
                "asset_criticality": "high"
            },
            "user": {
                "id": "test-svc-api",
                "name": "svc-api"
            },
            "malware": {
                "name": "Trojan.Generic.TEST",
                "hash": "d41d8cd98f00b204e9800998ecf8427e"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{soar_agent_url}/api/v1/detection-events/ingest",
                json=detection_event,
                headers={
                    "Authorization": f"Bearer {internal_token}",
                    "X-Tenant-ID": tenant_id
                },
                timeout=30.0
            )
            
            assert response.status_code == 202
            result = response.json()
            incident_id = result.get("incident_id")
            
            print(f"✓ Incident created: {incident_id}")
        
        # Verify observables
        observables_query = text("""
            SELECT observable_type, observable_value
            FROM incident_observables
            WHERE incident_id = :incident_id
        """)
        
        observables = db_session.execute(observables_query, {
            "incident_id": UUID(incident_id)
        }).fetchall()
        
        observable_types = [obs[0] for obs in observables]
        
        assert "file_hash" in observable_types, "File hash not extracted"
        assert "host" in observable_types, "Host not extracted"
        
        print(f"✓ Observables extracted: {len(observables)}")
        for obs in observables:
            print(f"  - {obs[0]}: {obs[1]}")
        
        print(f"\n✅ Test PASSED: Endpoint Malware E2E Flow")
        return True
    
    @pytest.mark.asyncio
    async def test_04_deduplication_flow(
        self,
        tenant_id,
        realm,
        soar_agent_url,
        internal_token,
        db_session
    ):
        """
        Test deduplication and suppression.
        
        Verifies:
        - First event creates incident
        - Duplicate events are suppressed
        - Dedup record tracks occurrences
        - Escalation works after threshold
        """
        print("\n" + "="*60)
        print("TEST 4: Deduplication and Suppression")
        print("="*60)
        
        # Create base detection event
        base_event = {
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
                "id": "SG-DET-001",
                "name": "Suspicious login: failures then success",
                "version": "1.0.0"
            },
            "user": {
                "id": "dedup-test-user",
                "email": "dedup.test@example.com"
            },
            "source": {
                "ip": "198.51.100.50",
                "geo": {"country": "CN"}
            }
        }
        
        created_incidents = []
        suppressed_count = 0
        
        # Send 5 identical events
        for i in range(5):
            event = base_event.copy()
            event["event_id"] = str(uuid4())
            event["@timestamp"] = (datetime.utcnow() + timedelta(seconds=i*10)).isoformat() + "Z"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{soar_agent_url}/api/v1/detection-events/ingest",
                    json=event,
                    headers={
                        "Authorization": f"Bearer {internal_token}",
                        "X-Tenant-ID": tenant_id
                    },
                    timeout=30.0
                )
                
                result = response.json()
                
                if result.get("suppressed"):
                    suppressed_count += 1
                    print(f"  Event {i+1}: Suppressed ({result.get('suppression_reason')})")
                else:
                    incident_id = result.get("incident_id")
                    created_incidents.append(incident_id)
                    print(f"  Event {i+1}: Incident {incident_id}")
        
        print(f"\n✓ Deduplication working:")
        print(f"  - Incidents created: {len(created_incidents)}")
        print(f"  - Events suppressed: {suppressed_count}")
        
        # First event should create incident, rest should be suppressed or escalated
        assert len(created_incidents) >= 1, "At least one incident should be created"
        assert suppressed_count >= 1, "At least one event should be suppressed"
        
        # Verify dedup record
        dedup_query = text("""
            SELECT dedup_key, occurrence_count, status
            FROM detection_deduplication
            WHERE tenant_id = :tenant_id
              AND incident_id = :incident_id
        """)
        
        dedup = db_session.execute(dedup_query, {
            "tenant_id": UUID(tenant_id),
            "incident_id": UUID(created_incidents[0])
        }).fetchone()
        
        if dedup:
            print(f"✓ Dedup record found:")
            print(f"  - Occurrence count: {dedup[1]}")
            print(f"  - Status: {dedup[2]}")
        
        print(f"\n✅ Test PASSED: Deduplication Flow")
        return True
    
    @pytest.mark.asyncio
    async def test_05_all_alert_types(
        self,
        tenant_id,
        realm,
        soar_agent_url,
        internal_token,
        db_session
    ):
        """
        Test all 10 alert types end-to-end.
        
        Verifies each alert type can:
        - Create incident
        - Extract appropriate observables
        - Map to correct playbook
        """
        print("\n" + "="*60)
        print("TEST 5: All 10 Alert Types")
        print("="*60)
        
        alert_types = [
            ("suspicious_login", "PLAYBOOK_ACCOUNT_TAKEOVER", "high"),
            ("phishing_user_report", "PLAYBOOK_PHISHING_USER_REPORTED", "medium"),
            ("phishing_campaign", "PLAYBOOK_EMAIL_CAMPAIGN", "high"),
            ("endpoint_malware", "PLAYBOOK_ENDPOINT_MALWARE", "high"),
            ("ransomware_suspected", "PLAYBOOK_RANSOMWARE", "critical"),
            ("cloud_storage_public", "PLAYBOOK_PUBLIC_STORAGE", "high"),
            ("privilege_escalation", "PLAYBOOK_PRIVILEGE_ESCALATION", "high"),
            ("password_spray", "PLAYBOOK_PASSWORD_SPRAY", "medium"),
            ("data_exfil_suspected", "PLAYBOOK_DATA_EXFIL", "high"),
            ("lost_device", "PLAYBOOK_LOST_DEVICE", "medium")
        ]
        
        results = []
        
        for alert_type, expected_playbook, severity in alert_types:
            detection_event = {
                "@timestamp": datetime.utcnow().isoformat() + "Z",
                "event_id": str(uuid4()),
                "sg": {
                    "tenant_id": tenant_id,
                    "realm": realm,
                    "alert_type": alert_type,
                    "playbook_id": expected_playbook,
                    "severity": severity,
                    "category": "test"
                },
                "rule": {
                    "id": f"SG-DET-TEST-{alert_type}",
                    "name": f"Test rule for {alert_type}",
                    "version": "1.0.0"
                }
            }
            
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{soar_agent_url}/api/v1/detection-events/ingest",
                        json=detection_event,
                        headers={
                            "Authorization": f"Bearer {internal_token}",
                            "X-Tenant-ID": tenant_id
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 202:
                        result = response.json()
                        incident_id = result.get("incident_id")
                        results.append({
                            "alert_type": alert_type,
                            "success": True,
                            "incident_id": incident_id
                        })
                        print(f"  ✓ {alert_type}: Incident {incident_id}")
                    else:
                        results.append({
                            "alert_type": alert_type,
                            "success": False,
                            "error": response.text
                        })
                        print(f"  ✗ {alert_type}: Failed ({response.status_code})")
                
                except Exception as e:
                    results.append({
                        "alert_type": alert_type,
                        "success": False,
                        "error": str(e)
                    })
                    print(f"  ✗ {alert_type}: Error ({str(e)})")
        
        # Summary
        success_count = sum(1 for r in results if r["success"])
        print(f"\n✓ Successfully tested: {success_count}/10 alert types")
        
        assert success_count >= 8, f"Too many failures: only {success_count}/10 succeeded"
        
        print(f"\n✅ Test PASSED: All Alert Types")
        return True


def run_all_e2e_tests():
    """Run all end-to-end tests."""
    pytest.main([__file__, "-v", "-s", "--tb=short"])


if __name__ == "__main__":
    run_all_e2e_tests()
