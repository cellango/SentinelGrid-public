from datetime import datetime
from uuid import uuid4
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_siem
from sg_core.db import get_tenant_session
from sg_core.models import Alert
from sg_core.opa import require_opa_allow
from sg_core.security import get_current_tenant


class _FakeQuery:
    def __init__(self, *, count_value=0, rows=None, row=None):
        self.count_value = count_value
        self.rows = list(rows or [])
        self.row = row

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def offset(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def count(self):
        return self.count_value

    def all(self):
        return self.rows

    def first(self):
        return self.row


class _FakeDB:
    def __init__(self, queries):
        self.queries = list(queries)
        self.added = []
        self.committed = False
        self.refreshed = []

    def query(self, *args, **kwargs):
        if not self.queries:
            raise AssertionError("Unexpected query() call")
        return self.queries.pop(0)

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.committed = True

    def refresh(self, value):
        self.refreshed.append(value)


class _ProxyResponse:
    def __init__(self, *, status_code=200, payload=None, text=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text if text is not None else json.dumps(self._payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.text)


@pytest.fixture
def siem_app():
    app = FastAPI()
    app.include_router(routes_siem.router, prefix="/api/v1/siem")
    return app


def _alert(*, tenant_id, alert_id=None, severity="high", status="open", raw_payload=None):
    return Alert(
        id=alert_id or uuid4(),
        tenant_id=tenant_id,
        source="wazuh",
        external_id=f"ext-{uuid4()}",
        title="Suspicious login",
        description="Investigate unusual login",
        raw_severity=severity,
        status=status,
        detection_time=datetime.utcnow(),
        asset_id="endpoint-22",
        user_identifier="analyst@example.com",
        raw_payload=raw_payload or {},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _client(app, fake_db, tenant_id: str):
    def _get_tenant():
        return tenant_id

    def _get_db():
        yield fake_db

    def _allow():
        return None

    app.dependency_overrides[get_current_tenant] = _get_tenant
    app.dependency_overrides[get_tenant_session] = _get_db
    app.dependency_overrides[require_opa_allow] = _allow

    return TestClient(app)


def _patch_async_client(monkeypatch, responses):
    calls = []
    queued = list(responses)

    def _next_response():
        if not queued:
            raise AssertionError("No queued proxy response available")
        return queued.pop(0)

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers=None, params=None):
            calls.append(
                {
                    "method": "GET",
                    "url": str(url),
                    "headers": headers or {},
                    "params": params,
                }
            )
            return _next_response()

        async def post(self, url, headers=None, params=None, json=None):
            calls.append(
                {
                    "method": "POST",
                    "url": str(url),
                    "headers": headers or {},
                    "params": params,
                    "json": json,
                }
            )
            return _next_response()

    monkeypatch.setattr(routes_siem.httpx, "AsyncClient", _FakeAsyncClient)
    return calls


def test_siem_stats_uses_tenant_scoped_dependency(siem_app):
    tenant_id = str(uuid4())
    fake_db = _FakeDB(
        [
            _FakeQuery(count_value=12),
            _FakeQuery(count_value=5),
            _FakeQuery(count_value=2),
            _FakeQuery(count_value=4),
            _FakeQuery(count_value=2),
            _FakeQuery(count_value=3),
            _FakeQuery(count_value=4),
            _FakeQuery(count_value=3),
            _FakeQuery(count_value=1),
            _FakeQuery(count_value=6),
        ]
    )

    with _client(siem_app, fake_db, tenant_id) as client:
        response = client.get("/api/v1/siem/stats")

    assert response.status_code == 200
    assert response.json()["alerts_count"] == 12
    assert response.json()["critical_alerts"] == 2
    assert response.json()["alerts_by_severity"] == {
        "critical": 2,
        "high": 3,
        "medium": 4,
        "low": 3,
    }
    assert response.json()["alerts_by_status"] == {
        "open": 5,
        "investigating": 1,
        "resolved": 6,
    }


def test_siem_alerts_list_uses_tenant_scoped_dependency(siem_app):
    tenant_uuid = uuid4()
    tenant_id = str(tenant_uuid)
    alerts = [
        _alert(tenant_id=tenant_uuid, severity="critical"),
        _alert(tenant_id=tenant_uuid, severity="high"),
    ]
    fake_db = _FakeDB([_FakeQuery(count_value=2, rows=alerts)])

    with _client(siem_app, fake_db, tenant_id) as client:
        response = client.get("/api/v1/siem/alerts?limit=50&offset=10&status=open&severity=high")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["limit"] == 50
    assert payload["offset"] == 10
    assert len(payload["alerts"]) == 2
    assert payload["items"] == payload["alerts"]
    assert payload["alerts"][0]["tenant_id"] == tenant_id


def test_get_siem_alert_scopes_lookup_to_authenticated_tenant(siem_app):
    tenant_uuid = uuid4()
    tenant_id = str(tenant_uuid)
    alert = _alert(tenant_id=tenant_uuid)
    fake_db = _FakeDB([_FakeQuery(row=alert)])

    with _client(siem_app, fake_db, tenant_id) as client:
        response = client.get(f"/api/v1/siem/alerts/{alert.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(alert.id)
    assert response.json()["tenant_id"] == tenant_id


def test_update_siem_alert_uses_tenant_scoped_dependency(siem_app):
    tenant_uuid = uuid4()
    tenant_id = str(tenant_uuid)
    alert = _alert(
        tenant_id=tenant_uuid,
        severity="medium",
        raw_payload={"assigned_to": "triage-queue", "comments": []},
    )
    fake_db = _FakeDB([_FakeQuery(row=alert)])

    with _client(siem_app, fake_db, tenant_id) as client:
        response = client.patch(
            f"/api/v1/siem/alerts/{alert.id}",
            json={
                "status": "investigating",
                "assigned_to": "secops-oncall",
                "due_date": "2026-03-29T12:00:00+00:00",
                "comments": "Escalated for review",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "investigating"
    assert payload["assigned_to"] == "secops-oncall"
    assert payload["due_date"] == "2026-03-29T12:00:00+00:00"
    audit_entries = payload["raw_payload"]["audit"]
    comments = payload["raw_payload"]["comments"]
    assert any(entry["text"] == "Status changed to investigating" for entry in audit_entries)
    assert any(entry["text"] == "Assigned to secops-oncall" for entry in audit_entries)
    assert comments[-1]["text"] == "Escalated for review"
    assert fake_db.added == [alert]
    assert fake_db.committed is True
    assert fake_db.refreshed == [alert]


def test_simple_log_search_forwards_authenticated_tenant(monkeypatch, siem_app):
    tenant_id = str(uuid4())
    fake_db = _FakeDB([])
    calls = _patch_async_client(monkeypatch, [_ProxyResponse(payload={"items": []})])

    with _client(siem_app, fake_db, tenant_id) as client:
        response = client.get(
            "/api/v1/siem/logs/search/simple?q=failed+login&event_type=auth&limit=25&offset=5",
            headers={"X-Realm": "realm-123"},
        )

    assert response.status_code == 200
    assert response.json() == {"items": []}
    assert calls[0]["headers"]["X-Tenant-ID"] == tenant_id
    assert calls[0]["headers"]["X-Realm"] == "realm-123"
    assert calls[0]["params"]["q"] == "failed login"
    assert calls[0]["url"].endswith("/siem/logs/search/simple")


def test_advanced_log_search_forwards_authenticated_tenant(monkeypatch, siem_app):
    tenant_id = str(uuid4())
    fake_db = _FakeDB([])
    calls = _patch_async_client(monkeypatch, [_ProxyResponse(payload={"total": 1})])

    with _client(siem_app, fake_db, tenant_id) as client:
        response = client.post(
            "/api/v1/siem/logs/search",
            json={"query": {"match_all": {}}},
            headers={"X-Realm": "realm-123"},
        )

    assert response.status_code == 200
    assert response.json() == {"total": 1}
    assert calls[0]["headers"]["X-Tenant-ID"] == tenant_id
    assert calls[0]["headers"]["X-Realm"] == "realm-123"
    assert calls[0]["json"] == {"query": {"match_all": {}}}
    assert calls[0]["url"].endswith("/siem/logs/search")


def test_detection_rule_detail_forwards_authenticated_tenant(monkeypatch, siem_app):
    tenant_id = str(uuid4())
    fake_db = _FakeDB([])
    calls = _patch_async_client(monkeypatch, [_ProxyResponse(payload={"id": "rule-123"})])

    with _client(siem_app, fake_db, tenant_id) as client:
        response = client.get(
            "/api/v1/siem/detection-rules/rule-123",
            headers={"X-Realm": "realm-123"},
        )

    assert response.status_code == 200
    assert response.json() == {"id": "rule-123"}
    assert calls[0]["headers"]["X-Tenant-ID"] == tenant_id
    assert calls[0]["headers"]["X-Realm"] == "realm-123"
    assert calls[0]["url"].endswith("/detection-rules/rule-123")


def test_entity_timeline_forwards_authenticated_tenant(monkeypatch, siem_app):
    tenant_id = str(uuid4())
    fake_db = _FakeDB([])
    calls = _patch_async_client(monkeypatch, [_ProxyResponse(payload={"events": []})])

    with _client(siem_app, fake_db, tenant_id) as client:
        response = client.get(
            "/api/v1/siem/entity-timeline?entity_type=user&entity_id=alice@example.com&limit=50",
            headers={"X-Realm": "realm-123"},
        )

    assert response.status_code == 200
    assert response.json() == {"events": []}
    assert calls[0]["headers"]["X-Tenant-ID"] == tenant_id
    assert calls[0]["headers"]["X-Realm"] == "realm-123"
    assert calls[0]["params"]["entity_type"] == "user"
    assert calls[0]["params"]["entity_id"] == "alice@example.com"
    assert calls[0]["url"].endswith("/siem/entity-timeline")
