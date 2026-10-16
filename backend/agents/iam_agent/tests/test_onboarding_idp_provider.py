"""Unit tests for onboarding IdP provider normalization and persistence."""

import json
import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api import onboarding


class _FakeResult:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeDB:
    def __init__(self):
        self.statements = []
        self.committed = False
        self.rolled_back = False

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params))

        if "INSERT INTO customer_idp_config" in sql:
            return _FakeResult(("cfg-123",))
        if "SELECT appsec_config" in sql and "FROM onboarding_progress" in sql:
            return _FakeResult((None, None, None, None, None, None, False, True))
        if "SELECT idp_type" in sql and "FROM customer_idp_config" in sql:
            return _FakeResult(("google_workspace",))

        return _FakeResult()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def _build_client(fake_db):
    app = FastAPI()
    app.include_router(onboarding.router)
    app.dependency_overrides[onboarding.get_db] = lambda: fake_db
    app.dependency_overrides[onboarding.get_tenant_session] = lambda: fake_db
    app.dependency_overrides[onboarding.get_onboarding_customer_id] = lambda: "tenant-123"
    return TestClient(app)


def test_normalize_idp_type_accepts_legacy_aliases():
    assert onboarding._normalize_idp_type("google") == "google_workspace"
    assert onboarding._normalize_idp_type("Google Workspace") == "google_workspace"
    assert onboarding._normalize_idp_type("microsoft") == "microsoft_entra"
    assert onboarding._normalize_idp_type("azure_ad") == "microsoft_entra"
    assert onboarding._normalize_idp_type("sentinelgrid") == "sentinelgrid"


def test_connect_idp_persists_canonical_provider(monkeypatch):
    fake_db = _FakeDB()
    client = _build_client(fake_db)

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)
    monkeypatch.setattr(onboarding, "encrypt_secret", lambda secret, tenant_id=None: "vault://idp/config")

    response = client.post(
        "/api/v1/onboarding/connect-idp",
        headers={"X-Tenant-ID": "tenant-123"},
        json={"idp_type": "google", "config": {"mode": "oauth"}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["message"] == "Successfully connected google_workspace"
    assert fake_db.committed is True

    insert_sql, insert_params = fake_db.statements[0]
    assert "INSERT INTO customer_idp_config" in insert_sql
    assert insert_params["idp_type"] == "google_workspace"

    progress_sql, progress_params = fake_db.statements[1]
    assert "INSERT INTO onboarding_progress" in progress_sql
    saved = json.loads(progress_params["services_selected"])
    assert saved == {"idpProvider": "google_workspace"}


def test_recheck_health_uses_saved_google_workspace_provider(monkeypatch):
    fake_db = _FakeDB()
    client = _build_client(fake_db)

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)

    response = client.post(
        "/api/v1/onboarding/recheck-health",
        headers={"X-Tenant-ID": "tenant-123"},
        json={"target": "idp"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["health"]["status"] == "healthy"
    assert payload["health"]["provider"] == "google_workspace"
