"""Launch readiness metadata and tenant compliance feature controls."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings


COMPLIANCE_LAUNCH_VERSION = "phase8_launch_2026_04_28"

CONTROL_DEFINITIONS: dict[str, dict[str, str]] = {
    "multi_framework_selection": {
        "label": "Multi-framework selection",
        "description": "Allow tenant admins to change selected compliance frameworks.",
        "env_var": "COMPLIANCE_MULTI_FRAMEWORK_ENABLED",
        "feature_flag_key": "compliance_multi_framework_enabled",
    },
    "durable_evidence_repository": {
        "label": "Durable evidence repository",
        "description": "Allow evidence repository, package, review, retention, and export workflows.",
        "env_var": "COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED",
        "feature_flag_key": "compliance_evidence_repository_enabled",
    },
    "compliance_agent_workflows": {
        "label": "Compliance Agent workflows",
        "description": "Allow supervised Compliance Agent recommendation workflows.",
        "env_var": "COMPLIANCE_AGENT_ENABLED",
        "feature_flag_key": "compliance_agent_enabled",
    },
}

FRAMEWORK_LIMITATIONS: list[dict[str, Any]] = [
    {
        "framework_id": "soc2",
        "framework_name": "SOC 2 Trust Services Criteria",
        "support_level": "readiness_and_evidence_backed_reporting",
        "available": [
            "selected framework scope",
            "SOC 2 coverage dashboard",
            "IAM evidence collection",
            "evidence package exports",
            "evidence-backed report snapshots",
            "supervised Compliance Agent recommendations",
        ],
        "limitations": [
            "Report readiness depends on accepted, non-expired evidence.",
            "SentinelGrid does not provide an auditor attestation or guarantee SOC 2 compliance.",
        ],
    },
    {
        "framework_id": "hipaa",
        "framework_name": "HIPAA Security Rule",
        "support_level": "catalog_and_gap_tracking",
        "available": [
            "framework selection",
            "control catalog",
            "gap visibility",
            "manual or IAM-linked evidence package inclusion",
            "report scope inclusion",
        ],
        "limitations": [
            "HIPAA legal compliance determination remains the customer's responsibility.",
            "Only mapped runtime signals affect status automatically; unmapped controls remain not started or needs evidence.",
        ],
    },
    {
        "framework_id": "pci_dss",
        "framework_name": "PCI DSS",
        "support_level": "catalog_and_gap_tracking",
        "available": [
            "framework selection",
            "control catalog",
            "gap visibility",
            "manual evidence package inclusion",
        ],
        "limitations": [
            "PCI assessor-ready evidence is not fully automated.",
            "Cardholder data environment scoping and compensating controls must be reviewed outside the product.",
        ],
    },
    {
        "framework_id": "nist_800_171",
        "framework_name": "NIST 800-171",
        "support_level": "catalog_and_gap_tracking",
        "available": [
            "framework selection",
            "control catalog",
            "gap visibility",
            "manual evidence package inclusion",
        ],
        "limitations": [
            "CUI boundary validation is not automated.",
            "Control implementation status is only as complete as mapped signals and reviewed evidence.",
        ],
    },
    {
        "framework_id": "iso27001",
        "framework_name": "ISO 27001 Starter Pack",
        "support_level": "starter_pack",
        "available": [
            "starter-pack positioning",
            "trust artifact workflow support",
        ],
        "limitations": [
            "No full ISO 27001 control catalog or automated statement of applicability is shipped in this slice.",
        ],
    },
    {
        "framework_id": "customer_questionnaires",
        "framework_name": "Customer Security Questionnaires",
        "support_level": "workflow_support",
        "available": [
            "questionnaire workflow support",
            "report and evidence context reuse",
        ],
        "limitations": [
            "Questionnaire assist is not a compliance framework and requires human review before sharing externally.",
        ],
    },
]


class ComplianceLaunchControlError(ValueError):
    """Raised when compliance launch control input is invalid."""


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _as_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _is_sqlite(db: Session) -> bool:
    return getattr(getattr(db.bind, "dialect", None), "name", "") == "sqlite"


def _json_bind(name: str, db: Session, *, jsonb: bool = True) -> str:
    if _is_sqlite(db):
        return f":{name}"
    return f"CAST(:{name} AS {'jsonb' if jsonb else 'json'})"


def _tenant_id_bind(db: Session) -> str:
    return ":tenant_id" if _is_sqlite(db) else "CAST(:tenant_id AS uuid)"


def _now_sql(db: Session) -> str:
    return "CURRENT_TIMESTAMP" if _is_sqlite(db) else "NOW()"


def _ensure_tenant_preferences_table(db: Session) -> None:
    if _is_sqlite(db):
        ddl = """
            CREATE TABLE IF NOT EXISTS tenant_preferences (
                tenant_id TEXT PRIMARY KEY,
                alert_preferences TEXT NOT NULL DEFAULT '{}',
                feature_flags TEXT NOT NULL DEFAULT '{}',
                notification_email TEXT,
                updated_at TEXT NOT NULL
            )
        """
    else:
        ddl = """
            CREATE TABLE IF NOT EXISTS public.tenant_preferences (
                tenant_id UUID PRIMARY KEY REFERENCES public.tenants(id) ON DELETE CASCADE,
                alert_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
                feature_flags JSONB NOT NULL DEFAULT '{}'::jsonb,
                notification_email TEXT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """
    db.execute(text(ddl))


def _platform_enabled(control_key: str) -> bool:
    if control_key == "multi_framework_selection":
        return bool(settings.COMPLIANCE_MULTI_FRAMEWORK_ENABLED)
    if control_key == "durable_evidence_repository":
        return bool(settings.COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED)
    if control_key == "compliance_agent_workflows":
        return bool(settings.COMPLIANCE_AGENT_ENABLED)
    return False


def _load_feature_flag_row(db: Session, tenant_id: str) -> dict[str, Any]:
    _ensure_tenant_preferences_table(db)
    tenant_id_bind = _tenant_id_bind(db)
    row = _first_mapping(
        db.execute(
            text(
                f"""
                SELECT feature_flags, updated_at
                FROM tenant_preferences
                WHERE tenant_id = {tenant_id_bind}
                """
            ),
            {"tenant_id": tenant_id},
        )
    )
    return {
        "feature_flags": _as_json_object(row.get("feature_flags")),
        "updated_at": row.get("updated_at"),
    }


def _control_payload(control_key: str, feature_flags: dict[str, Any]) -> dict[str, Any]:
    definition = CONTROL_DEFINITIONS[control_key]
    platform_enabled = _platform_enabled(control_key)
    raw_requested = feature_flags.get(definition["feature_flag_key"])
    requested_enabled = platform_enabled if raw_requested is None else bool(raw_requested)
    effective_enabled = platform_enabled and requested_enabled

    return {
        "key": control_key,
        "label": definition["label"],
        "description": definition["description"],
        "env_var": definition["env_var"],
        "feature_flag_key": definition["feature_flag_key"],
        "platform_enabled": platform_enabled,
        "requested_enabled": requested_enabled,
        "effective_enabled": effective_enabled,
        "mutable_by_admin": platform_enabled,
        "blocked_reason": None
        if platform_enabled
        else f"Set {definition['env_var']}=true before this tenant control can become effective.",
    }


class ComplianceLaunchReadinessService:
    """Build launch readiness and admin-control payloads."""

    def get_admin_settings(self, db: Session, tenant_id: str) -> dict[str, Any]:
        row = _load_feature_flag_row(db, tenant_id)
        feature_flags = row["feature_flags"]
        controls = {
            control_key: _control_payload(control_key, feature_flags)
            for control_key in CONTROL_DEFINITIONS
        }
        return {
            "tenant_id": tenant_id,
            "source": "tenant_preferences.feature_flags",
            "launch_version": COMPLIANCE_LAUNCH_VERSION,
            "updated_at": row.get("updated_at").isoformat()
            if hasattr(row.get("updated_at"), "isoformat")
            else row.get("updated_at"),
            "controls": controls,
        }

    def update_admin_settings(
        self,
        db: Session,
        tenant_id: str,
        updates: dict[str, bool],
        *,
        actor_id: str,
    ) -> dict[str, Any]:
        unknown = sorted(set(updates) - set(CONTROL_DEFINITIONS))
        if unknown:
            raise ComplianceLaunchControlError(
                f"Unsupported compliance launch controls: {', '.join(unknown)}"
            )

        row = _load_feature_flag_row(db, tenant_id)
        feature_flags = row["feature_flags"]
        for control_key, enabled in updates.items():
            feature_flags[CONTROL_DEFINITIONS[control_key]["feature_flag_key"]] = bool(enabled)

        feature_flags["compliance_launch_controls_updated_by"] = actor_id
        feature_flags["compliance_launch_controls_updated_at"] = _utcnow_iso()
        feature_flags["compliance_launch_version"] = COMPLIANCE_LAUNCH_VERSION

        feature_flags_bind = _json_bind("feature_flags", db)
        tenant_id_bind = _tenant_id_bind(db)
        now_sql = _now_sql(db)
        db.execute(
            text(
                f"""
                INSERT INTO tenant_preferences (tenant_id, feature_flags, updated_at)
                VALUES ({tenant_id_bind}, {feature_flags_bind}, {now_sql})
                ON CONFLICT (tenant_id)
                DO UPDATE SET
                    feature_flags = {feature_flags_bind},
                    updated_at = {now_sql}
                """
            ),
            {
                "tenant_id": tenant_id,
                "feature_flags": json.dumps(feature_flags, sort_keys=True),
            },
        )
        return self.get_admin_settings(db, tenant_id)

    def build_launch_readiness(self, db: Session, tenant_id: str) -> dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "launch_version": COMPLIANCE_LAUNCH_VERSION,
            "readiness_status": "go_recommended_with_operator_signoff",
            "product_copy": {
                "module_name": "Compliance",
                "dashboard_title": "Compliance Dashboard"
                if settings.COMPLIANCE_MULTI_FRAMEWORK_ENABLED
                else "SOC 2 Readiness Dashboard",
                "reports_title": "Compliance Reports"
                if settings.COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED
                else "Trust & SOC 2 Reports",
                "evidence_label": "Evidence items"
                if settings.COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED
                else "Report-ready signals",
                "customer_summary": (
                    "Select supported frameworks, collect and review evidence, package audit artifacts, "
                    "and generate evidence-backed compliance reports. Non-SOC 2 frameworks show truthful "
                    "catalog and gap state until mapped signals and reviewed evidence support the control."
                ),
            },
            "known_limitations": FRAMEWORK_LIMITATIONS,
            "admin_settings": self.get_admin_settings(db, tenant_id),
            "demo_seed": {
                "script": "backend/scripts/seed_compliance_launch_demo.py",
                "dry_run_command": (
                    "PYTHONPATH=backend/services/compliance_service:backend/libs "
                    "python backend/scripts/seed_compliance_launch_demo.py --tenant-slug demo"
                ),
                "apply_command": (
                    "PYTHONPATH=backend/services/compliance_service:backend/libs "
                    "python backend/scripts/seed_compliance_launch_demo.py --tenant-slug demo --apply"
                ),
            },
            "go_no_go_review": {
                "artifact": "docs/archive/validation/compliance/compliance-launch-readiness-signoff-2026-04-28.md",
                "required_owners": ["Product", "Security", "Platform", "Support"],
                "decision": "go_recommended",
            },
        }


launch_readiness_service = ComplianceLaunchReadinessService()
