from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_current_tenant, get_tenant_session
from app.main import app


class FakeResult:
    def __init__(self, *, row=None, rows=None, scalar_value=None, rowcount=1):
        self._row = row
        self._rows = rows or []
        self._scalar_value = scalar_value
        self.rowcount = rowcount

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows

    def scalar(self):
        return self._scalar_value


class FakeDB:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def execute(self, statement, params=None):
        self.calls.append({"sql": str(statement), "params": params or {}})
        if self.responses:
            return self.responses.pop(0)
        return FakeResult()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


@pytest.fixture
def audit_client():
    tenant_id = uuid4()
    fake_db = FakeDB()

    def _get_tenant():
        return tenant_id

    def _get_db():
        yield fake_db

    app.dependency_overrides[get_current_tenant] = _get_tenant
    app.dependency_overrides[get_tenant_session] = _get_db

    with TestClient(app) as client:
        yield client, fake_db, tenant_id

    app.dependency_overrides.clear()


def test_write_audit_log_rejects_foreign_tenant_body(audit_client):
    client, fake_db, _tenant_id = audit_client

    response = client.post(
        "/api/v1/audit/logs",
        json={
            "tenant_id": str(uuid4()),
            "realm_name": "acme",
            "action": "user.created",
        },
    )

    assert response.status_code == 403
    assert fake_db.calls == []


def test_write_audit_log_uses_authenticated_tenant(audit_client):
    client, fake_db, tenant_id = audit_client
    created_id = uuid4()
    ts = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)
    fake_db.responses = [FakeResult(row=(created_id, ts))]

    response = client.post(
        "/api/v1/audit/logs",
        json={
            "tenant_id": str(tenant_id),
            "realm_name": "acme",
            "action": "user.created",
            "metadata": {"source": "test"},
        },
    )

    assert response.status_code == 201
    assert response.json() == {"id": str(created_id), "timestamp": ts.isoformat()}
    assert fake_db.calls[0]["params"]["tenant_id"] == str(tenant_id)
    assert fake_db.committed is True


def test_get_audit_logs_scopes_query_to_authenticated_tenant(audit_client):
    client, fake_db, tenant_id = audit_client
    log_id = uuid4()
    ts = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)
    fake_db.responses = [
        FakeResult(
            rows=[
                (
                    log_id,
                    tenant_id,
                    "acme",
                    ts,
                    "user.created",
                    "iam",
                    "user-1",
                    "owner@example.com",
                    "user",
                    "user-1",
                    "Owner",
                    True,
                    None,
                    None,
                    {"source": "test"},
                )
            ]
        )
    ]

    response = client.get(f"/api/v1/audit/logs?tenant_id={tenant_id}&realm_name=acme&limit=10&offset=5")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["logs"][0]["tenant_id"] == str(tenant_id)
    assert fake_db.calls[0]["params"]["tenant_id"] == str(tenant_id)


def test_get_audit_logs_can_filter_by_action_category(audit_client):
    client, fake_db, tenant_id = audit_client

    response = client.get(
        f"/api/v1/audit/logs?tenant_id={tenant_id}&realm_name=acme&action_category=compliance"
    )

    assert response.status_code == 200
    assert fake_db.calls[0]["params"]["action_category"] == "compliance"
    assert "action_category = :action_category" in fake_db.calls[0]["sql"]


def test_get_audit_log_returns_detail_for_authenticated_tenant(audit_client):
    client, fake_db, tenant_id = audit_client
    log_id = uuid4()
    ts = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)
    fake_db.responses = [
        FakeResult(
            row=(
                log_id,
                tenant_id,
                "acme",
                ts,
                "user.created",
                "iam",
                "user-1",
                "owner@example.com",
                ["admin"],
                "user",
                "user-1",
                "Owner",
                None,
                None,
                None,
                True,
                None,
                None,
                "pytest",
                "req-1",
                "sess-1",
                {"source": "test"},
            )
        )
    ]

    response = client.get(f"/api/v1/audit/logs/{log_id}?tenant_id={tenant_id}&realm_name=acme")

    assert response.status_code == 200
    assert response.json()["id"] == str(log_id)
    assert response.json()["tenant_id"] == str(tenant_id)


def test_get_ai_activity_returns_items_and_total(audit_client):
    client, fake_db, tenant_id = audit_client
    ts = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)
    fake_db.responses = [
        FakeResult(rows=[(uuid4(), tenant_id, "acme", ts, "ai_activity", "user-1", "owner@example.com", {"query": "hello"})]),
        FakeResult(scalar_value=7),
    ]

    response = client.get(f"/api/v1/audit/ai-activity?tenant_id={tenant_id}&realm_name=acme&limit=25")

    assert response.status_code == 200
    assert response.json()["count"] == 7
    assert response.json()["items"][0]["tenant_id"] == str(tenant_id)


def test_write_ai_activity_uses_authenticated_tenant(audit_client):
    client, fake_db, tenant_id = audit_client
    created_id = uuid4()
    ts = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)
    fake_db.responses = [FakeResult(row=(created_id, ts))]

    response = client.post(
        "/api/v1/audit/ai-activity",
        json={
            "tenant_id": str(tenant_id),
            "realm_name": "acme",
            "action": "ai.query",
            "metadata": {"query": "hello"},
        },
    )

    assert response.status_code == 201
    assert fake_db.calls[0]["params"]["tenant_id"] == str(tenant_id)
    assert fake_db.calls[0]["params"]["action_category"] == "ai"


def test_get_audit_stats_scopes_to_authenticated_tenant(audit_client):
    client, fake_db, tenant_id = audit_client
    fake_db.responses = [FakeResult(row=(20, 18, 2, 3, 4, 5, 6, 2, 9))]

    response = client.get(f"/api/v1/audit/stats?tenant_id={tenant_id}&realm_name=acme")

    assert response.status_code == 200
    assert response.json()["total_events"] == 20
    assert response.json()["unique_actors"] == 9
    assert fake_db.calls[0]["params"]["tenant_id"] == str(tenant_id)


def test_export_audit_logs_returns_csv_payload(audit_client):
    client, fake_db, tenant_id = audit_client
    ts = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)
    fake_db.responses = [
        FakeResult(rows=[(ts, "user.created", "user-1", "owner@example.com", "user", "user-1", "Owner", True, None, None)])
    ]

    response = client.get(
        f"/api/v1/audit/export?tenant_id={tenant_id}&realm_name=acme"
        "&start_date=2026-03-01T00:00:00Z&end_date=2026-03-31T00:00:00Z&format=csv"
    )

    assert response.status_code == 200
    assert response.json()["format"] == "csv"
    assert "Timestamp,Action,Actor User ID" in response.json()["data"]


def test_get_retention_policies_scopes_to_authenticated_tenant(audit_client):
    client, fake_db, tenant_id = audit_client
    fake_db.responses = [
        FakeResult(
            rows=[
                (
                    uuid4(),
                    tenant_id,
                    "default",
                    90,
                    365,
                    2555,
                    False,
                    None,
                    True,
                    True,
                    True,
                    datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc),
                    datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc),
                )
            ]
        )
    ]

    response = client.get(f"/api/v1/audit/retention/policies?tenant_id={tenant_id}")

    assert response.status_code == 200
    assert response.json()["policies"][0]["tenant_id"] == str(tenant_id)
    assert fake_db.calls[0]["params"]["tenant_id"] == str(tenant_id)


def test_create_retention_policy_uses_authenticated_tenant(audit_client):
    client, fake_db, tenant_id = audit_client
    policy_id = uuid4()
    fake_db.responses = [FakeResult(row=(policy_id,))]

    response = client.post(
        f"/api/v1/audit/retention/policies?tenant_id={tenant_id}",
        json={"policy_name": "default"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(policy_id)
    assert fake_db.calls[0]["params"]["tenant_id"] == str(tenant_id)


def test_update_retention_policy_rejects_foreign_tenant(audit_client):
    client, fake_db, _tenant_id = audit_client

    response = client.put(
        f"/api/v1/audit/retention/policies/{uuid4()}?tenant_id={uuid4()}",
        json={"hot_retention_days": 120},
    )

    assert response.status_code == 403
    assert fake_db.calls == []
