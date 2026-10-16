"""Pytest configuration and fixtures for Ticketing Agent tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import os
import sys

# Add libs to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from sg_core.db import Base
from sg_core.models import Ticket, Alert, Tenant
from app.main import app
from app.core.database import get_db

# Test database URL
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://sg:sg@localhost:5432/sg_test")


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_tenant(db_session):
    """Create a test tenant."""
    tenant = Tenant(
        id="00000000-0000-0000-0000-000000000001",
        company_name="Test Company",
        admin_email="admin@test.com",
        status="active"
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def test_alert(db_session, test_tenant):
    """Create a test alert."""
    from sg_core.models import Alert
    alert = Alert(
        tenant_id=test_tenant.id,
        source="siem",
        external_id="alert-123",
        title="Suspicious Login Detected",
        description="Multiple failed login attempts",
        raw_severity="high",
        status="open",
        detection_time="2024-01-28T10:00:00Z",
        user_identifier="user@example.com"
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    return alert

