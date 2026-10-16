"""Pytest configuration and fixtures for Detection Service tests."""

import os
import sys
import types
import importlib.util
import importlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Mock environment variables
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_pass")

if importlib.util.find_spec("apscheduler") is None:
    apscheduler_module = types.ModuleType("apscheduler")
    schedulers_module = types.ModuleType("apscheduler.schedulers")
    asyncio_module = types.ModuleType("apscheduler.schedulers.asyncio")
    triggers_module = types.ModuleType("apscheduler.triggers")
    interval_module = types.ModuleType("apscheduler.triggers.interval")

    class _DummyScheduler:
        def __init__(self, *args, **kwargs):
            self.running = False

        def add_job(self, *args, **kwargs):
            return None

        def start(self):
            self.running = True

        def shutdown(self, wait=True):
            self.running = False

    class _DummyIntervalTrigger:
        def __init__(self, *args, **kwargs):
            pass

    asyncio_module.AsyncIOScheduler = _DummyScheduler
    interval_module.IntervalTrigger = _DummyIntervalTrigger

    sys.modules["apscheduler"] = apscheduler_module
    sys.modules["apscheduler.schedulers"] = schedulers_module
    sys.modules["apscheduler.schedulers.asyncio"] = asyncio_module
    sys.modules["apscheduler.triggers"] = triggers_module
    sys.modules["apscheduler.triggers.interval"] = interval_module

app_db = importlib.import_module("app.core.database")
app_db.Base.metadata.create_all = lambda *args, **kwargs: None

from app.main import app
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
