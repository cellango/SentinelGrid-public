"""Focused tenant-session coverage for detection rules routes."""

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.api import rules as rules_api
from app.core.database import get_db, get_tenant_session


def _unexpected_dependency():
    raise AssertionError("Unexpected plain DB dependency used")
    yield  # pragma: no cover


class _QueryResult:
    def __init__(self, first_value=None, all_values=None):
        self._first_value = first_value
        self._all_values = list(all_values or [])

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._all_values)

    def first(self):
        return self._first_value


class _FakeDB:
    def __init__(self, *, first_value=None, all_values=None):
        self._first_value = first_value
        self._all_values = list(all_values or [])
        self.added = []
        self.deleted = []
        self.commit_count = 0

    def query(self, *args, **kwargs):
        return _QueryResult(first_value=self._first_value, all_values=self._all_values)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commit_count += 1

    def refresh(self, obj):
        now = datetime(2026, 3, 29, 9, 0, 0)
        obj.id = getattr(obj, "id", None) or str(uuid4())
        obj.created_at = getattr(obj, "created_at", None) or now
        obj.updated_at = getattr(obj, "updated_at", None) or now

    def delete(self, obj):
        self.deleted.append(obj)


def _build_rule(tenant_id: str, rule_id: str | None = None):
    now = datetime(2026, 3, 29, 9, 0, 0)
    return SimpleNamespace(
        id=rule_id or str(uuid4()),
        tenant_id=tenant_id,
        name="Rule 1",
        description="desc",
        rule_type="failed_logins",
        pattern={"threshold": 5},
        enabled=True,
        severity="medium",
        created_at=now,
        updated_at=now,
    )


def test_rule_crud_routes_use_tenant_session(monkeypatch):
    tenant_id = str(uuid4())
    fake_db = _FakeDB(first_value=_build_rule(tenant_id), all_values=[_build_rule(tenant_id)])

    def override_tenant():
        return tenant_id

    def override_tenant_session():
        yield fake_db

    app.dependency_overrides[rules_api.get_current_tenant] = override_tenant
    app.dependency_overrides[get_db] = _unexpected_dependency
    app.dependency_overrides[get_tenant_session] = override_tenant_session

    try:
        client = TestClient(app, raise_server_exceptions=False)
        create_response = client.post(
            "/api/v1/rules",
            json={
                "name": "Rule 1",
                "rule_type": "failed_logins",
                "pattern": {"threshold": 5},
                "severity": "medium",
                "enabled": True,
            },
            headers={"X-Tenant-ID": tenant_id},
        )
        list_response = client.get("/api/v1/rules", headers={"X-Tenant-ID": tenant_id})
        get_response = client.get(
            f"/api/v1/rules/{fake_db._first_value.id}",
            headers={"X-Tenant-ID": tenant_id},
        )
        patch_response = client.patch(
            f"/api/v1/rules/{fake_db._first_value.id}",
            json={"severity": "high"},
            headers={"X-Tenant-ID": tenant_id},
        )
        delete_response = client.delete(
            f"/api/v1/rules/{fake_db._first_value.id}",
            headers={"X-Tenant-ID": tenant_id},
        )
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    assert get_response.status_code == 200
    assert patch_response.status_code == 200
    assert delete_response.status_code == 204
    assert len(fake_db.added) == 1
    assert len(fake_db.deleted) == 1


def test_rule_evaluation_routes_use_tenant_session(monkeypatch):
    tenant_id = str(uuid4())
    fake_db = _FakeDB(first_value=_build_rule(tenant_id))

    def override_tenant():
        return tenant_id

    def override_tenant_session():
        yield fake_db

    class _FakeRuleEngine:
        def __init__(self, db):
            assert db is fake_db

        async def evaluate_rule(self, rule):
            return [{"id": "alert-1"}]

        async def evaluate_all_rules(self, tenant):
            assert tenant == tenant_id
            return {"total_rules": 1, "rule_results": [{"alerts": [{"id": "alert-1"}]}]}

    async def _create_alerts(resolved_tenant_id, alerts):
        assert resolved_tenant_id == tenant_id
        return {"created": len(alerts)}

    monkeypatch.setattr(rules_api, "RuleEngine", _FakeRuleEngine)
    monkeypatch.setattr(rules_api, "create_alerts", _create_alerts)
    app.dependency_overrides[rules_api.get_current_tenant] = override_tenant
    app.dependency_overrides[get_db] = _unexpected_dependency
    app.dependency_overrides[get_tenant_session] = override_tenant_session

    try:
        client = TestClient(app, raise_server_exceptions=False)
        evaluate_one = client.post(
            f"/api/v1/rules/{fake_db._first_value.id}/evaluate",
            headers={"X-Tenant-ID": tenant_id},
        )
        evaluate_all = client.post(
            "/api/v1/rules/evaluate/all",
            headers={"X-Tenant-ID": tenant_id},
        )
    finally:
        app.dependency_overrides.clear()

    assert evaluate_one.status_code == 200
    assert evaluate_all.status_code == 200


def test_enable_baseline_rules_uses_tenant_session_and_rejects_cross_tenant():
    tenant_id = str(uuid4())
    fake_db = _FakeDB()

    def override_tenant():
        return tenant_id

    def override_tenant_session():
        yield fake_db

    app.dependency_overrides[rules_api.get_current_tenant] = override_tenant
    app.dependency_overrides[get_db] = _unexpected_dependency
    app.dependency_overrides[get_tenant_session] = override_tenant_session

    try:
        client = TestClient(app, raise_server_exceptions=False)
        cross_tenant_response = client.post(
            "/api/v1/rules/enable",
            json={
                "tenant_id": str(uuid4()),
                "rule_keys": ["failed_logins"],
            },
            headers={"X-Tenant-ID": tenant_id},
        )
        ok_response = client.post(
            "/api/v1/rules/enable",
            json={
                "tenant_id": tenant_id,
                "rule_keys": ["failed_logins"],
            },
            headers={"X-Tenant-ID": tenant_id},
        )
    finally:
        app.dependency_overrides.clear()

    assert cross_tenant_response.status_code == 403
    assert cross_tenant_response.json()["detail"] == "Cross-tenant access denied"
    assert ok_response.status_code == 200
    assert ok_response.json()["tenant_id"] == tenant_id
