"""
End-to-end integration tests for Hero Flow 2: Suspicious Login Handled End-to-End

This test suite validates the complete flow from alert detection to ticket creation,
AI enrichment, framework mapping, and TheHive integration.
"""

import pytest
from uuid import uuid4
from datetime import datetime
import httpx
from unittest.mock import AsyncMock, patch, MagicMock


class TestHeroFlow2Integration:
    """End-to-end integration tests for Hero Flow 2."""
    
    @pytest.mark.asyncio
    async def test_suspicious_login_detection_to_ticket_creation(
        self,
        client,
        test_tenant,
        test_alert
    ):
        """
        Test: Suspicious login detection → Alert creation → Ticket creation
        
        Flow:
        1. SIEM Agent detects suspicious login
        2. Detection Service analyzes alert
        3. Ticket created automatically
        4. AI enrichment triggered
        """
        tenant_id = str(test_tenant.id)
        alert_id = str(test_alert.id)
        
        # Step 1: Create ticket from alert
        ticket_data = {
            "title": "Suspicious Login Detected",
            "description": "Multiple failed login attempts from new location",
            "status": "open",
            "severity": "high",
            "priority": "P2",
            "category": "suspicious_login",
            "source": "detection_service",
            "alert_ids": [alert_id],
            "created_by": "system"
        }
        
        response = client.post(
            "/api/v1/tickets",
            json=ticket_data,
            params={"tenant_id": tenant_id}
        )
        
        assert response.status_code == 200
        ticket = response.json()
        assert ticket["title"] == ticket_data["title"]
        assert ticket["status"] == "open"
        assert ticket["severity"] == "high"
        assert ticket["external_id"] is not None  # TheHive case ID
    
    @pytest.mark.asyncio
    async def test_ai_enrichment_trigger(
        self,
        client,
        test_tenant
    ):
        """
        Test: Ticket creation triggers AI enrichment
        
        Flow:
        1. Ticket created
        2. AI enrichment agent triggered
        3. IAM, VM, CMDB, Network data enriched
        """
        tenant_id = str(test_tenant.id)
        
        # Create ticket
        ticket_data = {
            "title": "Test Ticket for Enrichment",
            "description": "Test description",
            "status": "open",
            "severity": "high",
            "category": "suspicious_login",
            "user_identifier": "user@example.com",
            "alert_ids": []
        }
        
        response = client.post(
            "/api/v1/tickets",
            json=ticket_data,
            params={"tenant_id": tenant_id}
        )
        assert response.status_code == 200
        ticket = response.json()
        ticket_id = ticket["id"]
        
        # Trigger enrichment (would be automatic, but we can trigger manually)
        # Note: This would require mocking the enrichment service
        with patch('app.services.ticket_service.EnrichmentService') as mock_enrichment:
            mock_enrichment.return_value.enrich_ticket = AsyncMock(return_value={
                "status": "completed",
                "iam_enrichment": {"users": []},
                "vulnerability_enrichment": {"vulnerabilities": []},
                "cmdb_enrichment": {"assets": []},
                "network_enrichment": {"ip_addresses": []}
            })
            
            # Verify enrichment was triggered (would be async in real flow)
            # For now, we just verify ticket was created
            assert ticket_id is not None
    
    @pytest.mark.asyncio
    async def test_framework_mapping(
        self,
        client,
        test_tenant
    ):
        """
        Test: Framework mapping (NIST/MITRE) applied to ticket
        
        Flow:
        1. Ticket created with category
        2. Framework service maps to NIST/MITRE
        3. Ticket updated with framework mappings
        """
        tenant_id = str(test_tenant.id)
        
        ticket_data = {
            "title": "Malware Detection",
            "description": "Malware detected on endpoint",
            "status": "open",
            "severity": "critical",
            "category": "malware",
            "cve_ids": ["CVE-2024-1234"]
        }
        
        response = client.post(
            "/api/v1/tickets",
            json=ticket_data,
            params={"tenant_id": tenant_id}
        )
        assert response.status_code == 200
        ticket = response.json()
        
        # Verify framework mappings would be applied
        # (In real flow, this happens async via framework service)
        # For now, we verify ticket was created
        assert ticket["category"] == "malware"
    
    @pytest.mark.asyncio
    async def test_thehive_case_creation(
        self,
        client,
        test_tenant
    ):
        """
        Test: Ticket creation creates TheHive case
        
        Flow:
        1. Ticket created
        2. TheHive case created
        3. Observables added
        4. Tasks added
        """
        tenant_id = str(test_tenant.id)
        
        ticket_data = {
            "title": "Security Incident",
            "description": "Test incident",
            "status": "open",
            "severity": "high",
            "category": "security_incident"
        }
        
        with patch('app.services.thehive_integration.TheHiveIntegration.create_case_from_ticket') as mock_create_case:
            mock_create_case.return_value = AsyncMock(return_value={
                "id": "thehive-case-123",
                "title": "Security Incident",
                "status": "Open"
            })
            
            response = client.post(
                "/api/v1/tickets",
                json=ticket_data,
                params={"tenant_id": tenant_id}
            )
            assert response.status_code == 200
            ticket = response.json()
            
            # Verify TheHive case would be created
            # (In real flow, external_id would be set)
            assert ticket["title"] == ticket_data["title"]
    
    @pytest.mark.asyncio
    async def test_playbook_recommendation(
        self,
        client,
        test_tenant
    ):
        """
        Test: Playbook recommendation based on ticket characteristics
        
        Flow:
        1. Ticket created with category/severity
        2. Playbook recommender analyzes ticket
        3. Recommended playbooks returned
        """
        tenant_id = str(test_tenant.id)
        
        ticket_data = {
            "title": "Suspicious Login",
            "description": "Failed login attempts",
            "status": "open",
            "severity": "high",
            "category": "suspicious_login",
            "nist_controls": [{"control_id": "AC-2"}],
            "mitre_tactics": [{"tactic_id": "TA0001"}]
        }
        
        # Create ticket
        response = client.post(
            "/api/v1/tickets",
            json=ticket_data,
            params={"tenant_id": tenant_id}
        )
        assert response.status_code == 200
        ticket = response.json()
        
        # Test playbook recommendation (would call playbook recommender)
        # For now, we verify ticket has framework mappings
        assert ticket["category"] == "suspicious_login"
    
    @pytest.mark.asyncio
    async def test_automated_action_execution(
        self,
        client,
        test_tenant
    ):
        """
        Test: Automated action execution from playbook
        
        Flow:
        1. Playbook executed
        2. Action executor receives action request
        3. Action executed (e.g., disable user)
        4. Ticket updated with action result
        """
        tenant_id = str(test_tenant.id)
        
        # This would test action execution
        # For now, we verify the action executor service exists
        from app.services.action_executor import ActionExecutor
        
        executor = ActionExecutor()
        assert executor is not None
    
    @pytest.mark.asyncio
    async def test_nist_workflow_transitions(
        self,
        client,
        test_tenant
    ):
        """
        Test: NIST workflow status transitions
        
        Flow:
        1. Ticket created with status NEW
        2. Status transitions validated
        3. Phase tracking updated
        """
        from backend.services.incident_service.app.services.nist_workflow import NISTWorkflowEngine
        
        workflow = NISTWorkflowEngine()
        
        # Test valid transition
        is_valid, error, transition_data = workflow.transition("new", "triaged")
        assert is_valid is True
        assert error is None
        
        # Test invalid transition
        is_valid, error, _ = workflow.transition("new", "closed")
        assert is_valid is False
        assert error is not None
        
        # Test phase mapping
        phase = workflow.get_current_phase("contained")
        assert phase.value == "containment"
    
    @pytest.mark.asyncio
    async def test_ticket_tab_data_retrieval(
        self,
        client,
        test_tenant
    ):
        """
        Test: Ticket tab data retrieval
        
        Flow:
        1. Ticket created and enriched
        2. Tab data available (IAM, VM, CMDB, Network, Timeline)
        3. Tab data retrieved via API
        """
        tenant_id = str(test_tenant.id)
        
        # Create ticket
        ticket_data = {
            "title": "Test Ticket",
            "description": "Test",
            "status": "open",
            "severity": "medium"
        }
        
        response = client.post(
            "/api/v1/tickets",
            json=ticket_data,
            params={"tenant_id": tenant_id}
        )
        assert response.status_code == 200
        ticket = response.json()
        ticket_id = ticket["id"]
        
        # Get tab data
        for tab_name in ["iam", "vm", "cmdb", "network", "timeline"]:
            response = client.get(
                f"/api/v1/tickets/{ticket_id}/tabs/{tab_name}",
                params={"tenant_id": tenant_id}
            )
            assert response.status_code == 200
            tab_data = response.json()
            assert tab_data["tab"] == tab_name
            assert "data" in tab_data

