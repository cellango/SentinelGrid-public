"""Focused tenant-session coverage for CMDB asset routes."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app import main as cmdb_main
from app.api import assets as assets_api
from app.core import database as cmdb_database


class FakeDB:
    """Minimal DB stub for dependency overrides."""


def _make_asset(tenant_id: str, asset_id: str = "asset-1"):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        tenant_id=UUID(tenant_id),
        asset_id=asset_id,
        asset_type="server",
        name="Primary Asset",
        hostname="asset-1.internal",
        ip_address="10.0.0.10",
        mac_address=None,
        manufacturer=None,
        model=None,
        serial_number=None,
        hardware_specs={},
        operating_system="linux",
        os_version="1.0",
        installed_software=[],
        installed_patches=[],
        network_segment=None,
        vlan=None,
        firewall_rules={},
        owner=None,
        location=None,
        department=None,
        vulnerabilities={"cves": []},
        compliance_status=None,
        last_scan_date=None,
        source="manual",
        user_id=None,
        external_id=None,
        metadata_json={},
        last_seen_at=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def tenant_scoped_client():
    """Create a client that requires query-tenant session usage."""
    fake_db = FakeDB()

    def unexpected_get_db():
        raise AssertionError("Route used get_db instead of get_query_tenant_session")
        yield  # pragma: no cover

    def override_get_query_tenant_session():
        yield fake_db

    cmdb_main.app.dependency_overrides[cmdb_database.get_db] = unexpected_get_db
    cmdb_main.app.dependency_overrides[cmdb_database.get_query_tenant_session] = (
        override_get_query_tenant_session
    )

    try:
        with TestClient(cmdb_main.app) as client:
            yield client, fake_db
    finally:
        cmdb_main.app.dependency_overrides.clear()


def test_asset_routes_use_query_tenant_session(monkeypatch, tenant_scoped_client):
    client, fake_db = tenant_scoped_client
    tenant_id = str(uuid4())
    asset = _make_asset(tenant_id)

    class FakeAssetManager:
        def get_asset(self, db, asset_id, tenant):
            assert db is fake_db
            assert asset_id == asset.asset_id
            assert str(tenant) == tenant_id
            return asset

        def create_asset(self, db, tenant, asset_data):
            assert db is fake_db
            assert str(tenant) == tenant_id
            asset.asset_id = asset_data["asset_id"]
            asset.name = asset_data["name"]
            asset.asset_type = asset_data["asset_type"]
            return asset

        def update_asset(self, db, asset_id, tenant, asset_data):
            assert db is fake_db
            assert asset_id == asset.asset_id
            assert str(tenant) == tenant_id
            for key, value in asset_data.items():
                setattr(asset, key, value)
            return asset

        def delete_asset(self, db, asset_id, tenant):
            assert db is fake_db
            assert asset_id == asset.asset_id
            assert str(tenant) == tenant_id
            return True

        def search_assets(
            self,
            db,
            tenant_id,
            search_term=None,
            asset_type=None,
            hostname=None,
            ip_address=None,
            limit=50,
            offset=0,
        ):
            assert db is fake_db
            assert str(tenant_id) == str(asset.tenant_id)
            return [asset]

        def link_vulnerability_to_asset(self, db, asset_id, tenant, cve_id):
            assert db is fake_db
            assert asset_id == asset.asset_id
            assert str(tenant) == tenant_id
            asset.vulnerabilities = {"cves": [cve_id]}
            return asset

        async def sync_cloud_assets(self, db, tenant):
            assert db is fake_db
            assert str(tenant) == tenant_id
            return {
                "status": "completed",
                "results": {"synced": [asset.asset_id], "updated": [], "failed": []},
            }

    monkeypatch.setattr(assets_api, "asset_manager", FakeAssetManager())

    get_response = client.get(f"/api/v1/assets/{asset.asset_id}?tenant_id={tenant_id}")
    assert get_response.status_code == 200
    assert get_response.json()["asset_id"] == asset.asset_id

    create_response = client.post(
        f"/api/v1/assets?tenant_id={tenant_id}",
        json={"asset_id": asset.asset_id, "asset_type": "server", "name": "Primary Asset"},
    )
    assert create_response.status_code == 200

    update_response = client.put(
        f"/api/v1/assets/{asset.asset_id}?tenant_id={tenant_id}",
        json={"name": "Updated Asset", "compliance_status": "compliant"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Asset"

    search_response = client.get(f"/api/v1/assets?tenant_id={tenant_id}")
    assert search_response.status_code == 200
    assert len(search_response.json()) == 1

    link_response = client.post(
        f"/api/v1/assets/{asset.asset_id}/vulnerabilities/CVE-2025-0001?tenant_id={tenant_id}"
    )
    assert link_response.status_code == 200
    assert link_response.json()["status"] == "linked"

    sync_response = client.post(f"/api/v1/assets/sync/cloud?tenant_id={tenant_id}")
    assert sync_response.status_code == 200
    assert sync_response.json()["status"] == "completed"

    delete_response = client.delete(f"/api/v1/assets/{asset.asset_id}?tenant_id={tenant_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"
