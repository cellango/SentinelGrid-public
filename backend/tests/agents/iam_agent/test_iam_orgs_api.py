"""
Tests for IAM org/tenant provisioning API (realm strategy + tenant creation).
"""

import uuid
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Path setup
import sys
from pathlib import Path

backend_agents_path = Path(__file__).parent.parent.parent.parent / "agents" / "iam_agent"
if str(backend_agents_path) not in sys.path:
    sys.path.insert(0, str(backend_agents_path))

from app.api import iam_orgs  # noqa: E402


def build_sqlite():
    """Create in-memory sqlite with minimal tables used by the API."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # ensure single shared in-memory DB
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE customers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT UNIQUE NOT NULL,
                    has_dedicated_realm BOOLEAN NOT NULL DEFAULT 0,
                    realm_name TEXT,
                    pricing_tier TEXT,
                    user_count INTEGER DEFAULT 0,
                    org_count INTEGER DEFAULT 0,
                    compliance_required BOOLEAN DEFAULT 0,
                    region TEXT,
                    status TEXT
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE organizations (
                    id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    realm_name TEXT NOT NULL,
                    org_type TEXT,
                    status TEXT
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE tenants (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    status TEXT,
                    customer_id TEXT,
                    organization_id TEXT,
                    realm_name TEXT,
                    realm_strategy TEXT,
                    region TEXT,
                    keycloak_org_id TEXT,
                    keycloak_group_id TEXT
                );
                """
            )
        )
    return engine


@pytest.fixture
def client(monkeypatch):
    """FastAPI client with sqlite DB and dependency overrides."""
    engine = build_sqlite()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
            db.commit()
        finally:
            db.close()

    app = FastAPI()
    app.include_router(iam_orgs.router)
    app.dependency_overrides[iam_orgs.get_db] = override_get_db

    return TestClient(app)


def make_mock_realm_manager(shared_realm: str = "sg-mt-us-1", dedicated_realm: str = "sg-mt-ded-1"):
    """Create a mock realm manager with predictable realm selection."""
    class MockManager:
        def get_available_shared_realm(self, region: str = "us"):
            return shared_realm

        def _create_new_shard(self, region: str = "us"):
            return dedicated_realm

        def assign_tenant_to_shared_realm(self, tenant_id: str, tenant_slug: str, realm_name: str, customer_id: str):
            return {
                "keycloak_org_id": f"org-{tenant_slug}",
                "keycloak_group_id": f"group-{tenant_slug}",
            }

    return MockManager()


class TestIamOrgsApi:
    @pytest.mark.parametrize(
        "projected_users,expected_strategy,expected_realm",
        [
            (0, "shared", "sg-mt-us-1"),
            (1000, "dedicated", "sg-mt-ded-1"),
        ],
    )
    def test_create_organization_auto_strategy(self, monkeypatch, client, projected_users, expected_strategy, expected_realm):
        mock_manager = make_mock_realm_manager(shared_realm="sg-mt-us-1", dedicated_realm="sg-mt-ded-1")
        monkeypatch.setattr(iam_orgs, "_get_realm_manager", lambda db: mock_manager)
        monkeypatch.setattr(
            iam_orgs,
            "_resolve_strategy",
            lambda requested, projected: "dedicated" if projected >= 500 else "shared",
        )

        resp = client.post(
            "/api/iam-portal/organizations",
            json={
                "name": f"Acme {projected_users}",
                "realm_strategy": "auto",
                "region": "us",
                "projected_user_count": projected_users,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["realm_strategy"] == expected_strategy
        assert data["realm_name"] == expected_realm
        assert data["initial_tenant"]["realm_name"] == expected_realm
        assert data["initial_tenant"]["id"]

    def test_create_tenant_under_org(self, monkeypatch, client):
        mock_manager = make_mock_realm_manager(shared_realm="sg-mt-us-5")
        monkeypatch.setattr(iam_orgs, "_get_realm_manager", lambda db: mock_manager)

        # Create org first
        org_resp = client.post(
            "/api/iam-portal/organizations",
            json={
                "name": "Tenant Parent Org",
                "realm_strategy": "shared",
                "region": "us",
                "projected_user_count": 10,
            },
        )
        assert org_resp.status_code == 201
        org_id = org_resp.json()["id"]
        realm_name = org_resp.json()["realm_name"]

        # Add tenant
        tenant_resp = client.post(
            f"/api/iam-portal/organizations/{org_id}/tenants",
            json={"tenant_name": "Child Tenant", "region": "us"},
        )
        assert tenant_resp.status_code == 201
        tenant_data = tenant_resp.json()
        assert tenant_data["org_id"] == org_id
        assert tenant_data["realm_name"] == realm_name
        assert tenant_data["keycloak_group_id"]
        assert tenant_data["slug"]
