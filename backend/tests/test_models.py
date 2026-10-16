"""Basic tests for core models."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../libs"))

from sg_core.models import Base, Tenant, Alert
from sg_core.db import SessionLocal


@pytest.fixture
def db_session():
    """Create a test database session."""
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal.configure(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_create_tenant(db_session):
    """Test creating a tenant."""
    tenant = Tenant(
        name="Test Company",
        slug="test-company",
        status="active"
    )
    db_session.add(tenant)
    db_session.commit()
    
    assert tenant.id is not None
    assert tenant.name == "Test Company"
    assert tenant.slug == "test-company"


def test_create_alert(db_session):
    """Test creating an alert."""
    # First create a tenant
    tenant = Tenant(
        name="Test Company",
        slug="test-company",
        status="active"
    )
    db_session.add(tenant)
    db_session.commit()
    
    # Create an alert
    alert = Alert(
        tenant_id=tenant.id,
        source="elastic",
        external_id="SIEM-12345",
        title="Test Alert",
        description="This is a test alert",
        raw_severity="high",
        status="open",
        detection_time="2025-11-28T12:34:56Z"
    )
    db_session.add(alert)
    db_session.commit()
    
    assert alert.id is not None
    assert alert.tenant_id == tenant.id
    assert alert.source == "elastic"

