"""Pytest configuration and fixtures for Connector Service tests."""

import os
import sys
import types
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.schema import MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Mock environment variables
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost:8005/auth/google/callback")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_pass")


sync_service_module = types.ModuleType("app.services.sync_service")


class _SyncService:
    def __init__(self, db):
        self.db = db

    def sync_connector(self, connector_id, tenant_id):
        return {"status": "stub", "connector_id": connector_id, "tenant_id": tenant_id}

    def sync_all_active_connectors(self, tenant_id):
        return {"status": "stub", "tenant_id": tenant_id}


sync_service_module.SyncService = _SyncService
sys.modules.setdefault("app.services.sync_service", sync_service_module)

google_auth_oauthlib_module = types.ModuleType("google_auth_oauthlib")
google_auth_oauthlib_flow_module = types.ModuleType("google_auth_oauthlib.flow")


class _Flow:
    scopes = []
    credentials = None

    @classmethod
    def from_client_config(cls, *args, **kwargs):
        return cls()

    def authorization_url(self, *args, **kwargs):
        return ("https://example.com/oauth", "state")

    def fetch_token(self, *args, **kwargs):
        self.credentials = types.SimpleNamespace(
            token="token",
            refresh_token="refresh-token",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="test-client-id",
            client_secret="test-client-secret",
            scopes=[],
        )


google_auth_oauthlib_flow_module.Flow = _Flow
google_auth_oauthlib_module.flow = google_auth_oauthlib_flow_module
sys.modules.setdefault("google_auth_oauthlib", google_auth_oauthlib_module)
sys.modules.setdefault("google_auth_oauthlib.flow", google_auth_oauthlib_flow_module)

google_oauth2_module = types.ModuleType("google.oauth2")
google_oauth2_credentials_module = types.ModuleType("google.oauth2.credentials")
google_oauth2_credentials_module.Credentials = object
sys.modules.setdefault("google.oauth2", google_oauth2_module)
sys.modules.setdefault("google.oauth2.credentials", google_oauth2_credentials_module)

googleapiclient_module = types.ModuleType("googleapiclient")
googleapiclient_discovery_module = types.ModuleType("googleapiclient.discovery")
googleapiclient_errors_module = types.ModuleType("googleapiclient.errors")
googleapiclient_discovery_module.build = lambda *args, **kwargs: None
googleapiclient_errors_module.HttpError = Exception
googleapiclient_module.discovery = googleapiclient_discovery_module
googleapiclient_module.errors = googleapiclient_errors_module
sys.modules.setdefault("googleapiclient", googleapiclient_module)
sys.modules.setdefault("googleapiclient.discovery", googleapiclient_discovery_module)
sys.modules.setdefault("googleapiclient.errors", googleapiclient_errors_module)

_original_create_all = MetaData.create_all
MetaData.create_all = lambda self, bind=None, tables=None, checkfirst=True: None
try:
    from app.main import app
finally:
    MetaData.create_all = _original_create_all

from app.core.database import Base, get_db, get_tenant_session


@pytest.fixture
def test_db():
    """Create a test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = TestingSessionLocal()
    try:
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
