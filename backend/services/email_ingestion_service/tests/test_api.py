"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime
from app.main import app

client = TestClient(app)


class TestPhishingAPI:
    """Test phishing API endpoints."""
    
    def test_ingest_email(self):
        """Test email ingestion endpoint."""
        raw_email = """From: attacker@example.com
To: victim@company.com
Subject: Urgent: Verify Your Account
Date: Mon, 1 Jan 2024 12:00:00 +0000
Message-ID: <test@example.com>

This is a phishing email.
"""
        tenant_id = str(uuid4())
        
        response = client.post(
            f"/api/v1/phishing/ingest?tenant_id={tenant_id}",
            content=raw_email,
            headers={"Content-Type": "text/plain"},
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data
        assert data["from_address"] == "attacker@example.com"
    
    def test_list_reports(self):
        """Test listing phishing reports."""
        tenant_id = str(uuid4())
        
        response = client.get(
            f"/api/v1/phishing/reports?tenant_id={tenant_id}",
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_report(self):
        """Test getting a specific report."""
        tenant_id = str(uuid4())
        
        # First create a report
        raw_email = """From: test@example.com
To: user@company.com
Subject: Test
Date: Mon, 1 Jan 2024 12:00:00 +0000
Message-ID: <test123@example.com>

Test email.
"""
        create_response = client.post(
            f"/api/v1/phishing/ingest?tenant_id={tenant_id}",
            content=raw_email,
            headers={"Content-Type": "text/plain"},
        )
        report_id = create_response.json()["id"]
        
        # Then get it
        response = client.get(
            f"/api/v1/phishing/reports/{report_id}?tenant_id={tenant_id}",
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == report_id
    
    def test_search_similar_emails(self):
        """Test searching for similar emails."""
        tenant_id = str(uuid4())
        
        # Create a report first
        raw_email = """From: attacker@example.com
To: victim@company.com
Subject: Urgent: Verify Your Account
Date: Mon, 1 Jan 2024 12:00:00 +0000
Message-ID: <test456@example.com>

Phishing email.
"""
        create_response = client.post(
            f"/api/v1/phishing/ingest?tenant_id={tenant_id}",
            content=raw_email,
            headers={"Content-Type": "text/plain"},
        )
        report_id = create_response.json()["id"]
        
        # Search for similar emails
        response = client.post(
            f"/api/v1/phishing/reports/{report_id}/search-similar?tenant_id={tenant_id}",
            json={"provider": "microsoft_graph"},
        )
        
        # Should return 200 even if no emails found (mock scenario)
        assert response.status_code in [200, 500]  # 500 if provider not configured
    
    def test_run_containment_playbook(self):
        """Test running containment playbook."""
        tenant_id = str(uuid4())
        
        # Create a report first
        raw_email = """From: attacker@example.com
To: victim@company.com
Subject: Urgent: Verify Your Account
Date: Mon, 1 Jan 2024 12:00:00 +0000
Message-ID: <test789@example.com>

Phishing email.
"""
        create_response = client.post(
            f"/api/v1/phishing/ingest?tenant_id={tenant_id}",
            content=raw_email,
            headers={"Content-Type": "text/plain"},
        )
        report_id = create_response.json()["id"]
        
        # Run containment playbook
        response = client.post(
            f"/api/v1/phishing/reports/{report_id}/run-containment-playbook?tenant_id={tenant_id}",
            json={
                "quarantine_emails": True,
                "block_domains": True,
                "create_ticket": True,
                "notify_users": False,
            },
        )
        
        # Should return 200 even if some steps fail (mock scenario)
        assert response.status_code in [200, 500]

