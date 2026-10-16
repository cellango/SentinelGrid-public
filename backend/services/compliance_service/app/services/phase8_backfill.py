"""Phase 8 migration and backfill helpers for compliance runtime rollout."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.framework_selection import (
    _available_selection_metadata,
    _extract_trust_profile_frameworks,
    normalize_selection_framework_id,
)


BACKFILL_VERSION = "phase8_2026_04_28"
LEGACY_SOC2_SOURCE = "legacy_soc2_readiness"
TRUST_PROFILE_SOURCE = "onboarding_trust_profile"


def _as_mapping(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    if isinstance(row, dict):
        return row
    return {}


def _as_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _has_path(payload: dict[str, Any], *keys: str) -> bool:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]
    return True


def _looks_compliance_report(row: dict[str, Any]) -> bool:
    metadata = _as_json_object(row.get("metadata"))
    haystack = " ".join(
        str(value or "")
        for value in (
            row.get("name"),
            row.get("report_name"),
            row.get("report_type"),
            row.get("template_name"),
            row.get("template_type"),
            metadata.get("report_type"),
            metadata.get("template_key"),
        )
    ).lower()
    return any(token in haystack for token in ("soc2", "soc 2", "compliance", "trust", "evidence", "audit"))


def _infer_framework_ids(row: dict[str, Any]) -> list[str]:
    metadata = _as_json_object(row.get("metadata"))
    existing_inputs = _as_json_object(metadata.get("report_inputs"))
    existing_frameworks = existing_inputs.get("framework_ids") or metadata.get("framework_ids") or []
    inferred: list[str] = []

    for value in existing_frameworks if isinstance(existing_frameworks, list) else [existing_frameworks]:
        framework_id = normalize_selection_framework_id(str(value))
        if framework_id and framework_id not in inferred:
            inferred.append(framework_id)

    haystack = " ".join(
        str(value or "")
        for value in (
            row.get("name"),
            row.get("report_name"),
            row.get("report_type"),
            row.get("template_name"),
            row.get("template_type"),
            metadata.get("report_type"),
            metadata.get("template_key"),
        )
    ).lower()
    aliases = (
        ("soc2", ("soc2", "soc 2", "soc_2")),
        ("hipaa", ("hipaa",)),
        ("pci_dss", ("pci", "pci dss", "pci_dss")),
        ("nist_800_171", ("nist", "nist 800-171", "nist_800_171")),
    )
    for framework_id, tokens in aliases:
        if any(token in haystack for token in tokens) and framework_id not in inferred:
            inferred.append(framework_id)

    return inferred


def build_legacy_report_metadata(row: dict[str, Any]) -> dict[str, Any] | None:
    """Return metadata for a legacy compliance report without claiming evidence."""
    if not _looks_compliance_report(row):
        return None

    metadata = _as_json_object(row.get("metadata"))
    if _has_path(metadata, "compliance_snapshot", "snapshot_hash_sha256"):
        return None

    framework_ids = _infer_framework_ids(row)
    if not framework_ids:
        framework_ids = ["soc2"]

    report_inputs = _as_json_object(metadata.get("report_inputs"))
    report_inputs.setdefault("framework_ids", framework_ids)
    if row.get("report_type"):
        report_inputs.setdefault("legacy_report_type", row.get("report_type"))

    metadata["report_inputs"] = report_inputs
    metadata.setdefault("report_type", row.get("template_type") or row.get("report_type") or "compliance")
    metadata.setdefault(
        "compliance_snapshot",
        {
            "status": "legacy_metadata_only",
            "source": "phase8_migration_backfill",
            "snapshot_hash_sha256": None,
            "evidence_backfilled": False,
            "reason": "Report was generated before durable evidence-backed report snapshots existed.",
        },
    )
    metadata.setdefault("coverage_snapshot_source", "legacy_report_metadata_only")
    metadata["phase8_migration_backfill"] = {
        "version": BACKFILL_VERSION,
        "evidence_items_created": 0,
        "evidence_backfilled": False,
        "note": "No evidence items were created from inferred legacy report counts.",
    }
    return metadata


@dataclass
class CompliancePhase8BackfillResult:
    dry_run: bool
    tenant_scope: str | None = None
    tenants_seen: int = 0
    framework_selection_rows_planned: int = 0
    framework_selection_rows_written: int = 0
    tenants_with_existing_selections: int = 0
    tenants_seeded_from_trust_profile: int = 0
    tenants_seeded_from_legacy_soc2: int = 0
    reports_seen: int = 0
    reports_planned: int = 0
    reports_written: int = 0
    legacy_generated_reports_seen: int = 0
    legacy_generated_reports_planned: int = 0
    legacy_generated_reports_written: int = 0
    evidence_items_created: int = 0
    planned_framework_selections: list[dict[str, Any]] = field(default_factory=list)
    planned_report_metadata_updates: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "tenant_scope": self.tenant_scope,
            "tenants_seen": self.tenants_seen,
            "framework_selection_rows_planned": self.framework_selection_rows_planned,
            "framework_selection_rows_written": self.framework_selection_rows_written,
            "tenants_with_existing_selections": self.tenants_with_existing_selections,
            "tenants_seeded_from_trust_profile": self.tenants_seeded_from_trust_profile,
            "tenants_seeded_from_legacy_soc2": self.tenants_seeded_from_legacy_soc2,
            "reports_seen": self.reports_seen,
            "reports_planned": self.reports_planned,
            "reports_written": self.reports_written,
            "legacy_generated_reports_seen": self.legacy_generated_reports_seen,
            "legacy_generated_reports_planned": self.legacy_generated_reports_planned,
            "legacy_generated_reports_written": self.legacy_generated_reports_written,
            "evidence_items_created": self.evidence_items_created,
            "planned_framework_selections": self.planned_framework_selections,
            "planned_report_metadata_updates": self.planned_report_metadata_updates,
        }


class CompliancePhase8BackfillService:
    """Conservative data backfill for Phase 8.1 migration."""

    def run(
        self,
        db: Session,
        *,
        tenant_id: str | None = None,
        dry_run: bool = True,
    ) -> CompliancePhase8BackfillResult:
        result = CompliancePhase8BackfillResult(dry_run=dry_run, tenant_scope=tenant_id)
        tenant_rows = self._load_tenant_rows(db, tenant_id)
        result.tenants_seen = len(tenant_rows)

        for row in tenant_rows:
            self._backfill_framework_selections(db, row, result)

        self._backfill_reports(db, result, tenant_id=tenant_id, legacy=False)
        self._backfill_reports(db, result, tenant_id=tenant_id, legacy=True)

        if not dry_run:
            db.commit()
        return result

    def _load_tenant_rows(self, db: Session, tenant_id: str | None) -> list[dict[str, Any]]:
        where_clause = "WHERE t.id = CAST(:tenant_id AS uuid)" if tenant_id else ""
        rows = (
            db.execute(
                text(
                    f"""
                    SELECT CAST(t.id AS text) AS tenant_id,
                           t.name AS tenant_name,
                           t.slug AS tenant_slug,
                           t.services_selected AS tenant_services,
                           op.services_selected AS onboarding_services
                    FROM tenants t
                    LEFT JOIN onboarding_progress op ON op.customer_id = t.customer_id
                    {where_clause}
                    ORDER BY t.created_at, t.id
                    """
                ),
                {"tenant_id": tenant_id} if tenant_id else {},
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def _selection_count(self, db: Session, tenant_id: str) -> int:
        row = db.execute(
            text(
                """
                SELECT COUNT(*) AS count
                FROM tenant_framework_selections
                WHERE tenant_id = CAST(:tenant_id AS uuid)
                """
            ),
            {"tenant_id": tenant_id},
        ).first()
        return int(_as_mapping(row).get("count") or 0)

    def _framework_status(self, framework_id: str, *, source: str) -> str:
        if source == LEGACY_SOC2_SOURCE:
            return "active"
        runtime_support = _available_selection_metadata()[framework_id]["runtime_support"]
        return "evaluating" if runtime_support in {"starter", "workflow"} else "active"

    def _backfill_framework_selections(
        self,
        db: Session,
        tenant_row: dict[str, Any],
        result: CompliancePhase8BackfillResult,
    ) -> None:
        tenant_id = str(tenant_row["tenant_id"])
        if self._selection_count(db, tenant_id) > 0:
            result.tenants_with_existing_selections += 1
            return

        frameworks = _extract_trust_profile_frameworks(tenant_row)
        source = TRUST_PROFILE_SOURCE
        if not frameworks:
            frameworks = ["soc2"]
            source = LEGACY_SOC2_SOURCE

        if source == TRUST_PROFILE_SOURCE:
            result.tenants_seeded_from_trust_profile += 1
        else:
            result.tenants_seeded_from_legacy_soc2 += 1

        for index, framework_id in enumerate(frameworks, start=1):
            status = self._framework_status(framework_id, source=source)
            planned = {
                "tenant_id": tenant_id,
                "framework_id": framework_id,
                "status": status,
                "priority": index,
                "source": source,
            }
            result.framework_selection_rows_planned += 1
            result.planned_framework_selections.append(planned)
            if result.dry_run:
                continue

            db.execute(
                text(
                    """
                    INSERT INTO tenant_framework_selections (
                        tenant_id, framework_id, status, priority,
                        selected_by, selected_at, source
                    )
                    VALUES (
                        CAST(:tenant_id AS uuid), :framework_id, :status, :priority,
                        :selected_by, NOW(), :source
                    )
                    ON CONFLICT (tenant_id, framework_id) DO NOTHING
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "framework_id": framework_id,
                    "status": status,
                    "priority": index,
                    "selected_by": source,
                    "source": source,
                },
            )
            result.framework_selection_rows_written += 1

    def _report_rows(self, db: Session, *, tenant_id: str | None, legacy: bool) -> list[dict[str, Any]]:
        where_clause = "WHERE r.tenant_id = CAST(:tenant_id AS uuid)" if tenant_id else ""
        params = {"tenant_id": tenant_id} if tenant_id else {}
        if legacy:
            rows = (
                db.execute(
                    text(
                        f"""
                        SELECT CAST(r.id AS text) AS id,
                               CAST(r.tenant_id AS text) AS tenant_id,
                               r.report_name AS name,
                               r.report_type,
                               r.metadata
                        FROM reporting.generated_reports r
                        {where_clause}
                        ORDER BY r.generated_at NULLS LAST, r.id
                        """
                    ),
                    params,
                )
                .mappings()
                .all()
            )
            return [dict(row) for row in rows]

        rows = (
            db.execute(
                text(
                    f"""
                    SELECT r.id,
                           r.tenant_id,
                           r.name,
                           r.metadata,
                           rt.type AS template_type,
                           rt.name AS template_name
                    FROM reporting.reports r
                    LEFT JOIN reporting.report_templates rt ON rt.id = r.template_id
                    {where_clause}
                    ORDER BY r.created_at NULLS LAST, r.id
                    """
                ),
                params,
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def _backfill_reports(
        self,
        db: Session,
        result: CompliancePhase8BackfillResult,
        *,
        tenant_id: str | None,
        legacy: bool,
    ) -> None:
        rows = self._report_rows(db, tenant_id=tenant_id, legacy=legacy)
        if legacy:
            result.legacy_generated_reports_seen = len(rows)
        else:
            result.reports_seen = len(rows)

        for row in rows:
            metadata = build_legacy_report_metadata(row)
            if metadata is None:
                continue

            planned = {
                "report_id": row["id"],
                "tenant_id": row["tenant_id"],
                "legacy_generated_report": legacy,
                "framework_ids": metadata.get("report_inputs", {}).get("framework_ids", []),
                "snapshot_status": metadata.get("compliance_snapshot", {}).get("status"),
            }
            result.planned_report_metadata_updates.append(planned)
            if legacy:
                result.legacy_generated_reports_planned += 1
            else:
                result.reports_planned += 1
            if result.dry_run:
                continue

            if legacy:
                db.execute(
                    text(
                        """
                        UPDATE reporting.generated_reports
                        SET metadata = CAST(:metadata AS jsonb), updated_at = NOW()
                        WHERE id = CAST(:report_id AS uuid)
                        """
                    ),
                    {"report_id": row["id"], "metadata": json.dumps(metadata, sort_keys=True)},
                )
                result.legacy_generated_reports_written += 1
            else:
                db.execute(
                    text(
                        """
                        UPDATE reporting.reports
                        SET metadata = CAST(:metadata AS json), updated_at = NOW()
                        WHERE id = :report_id
                        """
                    ),
                    {"report_id": row["id"], "metadata": json.dumps(metadata, sort_keys=True)},
                )
                result.reports_written += 1


phase8_backfill_service = CompliancePhase8BackfillService()
