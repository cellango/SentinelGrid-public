"""Focused tenant-session coverage for metadata-service asset and vulnerability routes."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api import assets as assets_api
from app.api import vulnerabilities as vulnerabilities_api
from app.core.database import (
    get_current_tenant,
    get_db,
    get_tenant_session,
)


def _unexpected_dependency():
    raise AssertionError("Unexpected plain DB dependency used")
    yield  # pragma: no cover


@pytest.fixture
def tenant_context():
    return str(uuid4())


@pytest.fixture
def client_with_tenant_session(tenant_context):
    fake_db = object()

    def override_current_tenant():
        return tenant_context

    def override_tenant_session():
        yield fake_db

    app.dependency_overrides[get_current_tenant] = override_current_tenant
    app.dependency_overrides[get_db] = _unexpected_dependency
    app.dependency_overrides[get_tenant_session] = override_tenant_session

    try:
        yield TestClient(app, raise_server_exceptions=False), fake_db
    finally:
        app.dependency_overrides.clear()


def test_asset_routes_use_tenant_session(client_with_tenant_session, tenant_context, monkeypatch):
    client, fake_db = client_with_tenant_session
    calls = []

    def record(name, payload):
        calls.append((name, payload))

    monkeypatch.setattr(
        assets_api.asset_manager,
        "get_asset",
        lambda db, asset_id, tenant_id: (
            record("get_asset", (db, asset_id, tenant_id))
            or {"id": asset_id}
        ),
        raising=False,
    )
    monkeypatch.setattr(
        assets_api.asset_manager,
        "create_asset",
        lambda db, tenant_id, asset_data: (
            record("create_asset", (db, tenant_id, asset_data))
            or {"id": asset_data["asset_id"]}
        ),
        raising=False,
    )
    monkeypatch.setattr(
        assets_api.asset_manager,
        "search_assets",
        lambda **kwargs: (
            record("search_assets", kwargs)
            or [{"id": "asset-1"}]
        ),
        raising=False,
    )
    async def _sync_cloud_assets(db, tenant_id):
        record("sync_cloud_assets", (db, tenant_id))
        return {"status": "ok", "tenant_id": tenant_id}

    monkeypatch.setattr(
        assets_api.asset_manager,
        "sync_cloud_assets",
        _sync_cloud_assets,
        raising=False,
    )

    get_response = client.get(f"/api/v1/metadata/assets/asset-1?tenant_id={tenant_context}")
    create_response = client.post(
        f"/api/v1/metadata/assets?tenant_id={tenant_context}",
        json={"asset_id": "asset-2", "asset_type": "server", "name": "Server 2"},
    )
    search_response = client.get(f"/api/v1/metadata/assets?tenant_id={tenant_context}")
    sync_response = client.post(f"/api/v1/metadata/assets/sync/cloud?tenant_id={tenant_context}")

    assert get_response.status_code == 200
    assert create_response.status_code == 200
    assert search_response.status_code == 200
    assert sync_response.status_code == 200

    assert calls[0] == ("get_asset", (fake_db, "asset-1", tenant_context))
    assert calls[1][0] == "create_asset"
    assert calls[1][1][0] is fake_db
    assert calls[1][1][1] == tenant_context
    assert calls[2][0] == "search_assets"
    assert calls[2][1]["db"] is fake_db
    assert calls[2][1]["tenant_id"] == tenant_context
    assert calls[3] == ("sync_cloud_assets", (fake_db, tenant_context))


def test_asset_routes_reject_cross_tenant_query(client_with_tenant_session, tenant_context):
    client, _ = client_with_tenant_session
    foreign_tenant = str(uuid4())

    response = client.get(f"/api/v1/metadata/assets/asset-1?tenant_id={foreign_tenant}")

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"


def test_vulnerability_routes_use_tenant_session(client_with_tenant_session, tenant_context, monkeypatch):
    client, fake_db = client_with_tenant_session
    calls = []

    def record(name, payload):
        calls.append((name, payload))

    async def _get_or_create_vulnerability(db, cve_id, tenant_id):
        record("get_or_create_vulnerability", (db, cve_id, tenant_id))
        return {"id": cve_id}

    monkeypatch.setattr(
        vulnerabilities_api.vulnerability_service,
        "get_or_create_vulnerability",
        _get_or_create_vulnerability,
        raising=False,
    )
    monkeypatch.setattr(
        vulnerabilities_api.vulnerability_service,
        "search_vulnerabilities",
        lambda **kwargs: (
            record("search_vulnerabilities", kwargs)
            or [{"id": "CVE-2026-0001"}]
        ),
        raising=False,
    )
    async def _sync_cves_from_nvd(db, cve_ids, tenant_id):
        record("sync_cves_from_nvd", (db, cve_ids, tenant_id))
        return {"synced": cve_ids, "skipped": [], "failed": []}

    monkeypatch.setattr(
        vulnerabilities_api.vulnerability_service,
        "sync_cves_from_nvd",
        _sync_cves_from_nvd,
        raising=False,
    )

    get_response = client.get(
        f"/api/v1/metadata/vulnerabilities/CVE-2026-0001?tenant_id={tenant_context}"
    )
    search_response = client.get(f"/api/v1/metadata/vulnerabilities?tenant_id={tenant_context}")
    sync_response = client.post(
        f"/api/v1/metadata/vulnerabilities/sync?tenant_id={tenant_context}",
        json=["CVE-2026-0001"],
    )

    assert get_response.status_code == 200
    assert search_response.status_code == 200
    assert sync_response.status_code == 200

    assert calls[0] == ("get_or_create_vulnerability", (fake_db, "CVE-2026-0001", tenant_context))
    assert calls[1][0] == "search_vulnerabilities"
    assert calls[1][1]["db"] is fake_db
    assert calls[1][1]["tenant_id"] == tenant_context
    assert calls[2] == ("sync_cves_from_nvd", (fake_db, ["CVE-2026-0001"], tenant_context))


def test_vulnerability_routes_reject_cross_tenant_query(client_with_tenant_session):
    client, _ = client_with_tenant_session
    foreign_tenant = str(uuid4())

    response = client.get(
        f"/api/v1/metadata/vulnerabilities/CVE-2026-0001?tenant_id={foreign_tenant}"
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"
