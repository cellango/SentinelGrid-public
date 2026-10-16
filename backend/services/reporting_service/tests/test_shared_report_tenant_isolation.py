"""Focused tenant-isolation coverage for public report shares."""

from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import shares as shares_api


@pytest.fixture(autouse=True)
def _disable_route_audit(monkeypatch):
    async def noop_log_event(self, payload):
        return None

    monkeypatch.setattr("app.services.report_access.AuditClient.log_event", noop_log_event)


def test_shared_report_access_uses_resolved_tenant_scope():
    """Public share access should resolve tenant scope before DB access."""
    calls = {"tenant": 0, "session": 0}
    report = SimpleNamespace(
        id="report-1",
        name="Quarterly Report",
        download_url="https://reports.example/report-1.pdf",
        format="PDF",
        status="completed",
        generated_at=datetime(2026, 3, 28, 12, 0, 0),
    )
    share = SimpleNamespace(
        id="share-1",
        tenant_id="11111111-1111-1111-1111-111111111111",
        report_id="report-1",
        password_hash=None,
        expires_at=None,
        access_count=0,
    )

    class _QueryResult:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return report

    class _FakeSession:
        def query(self, *args, **kwargs):
            return _QueryResult()

    test_app = FastAPI()
    test_app.include_router(shares_api.router)

    def override_resolve_shared_report_tenant():
        calls["tenant"] += 1
        return "11111111-1111-1111-1111-111111111111"

    def override_get_shared_report_session():
        calls["session"] += 1
        yield _FakeSession()

    test_app.dependency_overrides[shares_api.resolve_shared_report_tenant] = (
        override_resolve_shared_report_tenant
    )
    test_app.dependency_overrides[shares_api.get_shared_report_session] = (
        override_get_shared_report_session
    )

    original_get_share_record = shares_api.ShareService.get_share_record
    original_access_share = shares_api.ShareService.access_share
    shares_api.ShareService.get_share_record = lambda self, db, share_token: share
    shares_api.ShareService.access_share = lambda self, db, share_obj: None

    try:
        client = TestClient(test_app)
        response = client.get("/shared/share-token-1")
    finally:
        shares_api.ShareService.get_share_record = original_get_share_record
        shares_api.ShareService.access_share = original_access_share

    assert response.status_code == 200
    assert calls == {"tenant": 1, "session": 1}
