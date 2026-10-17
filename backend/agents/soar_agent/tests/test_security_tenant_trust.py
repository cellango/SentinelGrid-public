"""Legacy credentials cannot regain SOAR admission, including development/test."""
from unittest.mock import Mock
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.api import detection_events
from app.core.config import settings

TEST_TENANT_ID="11111111-1111-4111-8111-111111111111"

@pytest.mark.parametrize("environment",["development","test","production"])
@pytest.mark.parametrize("authorization",[None,"Bearer disposable-local-only","Bearer forged.jwt.token"])
def test_legacy_tenant_authority_is_rejected_in_every_environment(monkeypatch,environment,authorization):
    monkeypatch.setattr(settings,"ENVIRONMENT",environment)
    h={"X-Tenant-ID":TEST_TENANT_ID}
    if authorization:h["Authorization"]=authorization
    with TestClient(app) as client:r=client.get("/soar/playbooks",headers=h)
    assert r.status_code==401

@pytest.mark.parametrize("hint",[TEST_TENANT_ID,"not-a-uuid","22222222-2222-4222-8222-222222222222"])
def test_standalone_detection_router_denies_before_incident_or_session(monkeypatch,hint):
    effect=Mock(side_effect=AssertionError("No incident/provider constructor"))
    monkeypatch.setattr(detection_events,"IncidentCreator",effect)
    a=FastAPI();a.include_router(detection_events.router,prefix="/api/v1")
    with TestClient(a) as client:r=client.post("/api/v1/detection-events/ingest",
        headers={"Authorization":"Bearer disposable-local-only","X-Tenant-ID":hint},
        json={"sg":{"tenant_id":TEST_TENANT_ID,"alert_type":"phishing","approved":True}})
    assert r.status_code==503;effect.assert_not_called()
