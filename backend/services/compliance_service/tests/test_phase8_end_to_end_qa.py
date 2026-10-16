"""Phase 8.2 executable QA journey for compliance-service surfaces."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

os.environ.setdefault("DB_HOST", "localhost")

from sg_core.security import get_current_payload  # noqa: E402

from app.api import agent_workflow, coverage as coverage_api, evidence as evidence_api, framework_selections  # noqa: E402
from app.core.database import get_current_tenant, get_tenant_session  # noqa: E402
from app.main import app  # noqa: E402


TENANT_ID = "00000000-0000-0000-0000-000000000111"
OTHER_TENANT_ID = "00000000-0000-0000-0000-000000000222"
VALID_HASH = "b" * 64


class ScenarioState:
    def __init__(self):
        self.selections = [
            self.selection("soc2", "active", 1, "onboarding_trust_profile"),
            self.selection("hipaa", "evaluating", 2, "onboarding_trust_profile"),
        ]
        self.evidence: dict[str, dict] = {}
        self.packages: dict[str, dict] = {}
        self.tasks: list[dict] = []
        self.recommendations: list[dict] = []

    def selection(self, framework_id: str, status: str, priority: int, source: str) -> dict:
        names = {"soc2": "SOC 2", "hipaa": "HIPAA Security Rule"}
        return {
            "framework_id": framework_id,
            "framework_code": framework_id.upper(),
            "framework_name": names.get(framework_id, framework_id),
            "runtime_support": "native" if framework_id == "soc2" else "catalog",
            "control_count": 9 if framework_id == "soc2" else 3,
            "status": status,
            "priority": priority,
            "target_date": None,
            "selected_by": source,
            "selected_at": "2026-04-28T00:00:00Z",
            "updated_at": "2026-04-28T00:00:00Z",
            "source": source,
        }


class ScenarioFrameworkSelectionService:
    def __init__(self, state: ScenarioState):
        self.state = state

    def list_selections(self, db, tenant_id):
        return {
            "tenant_id": tenant_id,
            "items": list(self.state.selections),
            "count": len(self.state.selections),
            "available_frameworks": [
                self.state.selection("soc2", "active", 1, "catalog"),
                self.state.selection("hipaa", "evaluating", 2, "catalog"),
            ],
        }

    def replace_selections(self, db, tenant_id, selections, selected_by=None):
        self.state.selections = [
            self.state.selection(
                item["framework_id"],
                item.get("status") or "active",
                item.get("priority") or index,
                "manual",
            )
            | {"selected_by": selected_by or "system"}
            for index, item in enumerate(selections, start=1)
        ]
        return self.list_selections(db, tenant_id)


class ScenarioEvidenceRepository:
    def __init__(self, state: ScenarioState):
        self.state = state

    def create_collection_task(self, db, tenant_id, request, actor_id=None):
        task = {
            "id": f"task-{len(self.state.tasks) + 1}",
            "tenant_id": tenant_id,
            "status": request["status"],
            "task_type": request["task_type"],
            "source_system": request.get("source_system"),
            "requested_by": actor_id,
        }
        self.state.tasks.append(task)
        return task

    def list_collection_tasks(self, db, tenant_id, filters, limit=50, offset=0):
        return {"tenant_id": tenant_id, "items": self.state.tasks[offset : offset + limit], "count": len(self.state.tasks)}

    def create_evidence_item(self, db, tenant_id, request, actor_id=None):
        evidence_id = f"ev-{len(self.state.evidence) + 1}"
        item = {
            **request,
            "id": evidence_id,
            "tenant_id": tenant_id,
            "created_by": actor_id,
            "review_status": request.get("review_status") or "pending",
        }
        self.state.evidence[evidence_id] = item
        return item

    def list_evidence(self, db, tenant_id, filters, limit=50, offset=0):
        items = [item for item in self.state.evidence.values() if item["tenant_id"] == tenant_id]
        return {"tenant_id": tenant_id, "items": items[offset : offset + limit], "count": len(items), "limit": limit, "offset": offset}

    def count_stale_evidence(self, db, tenant_id):
        return 0

    def review_evidence_item(self, db, tenant_id, evidence_id, request, actor_id=None):
        item = self.state.evidence[evidence_id]
        item["review_status"] = request["review_status"]
        item["reviewer"] = actor_id
        item["review_notes"] = request.get("review_notes")
        return {
            "evidence": item,
            "review": {
                "review_status": request["review_status"],
                "reviewer": actor_id,
                "review_notes": request.get("review_notes"),
            },
        }

    def create_package(self, db, tenant_id, request, actor_id=None):
        package_id = "pkg-soc2-q2"
        item_ids = request.get("evidence_item_ids") or []
        package = {
            "id": package_id,
            "tenant_id": tenant_id,
            "package_name": request["package_name"],
            "framework_id": request.get("framework_id"),
            "evidence_item_ids": item_ids,
            "items": [self.state.evidence[item_id] for item_id in item_ids],
            "created_by": actor_id,
            "exports": [],
        }
        self.state.packages[package_id] = package
        return package

    def list_packages(self, db, tenant_id, filters, limit=50, offset=0):
        items = [item for item in self.state.packages.values() if item["tenant_id"] == tenant_id]
        return {"tenant_id": tenant_id, "items": items[offset : offset + limit], "count": len(items)}

    def get_package(self, db, tenant_id, package_id):
        return self.state.packages[package_id]

    def create_export(self, db, tenant_id, package_id, request, actor_id=None):
        export = {
            "id": "export-1",
            "tenant_id": tenant_id,
            "package_id": package_id,
            "export_format": request["export_format"],
            "status": "requested",
            "manifest": {"evidence_item_count": len(self.state.packages[package_id]["items"])},
        }
        self.state.packages[package_id]["exports"].append(export)
        return export


class ScenarioWorkflowService:
    def __init__(self, state: ScenarioState):
        self.state = state

    async def create_recommendation_and_task(self, db, **kwargs):
        recommendation_id = f"rec-{len(self.state.recommendations) + 1}"
        recommendation = {
            "id": recommendation_id,
            "tenant_id": kwargs["tenant_id"],
            "state": "proposed",
            "trigger_type": kwargs.get("trigger_type"),
            "recommendation_type": kwargs.get("recommendation_type"),
            "framework_id": kwargs.get("framework_id"),
            "control_id": kwargs.get("control_id"),
            "metadata": kwargs.get("metadata") or {},
            "created_by": kwargs.get("created_by"),
        }
        self.state.recommendations.append(recommendation)
        return recommendation


class ScenarioRecommendationRepository:
    def __init__(self, state: ScenarioState):
        self.state = state

    def list_recommendations(self, db, tenant_id, **filters):
        items = [item for item in self.state.recommendations if item["tenant_id"] == tenant_id]
        for key in ("state", "trigger_type", "framework_id", "control_id"):
            if filters.get(key):
                items = [item for item in items if item.get(key) == filters[key]]
        return {"tenant_id": tenant_id, "items": items, "count": len(items), "limit": filters["limit"], "offset": filters["offset"]}

    def record_decision(self, db, **kwargs):
        for item in self.state.recommendations:
            if item["id"] == kwargs["recommendation_id"] and item["tenant_id"] == kwargs["tenant_id"]:
                item["state"] = kwargs["state"]
                item["decided_by"] = kwargs["decided_by"]
                item["decision_notes"] = kwargs["decision_notes"]
                return item
        return None


def _evidence_request(tenant_id: str, title: str, control_id: str = "CC6.1") -> dict:
    return {
        "tenant_id": tenant_id,
        "evidence_type": "configuration",
        "title": title,
        "source_system": "iam_agent",
        "source_resource_id": title.lower().replace(" ", "-"),
        "collector": "iam_agent",
        "collection_method": "api",
        "valid_from": "2026-04-01T00:00:00Z",
        "valid_until": "2026-07-01T00:00:00Z",
        "hash_sha256": VALID_HASH,
        "storage_uri": f"s3://evidence/{tenant_id}/{title}.json",
        "summary": "IAM evidence collected for launch QA.",
        "control_links": [{"control_id": control_id, "framework_id": "soc2"}],
    }


def _coverage_payload_from_state(state: ScenarioState, tenant_id: str, limit: int = 100, offset: int = 0) -> dict:
    accepted_soc2_evidence = [
        item
        for item in state.evidence.values()
        if item.get("review_status") == "accepted"
        and any(link.get("framework_id") == "soc2" and link.get("control_id") == "CC6.1" for link in item.get("control_links", []))
    ]
    soc2_status = "operating" if accepted_soc2_evidence else "needs_evidence"
    return {
        "tenant_id": tenant_id,
        "items": [
            {
                "tenant_id": tenant_id,
                "framework_id": "soc2",
                "framework_name": "SOC 2",
                "selection_status": "active",
                "status": soc2_status,
                "controls": [
                    {
                        "control_id": "CC6.1",
                        "title": "Logical access",
                        "status": soc2_status,
                        "evidence_items": len(accepted_soc2_evidence),
                        "gaps": [] if accepted_soc2_evidence else [{"id": "gap-soc2", "severity": "high"}],
                    }
                ],
            },
            {
                "tenant_id": tenant_id,
                "framework_id": "hipaa",
                "framework_name": "HIPAA Security Rule",
                "selection_status": "active",
                "status": "needs_evidence",
                "controls": [
                    {
                        "control_id": "164.308(a)(1)",
                        "title": "Security management process",
                        "status": "needs_evidence",
                        "gaps": [
                            {
                                "id": "gap-hipaa-risk-analysis",
                                "severity": "high",
                                "title": "Risk analysis evidence missing",
                            }
                        ],
                    }
                ],
            },
        ],
        "count": 2,
        "limit": limit,
        "offset": offset,
        "source": "phase8_e2e_test",
    }


def test_phase8_compliance_customer_journey(monkeypatch):
    state = ScenarioState()
    fake_db = object()
    workflow = ScenarioWorkflowService(state)

    def override_tenant_session():
        yield fake_db

    app.dependency_overrides[get_current_tenant] = lambda: TENANT_ID
    app.dependency_overrides[get_tenant_session] = override_tenant_session
    app.dependency_overrides[get_current_payload] = lambda: {
        "tenant_id": TENANT_ID,
        "user_id": "qa-user",
        "roles": ["compliance_manager", "evidence_reviewer"],
    }
    app.dependency_overrides[framework_selections.get_compliance_agent_workflow_service] = lambda: workflow
    app.dependency_overrides[evidence_api.get_compliance_agent_workflow_service] = lambda: workflow
    app.dependency_overrides[coverage_api.get_compliance_agent_workflow_service] = lambda: workflow
    app.dependency_overrides[agent_workflow.get_recommendation_repository] = lambda: ScenarioRecommendationRepository(state)

    monkeypatch.setattr(framework_selections, "framework_selection_service", ScenarioFrameworkSelectionService(state))
    monkeypatch.setattr(evidence_api, "evidence_repository", ScenarioEvidenceRepository(state))
    monkeypatch.setattr(coverage_api, "_load_soc2_reporting_inputs", lambda db, tenant_id: {})
    monkeypatch.setattr(
        coverage_api,
        "build_multi_framework_coverage_payload",
        lambda db, tenant_id, inputs, limit=100, offset=0: _coverage_payload_from_state(state, tenant_id, limit, offset),
    )

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            onboarding_selection = client.get("/api/v1/compliance/framework-selections", headers={"X-Tenant-ID": TENANT_ID})
            assert onboarding_selection.status_code == 200
            assert [item["framework_id"] for item in onboarding_selection.json()["items"]] == ["soc2", "hipaa"]
            assert onboarding_selection.json()["items"][0]["source"] == "onboarding_trust_profile"

            dashboard_selection = client.put(
                "/api/v1/compliance/framework-selections",
                headers={"X-Tenant-ID": TENANT_ID, "X-User-ID": "qa-user"},
                json={
                    "tenant_id": TENANT_ID,
                    "selections": [
                        {"framework_id": "soc2", "status": "active", "priority": 1},
                        {"framework_id": "hipaa", "status": "active", "priority": 2},
                    ],
                },
            )
            assert dashboard_selection.status_code == 200
            assert [item["status"] for item in dashboard_selection.json()["items"]] == ["active", "active"]

            task_response = client.post(
                "/api/v1/compliance/evidence/tasks",
                headers={"X-Tenant-ID": TENANT_ID, "X-User-ID": "qa-user"},
                json={
                    "tenant_id": TENANT_ID,
                    "task_name": "Collect IAM MFA evidence",
                    "task_type": "iam_evidence_collection",
                    "status": "completed",
                    "source_system": "iam_agent",
                    "collection_method": "api",
                },
            )
            assert task_response.status_code == 200
            assert task_response.json()["source_system"] == "iam_agent"

            accepted_create = client.post("/api/v1/compliance/evidence", json=_evidence_request(TENANT_ID, "MFA enforcement export"))
            rejected_create = client.post("/api/v1/compliance/evidence", json=_evidence_request(TENANT_ID, "Stale access review export"))
            assert accepted_create.status_code == 200
            assert rejected_create.status_code == 200
            accepted_id = accepted_create.json()["id"]
            rejected_id = rejected_create.json()["id"]

            accepted_review = client.post(
                f"/api/v1/compliance/evidence/{accepted_id}/review",
                headers={"X-User-ID": "reviewer-1"},
                json={"tenant_id": TENANT_ID, "review_status": "accepted", "review_notes": "Current connector evidence."},
            )
            rejected_review = client.post(
                f"/api/v1/compliance/evidence/{rejected_id}/review",
                headers={"X-User-ID": "reviewer-1"},
                json={"tenant_id": TENANT_ID, "review_status": "rejected", "rejection_reason": "Stale source export."},
            )
            assert accepted_review.status_code == 200
            assert rejected_review.status_code == 200

            coverage_response = client.get("/api/v1/compliance/coverage", headers={"X-Tenant-ID": TENANT_ID})
            assert coverage_response.status_code == 200
            soc2_control = coverage_response.json()["items"][0]["controls"][0]
            assert soc2_control["status"] == "operating"
            assert soc2_control["evidence_items"] == 1

            package_response = client.post(
                "/api/v1/compliance/evidence/packages",
                json={
                    "tenant_id": TENANT_ID,
                    "package_name": "SOC 2 Q2 Evidence",
                    "framework_id": "soc2",
                    "report_period_start": "2026-04-01",
                    "report_period_end": "2026-06-30",
                    "evidence_item_ids": [accepted_id],
                },
            )
            assert package_response.status_code == 200
            assert package_response.json()["id"] == "pkg-soc2-q2"
            assert len(package_response.json()["items"]) == 1

            export_response = client.post(
                "/api/v1/compliance/evidence/packages/pkg-soc2-q2/export",
                json={"tenant_id": TENANT_ID, "export_format": "zip"},
            )
            assert export_response.status_code == 200
            assert export_response.json()["manifest"]["evidence_item_count"] == 1

            recommendations = client.get(
                "/api/v1/compliance/agent/recommendations",
                params={"state": "proposed", "trigger_type": "high_priority_control_gap_detected"},
            )
            assert recommendations.status_code == 200
            gap_recommendation = recommendations.json()["items"][0]
            assert gap_recommendation["framework_id"] == "hipaa"
            assert gap_recommendation["recommendation_type"] == "create_evidence_collection_task"

            decision = client.post(
                f"/api/v1/compliance/agent/recommendations/{gap_recommendation['id']}/decision",
                headers={"X-User-ID": "qa-approver"},
                json={"state": "accepted", "decision_notes": "Create manual HIPAA evidence task."},
            )
            assert decision.status_code == 200
            assert decision.json()["state"] == "accepted"
            assert decision.json()["decided_by"] == "qa-approver"

            cross_tenant_selection = client.put(
                "/api/v1/compliance/framework-selections",
                headers={"X-Tenant-ID": OTHER_TENANT_ID},
                json={"tenant_id": OTHER_TENANT_ID, "selections": [{"framework_id": "soc2"}]},
            )
            cross_tenant_evidence = client.post(
                "/api/v1/compliance/evidence",
                headers={"X-Tenant-ID": TENANT_ID},
                json=_evidence_request(OTHER_TENANT_ID, "Foreign tenant export"),
            )
            assert cross_tenant_selection.status_code == 403
            assert cross_tenant_evidence.status_code == 403
    finally:
        app.dependency_overrides.clear()
