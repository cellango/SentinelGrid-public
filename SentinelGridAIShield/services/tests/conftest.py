import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.constants import TEST_ORG_ID

# Default to Postgres because the service models use PostgreSQL types.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/sentinelgrid_ai_shield_test",
)
os.environ.setdefault("DB_URL", TEST_DATABASE_URL)
os.environ.setdefault("AI_SHIELD_SKIP_DB_INIT_ON_STARTUP", "true")

from app.main import app
from app.core.database import Base, get_db

@pytest.fixture
def test_db():
    """Create a test database"""
    engine = create_engine(TEST_DATABASE_URL)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    app.dependency_overrides.clear()

@pytest.fixture
def client():
    """Create a test client without forcing database setup."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_client(test_db):
    """Create a test client backed by the test database."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def org_id():
    return TEST_ORG_ID


@pytest.fixture
def internal_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer internal-service-token-change-in-production",
        "X-Tenant-ID": TEST_ORG_ID,
    }
