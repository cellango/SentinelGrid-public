"""Snapshot reads include model calls and require their own admitted contract."""
from unittest.mock import Mock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import snapshot

TEST_ID="11111111-1111-4111-8111-111111111111"

@pytest.mark.parametrize("hint",[TEST_ID,"22222222-2222-4222-8222-222222222222","default"])
def test_standalone_snapshot_router_rejects_before_service_factory(monkeypatch,hint):
    factory=Mock(side_effect=AssertionError("Snapshot provider/model clients must not initialize"))
    monkeypatch.setattr(snapshot,"SnapshotService",factory)
    app=FastAPI();app.include_router(snapshot.router)
    with TestClient(app) as client:
        r=client.get(f"/tenant/{TEST_ID}/security-snapshot",headers={
            "Authorization":"Bearer disposable-local-only","X-Tenant-ID":hint})
    assert r.status_code==503;factory.assert_not_called()
