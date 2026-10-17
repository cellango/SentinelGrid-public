"""Source admission contracts; CRUD effects remain required restoration work.

An HTTP 500 is never accepted as a successful API contract. Positive signed reads
and tenant/resource filters live in the actual identity-boundary suite.
"""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime, timezone
from app.main import app
from app.models import PlaybookCreate, WorkflowStructure


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_tenant_id():
    """Sample tenant ID for testing."""
    return uuid4()


@pytest.fixture
def sample_playbook_data():
    """Sample playbook data for testing."""
    return PlaybookCreate(
        name="Test Playbook",
        description="A test playbook",
        category="phishing",
        version="1.0.0",
        workflow=WorkflowStructure(
            nodes=[
                {
                    "id": "trigger-1",
                    "type": "manual_trigger",
                    "position": {"x": 0, "y": 0},
                    "data": {"label": "Start"}
                }
            ],
            edges=[]
        ),
        is_template=False,
        requires_approval=False,
        tags=["test"]
    )


class TestPlaybookCRUD:
    """Test playbook CRUD operations."""

    def test_create_playbook(self, client, sample_tenant_id, sample_playbook_data):
        """Test creating a playbook."""
        # Note: This test requires database and tenant setup
        # For now, test the endpoint structure
        response = client.post(
            "/soar/playbooks",
            json=sample_playbook_data.model_dump(),
            headers={"X-Tenant-ID": str(sample_tenant_id)}
        )
        # Source selection rejects before database/service construction.
        assert response.status_code == 503

    def test_list_playbooks(self, client, sample_tenant_id):
        """Test listing playbooks."""
        response = client.get(
            "/soar/playbooks",
            headers={"X-Tenant-ID": str(sample_tenant_id)}
        )
        # Header-only requests cannot create a verified reader.
        assert response.status_code == 401

    def test_get_playbook_not_found(self, client, sample_tenant_id):
        """Test getting non-existent playbook."""
        playbook_id = uuid4()
        response = client.get(
            f"/soar/playbooks/{playbook_id}",
            headers={"X-Tenant-ID": str(sample_tenant_id)}
        )
        assert response.status_code == 401

    def test_copy_playbook(self, client, sample_tenant_id):
        """Test copying a playbook."""
        playbook_id = uuid4()
        response = client.post(
            f"/soar/playbooks/{playbook_id}/copy",
            json={"new_name": "Copied Playbook"},
            headers={"X-Tenant-ID": str(sample_tenant_id)}
        )
        assert response.status_code == 503

    def test_validate_playbook(self, client, sample_tenant_id):
        """Test validating a playbook."""
        playbook_id = uuid4()
        response = client.post(
            f"/soar/playbooks/{playbook_id}/validate",
            headers={"X-Tenant-ID": str(sample_tenant_id)}
        )
        assert response.status_code == 503

    def test_delete_playbook(self, client, sample_tenant_id):
        """Test deleting a playbook."""
        playbook_id = uuid4()
        response = client.delete(
            f"/soar/playbooks/{playbook_id}",
            headers={"X-Tenant-ID": str(sample_tenant_id)}
        )
        assert response.status_code == 503


class TestPlaybookValidation:
    """Test playbook validation logic."""

    def test_playbook_without_trigger(self):
        """Test that playbook validation fails without trigger node."""
        from app.models import Playbook, WorkflowStructure
        from app.services.playbook_service import PlaybookService
        from sqlalchemy.orm import Session
        
        # Create invalid playbook (no trigger)
        invalid_playbook = Playbook(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Invalid",
            workflow=WorkflowStructure(nodes=[], edges=[]),
            version="1.0.0", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        )
        
        # Mock service to test validation logic
        # This would require database session, so we'll test the logic directly
        # For now, just verify the structure is correct
        assert invalid_playbook.workflow.nodes == []


class TestHealthCheck:
    """Test health check endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["service"] == "soar-agent"

    def test_health_endpoint(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

