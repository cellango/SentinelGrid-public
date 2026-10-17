"""Required webhook/catalog operations stay unavailable before old data helpers."""
from unittest.mock import Mock
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.api import detection_events,ootb_playbooks
from app.core import database

TEST_ID="11111111-1111-4111-8111-111111111111"

@pytest.mark.parametrize("path,headers",[
 ("/api/v1/detection-events/ingest",{"Authorization":"Bearer disposable-local-only","X-Tenant-ID":TEST_ID}),
 ("/api/v1/detection-events/ingest",{"Authorization":"Bearer disposable-local-only","X-Tenant-ID":"22222222-2222-4222-8222-222222222222"}),
 ("/soar/ootb/seed",{"X-Tenant-ID":TEST_ID}),
 ("/api/v1/thehive/case/update",{"X-API-Key":"synthetic","X-Tenant-ID":TEST_ID}),
 ("/api/v1/thehive/observable/update",{"X-Tenant-ID":TEST_ID}),
])
def test_required_critical_operations_reject_before_storage_or_side_effects(monkeypatch,path,headers):
    effect=Mock(side_effect=AssertionError("No legacy store or effect"))
    monkeypatch.setattr(detection_events,"IncidentCreator",effect)
    monkeypatch.setattr(ootb_playbooks,"seed_all_ootb_playbooks",effect)
    monkeypatch.setattr(database,"SessionLocal",effect)
    with TestClient(app) as client:r=client.post(path,headers=headers,json={"sg":{"tenant_id":TEST_ID},"approved":True})
    assert r.status_code==503;effect.assert_not_called()
