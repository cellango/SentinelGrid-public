"""Pytest configuration and fixtures for Tenant Service tests."""

import pytest
import os
import sys
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Mock environment variables
os.environ.setdefault("KEYCLOAK_URL", "http://localhost:8080")
os.environ.setdefault("KEYCLOAK_ADMIN_USER", "admin")
os.environ.setdefault("KEYCLOAK_ADMIN_PASSWORD", "admin")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_pass")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
IAM_AGENT_APP = os.path.join(REPO_ROOT, "backend/agents/iam_agent/app")
BACKEND_LIBS = os.path.join(REPO_ROOT, "backend/libs")
if IAM_AGENT_APP not in sys.path:
    sys.path.insert(0, IAM_AGENT_APP)
if BACKEND_LIBS not in sys.path:
    sys.path.insert(0, BACKEND_LIBS)

from app.main import app
from app.core.database import Base, get_db, get_tenant_session


def _ensure_schema(db):
    """Create the minimal tenant-service schema used by the tests."""
    db.execute(text("PRAGMA foreign_keys=ON"))
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                pricing_tier TEXT,
                plan_tier TEXT NOT NULL DEFAULT 'protect',
                region TEXT,
                compliance_required BOOLEAN,
                employee_count INTEGER,
                industry TEXT,
                has_dedicated_realm BOOLEAN,
                user_count INTEGER DEFAULT 0,
                org_count INTEGER DEFAULT 0,
                status TEXT,
                realm_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS tenants (
                id TEXT PRIMARY KEY,
                customer_id TEXT REFERENCES customers(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                realm_name TEXT,
                region TEXT,
                pricing_tier TEXT,
                plan_tier TEXT NOT NULL DEFAULT 'protect',
                realm_strategy TEXT,
                incident_management_mode TEXT,
                ticketing_provider TEXT,
                ticketing_project TEXT,
                services_selected TEXT,
                keycloak_org_id TEXT,
                keycloak_group_id TEXT,
                status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS tenant_provisioning_log (
                id TEXT PRIMARY KEY,
                tenant_id TEXT REFERENCES tenants(id) ON DELETE CASCADE,
                customer_id TEXT REFERENCES customers(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                realm_name TEXT,
                details TEXT,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    )
    db.commit()


@pytest.fixture
def test_db():
    """Create a test database."""
    # Use in-memory SQLite for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = TestingSessionLocal()
    try:
        _ensure_schema(session)
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def client(test_db):
    """Create test client with database override."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    def override_get_tenant_session():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_tenant_session] = override_get_tenant_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_keycloak_client():
    """Mock Keycloak admin client."""
    with patch('app.core.keycloak.KeycloakAdminClient') as mock:
        mock_instance = Mock()
        mock_instance.create_realm.return_value = {"realm": "test-realm"}
        mock_instance.create_client.return_value = {"id": "client-123"}
        mock_instance.create_user.return_value = "user-123"
        mock_instance.assign_role.return_value = None
        mock_instance.add_tenant_id_mapper.return_value = None
        mock_instance.send_verification_email.return_value = None
        mock.return_value = mock_instance
        yield mock_instance
