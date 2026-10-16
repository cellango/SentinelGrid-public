"""Pytest fixtures for Hero Flow 1 tests."""

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def test_tenant_id():
    """Generate a test tenant ID."""
    return str(uuid4())


@pytest.fixture
def test_tenant_data(test_tenant_id):
    """Create test tenant data."""
    return {
        "tenant_id": test_tenant_id,
        "name": "Test Company",
        "slug": "test-company",
        "status": "active",
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def mock_identity_events(test_tenant_id):
    """Generate mock identity events."""
    return [
        {
            "id": str(uuid4()),
            "tenant_id": test_tenant_id,
            "event_type": "authentication",
            "source": "google_workspace",
            "action": "login_success",
            "user": {"email": "user1@testcompany.com"},
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "id": str(uuid4()),
            "tenant_id": test_tenant_id,
            "event_type": "authentication",
            "source": "google_workspace",
            "action": "login_failed",
            "user": {"email": "user2@testcompany.com"},
            "timestamp": datetime.utcnow().isoformat()
        }
    ]


@pytest.fixture
def mock_cloud_events(test_tenant_id):
    """Generate mock cloud events."""
    return [
        {
            "id": str(uuid4()),
            "tenant_id": test_tenant_id,
            "event_type": "cloud_api_call",
            "source": "aws_cloudtrail",
            "action": "CreateBucket",
            "user": {"arn": "arn:aws:iam::123456789012:user/admin"},
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "id": str(uuid4()),
            "tenant_id": test_tenant_id,
            "event_type": "cloud_api_call",
            "source": "aws_cloudtrail",
            "action": "PutBucketPolicy",
            "user": {"arn": "arn:aws:iam::123456789012:user/admin"},
            "timestamp": datetime.utcnow().isoformat()
        }
    ]


@pytest.fixture
def mock_alerts(test_tenant_id):
    """Generate mock alerts."""
    return [
        {
            "id": str(uuid4()),
            "tenant_id": test_tenant_id,
            "severity": "high",
            "status": "open",
            "title": "S3 Bucket Made Public",
            "description": "Bucket 'customer-data' was made publicly accessible",
            "source": "detection_rule",
            "detection_rule_id": "rule-suspicious-cloud",
            "timestamp": datetime.utcnow().isoformat()
        },
        {
            "id": str(uuid4()),
            "tenant_id": test_tenant_id,
            "severity": "medium",
            "status": "open",
            "title": "Multiple Failed Login Attempts",
            "description": "User alice@testcompany.com had 7 failed login attempts",
            "source": "detection_rule",
            "detection_rule_id": "rule-failed-logins",
            "user_id": "alice@testcompany.com",
            "timestamp": datetime.utcnow().isoformat()
        }
    ]


@pytest.fixture
def mock_security_snapshot(test_tenant_id):
    """Generate mock security snapshot."""
    return {
        "tenant_id": test_tenant_id,
        "generated_at": datetime.utcnow().isoformat(),
        "summary": {
            "events_count": 2515,
            "alerts_count": 3,
            "users_active": 38,
            "cloud_resources": 45
        },
        "top_findings": [
            {
                "severity": "high",
                "title": "S3 Bucket Made Public",
                "description": "Bucket 'customer-data' is publicly accessible",
                "recommendation": "Restrict bucket access to specific IAM roles"
            }
        ],
        "ai_analysis": {
            "summary": "Your organization shows good overall security posture...",
            "risk_score": 6.5,
            "recommended_actions": [
                "Secure the public S3 bucket",
                "Review failed login attempts"
            ]
        }
    }


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client for service calls."""
    return AsyncMock()


@pytest.fixture
def service_urls():
    """Service URLs for testing."""
    return {
        "siem_agent": "http://siem_agent:8000",
        "iam_agent": "http://iam_agent:8000",
        "orchestrator": "http://orchestrator:8000",
        "internal_token": "internal-service-token-change-in-production"
    }

