"""Idempotent demo tenant seed data for Compliance launch readiness."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import text
from sqlalchemy.orm import Session


DEMO_SEED_VERSION = "phase8_launch_demo_2026_04_28"


def _row_mapping(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    if isinstance(row, Mapping):
        return dict(row)
    if isinstance(row, dict):
        return dict(row)
    return {}


def _first_mapping(result: Any) -> dict[str, Any]:
    if hasattr(result, "mappings"):
        mapped = result.mappings()
        if hasattr(mapped, "first"):
            return _row_mapping(mapped.first())
    if hasattr(result, "first"):
        return _row_mapping(result.first())
    return {}


def _json(value: Any) -> str:
    return json.dumps(value or {}, sort_keys=True, default=str)


def _json_array(value: Any) -> str:
    return json.dumps(value or [], sort_keys=True, default=str)


def _uuid_array_literal(values: list[str]) -> str:
    return "{" + ",".join(str(value) for value in values) + "}"


def _stable_uuid(tenant_id: str, name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"sentinelgrid:{DEMO_SEED_VERSION}:{tenant_id}:{name}"))


def _stable_hash(tenant_id: str, name: str) -> str:
    return hashlib.sha256(f"{DEMO_SEED_VERSION}:{tenant_id}:{name}".encode("utf-8")).hexdigest()


def _iso(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


@dataclass
class ComplianceLaunchDemoSeedResult:
    dry_run: bool
    tenant_scope: str | None = None
    tenant_id: str | None = None
    tenant_slug: str | None = None
    tenant_name: str | None = None
    framework_selections_planned: int = 0
    framework_selections_written: int = 0
    evidence_packages_planned: int = 0
    evidence_packages_written: int = 0
    evidence_items_planned: int = 0
    evidence_items_written: int = 0
    collection_tasks_planned: int = 0
    collection_tasks_written: int = 0
    reports_planned: int = 0
    reports_written: int = 0
    recommendations_planned: int = 0
    recommendations_written: int = 0
    planned_framework_selections: list[dict[str, Any]] = field(default_factory=list)
    planned_evidence_packages: list[dict[str, Any]] = field(default_factory=list)
    planned_evidence_items: list[dict[str, Any]] = field(default_factory=list)
    planned_collection_tasks: list[dict[str, Any]] = field(default_factory=list)
    planned_reports: list[dict[str, Any]] = field(default_factory=list)
    planned_recommendations: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "tenant_scope": self.tenant_scope,
            "tenant_id": self.tenant_id,
            "tenant_slug": self.tenant_slug,
            "tenant_name": self.tenant_name,
            "seed_version": DEMO_SEED_VERSION,
            "framework_selections_planned": self.framework_selections_planned,
            "framework_selections_written": self.framework_selections_written,
            "evidence_packages_planned": self.evidence_packages_planned,
            "evidence_packages_written": self.evidence_packages_written,
            "evidence_items_planned": self.evidence_items_planned,
            "evidence_items_written": self.evidence_items_written,
            "collection_tasks_planned": self.collection_tasks_planned,
            "collection_tasks_written": self.collection_tasks_written,
            "reports_planned": self.reports_planned,
            "reports_written": self.reports_written,
            "recommendations_planned": self.recommendations_planned,
            "recommendations_written": self.recommendations_written,
            "planned_framework_selections": self.planned_framework_selections,
            "planned_evidence_packages": self.planned_evidence_packages,
            "planned_evidence_items": self.planned_evidence_items,
            "planned_collection_tasks": self.planned_collection_tasks,
            "planned_reports": self.planned_reports,
            "planned_recommendations": self.planned_recommendations,
        }


class ComplianceLaunchDemoSeedService:
    """Build and optionally apply realistic Compliance demo tenant data."""

    def run(
        self,
        db: Session,
        *,
        tenant_id: str | None = None,
        tenant_slug: str = "demo",
        dry_run: bool = True,
    ) -> ComplianceLaunchDemoSeedResult:
        tenant = self._load_tenant(db, tenant_id=tenant_id, tenant_slug=tenant_slug)
        if not tenant:
            raise ValueError(f"Demo tenant not found for tenant_id={tenant_id!r} tenant_slug={tenant_slug!r}")

        tenant_id = str(tenant["tenant_id"])
        result = ComplianceLaunchDemoSeedResult(
            dry_run=dry_run,
            tenant_scope=tenant_id or tenant_slug,
            tenant_id=tenant_id,
            tenant_slug=tenant.get("tenant_slug"),
            tenant_name=tenant.get("tenant_name"),
        )
        plan = self._build_plan(tenant)
        result.planned_framework_selections = plan["framework_selections"]
        result.planned_evidence_packages = plan["evidence_packages"]
        result.planned_evidence_items = plan["evidence_items"]
        result.planned_collection_tasks = plan["collection_tasks"]
        result.planned_reports = plan["reports"]
        result.planned_recommendations = plan["recommendations"]
        result.framework_selections_planned = len(result.planned_framework_selections)
        result.evidence_packages_planned = len(result.planned_evidence_packages)
        result.evidence_items_planned = len(result.planned_evidence_items)
        result.collection_tasks_planned = len(result.planned_collection_tasks)
        result.reports_planned = len(result.planned_reports)
        result.recommendations_planned = len(result.planned_recommendations)

        if dry_run:
            return result

        result.framework_selections_written = self._apply_framework_selections(
            db, tenant_id, result.planned_framework_selections
        )
        result.evidence_packages_written = self._apply_evidence_packages(
            db, tenant_id, result.planned_evidence_packages
        )
        result.evidence_items_written = self._apply_evidence_items(db, tenant_id, result.planned_evidence_items)
        result.collection_tasks_written = self._apply_collection_tasks(
            db, tenant_id, result.planned_collection_tasks
        )
        result.reports_written = self._apply_reports(db, tenant_id, result.planned_reports)
        result.recommendations_written = self._apply_recommendations(
            db, tenant_id, result.planned_recommendations
        )
        db.commit()
        return result

    def _load_tenant(self, db: Session, *, tenant_id: str | None, tenant_slug: str) -> dict[str, Any]:
        if tenant_id:
            where_sql = "WHERE id = CAST(:tenant_id AS uuid)"
            params = {"tenant_id": tenant_id}
        else:
            where_sql = "WHERE slug = :tenant_slug"
            params = {"tenant_slug": tenant_slug}

        row = _first_mapping(
            db.execute(
                text(
                    f"""
                    SELECT CAST(id AS text) AS tenant_id,
                           slug AS tenant_slug,
                           name AS tenant_name,
                           COALESCE(realm_name, slug, 'default') AS realm_name
                    FROM tenants
                    {where_sql}
                    LIMIT 1
                    """
                ),
                params,
            )
        )
        return row

    def _build_plan(self, tenant: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        tenant_id = str(tenant["tenant_id"])
        realm_name = tenant.get("realm_name") or "default"
        package_id = _stable_uuid(tenant_id, "soc2-q2-evidence-package")
        access_review_evidence_id = _stable_uuid(tenant_id, "iam-access-review-evidence")
        mfa_evidence_id = _stable_uuid(tenant_id, "iam-mfa-policy-evidence")
        now = datetime.now(timezone.utc)

        framework_selections = [
            {
                "framework_id": "soc2",
                "status": "active",
                "priority": 1,
                "target_date": "2026-06-30",
                "source": DEMO_SEED_VERSION,
            },
            {
                "framework_id": "hipaa",
                "status": "evaluating",
                "priority": 2,
                "target_date": "2026-09-30",
                "source": DEMO_SEED_VERSION,
            },
            {
                "framework_id": "pci_dss",
                "status": "evaluating",
                "priority": 3,
                "target_date": "2026-12-31",
                "source": DEMO_SEED_VERSION,
            },
        ]
        evidence_packages = [
            {
                "id": package_id,
                "realm_name": realm_name,
                "package_name": "SOC 2 Q2 Audit Evidence Package",
                "framework_id": "soc2",
                "report_period_start": "2026-04-01",
                "report_period_end": "2026-06-30",
                "created_by": "phase8_launch_demo_seed",
                "status": "exported",
                "package_type": "audit_package",
                "summary": "Demo package with accepted IAM evidence for SOC 2 logical access controls.",
                "description": "Used for launch demos and QA walkthroughs.",
                "sensitivity": "internal",
                "review_status": "accepted",
                "metadata": {
                    "seed_version": DEMO_SEED_VERSION,
                    "framework_id": "soc2",
                    "control_ids": ["CC6.1"],
                    "evidence_item_ids": [access_review_evidence_id, mfa_evidence_id],
                },
                "manifest": {
                    "manifest_version": "1.0",
                    "files": [
                        {"evidence_item_id": access_review_evidence_id, "path": "iam/access-review-q2.csv"},
                        {"evidence_item_id": mfa_evidence_id, "path": "iam/mfa-policy-snapshot.json"},
                    ],
                },
                "coverage_snapshot": {
                    "framework_id": "soc2",
                    "accepted_controls": ["CC6.1"],
                    "snapshot_hash_sha256": _stable_hash(tenant_id, "soc2-q2-coverage-snapshot"),
                },
            }
        ]
        evidence_items = [
            {
                "id": access_review_evidence_id,
                "realm_name": realm_name,
                "package_id": package_id,
                "control_ref": "CC6.1",
                "framework_id": "soc2",
                "evidence_type": "export",
                "title": "Q2 IAM access review export",
                "description": "Reviewed access grants and privileged-role assignments for Q2.",
                "source_system": "iam_agent",
                "source_resource_id": "demo-q2-access-review",
                "collector": "iam_agent",
                "collection_method": "api",
                "valid_from": "2026-04-01T00:00:00+00:00",
                "valid_until": "2026-07-01T00:00:00+00:00",
                "hash_sha256": _stable_hash(tenant_id, "iam-access-review-evidence"),
                "storage_uri": f"s3://sentinelgrid-demo/{tenant_id}/compliance/iam/access-review-q2.csv",
                "summary": "All standing administrator grants were reviewed with two exceptions remediated.",
                "sensitivity": "confidential",
                "review_status": "accepted",
                "created_by": "phase8_launch_demo_seed",
                "metadata": {"seed_version": DEMO_SEED_VERSION, "control_id": "CC6.1"},
            },
            {
                "id": mfa_evidence_id,
                "realm_name": realm_name,
                "package_id": package_id,
                "control_ref": "CC6.1",
                "framework_id": "soc2",
                "evidence_type": "configuration",
                "title": "MFA policy configuration snapshot",
                "description": "Snapshot of tenant MFA policy enforcement for privileged users.",
                "source_system": "iam_agent",
                "source_resource_id": "demo-mfa-policy",
                "collector": "iam_agent",
                "collection_method": "api",
                "valid_from": "2026-04-01T00:00:00+00:00",
                "valid_until": "2026-07-01T00:00:00+00:00",
                "hash_sha256": _stable_hash(tenant_id, "iam-mfa-policy-evidence"),
                "storage_uri": f"s3://sentinelgrid-demo/{tenant_id}/compliance/iam/mfa-policy.json",
                "summary": "MFA is enforced for privileged groups and break-glass access is tracked.",
                "sensitivity": "internal",
                "review_status": "accepted",
                "created_by": "phase8_launch_demo_seed",
                "metadata": {"seed_version": DEMO_SEED_VERSION, "control_id": "CC6.1"},
            },
        ]
        collection_tasks = [
            {
                "id": _stable_uuid(tenant_id, "iam-access-review-task"),
                "realm_name": realm_name,
                "package_id": package_id,
                "task_name": "Collect Q2 IAM access review evidence",
                "task_type": "iam_access_review",
                "status": "completed",
                "source_system": "iam_agent",
                "source_resource_id": "demo-q2-access-review",
                "collector": "iam_agent",
                "collection_method": "api",
                "requested_by": "phase8_launch_demo_seed",
                "completed_at": now.isoformat(),
                "evidence_items_created": [access_review_evidence_id, mfa_evidence_id],
                "metadata": {
                    "seed_version": DEMO_SEED_VERSION,
                    "framework_id": "soc2",
                    "control_ids": ["CC6.1"],
                },
            }
        ]
        reports = [
            {
                "id": f"phase8-demo-soc2-report-{tenant_id[:8]}",
                "name": "SOC 2 Evidence Summary - Demo Q2",
                "format": "PDF",
                "status": "COMPLETED",
                "generated_by": "phase8_launch_demo_seed",
                "date_range_start": "2026-04-01T00:00:00+00:00",
                "date_range_end": "2026-06-30T23:59:59+00:00",
                "file_path": f"s3://sentinelgrid-demo/{tenant_id}/reports/soc2-evidence-summary-q2.pdf",
                "file_size_bytes": 245760,
                "metadata": {
                    "seed_version": DEMO_SEED_VERSION,
                    "template_key": "soc2_evidence_summary",
                    "report_inputs": {
                        "framework_ids": ["soc2"],
                        "control_ids": ["CC6.1"],
                        "evidence_package_ids": [package_id],
                        "include_gaps": True,
                    },
                    "compliance_snapshot": {
                        "snapshot_hash_sha256": _stable_hash(tenant_id, "soc2-demo-report-snapshot"),
                        "evidence_package_ids": [package_id],
                    },
                    "evidence_basis": "accepted_evidence",
                },
            }
        ]
        recommendations = [
            {
                "id": _stable_uuid(tenant_id, "hipaa-missing-evidence-recommendation"),
                "trigger_type": "coverage_gap_detected",
                "recommendation_type": "create_evidence_collection_task",
                "state": "proposed",
                "priority": "high",
                "source_type": "control_gap",
                "source_id": "hipaa:164.308(a)(1)",
                "framework_id": "hipaa",
                "control_id": "164.308(a)(1)",
                "title": "Collect HIPAA security management evidence",
                "summary": "Attach risk-analysis and security-management policy evidence before HIPAA reporting.",
                "proposed_actions": [
                    {
                        "type": "create_evidence_collection_task",
                        "collector": "manual",
                        "framework_id": "hipaa",
                        "control_id": "164.308(a)(1)",
                    }
                ],
                "requires_approval": True,
                "created_by": "phase8_launch_demo_seed",
                "idempotency_key": f"{DEMO_SEED_VERSION}:hipaa:164.308(a)(1)",
                "metadata": {"seed_version": DEMO_SEED_VERSION},
            }
        ]
        return {
            "framework_selections": framework_selections,
            "evidence_packages": evidence_packages,
            "evidence_items": evidence_items,
            "collection_tasks": collection_tasks,
            "reports": reports,
            "recommendations": recommendations,
        }

    def _resolve_framework_uuid(self, db: Session, framework_id: str) -> str | None:
        aliases = {"soc2": "SOC2", "hipaa": "HIPAA", "pci_dss": "PCI_DSS", "nist_800_171": "NIST_800_171"}
        row = _first_mapping(
            db.execute(
                text(
                    """
                    SELECT CAST(id AS text) AS id
                    FROM compliance_frameworks
                    WHERE lower(framework_code) IN (lower(:framework_id), lower(:framework_code))
                    LIMIT 1
                    """
                ),
                {"framework_id": framework_id, "framework_code": aliases.get(framework_id, framework_id)},
            )
        )
        return str(row["id"]) if row.get("id") else None

    def _resolve_control_uuid(self, db: Session, framework_uuid: str | None, control_ref: str | None) -> str | None:
        if not framework_uuid or not control_ref:
            return None
        row = _first_mapping(
            db.execute(
                text(
                    """
                    SELECT CAST(id AS text) AS id
                    FROM compliance_controls
                    WHERE framework_id = CAST(:framework_uuid AS uuid)
                      AND lower(control_id) = lower(:control_ref)
                    LIMIT 1
                    """
                ),
                {"framework_uuid": framework_uuid, "control_ref": control_ref},
            )
        )
        return str(row["id"]) if row.get("id") else None

    def _apply_framework_selections(
        self,
        db: Session,
        tenant_id: str,
        selections: list[dict[str, Any]],
    ) -> int:
        for selection in selections:
            db.execute(
                text(
                    """
                    INSERT INTO tenant_framework_selections (
                        tenant_id, framework_id, status, priority, target_date,
                        selected_by, selected_at, source
                    )
                    VALUES (
                        CAST(:tenant_id AS uuid), :framework_id, :status, :priority,
                        CAST(:target_date AS date), :selected_by, NOW(), :source
                    )
                    ON CONFLICT (tenant_id, framework_id)
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        priority = EXCLUDED.priority,
                        target_date = EXCLUDED.target_date,
                        selected_by = EXCLUDED.selected_by,
                        selected_at = NOW(),
                        source = EXCLUDED.source
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "framework_id": selection["framework_id"],
                    "status": selection["status"],
                    "priority": selection["priority"],
                    "target_date": selection["target_date"],
                    "selected_by": DEMO_SEED_VERSION,
                    "source": selection["source"],
                },
            )
        return len(selections)

    def _apply_evidence_packages(
        self,
        db: Session,
        tenant_id: str,
        packages: list[dict[str, Any]],
    ) -> int:
        for package in packages:
            framework_uuid = self._resolve_framework_uuid(db, package["framework_id"])
            db.execute(
                text(
                    """
                    INSERT INTO evidence_packages (
                        id, tenant_id, realm_name, package_name, framework_id,
                        report_period_start, report_period_end, created_by, status,
                        package_type, summary, description, sensitivity, review_status,
                        manifest, coverage_snapshot, metadata
                    )
                    VALUES (
                        CAST(:id AS uuid), CAST(:tenant_id AS uuid), :realm_name,
                        :package_name, CAST(:framework_uuid AS uuid),
                        CAST(:report_period_start AS date), CAST(:report_period_end AS date),
                        :created_by, :status, :package_type, :summary, :description,
                        :sensitivity, :review_status, CAST(:manifest AS jsonb),
                        CAST(:coverage_snapshot AS jsonb), CAST(:metadata AS jsonb)
                    )
                    ON CONFLICT (id)
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        review_status = EXCLUDED.review_status,
                        manifest = EXCLUDED.manifest,
                        coverage_snapshot = EXCLUDED.coverage_snapshot,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """
                ),
                {
                    "id": package["id"],
                    "tenant_id": tenant_id,
                    "realm_name": package["realm_name"],
                    "package_name": package["package_name"],
                    "framework_uuid": framework_uuid,
                    "report_period_start": package["report_period_start"],
                    "report_period_end": package["report_period_end"],
                    "created_by": package["created_by"],
                    "status": package["status"],
                    "package_type": package["package_type"],
                    "summary": package["summary"],
                    "description": package["description"],
                    "sensitivity": package["sensitivity"],
                    "review_status": package["review_status"],
                    "manifest": _json(package["manifest"]),
                    "coverage_snapshot": _json(package["coverage_snapshot"]),
                    "metadata": _json(package["metadata"]),
                },
            )
        return len(packages)

    def _apply_evidence_items(self, db: Session, tenant_id: str, evidence_items: list[dict[str, Any]]) -> int:
        for item in evidence_items:
            framework_uuid = self._resolve_framework_uuid(db, item["framework_id"])
            control_uuid = self._resolve_control_uuid(db, framework_uuid, item.get("control_ref"))
            db.execute(
                text(
                    """
                    INSERT INTO evidence_items (
                        id, tenant_id, realm_name, package_id, control_id,
                        evidence_type, evidence_title, evidence_description,
                        file_path, file_hash, source_system, source_reference,
                        source_resource_id, collected_at, collected_by, collector,
                        collection_method, valid_from, valid_until, hash_sha256,
                        storage_uri, summary, sensitivity, review_status, created_by,
                        metadata, provenance, integrity_metadata, chain_of_custody
                    )
                    VALUES (
                        CAST(:id AS uuid), CAST(:tenant_id AS uuid), :realm_name,
                        CAST(:package_id AS uuid), CAST(:control_uuid AS uuid),
                        :evidence_type, :title, :description, :storage_uri, :hash_sha256,
                        :source_system, :source_resource_id, :source_resource_id, NOW(),
                        :collector, :collector, :collection_method, :valid_from,
                        :valid_until, :hash_sha256, :storage_uri, :summary,
                        :sensitivity, :review_status, :created_by,
                        CAST(:metadata AS jsonb), CAST(:provenance AS jsonb),
                        CAST(:integrity_metadata AS jsonb), CAST(:chain_of_custody AS jsonb)
                    )
                    ON CONFLICT (id)
                    DO UPDATE SET
                        package_id = EXCLUDED.package_id,
                        review_status = EXCLUDED.review_status,
                        valid_until = EXCLUDED.valid_until,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """
                ),
                {
                    "id": item["id"],
                    "tenant_id": tenant_id,
                    "realm_name": item["realm_name"],
                    "package_id": item["package_id"],
                    "control_uuid": control_uuid,
                    "evidence_type": item["evidence_type"],
                    "title": item["title"],
                    "description": item["description"],
                    "storage_uri": item["storage_uri"],
                    "hash_sha256": item["hash_sha256"],
                    "source_system": item["source_system"],
                    "source_resource_id": item["source_resource_id"],
                    "collector": item["collector"],
                    "collection_method": item["collection_method"],
                    "valid_from": item["valid_from"],
                    "valid_until": item["valid_until"],
                    "summary": item["summary"],
                    "sensitivity": item["sensitivity"],
                    "review_status": item["review_status"],
                    "created_by": item["created_by"],
                    "metadata": _json(item["metadata"]),
                    "provenance": _json({"seed_version": DEMO_SEED_VERSION, "source": "launch_demo_seed"}),
                    "integrity_metadata": _json({"hash_algorithm": "sha256", "hash_sha256": item["hash_sha256"]}),
                    "chain_of_custody": _json_array(
                        [{"action": "seeded", "actor": DEMO_SEED_VERSION, "timestamp": datetime.now(timezone.utc)}]
                    ),
                },
            )
            if framework_uuid and control_uuid:
                db.execute(
                    text(
                        """
                        INSERT INTO evidence_control_links (
                            tenant_id, evidence_item_id, control_id, framework_id,
                            package_id, link_type, status, linked_by, rationale,
                            metadata
                        )
                        VALUES (
                            CAST(:tenant_id AS uuid), CAST(:evidence_item_id AS uuid),
                            CAST(:control_id AS uuid), CAST(:framework_id AS uuid),
                            CAST(:package_id AS uuid), 'supports', 'active',
                            :linked_by, :rationale, CAST(:metadata AS jsonb)
                        )
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "evidence_item_id": item["id"],
                        "control_id": control_uuid,
                        "framework_id": framework_uuid,
                        "package_id": item["package_id"],
                        "linked_by": DEMO_SEED_VERSION,
                        "rationale": "Launch demo evidence supports SOC 2 logical access review.",
                        "metadata": _json({"seed_version": DEMO_SEED_VERSION}),
                    },
                )
        return len(evidence_items)

    def _apply_collection_tasks(self, db: Session, tenant_id: str, tasks: list[dict[str, Any]]) -> int:
        for task in tasks:
            db.execute(
                text(
                    """
                    INSERT INTO evidence_collection_tasks (
                        id, tenant_id, realm_name, package_id, task_name, task_type,
                        status, completed_at, evidence_items_created, source_system,
                        source_resource_id, collector, collection_method, requested_by,
                        created_by, metadata
                    )
                    VALUES (
                        CAST(:id AS uuid), CAST(:tenant_id AS uuid), :realm_name,
                        CAST(:package_id AS uuid), :task_name, :task_type, :status,
                        :completed_at, CAST(:evidence_items_created AS uuid[]),
                        :source_system, :source_resource_id, :collector,
                        :collection_method, :requested_by, :requested_by,
                        CAST(:metadata AS jsonb)
                    )
                    ON CONFLICT (id)
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        evidence_items_created = EXCLUDED.evidence_items_created,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """
                ),
                {
                    "id": task["id"],
                    "tenant_id": tenant_id,
                    "realm_name": task["realm_name"],
                    "package_id": task["package_id"],
                    "task_name": task["task_name"],
                    "task_type": task["task_type"],
                    "status": task["status"],
                    "completed_at": task["completed_at"],
                    "evidence_items_created": _uuid_array_literal(task["evidence_items_created"]),
                    "source_system": task["source_system"],
                    "source_resource_id": task["source_resource_id"],
                    "collector": task["collector"],
                    "collection_method": task["collection_method"],
                    "requested_by": task["requested_by"],
                    "metadata": _json(task["metadata"]),
                },
            )
        return len(tasks)

    def _apply_reports(self, db: Session, tenant_id: str, reports: list[dict[str, Any]]) -> int:
        for report in reports:
            db.execute(
                text(
                    """
                    INSERT INTO reporting.reports (
                        id, tenant_id, template_id, name, format, status,
                        generated_by, date_range_start, date_range_end, file_path,
                        file_size_bytes, metadata, sections
                    )
                    VALUES (
                        :id, :tenant_id, NULL, :name, :format, :status,
                        :generated_by, :date_range_start, :date_range_end, :file_path,
                        :file_size_bytes, CAST(:metadata AS json), CAST(:sections AS json)
                    )
                    ON CONFLICT (id)
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        file_path = EXCLUDED.file_path,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """
                ),
                {
                    "id": report["id"],
                    "tenant_id": tenant_id,
                    "name": report["name"],
                    "format": report["format"],
                    "status": report["status"],
                    "generated_by": report["generated_by"],
                    "date_range_start": report["date_range_start"],
                    "date_range_end": report["date_range_end"],
                    "file_path": report["file_path"],
                    "file_size_bytes": report["file_size_bytes"],
                    "metadata": _json(report["metadata"]),
                    "sections": _json_array([]),
                },
            )
        return len(reports)

    def _apply_recommendations(self, db: Session, tenant_id: str, recommendations: list[dict[str, Any]]) -> int:
        for recommendation in recommendations:
            db.execute(
                text(
                    """
                    INSERT INTO compliance_agent_recommendations (
                        id, tenant_id, trigger_type, recommendation_type, state,
                        priority, source_type, source_id, framework_id, control_id,
                        title, summary, proposed_actions, requires_approval,
                        created_by, idempotency_key, metadata
                    )
                    VALUES (
                        CAST(:id AS uuid), CAST(:tenant_id AS uuid), :trigger_type,
                        :recommendation_type, :state, :priority, :source_type,
                        :source_id, :framework_id, :control_id, :title, :summary,
                        CAST(:proposed_actions AS jsonb), :requires_approval,
                        :created_by, :idempotency_key, CAST(:metadata AS jsonb)
                    )
                    ON CONFLICT (id)
                    DO UPDATE SET
                        state = EXCLUDED.state,
                        priority = EXCLUDED.priority,
                        summary = EXCLUDED.summary,
                        proposed_actions = EXCLUDED.proposed_actions,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """
                ),
                {
                    "id": recommendation["id"],
                    "tenant_id": tenant_id,
                    "trigger_type": recommendation["trigger_type"],
                    "recommendation_type": recommendation["recommendation_type"],
                    "state": recommendation["state"],
                    "priority": recommendation["priority"],
                    "source_type": recommendation["source_type"],
                    "source_id": recommendation["source_id"],
                    "framework_id": recommendation["framework_id"],
                    "control_id": recommendation["control_id"],
                    "title": recommendation["title"],
                    "summary": recommendation["summary"],
                    "proposed_actions": _json_array(recommendation["proposed_actions"]),
                    "requires_approval": recommendation["requires_approval"],
                    "created_by": recommendation["created_by"],
                    "idempotency_key": recommendation["idempotency_key"],
                    "metadata": _json(recommendation["metadata"]),
                },
            )
        return len(recommendations)


launch_demo_seed_service = ComplianceLaunchDemoSeedService()
