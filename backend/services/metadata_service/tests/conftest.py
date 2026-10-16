"""Pytest configuration for metadata-service tenant isolation tests."""

import os
import sys
import types

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_URL", "sqlite:///./test_metadata_service.db")


services_pkg = types.ModuleType("app.services")


class _AssetManager:
    pass


class _VulnerabilityService:
    pass


asset_manager_module = types.ModuleType("app.services.asset_manager")
asset_manager_module.AssetManager = _AssetManager

vulnerability_service_module = types.ModuleType("app.services.vulnerability_service")
vulnerability_service_module.VulnerabilityService = _VulnerabilityService

sys.modules.setdefault("app.services", services_pkg)
sys.modules.setdefault("app.services.asset_manager", asset_manager_module)
sys.modules.setdefault("app.services.vulnerability_service", vulnerability_service_module)

import sg_core.schemas as sg_schemas


class _AssetResponse(PydanticBaseModel):
    id: str | None = None


class _VulnerabilityResponse(PydanticBaseModel):
    id: str | None = None


if not hasattr(sg_schemas, "AssetResponse"):
    sg_schemas.AssetResponse = _AssetResponse

if not hasattr(sg_schemas, "VulnerabilityResponse"):
    sg_schemas.VulnerabilityResponse = _VulnerabilityResponse

from app.main import app
from app.core.database import Base, get_current_tenant, get_db, get_tenant_session


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_current_tenant():
        return "tenant-alpha"

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_tenant_session():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_current_tenant] = override_get_current_tenant
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_tenant_session] = override_get_tenant_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
