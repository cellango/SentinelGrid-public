from pathlib import Path
import os
import sys
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

os.environ.setdefault("DB_HOST", "localhost")

from app.main import app
from app.api import framework_selections as selections_api
from app.core.database import get_current_tenant, get_tenant_session
from app.services.framework_selection import (
    FrameworkSelectionService,
    normalize_selection_framework_id,
)
from sg_core.service_metrics import get_service_metrics, reset_service_metrics


class FakeResult:
    def __init__(self, first_row=None, rows=None):
        self._first_row = first_row
        self._rows = rows or []

    def first(self):
        return self._first_row

    def mappings(self):
        return self

    def all(self):
        return self._rows


class FakeDB:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []
        self.inserted_frameworks = []

    def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}
        self.calls.append({"sql": sql, "params": params})
        if sql.lstrip().upper().startswith("INSERT INTO TENANT_FRAMEWORK_SELECTIONS"):
            self.inserted_frameworks.append(
                {
                    "framework_id": params["framework_id"],
                    "status": params["status"],
                    "source": "onboarding_trust_profile" if "ON CONFLICT" in sql else "manual",
                }
            )
            return FakeResult()
        if self.results:
            return self.results.pop(0)
        return FakeResult()


class FakeWorkflowService:
    def __init__(self, calls):
        self.calls = calls

    async def create_recommendation_and_task(self, db, **kwargs):
        self.calls.setdefault("workflow", []).append({"db": db, "kwargs": kwargs})
        return {"id": "recommendation-1"}


def test_selection_framework_normalization_allows_catalog_and_starter_options():
    assert normalize_selection_framework_id("SOC 2") == "soc2"
    assert normalize_selection_framework_id("pci") == "pci_dss"
    assert normalize_selection_framework_id("iso_27001") == "iso27001"
    assert normalize_selection_framework_id("customer_questionnaire") == "customer_questionnaires"
    assert normalize_selection_framework_id("unknown") is None


def test_list_selections_seeds_from_onboarding_trust_profile_when_empty():
    tenant_id = str(uuid4())
    db = FakeDB(
        [
            FakeResult(first_row={"count": 0}),
            FakeResult(
                first_row={
                    "tenant_services": {},
                    "onboarding_services": {
                        "trustProfile": {
                            "frameworks": ["soc2", "iso27001", "unknown"],
                        }
                    },
                }
            ),
            FakeResult(
                rows=[
                    {
                        "framework_id": "soc2",
                        "status": "active",
                        "priority": 1,
                        "target_date": None,
                        "selected_by": "onboarding_trust_profile",
                        "selected_at": "2026-04-27T00:00:00Z",
                        "updated_at": "2026-04-27T00:00:00Z",
                        "source": "onboarding_trust_profile",
                    },
                    {
                        "framework_id": "iso27001",
                        "status": "evaluating",
                        "priority": 2,
                        "target_date": None,
                        "selected_by": "onboarding_trust_profile",
                        "selected_at": "2026-04-27T00:00:00Z",
                        "updated_at": "2026-04-27T00:00:00Z",
                        "source": "onboarding_trust_profile",
                    },
                ]
            ),
        ]
    )

    payload = FrameworkSelectionService().list_selections(db, tenant_id)

    assert [item["framework_id"] for item in db.inserted_frameworks] == ["soc2", "iso27001"]
    assert db.inserted_frameworks[0]["status"] == "active"
    assert db.inserted_frameworks[1]["status"] == "evaluating"
    assert payload["tenant_id"] == tenant_id
    assert payload["count"] == 2
    assert payload["items"][1]["framework_name"] == "ISO 27001 Starter Pack"
    assert any(item["framework_id"] == "hipaa" for item in payload["available_frameworks"])


def test_replace_selections_rejects_empty_selection_set():
    service = FrameworkSelectionService()
    with pytest.raises(ValueError, match="At least one framework selection is required"):
        service.replace_selections(FakeDB([]), str(uuid4()), [])


@pytest.fixture
def selection_client(monkeypatch):
    tenant_id = str(uuid4())
    fake_db = object()
    calls = {}

    class FakeSelectionService:
        def list_selections(self, db, resolved_tenant_id):
            calls["list"] = {"db": db, "tenant_id": resolved_tenant_id}
            return {"tenant_id": resolved_tenant_id, "items": [], "count": 0, "available_frameworks": []}

        def replace_selections(self, db, resolved_tenant_id, selections, selected_by=None):
            calls["replace"] = {
                "db": db,
                "tenant_id": resolved_tenant_id,
                "selections": selections,
                "selected_by": selected_by,
            }
            return {
                "tenant_id": resolved_tenant_id,
                "items": selections,
                "count": len(selections),
                "available_frameworks": [],
            }

    def override_get_current_tenant():
        return tenant_id

    def override_get_tenant_session():
        yield fake_db

    app.dependency_overrides[get_current_tenant] = override_get_current_tenant
    app.dependency_overrides[get_tenant_session] = override_get_tenant_session
    app.dependency_overrides[selections_api.get_compliance_agent_workflow_service] = lambda: FakeWorkflowService(calls)
    monkeypatch.setattr(selections_api, "framework_selection_service", FakeSelectionService())

    try:
        with TestClient(app) as client:
            yield client, tenant_id, calls
    finally:
        app.dependency_overrides.clear()


def test_framework_selection_endpoints_use_tenant_context(selection_client):
    client, tenant_id, calls = selection_client
    reset_service_metrics("compliance-service")

    get_response = client.get("/api/v1/compliance/framework-selections", headers={"X-Tenant-ID": tenant_id})

    assert get_response.status_code == 200
    assert calls["list"]["tenant_id"] == tenant_id

    put_response = client.put(
        "/api/v1/compliance/framework-selections",
        headers={"X-Tenant-ID": tenant_id, "X-User-ID": "user-123", "Authorization": "Bearer user-token"},
        json={
            "tenant_id": tenant_id,
            "selections": [{"framework_id": "soc2", "status": "active", "priority": 1}],
        },
    )

    assert put_response.status_code == 200
    assert calls["replace"]["tenant_id"] == tenant_id
    assert calls["replace"]["selected_by"] == "user-123"
    assert calls["replace"]["selections"] == [{"framework_id": "soc2", "status": "active", "priority": 1, "target_date": None}]
    assert calls["workflow"][0]["kwargs"]["tenant_id"] == tenant_id
    assert calls["workflow"][0]["kwargs"]["created_by"] == "user-123"
    assert calls["workflow"][0]["kwargs"]["authorization"] == "Bearer user-token"
    metrics = get_service_metrics("compliance-service").snapshot()
    assert metrics["counters"]["compliance_framework_selection_changes_total"]["series"][
        "framework_id=soc2,status=active"
    ] == 1


def test_framework_selection_endpoints_reject_cross_tenant(selection_client):
    client, _tenant_id, calls = selection_client
    other_tenant_id = str(uuid4())

    response = client.put(
        "/api/v1/compliance/framework-selections",
        headers={"X-Tenant-ID": other_tenant_id},
        json={"selections": [{"framework_id": "soc2"}]},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"
    assert "replace" not in calls
