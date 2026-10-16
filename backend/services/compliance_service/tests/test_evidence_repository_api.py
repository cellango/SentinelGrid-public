from pathlib import Path
import hashlib
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

from sg_core.security import get_current_payload

from app.main import app
from app.api import evidence as evidence_api
from app.core.database import get_current_tenant, get_tenant_session
from app.services.evidence_repository import EvidenceRepository
from sg_core.service_metrics import get_service_metrics, reset_service_metrics


VALID_HASH = "a" * 64


@pytest.fixture(autouse=True)
def _disable_evidence_audit(monkeypatch):
    async def noop_log_event(self, payload):
        return None

    monkeypatch.setattr("app.services.audit_client.AuditClient.log_event", noop_log_event)


class FakeEvidenceRepository:
    def __init__(self):
        self.calls = {}

    def list_evidence(self, db, tenant_id, filters, limit=50, offset=0):
        self.calls["list"] = {
            "db": db,
            "tenant_id": tenant_id,
            "filters": filters,
            "limit": limit,
            "offset": offset,
        }
        return {"tenant_id": tenant_id, "items": [], "count": 0, "limit": limit, "offset": offset}

    def count_stale_evidence(self, db, tenant_id):
        self.calls["count_stale"] = {"db": db, "tenant_id": tenant_id}
        return 2

    def create_evidence_item(self, db, tenant_id, request, actor_id=None):
        self.calls["create"] = {
            "db": db,
            "tenant_id": tenant_id,
            "request": request,
            "actor_id": actor_id,
        }
        return {"id": str(uuid4()), "tenant_id": tenant_id, "review_status": request["review_status"]}

    def get_evidence_item(self, db, tenant_id, evidence_id):
        self.calls["get"] = {"db": db, "tenant_id": tenant_id, "evidence_id": evidence_id}
        return {"id": evidence_id, "tenant_id": tenant_id, "control_links": [], "reviews": []}

    def review_evidence_item(self, db, tenant_id, evidence_id, request, actor_id=None):
        self.calls["review"] = {
            "db": db,
            "tenant_id": tenant_id,
            "evidence_id": evidence_id,
            "request": request,
            "actor_id": actor_id,
        }
        return {
            "evidence": {"id": evidence_id, "tenant_id": tenant_id, "review_status": request["review_status"]},
            "review": {"review_status": request["review_status"], "reviewer": actor_id},
        }

    def create_package(self, db, tenant_id, request, actor_id=None):
        self.calls["create_package"] = {
            "db": db,
            "tenant_id": tenant_id,
            "request": request,
            "actor_id": actor_id,
        }
        return {"id": str(uuid4()), "tenant_id": tenant_id, "package_name": request["package_name"]}

    def list_packages(self, db, tenant_id, filters, limit=50, offset=0):
        self.calls["list_packages"] = {
            "db": db,
            "tenant_id": tenant_id,
            "filters": filters,
            "limit": limit,
            "offset": offset,
        }
        return {"tenant_id": tenant_id, "items": [], "count": 0, "limit": limit, "offset": offset}

    def create_collection_task(self, db, tenant_id, request, actor_id=None):
        self.calls["create_task"] = {
            "db": db,
            "tenant_id": tenant_id,
            "request": request,
            "actor_id": actor_id,
        }
        return {"id": str(uuid4()), "tenant_id": tenant_id, "status": request["status"]}

    def list_collection_tasks(self, db, tenant_id, filters, limit=50, offset=0):
        self.calls["list_tasks"] = {
            "db": db,
            "tenant_id": tenant_id,
            "filters": filters,
            "limit": limit,
            "offset": offset,
        }
        return {"tenant_id": tenant_id, "items": [], "count": 0, "limit": limit, "offset": offset}

    def get_package(self, db, tenant_id, package_id):
        self.calls["get_package"] = {"db": db, "tenant_id": tenant_id, "package_id": package_id}
        return {"id": package_id, "tenant_id": tenant_id, "items": [], "exports": []}

    def create_export(self, db, tenant_id, package_id, request, actor_id=None):
        self.calls["export"] = {
            "db": db,
            "tenant_id": tenant_id,
            "package_id": package_id,
            "request": request,
            "actor_id": actor_id,
        }
        return {"id": str(uuid4()), "tenant_id": tenant_id, "package_id": package_id, "status": "requested"}

    def complete_export(self, db, tenant_id, package_id, export_id, request, actor_id=None):
        self.calls["complete_export"] = {
            "db": db,
            "tenant_id": tenant_id,
            "package_id": package_id,
            "export_id": export_id,
            "request": request,
            "actor_id": actor_id,
        }
        return {
            "id": export_id,
            "tenant_id": tenant_id,
            "package_id": package_id,
            "status": request["status"],
            "hash_sha256": request.get("hash_sha256"),
            "immutable_after": request.get("completed_at") or "2026-04-27T12:00:00+00:00",
        }

    def verify_evidence_item(self, db, tenant_id, evidence_id, request, actor_id=None):
        self.calls["verify"] = {
            "db": db,
            "tenant_id": tenant_id,
            "evidence_id": evidence_id,
            "request": request,
            "actor_id": actor_id,
        }
        observed = request.get("observed_hash_sha256")
        status = "verified" if observed and observed.lower() == VALID_HASH else "mismatch"
        return {
            "evidence": {"id": evidence_id, "tenant_id": tenant_id, "title": "MFA export"},
            "verification": {
                "verification_status": status,
                "expected_hash_sha256": VALID_HASH,
                "observed_hash_sha256": observed,
            },
        }

    def list_retention_policies(self, db, tenant_id, filters):
        self.calls["list_retention"] = {
            "db": db,
            "tenant_id": tenant_id,
            "filters": filters,
        }
        return {"tenant_id": tenant_id, "items": [], "count": 0, "filters": filters}

    def upsert_retention_policy(self, db, tenant_id, request, actor_id=None):
        self.calls["upsert_retention"] = {
            "db": db,
            "tenant_id": tenant_id,
            "request": request,
            "actor_id": actor_id,
        }
        return {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "framework_id": request.get("framework_id"),
            "subject_type": request["subject_type"],
            "retention_days": request["retention_days"],
            "policy_name": request.get("policy_name") or "default",
            "legal_hold": request.get("legal_hold", False),
        }

    def schedule_recollection_task(self, db, tenant_id, evidence_id, request, actor_id=None):
        self.calls["schedule_recollection"] = {
            "db": db,
            "tenant_id": tenant_id,
            "evidence_id": evidence_id,
            "request": request,
            "actor_id": actor_id,
        }
        return {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "task_name": "Recollect evidence: MFA export",
            "status": request.get("task_status") or "pending",
        }

    def retire_evidence_item(self, db, tenant_id, evidence_id, actor_id=None, metadata=None):
        self.calls["retire"] = {
            "db": db,
            "tenant_id": tenant_id,
            "evidence_id": evidence_id,
            "actor_id": actor_id,
            "metadata": metadata,
        }
        return {"id": evidence_id, "tenant_id": tenant_id, "title": "MFA export", "review_status": "retired"}

    def delete_evidence_item(self, db, tenant_id, evidence_id, actor_id=None):
        self.calls["delete"] = {
            "db": db,
            "tenant_id": tenant_id,
            "evidence_id": evidence_id,
            "actor_id": actor_id,
        }
        return {
            "id": evidence_id,
            "tenant_id": tenant_id,
            "title": "MFA export",
            "review_status": "retired",
            "deleted_at": "2026-04-27T12:00:00+00:00",
        }


class FakeWorkflowService:
    def __init__(self):
        self.calls = []

    async def create_recommendation_and_task(self, db, **kwargs):
        self.calls.append({"db": db, "kwargs": kwargs})
        return {"id": "recommendation-1"}


@pytest.fixture
def evidence_client(monkeypatch):
    tenant_id = str(uuid4())
    fake_db = object()
    fake_repository = FakeEvidenceRepository()
    fake_workflow = FakeWorkflowService()
    fake_repository.workflow_calls = fake_workflow.calls

    def override_get_current_tenant():
        return tenant_id

    def override_get_tenant_session():
        yield fake_db

    def override_get_current_payload():
        return {"tenant_id": tenant_id, "user_id": "user-123", "roles": ["compliance_officer"]}

    app.dependency_overrides[get_current_tenant] = override_get_current_tenant
    app.dependency_overrides[get_tenant_session] = override_get_tenant_session
    app.dependency_overrides[get_current_payload] = override_get_current_payload
    app.dependency_overrides[evidence_api.get_compliance_agent_workflow_service] = lambda: fake_workflow
    monkeypatch.setattr(evidence_api, "evidence_repository", fake_repository)

    try:
        with TestClient(app) as client:
            yield client, tenant_id, fake_repository
    finally:
        app.dependency_overrides.clear()


def _evidence_request(tenant_id: str) -> dict:
    return {
        "tenant_id": tenant_id,
        "evidence_type": "configuration",
        "title": "MFA configuration export",
        "source_system": "iam_agent",
        "source_resource_id": "tenant-mfa-settings",
        "collector": "iam_agent",
        "collection_method": "api",
        "valid_from": "2026-04-01T00:00:00Z",
        "valid_until": "2026-07-01T00:00:00Z",
        "hash_sha256": VALID_HASH,
        "storage_uri": "s3://evidence/tenant/mfa.json",
        "summary": "MFA is enforced for privileged users.",
        "control_links": [{"control_id": "CC6.1", "framework_id": "soc2"}],
    }


def test_evidence_list_endpoint_uses_tenant_context_and_filters(evidence_client):
    client, tenant_id, fake_repository = evidence_client
    reset_service_metrics("compliance-service")

    response = client.get(
        "/api/v1/compliance/evidence",
        headers={"X-Tenant-ID": tenant_id},
        params={"framework_id": "soc2", "control_id": "CC6.1", "review_status": "accepted", "limit": 25},
    )

    assert response.status_code == 200
    call = fake_repository.calls["list"]
    assert call["tenant_id"] == tenant_id
    assert call["filters"]["framework_id"] == "soc2"
    assert call["filters"]["control_id"] == "CC6.1"
    assert call["filters"]["review_status"] == "accepted"
    assert call["limit"] == 25
    assert response.json()["stale_evidence_count"] == 2
    metrics = get_service_metrics("compliance-service").snapshot()
    assert metrics["gauges"]["compliance_stale_evidence_items"][f"tenant_id={tenant_id}"] == 2


def test_evidence_create_endpoint_enforces_role_and_records_actor(evidence_client):
    client, tenant_id, fake_repository = evidence_client
    reset_service_metrics("compliance-service")

    response = client.post("/api/v1/compliance/evidence", json=_evidence_request(tenant_id))

    assert response.status_code == 200
    call = fake_repository.calls["create"]
    assert call["tenant_id"] == tenant_id
    assert call["actor_id"] == "user-123"
    assert call["request"]["hash_sha256"] == VALID_HASH
    assert call["request"]["control_links"][0]["framework_id"] == "soc2"
    metrics = get_service_metrics("compliance-service").snapshot()
    assert (
        metrics["counters"]["compliance_evidence_collection_total"]["series"][
            "collection_method=api,outcome=success,source_system=iam_agent"
        ]
        == 1
    )


def test_evidence_create_recommendation_preserves_tenant_actor_and_auth(evidence_client):
    client, tenant_id, fake_repository = evidence_client

    response = client.post(
        "/api/v1/compliance/evidence",
        headers={"X-User-ID": "manager-1", "Authorization": "Bearer compliance-token"},
        json=_evidence_request(tenant_id),
    )

    assert response.status_code == 200
    assert fake_repository.workflow_calls
    workflow_call = fake_repository.workflow_calls[0]["kwargs"]
    assert workflow_call["tenant_id"] == tenant_id
    assert workflow_call["created_by"] == "manager-1"
    assert workflow_call["authorization"] == "Bearer compliance-token"
    assert workflow_call["metadata"]["evidence"]["tenant_id"] == tenant_id


def test_evidence_create_endpoint_rejects_cross_tenant(evidence_client):
    client, _tenant_id, fake_repository = evidence_client

    response = client.post("/api/v1/compliance/evidence", json=_evidence_request(str(uuid4())))

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"
    assert "create" not in fake_repository.calls


def test_evidence_hash_and_integrity_verification_endpoints(evidence_client):
    client, tenant_id, fake_repository = evidence_client
    evidence_id = str(uuid4())

    hash_response = client.post(
        "/api/v1/compliance/evidence/hash",
        json={"content": "MFA is enforced", "encoding": "utf-8"},
    )
    verify_response = client.post(
        f"/api/v1/compliance/evidence/{evidence_id}/verify",
        json={"tenant_id": tenant_id, "observed_hash_sha256": VALID_HASH},
    )

    assert hash_response.status_code == 200
    assert hash_response.json()["hash_sha256"] == hashlib.sha256(b"MFA is enforced").hexdigest()
    assert hash_response.json()["byte_length"] == len(b"MFA is enforced")

    assert verify_response.status_code == 200
    assert verify_response.json()["verification"]["verification_status"] == "verified"
    assert fake_repository.calls["verify"]["tenant_id"] == tenant_id
    assert fake_repository.calls["verify"]["evidence_id"] == evidence_id
    assert fake_repository.calls["verify"]["actor_id"] == "user-123"


def test_evidence_retention_policy_endpoints_use_tenant_and_actor(evidence_client):
    client, tenant_id, fake_repository = evidence_client

    list_response = client.get(
        "/api/v1/compliance/evidence/retention-policies",
        params={"tenant_id": tenant_id, "framework_id": "soc2", "subject_type": "evidence_item"},
    )
    upsert_response = client.put(
        "/api/v1/compliance/evidence/retention-policies",
        json={
            "tenant_id": tenant_id,
            "framework_id": "soc2",
            "subject_type": "evidence_item",
            "retention_days": 2555,
            "policy_name": "SOC 2 evidence retention",
        },
    )

    assert list_response.status_code == 200
    assert fake_repository.calls["list_retention"]["tenant_id"] == tenant_id
    assert fake_repository.calls["list_retention"]["filters"]["framework_id"] == "soc2"

    assert upsert_response.status_code == 200
    assert upsert_response.json()["retention_days"] == 2555
    assert fake_repository.calls["upsert_retention"]["tenant_id"] == tenant_id
    assert fake_repository.calls["upsert_retention"]["actor_id"] == "user-123"


def test_evidence_recollection_retire_and_delete_endpoints(evidence_client):
    client, tenant_id, fake_repository = evidence_client
    evidence_id = str(uuid4())

    recollect_response = client.post(
        f"/api/v1/compliance/evidence/{evidence_id}/recollection-task",
        json={"tenant_id": tenant_id, "reason": "expired", "task_status": "pending"},
    )
    retire_response = client.post(
        f"/api/v1/compliance/evidence/{evidence_id}/retire",
        json={"tenant_id": tenant_id, "reason": "superseded by fresh connector evidence"},
    )
    delete_response = client.delete(f"/api/v1/compliance/evidence/{evidence_id}")

    assert recollect_response.status_code == 200
    assert fake_repository.calls["schedule_recollection"]["evidence_id"] == evidence_id
    assert fake_repository.calls["schedule_recollection"]["request"]["reason"] == "expired"

    assert retire_response.status_code == 200
    assert retire_response.json()["review_status"] == "retired"
    assert fake_repository.calls["retire"]["metadata"]["reason"] == "superseded by fresh connector evidence"

    assert delete_response.status_code == 200
    assert delete_response.json()["deleted_at"] == "2026-04-27T12:00:00+00:00"
    assert fake_repository.calls["delete"]["actor_id"] == "user-123"


@pytest.mark.parametrize(
    ("role", "create_status", "review_status", "export_status"),
    [
        ("compliance_viewer", 403, 403, 403),
        ("compliance_manager", 200, 200, 200),
        ("evidence_reviewer", 200, 200, 200),
        ("report_exporter", 403, 403, 200),
        ("admin", 200, 200, 200),
    ],
)
def test_evidence_role_matrix_for_mutating_surfaces(
    evidence_client,
    role,
    create_status,
    review_status,
    export_status,
):
    client, tenant_id, fake_repository = evidence_client
    fake_repository.calls.clear()

    app.dependency_overrides[get_current_payload] = lambda: {
        "tenant_id": tenant_id,
        "user_id": f"{role}-user",
        "roles": [role],
    }

    list_response = client.get("/api/v1/compliance/evidence", params={"tenant_id": tenant_id})
    create_response = client.post("/api/v1/compliance/evidence", json=_evidence_request(tenant_id))
    review_response = client.post(
        f"/api/v1/compliance/evidence/{uuid4()}/review",
        json={"tenant_id": tenant_id, "review_status": "accepted"},
    )
    export_response = client.post(
        f"/api/v1/compliance/evidence/packages/{uuid4()}/export",
        json={"tenant_id": tenant_id, "export_format": "zip"},
    )

    assert list_response.status_code == 200
    assert create_response.status_code == create_status
    assert review_response.status_code == review_status
    assert export_response.status_code == export_status


def test_evidence_review_endpoint_requires_reviewer_role(monkeypatch, evidence_client):
    client, tenant_id, fake_repository = evidence_client

    def viewer_payload():
        return {"tenant_id": tenant_id, "user_id": "viewer-1", "roles": ["viewer"]}

    app.dependency_overrides[get_current_payload] = viewer_payload

    response = client.post(
        f"/api/v1/compliance/evidence/{uuid4()}/review",
        json={"tenant_id": tenant_id, "review_status": "accepted"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Required compliance evidence role not found"
    assert "review" not in fake_repository.calls


def test_evidence_package_endpoints_reject_cross_tenant_selectors(evidence_client):
    client, _tenant_id, fake_repository = evidence_client
    other_tenant_id = str(uuid4())

    list_response = client.get(
        "/api/v1/compliance/evidence/packages",
        params={"tenant_id": other_tenant_id},
    )
    create_response = client.post(
        "/api/v1/compliance/evidence/packages",
        json={
            "tenant_id": other_tenant_id,
            "package_name": "Foreign tenant evidence",
            "report_period_start": "2026-04-01",
            "report_period_end": "2026-06-30",
        },
    )
    export_response = client.post(
        f"/api/v1/compliance/evidence/packages/{uuid4()}/export",
        json={"tenant_id": other_tenant_id, "export_format": "zip"},
    )

    assert list_response.status_code == 403
    assert create_response.status_code == 403
    assert export_response.status_code == 403
    assert "list_packages" not in fake_repository.calls
    assert "create_package" not in fake_repository.calls
    assert "export" not in fake_repository.calls


def test_evidence_package_and_export_endpoints_use_repository(evidence_client):
    client, tenant_id, fake_repository = evidence_client
    package_id = str(uuid4())

    list_response = client.get(
        "/api/v1/compliance/evidence/packages",
        params={"tenant_id": tenant_id, "framework_id": "soc2", "status": "collecting", "limit": 10},
    )
    create_response = client.post(
        "/api/v1/compliance/evidence/packages",
        json={
            "tenant_id": tenant_id,
            "package_name": "SOC 2 Q2 Evidence",
            "framework_id": "soc2",
            "report_period_start": "2026-04-01",
            "report_period_end": "2026-06-30",
        },
    )
    get_response = client.get(f"/api/v1/compliance/evidence/packages/{package_id}")
    export_response = client.post(
        f"/api/v1/compliance/evidence/packages/{package_id}/export",
        json={"tenant_id": tenant_id, "export_format": "zip"},
    )

    assert list_response.status_code == 200
    assert fake_repository.calls["list_packages"]["tenant_id"] == tenant_id
    assert fake_repository.calls["list_packages"]["filters"]["framework_id"] == "soc2"
    assert fake_repository.calls["list_packages"]["filters"]["status"] == "collecting"
    assert fake_repository.calls["list_packages"]["limit"] == 10

    assert create_response.status_code == 200
    assert fake_repository.calls["create_package"]["tenant_id"] == tenant_id
    assert fake_repository.calls["create_package"]["actor_id"] == "user-123"
    assert fake_repository.calls["create_package"]["request"]["framework_id"] == "soc2"

    assert get_response.status_code == 200
    assert fake_repository.calls["get_package"]["package_id"] == package_id

    assert export_response.status_code == 200
    assert fake_repository.calls["export"]["package_id"] == package_id
    assert export_response.json()["status"] == "requested"
    assert fake_repository.calls["export"]["request"]["export_format"] == "zip"
    csv_export_response = client.post(
        f"/api/v1/compliance/evidence/packages/{package_id}/export",
        json={"tenant_id": tenant_id, "export_format": "csv"},
    )
    finalize_response = client.patch(
        f"/api/v1/compliance/evidence/packages/{package_id}/exports/{uuid4()}",
        json={
            "tenant_id": tenant_id,
            "status": "completed",
            "storage_uri": "s3://evidence/exports/pkg.zip",
            "hash_sha256": VALID_HASH,
            "file_size_bytes": 1024,
        },
    )
    assert csv_export_response.status_code == 200
    assert fake_repository.calls["export"]["request"]["export_format"] == "csv"
    assert finalize_response.status_code == 200
    assert fake_repository.calls["complete_export"]["package_id"] == package_id
    assert fake_repository.calls["complete_export"]["request"]["status"] == "completed"
    assert finalize_response.json()["immutable_after"] is not None


def test_evidence_package_export_rejects_unsupported_json_format(evidence_client):
    client, tenant_id, fake_repository = evidence_client

    response = client.post(
        f"/api/v1/compliance/evidence/packages/{uuid4()}/export",
        json={"tenant_id": tenant_id, "export_format": "json"},
    )

    assert response.status_code == 422
    assert "export" not in fake_repository.calls


def test_evidence_package_csv_export_manifest_maps_authorized_items(monkeypatch):
    repository = EvidenceRepository()

    monkeypatch.setattr(
        repository,
        "_package_items_with_links",
        lambda db, tenant_id, package_id: [
            {
                "id": "ev-1",
                "title": "MFA export",
                "evidence_type": "configuration",
                "review_status": "accepted",
                "valid_until": "2026-07-01T00:00:00Z",
                "storage_uri": "s3://evidence/tenant/mfa.json",
                "hash_sha256": VALID_HASH,
                "sensitivity": "internal",
                "metadata": {"file_size_bytes": 100},
                "control_links": [
                    {
                        "framework_code": "soc2",
                        "framework_name": "SOC 2",
                        "control_ref": "CC6.1",
                        "control_name": "Logical access",
                        "link_type": "supports",
                        "status": "active",
                    }
                ],
            },
            {
                "id": "ev-2",
                "title": "Restricted admin notes",
                "evidence_type": "attestation",
                "review_status": "pending",
                "storage_uri": "s3://evidence/tenant/admin-notes.txt",
                "hash_sha256": "b" * 64,
                "sensitivity": "restricted",
                "control_links": [],
            },
            {
                "id": "ev-expired",
                "title": "Expired MFA export",
                "evidence_type": "configuration",
                "review_status": "accepted",
                "valid_until": "2020-01-01T00:00:00Z",
                "storage_uri": "s3://evidence/tenant/expired-mfa.json",
                "hash_sha256": "c" * 64,
                "sensitivity": "internal",
                "control_links": [
                    {
                        "framework_code": "soc2",
                        "framework_name": "SOC 2",
                        "control_ref": "CC6.1",
                        "control_name": "Logical access",
                        "link_type": "supports",
                        "status": "active",
                    }
                ],
            },
        ],
    )

    manifest = repository._build_package_export_manifest(  # noqa: SLF001
        object(),
        "tenant-1",
        "package-1",
        {"export_format": "csv", "include_sensitive": False, "manifest": {"purpose": "audit"}},
    )

    assert manifest["artifact_kind"] == "control_evidence_mapping_csv"
    assert manifest["evidence_item_count"] == 3
    assert manifest["exported_evidence_item_count"] == 1
    assert manifest["excluded_sensitive_item_count"] == 1
    assert manifest["excluded_expired_item_count"] == 1
    assert manifest["excluded_non_supporting_item_count"] == 2
    assert manifest["storage_supported"] is True
    assert manifest["requested_manifest"]["purpose"] == "audit"
    assert manifest["control_evidence_mapping"][0]["control_id"] == "CC6.1"
    assert manifest["control_evidence_mapping"][0]["evidence_item_id"] == "ev-1"
    assert manifest["control_evidence_mapping"][0]["audit_support_status"] == "supporting"


def test_evidence_collection_task_endpoint_uses_repository(evidence_client):
    client, tenant_id, fake_repository = evidence_client

    list_response = client.get(
        "/api/v1/compliance/evidence/tasks",
        params={"tenant_id": tenant_id, "status": "manual_evidence_required", "limit": 10},
    )
    response = client.post(
        "/api/v1/compliance/evidence/tasks",
        json={
            "tenant_id": tenant_id,
            "task_name": "Manual IA-2 MFA attestation",
            "task_type": "api_response",
            "status": "manual_evidence_required",
            "source_system": "iam_agent",
            "source_resource_id": "IA-2:api_response",
            "collector": "iam_agent",
            "collection_method": "manual_attestation",
            "idempotency_key": f"iam:{tenant_id}:IA-2:api_response:task",
        },
    )

    assert list_response.status_code == 200
    list_call = fake_repository.calls["list_tasks"]
    assert list_call["tenant_id"] == tenant_id
    assert list_call["filters"]["status"] == "manual_evidence_required"
    assert list_call["limit"] == 10

    assert response.status_code == 200
    call = fake_repository.calls["create_task"]
    assert call["tenant_id"] == tenant_id
    assert call["actor_id"] == "user-123"
    assert call["request"]["status"] == "manual_evidence_required"
    assert call["request"]["idempotency_key"].endswith(":task")
