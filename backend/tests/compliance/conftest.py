"""
Pytest configuration and fixtures for compliance tests
"""

import pytest
import os
from uuid import uuid4, UUID
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# Test database URL
# Default to the running dev Postgres (docker-compose) unless explicitly overridden.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://sg:sg@localhost:5432/sg"
)


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL)
    return engine


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a new database session for each test."""
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        # Roll back any changes to keep tests isolated
        session.rollback()
        session.close()


@pytest.fixture
def tenant_a():
    """Fixture for Tenant A."""
    return {
        "id": uuid4(),
        "name": "Acme Corp",
        "realm": "acme-corp"
    }


@pytest.fixture
def tenant_b():
    """Fixture for Tenant B."""
    return {
        "id": uuid4(),
        "name": "TechStart Inc",
        "realm": "techstart"
    }


@pytest.fixture
def test_user_a():
    """Test user for Tenant A."""
    return {
        "id": "user-a-123",
        "email": "admin@acme.com",
        "name": "Admin User A",
        "roles": ["TENANT_ADMIN"]
    }


@pytest.fixture
def test_user_b():
    """Test user for Tenant B."""
    return {
        "id": "user-b-456",
        "email": "admin@techstart.com",
        "name": "Admin User B",
        "roles": ["TENANT_ADMIN"]
    }


@pytest.fixture
def sample_report_data():
    """Sample report data for testing."""
    return {
        "report_title": "SOC 2 Coverage Report",
        "tenant_name": "Acme Corp",
        "period_start": "2025-11-01",
        "period_end": "2025-11-30",
        "soc2_coverage_percentage": 87.5,
        "controls_implemented": 28,
        "total_controls": 32,
        "evidence_collected_percentage": 92.0,
        "evidence_count": 342,
        "gap_count": 4,
        "categories": [
            {
                "name": "CC6 - Access Control",
                "total_controls": 8,
                "implemented_controls": 7,
                "coverage_percentage": 87.5,
                "controls": [
                    {
                        "control_id": "CC6.1",
                        "control_name": "Logical and physical access controls",
                        "features": ["IAM Agent", "RBAC", "Audit Logs"],
                        "status": "implemented",
                        "evidence_count": 5
                    }
                ]
            }
        ],
        "gaps": [],
        "evidence_summary": []
    }


@pytest.fixture
def mock_embedding_model(mocker):
    """Mock embedding model for testing."""
    mock_model = mocker.Mock()
    mock_model.encode.return_value = [0.1] * 384  # 384-dimensional vector
    return mock_model


@pytest.fixture
def mock_llm_client(mocker):
    """Mock LLM client for testing."""
    mock_client = mocker.Mock()
    mock_client.generate.return_value = "Based on your reports, the MFA coverage is 87.5%."
    return mock_client


@pytest.fixture
def temp_report_dir(tmp_path):
    """Temporary directory for report files."""
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    return report_dir
