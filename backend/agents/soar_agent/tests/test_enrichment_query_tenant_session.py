"""Caller-selected query tenant cannot authorize enrichment/containment effects."""
from unittest.mock import Mock
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app.api import enrichment,phishing_containment

TEST_ID="11111111-1111-4111-8111-111111111111"

@pytest.mark.parametrize("method,path",[("POST",f"/api/v1/enrichment/ticket/{TEST_ID}"),
 ("GET",f"/api/v1/enrichment/ticket/{TEST_ID}"),("POST","/api/v1/playbooks/phishing-containment/execute")])
def test_query_context_does_not_reach_providers_or_storage(monkeypatch,method,path):
    factory=Mock(side_effect=AssertionError("No provider/client creation"))
    monkeypatch.setattr(enrichment,"EnrichmentService",factory)
    monkeypatch.setattr(phishing_containment,"PhishingContainmentPlaybook",factory)
    with TestClient(app) as client:r=client.request(method,path,params={"tenant_id":TEST_ID},
        json={"phishing_report_id":TEST_ID,"approved":True} if method=="POST" else None)
    assert r.status_code==503;factory.assert_not_called()
