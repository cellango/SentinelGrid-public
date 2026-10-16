"""Test suite for tenant isolation in Playbook API."""

import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.models import PlaybookCreate
from app.database import Base, PlaybookDB as PlaybookORM
from app.core.database import get_db, engine, SessionLocal
from app.core.config import settings


@pytest.fixture
def client():
    """Create test client with database override."""
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def tenant_1_id():
    """Tenant 1 ID for testing."""
    return str(uuid4())


@pytest.fixture
def tenant_2_id():
    """Tenant 2 ID for testing."""
    return str(uuid4())


@pytest.fixture
def setup_database():
    """Set up database tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def tenant_1_playbooks(client, tenant_1_id, setup_database):
    """Create playbooks for tenant 1."""
    playbooks = []
    for i in range(3):
        response = client.post(
            "/soar/playbooks",
            json={
                "name": f"Tenant 1 Playbook {i+1}",
                "description": f"Playbook {i+1} for tenant 1",
                "category": "phishing",
                "version": "1.0.0",
                "workflow": {"nodes": [], "edges": []},
                "is_template": False,
                "requires_approval": False,
                "tags": [],
            },
            headers={"X-Tenant-ID": tenant_1_id}
        )
        if response.status_code == 201:
            playbooks.append(response.json())
    return playbooks


@pytest.fixture
def tenant_2_playbooks(client, tenant_2_id, setup_database):
    """Create playbooks for tenant 2."""
    playbooks = []
    for i in range(2):
        response = client.post(
            "/soar/playbooks",
            json={
                "name": f"Tenant 2 Playbook {i+1}",
                "description": f"Playbook {i+1} for tenant 2",
                "category": "malware",
                "version": "1.0.0",
                "workflow": {"nodes": [], "edges": []},
                "is_template": False,
                "requires_approval": False,
                "tags": [],
            },
            headers={"X-Tenant-ID": tenant_2_id}
        )
        if response.status_code == 201:
            playbooks.append(response.json())
    return playbooks


class TestTenantIsolation:
    """Test tenant isolation in playbook operations."""

    def test_list_playbooks_tenant_isolation(
        self, client, tenant_1_id, tenant_2_id, tenant_1_playbooks, tenant_2_playbooks
    ):
        """Test that tenants only see their own playbooks."""
        # Tenant 1 should only see their 3 playbooks
        response = client.get(
            "/soar/playbooks",
            headers={"X-Tenant-ID": tenant_1_id}
        )
        assert response.status_code == 200
        playbooks = response.json()
        assert len(playbooks) == 3
        assert all(pb["tenant_id"] == tenant_1_id for pb in playbooks)
        assert all("Tenant 1" in pb["name"] for pb in playbooks)

        # Tenant 2 should only see their 2 playbooks
        response = client.get(
            "/soar/playbooks",
            headers={"X-Tenant-ID": tenant_2_id}
        )
        assert response.status_code == 200
        playbooks = response.json()
        assert len(playbooks) == 2
        assert all(pb["tenant_id"] == tenant_2_id for pb in playbooks)
        assert all("Tenant 2" in pb["name"] for pb in playbooks)

    def test_get_playbook_cross_tenant_access_denied(
        self, client, tenant_1_id, tenant_2_id, tenant_1_playbooks, tenant_2_playbooks
    ):
        """Test that tenants cannot access other tenants' playbooks."""
        # Get tenant 1's playbook ID
        tenant_1_playbook_id = tenant_1_playbooks[0]["id"]

        # Tenant 2 tries to access tenant 1's playbook - should fail
        response = client.get(
            f"/soar/playbooks/{tenant_1_playbook_id}",
            headers={"X-Tenant-ID": tenant_2_id}
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

        # Tenant 1 should be able to access their own playbook
        response = client.get(
            f"/soar/playbooks/{tenant_1_playbook_id}",
            headers={"X-Tenant-ID": tenant_1_id}
        )
        assert response.status_code == 200
        assert response.json()["id"] == tenant_1_playbook_id

    def test_update_playbook_cross_tenant_access_denied(
        self, client, tenant_1_id, tenant_2_id, tenant_1_playbooks, tenant_2_playbooks
    ):
        """Test that tenants cannot update other tenants' playbooks."""
        tenant_1_playbook_id = tenant_1_playbooks[0]["id"]

        # Tenant 2 tries to update tenant 1's playbook - should fail
        response = client.put(
            f"/soar/playbooks/{tenant_1_playbook_id}",
            json={
                "name": "Hacked Playbook",
                "description": "Unauthorized update",
                "workflow": {"nodes": [], "edges": []},
            },
            headers={"X-Tenant-ID": tenant_2_id}
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

        # Tenant 1 should be able to update their own playbook
        response = client.put(
            f"/soar/playbooks/{tenant_1_playbook_id}",
            json={
                "name": "Updated Playbook Name",
                "description": "Updated description",
                "workflow": {"nodes": [], "edges": []},
            },
            headers={"X-Tenant-ID": tenant_1_id}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Playbook Name"

    def test_delete_playbook_cross_tenant_access_denied(
        self, client, tenant_1_id, tenant_2_id, tenant_1_playbooks, tenant_2_playbooks
    ):
        """Test that tenants cannot delete other tenants' playbooks."""
        tenant_1_playbook_id = tenant_1_playbooks[0]["id"]

        # Tenant 2 tries to delete tenant 1's playbook - should fail
        response = client.delete(
            f"/soar/playbooks/{tenant_1_playbook_id}",
            headers={"X-Tenant-ID": tenant_2_id}
        )
        assert response.status_code == 404

        # Verify playbook still exists
        response = client.get(
            f"/soar/playbooks/{tenant_1_playbook_id}",
            headers={"X-Tenant-ID": tenant_1_id}
        )
        assert response.status_code == 200

        # Tenant 1 should be able to delete their own playbook
        response = client.delete(
            f"/soar/playbooks/{tenant_1_playbook_id}",
            headers={"X-Tenant-ID": tenant_1_id}
        )
        assert response.status_code == 204

        # Verify playbook is deleted
        response = client.get(
            f"/soar/playbooks/{tenant_1_playbook_id}",
            headers={"X-Tenant-ID": tenant_1_id}
        )
        assert response.status_code == 404

    def test_copy_playbook_cross_tenant_access_denied(
        self, client, tenant_1_id, tenant_2_id, tenant_1_playbooks, tenant_2_playbooks
    ):
        """Test that tenants cannot copy other tenants' playbooks."""
        tenant_1_playbook_id = tenant_1_playbooks[0]["id"]

        # Tenant 2 tries to copy tenant 1's playbook - should fail
        response = client.post(
            f"/soar/playbooks/{tenant_1_playbook_id}/copy",
            json={"new_name": "Stolen Playbook"},
            headers={"X-Tenant-ID": tenant_2_id}
        )
        assert response.status_code == 404

        # Tenant 1 should be able to copy their own playbook
        response = client.post(
            f"/soar/playbooks/{tenant_1_playbook_id}/copy",
            json={"new_name": "Copied Playbook"},
            headers={"X-Tenant-ID": tenant_1_id}
        )
        assert response.status_code == 201
        copied_playbook = response.json()
        assert copied_playbook["name"] == "Copied Playbook"
        assert copied_playbook["tenant_id"] == tenant_1_id

    def test_validate_playbook_cross_tenant_access_denied(
        self, client, tenant_1_id, tenant_2_id, tenant_1_playbooks, tenant_2_playbooks
    ):
        """Test that tenants cannot validate other tenants' playbooks."""
        tenant_1_playbook_id = tenant_1_playbooks[0]["id"]

        # Tenant 2 tries to validate tenant 1's playbook - should fail
        response = client.post(
            f"/soar/playbooks/{tenant_1_playbook_id}/validate",
            headers={"X-Tenant-ID": tenant_2_id}
        )
        assert response.status_code == 404

        # Tenant 1 should be able to validate their own playbook
        response = client.post(
            f"/soar/playbooks/{tenant_1_playbook_id}/validate",
            headers={"X-Tenant-ID": tenant_1_id}
        )
        assert response.status_code == 200

    def test_create_playbook_tenant_assignment(
        self, client, tenant_1_id, tenant_2_id, setup_database
    ):
        """Test that created playbooks are assigned to the correct tenant."""
        # Tenant 1 creates a playbook
        response = client.post(
            "/soar/playbooks",
            json={
                "name": "New Playbook",
                "description": "Test playbook",
                "category": "phishing",
                "version": "1.0.0",
                "workflow": {"nodes": [], "edges": []},
                "is_template": False,
                "requires_approval": False,
                "tags": [],
            },
            headers={"X-Tenant-ID": tenant_1_id}
        )
        assert response.status_code == 201
        playbook = response.json()
        assert playbook["tenant_id"] == tenant_1_id

        # Tenant 2 creates a playbook
        response = client.post(
            "/soar/playbooks",
            json={
                "name": "Another Playbook",
                "description": "Test playbook 2",
                "category": "malware",
                "version": "1.0.0",
                "workflow": {"nodes": [], "edges": []},
                "is_template": False,
                "requires_approval": False,
                "tags": [],
            },
            headers={"X-Tenant-ID": tenant_2_id}
        )
        assert response.status_code == 201
        playbook = response.json()
        assert playbook["tenant_id"] == tenant_2_id

    def test_execute_playbook_cross_tenant_access_denied(
        self, client, tenant_1_id, tenant_2_id, tenant_1_playbooks, tenant_2_playbooks
    ):
        """Test that tenants cannot execute other tenants' playbooks."""
        tenant_1_playbook_id = tenant_1_playbooks[0]["id"]

        # Tenant 2 tries to execute tenant 1's playbook - should fail
        response = client.post(
            f"/soar/playbooks/{tenant_1_playbook_id}/execute",
            json={
                "triggered_by": "tenant_2_user",
                "context": {}
            },
            headers={"X-Tenant-ID": tenant_2_id}
        )
        # Should either return 404 or 403
        assert response.status_code in [404, 403]

        # Tenant 1 should be able to execute their own playbook
        response = client.post(
            f"/soar/playbooks/{tenant_1_playbook_id}/execute",
            json={
                "triggered_by": "tenant_1_user",
                "context": {}
            },
            headers={"X-Tenant-ID": tenant_1_id}
        )
        assert response.status_code == 200

    def test_list_playbooks_with_filters_tenant_isolation(
        self, client, tenant_1_id, tenant_2_id, tenant_1_playbooks, tenant_2_playbooks
    ):
        """Test that filters work correctly with tenant isolation."""
        # Tenant 1 filters by category
        response = client.get(
            "/soar/playbooks?category=phishing",
            headers={"X-Tenant-ID": tenant_1_id}
        )
        assert response.status_code == 200
        playbooks = response.json()
        assert all(pb["category"] == "phishing" for pb in playbooks)
        assert all(pb["tenant_id"] == tenant_1_id for pb in playbooks)

        # Tenant 2 filters by category
        response = client.get(
            "/soar/playbooks?category=malware",
            headers={"X-Tenant-ID": tenant_2_id}
        )
        assert response.status_code == 200
        playbooks = response.json()
        assert all(pb["category"] == "malware" for pb in playbooks)
        assert all(pb["tenant_id"] == tenant_2_id for pb in playbooks)

    def test_template_playbooks_tenant_isolation(
        self, client, tenant_1_id, tenant_2_id, setup_database
    ):
        """Test that template playbooks are also tenant-isolated."""
        # Tenant 1 creates a template
        response = client.post(
            "/soar/playbooks",
            json={
                "name": "Tenant 1 Template",
                "description": "Template for tenant 1",
                "category": "phishing",
                "version": "1.0.0",
                "workflow": {"nodes": [], "edges": []},
                "is_template": True,
                "requires_approval": False,
                "tags": [],
            },
            headers={"X-Tenant-ID": tenant_1_id}
        )
        tenant_1_template_id = response.json()["id"]

        # Tenant 2 creates a template
        response = client.post(
            "/soar/playbooks",
            json={
                "name": "Tenant 2 Template",
                "description": "Template for tenant 2",
                "category": "malware",
                "version": "1.0.0",
                "workflow": {"nodes": [], "edges": []},
                "is_template": True,
                "requires_approval": False,
                "tags": [],
            },
            headers={"X-Tenant-ID": tenant_2_id}
        )

        # Tenant 1 should only see their template
        response = client.get(
            "/soar/playbooks?is_template=true",
            headers={"X-Tenant-ID": tenant_1_id}
        )
        assert response.status_code == 200
        templates = response.json()
        assert len(templates) == 1
        assert templates[0]["id"] == tenant_1_template_id
        assert templates[0]["tenant_id"] == tenant_1_id

        # Tenant 2 should only see their template
        response = client.get(
            "/soar/playbooks?is_template=true",
            headers={"X-Tenant-ID": tenant_2_id}
        )
        assert response.status_code == 200
        templates = response.json()
        assert len(templates) == 1
        assert templates[0]["tenant_id"] == tenant_2_id

    def test_execution_status_tenant_isolation(
        self, client, tenant_1_id, tenant_2_id, tenant_1_playbooks, tenant_2_playbooks
    ):
        """Test that execution status is tenant-isolated."""
        tenant_1_playbook_id = tenant_1_playbooks[0]["id"]

        # Tenant 1 executes their playbook
        response = client.post(
            f"/soar/playbooks/{tenant_1_playbook_id}/execute",
            json={
                "triggered_by": "tenant_1_user",
                "context": {}
            },
            headers={"X-Tenant-ID": tenant_1_id}
        )
        assert response.status_code == 200
        execution_id = response.json()["execution_id"]

        # Tenant 1 can check their execution status
        response = client.get(
            f"/soar/executions/{execution_id}",
            headers={"X-Tenant-ID": tenant_1_id}
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(execution_id)

        # Tenant 2 cannot access tenant 1's execution
        response = client.get(
            f"/soar/executions/{execution_id}",
            headers={"X-Tenant-ID": tenant_2_id}
        )
        assert response.status_code == 404


class TestTenantHeaderValidation:
    """Test tenant header validation and security."""

    def test_missing_tenant_header_rejected(self, client, setup_database):
        """Test that requests without tenant header are rejected."""
        response = client.get("/soar/playbooks")
        assert response.status_code == 401

    def test_invalid_tenant_header_format(self, client, setup_database):
        """Test that invalid tenant header formats are rejected."""
        response = client.get(
            "/soar/playbooks",
            headers={"X-Tenant-ID": "not-a-valid-uuid"}
        )
        # Should either reject invalid format or handle gracefully
        assert response.status_code in [400, 401, 422]

    def test_empty_tenant_header_rejected(self, client, setup_database):
        """Test that empty tenant header is rejected."""
        response = client.get(
            "/soar/playbooks",
            headers={"X-Tenant-ID": ""}
        )
        assert response.status_code == 401

