"""Standalone response routers cannot restore unqualified workload/action calls."""
from unittest.mock import Mock
from uuid import UUID
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from app.api import response
from app.core import security

TEST_ID="11111111-1111-4111-8111-111111111111"
OPERATIONS=[("POST",f"/api/v1/orchestrator/alerts/{TEST_ID}/orchestrate"),
 ("POST",f"/api/v1/orchestrator/findings/{TEST_ID}/orchestrate?finding_type=iam_finding"),
 ("GET",f"/api/v1/orchestrator/executions/{TEST_ID}/status"),
 ("GET","/api/v1/orchestrator/reports/executions")]

@pytest.mark.parametrize("method,path",OPERATIONS)
@pytest.mark.parametrize("hint",[None,"default",TEST_ID])
def test_response_operations_unavailable_before_orchestrator_construction(monkeypatch,method,path,hint):
    effect=Mock(side_effect=AssertionError("Unqualified orchestrator must not initialize"))
    monkeypatch.setattr(response,"ResponseOrchestrator",effect)
    app=FastAPI();app.include_router(response.router)
    headers={"Authorization":"Bearer disposable-local-only"}
    if hint is not None:headers["X-Tenant-ID"]=hint
    with TestClient(app) as client:
        r=client.request(method,path,headers=headers,json={"approved":True,"roles":["PLATFORM_ADMIN"]} if method=="POST" else None)
    assert r.status_code==503;effect.assert_not_called()


def test_compatibility_tenant_helper_does_not_admit_arbitrary_route():
    app=FastAPI()
    @app.get("/tenant")
    def route(tenant_id:UUID=Depends(security.get_current_tenant)):return {"tenant_id":str(tenant_id)}
    with TestClient(app) as client:r=client.get("/tenant",headers={"X-Tenant-ID":TEST_ID})
    assert r.status_code==503
