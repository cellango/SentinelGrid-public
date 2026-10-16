"""Tenant compliance framework selection persistence."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.framework_catalog import load_framework_catalog, normalize_framework_id


VALID_SELECTION_STATUSES = {"active", "inactive", "evaluating"}

EXTRA_SELECTION_OPTIONS = {
    "iso27001": {
        "framework_id": "iso27001",
        "framework_code": "ISO27001",
        "framework_name": "ISO 27001 Starter Pack",
        "runtime_support": "starter",
        "control_count": 0,
        "description": "Starter-pack support for ISO 27001 readiness workflows.",
    },
    "customer_questionnaires": {
        "framework_id": "customer_questionnaires",
        "framework_code": "CUSTOMER_QUESTIONNAIRES",
        "framework_name": "Customer Security Questionnaires",
        "runtime_support": "workflow",
        "control_count": 0,
        "description": "Questionnaire support for customer security reviews.",
    },
}


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


def _row_mapping(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    if isinstance(row, dict):
        return row
    return {}


def _available_selection_metadata() -> dict[str, dict[str, Any]]:
    catalog = load_framework_catalog()
    options: dict[str, dict[str, Any]] = {}

    for framework_id, framework in catalog.items():
        options[framework_id] = {
            "framework_id": framework_id,
            "framework_code": framework["framework_code"],
            "framework_name": framework["framework_name"],
            "runtime_support": framework["runtime_support"],
            "control_count": framework["control_count"],
            "description": framework["description"],
        }

    options.update(EXTRA_SELECTION_OPTIONS)
    return options


def available_framework_options() -> list[dict[str, Any]]:
    return list(_available_selection_metadata().values())


def normalize_selection_framework_id(value: str) -> str | None:
    normalized = normalize_framework_id(value)
    if normalized in _available_selection_metadata():
        return normalized
    return None


def _selection_payload(row: dict[str, Any]) -> dict[str, Any]:
    framework_id = normalize_selection_framework_id(str(row.get("framework_id") or ""))
    if not framework_id:
        framework_id = str(row.get("framework_id") or "")

    metadata = _available_selection_metadata().get(framework_id, {})
    selected_at = row.get("selected_at")
    updated_at = row.get("updated_at")
    target_date = row.get("target_date")

    return {
        "framework_id": framework_id,
        "framework_code": metadata.get("framework_code"),
        "framework_name": metadata.get("framework_name", framework_id),
        "runtime_support": metadata.get("runtime_support", "unknown"),
        "control_count": metadata.get("control_count", 0),
        "status": row.get("status", "active"),
        "priority": row.get("priority"),
        "target_date": target_date.isoformat() if isinstance(target_date, date) else target_date,
        "selected_by": row.get("selected_by"),
        "selected_at": selected_at.isoformat() if hasattr(selected_at, "isoformat") else selected_at,
        "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
        "source": row.get("source", "manual"),
    }


def _extract_trust_profile_frameworks(row: dict[str, Any]) -> list[str]:
    frameworks: list[str] = []
    for key in ("tenant_services", "onboarding_services"):
        services = _as_json_object(row.get(key))
        profile = services.get("trustProfile") if isinstance(services.get("trustProfile"), dict) else {}
        for raw_framework in profile.get("frameworks") or []:
            framework_id = normalize_selection_framework_id(str(raw_framework))
            if framework_id and framework_id not in frameworks:
                frameworks.append(framework_id)
    return frameworks


class FrameworkSelectionService:
    """Tenant framework selection read/write service."""

    def list_selections(self, db: Session, tenant_id: str) -> dict[str, Any]:
        self.seed_from_onboarding_if_empty(db, tenant_id)
        rows = db.execute(
            text(
                """
                SELECT framework_id, status, priority, target_date, selected_by,
                       selected_at, updated_at, source
                FROM tenant_framework_selections
                WHERE tenant_id = CAST(:tenant_id AS uuid)
                ORDER BY COALESCE(priority, 999), framework_id
                """
            ),
            {"tenant_id": tenant_id},
        ).mappings().all()

        items = [_selection_payload(dict(row)) for row in rows]
        return {
            "tenant_id": tenant_id,
            "items": items,
            "count": len(items),
            "available_frameworks": available_framework_options(),
            "source": "tenant_framework_selections",
        }

    def replace_selections(
        self,
        db: Session,
        tenant_id: str,
        selections: list[dict[str, Any]],
        selected_by: str | None = None,
    ) -> dict[str, Any]:
        if not selections:
            raise ValueError("At least one framework selection is required")

        normalized_rows: list[dict[str, Any]] = []
        seen: set[str] = set()

        for index, selection in enumerate(selections):
            framework_id = normalize_selection_framework_id(str(selection.get("framework_id") or ""))
            if not framework_id:
                raise ValueError(f"Unsupported compliance framework: {selection.get('framework_id')}")
            if framework_id in seen:
                raise ValueError(f"Duplicate compliance framework selection: {framework_id}")

            status = str(selection.get("status") or "active").strip().lower()
            if status not in VALID_SELECTION_STATUSES:
                raise ValueError(f"Unsupported framework selection status: {status}")

            seen.add(framework_id)
            normalized_rows.append(
                {
                    "framework_id": framework_id,
                    "status": status,
                    "priority": selection.get("priority", index + 1),
                    "target_date": selection.get("target_date"),
                    "selected_by": selected_by or selection.get("selected_by") or "system",
                }
            )

        db.execute(
            text("DELETE FROM tenant_framework_selections WHERE tenant_id = CAST(:tenant_id AS uuid)"),
            {"tenant_id": tenant_id},
        )
        for row in normalized_rows:
            db.execute(
                text(
                    """
                    INSERT INTO tenant_framework_selections (
                        tenant_id, framework_id, status, priority, target_date,
                        selected_by, selected_at, source
                    )
                    VALUES (
                        CAST(:tenant_id AS uuid), :framework_id, :status, :priority,
                        CAST(:target_date AS date), :selected_by, NOW(), 'manual'
                    )
                    """
                ),
                {"tenant_id": tenant_id, **row},
            )

        return self.list_selections(db, tenant_id)

    def seed_from_onboarding_if_empty(self, db: Session, tenant_id: str) -> None:
        count_row = db.execute(
            text(
                """
                SELECT COUNT(*) AS count
                FROM tenant_framework_selections
                WHERE tenant_id = CAST(:tenant_id AS uuid)
                """
            ),
            {"tenant_id": tenant_id},
        ).first()
        count = int(_row_mapping(count_row).get("count") or 0)
        if count > 0:
            return

        trust_profile_row = db.execute(
            text(
                """
                SELECT t.services_selected AS tenant_services,
                       op.services_selected AS onboarding_services
                FROM tenants t
                LEFT JOIN onboarding_progress op ON op.customer_id = t.customer_id
                WHERE t.id = CAST(:tenant_id AS uuid)
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        ).first()
        frameworks = _extract_trust_profile_frameworks(_row_mapping(trust_profile_row))
        if not frameworks:
            return

        for index, framework_id in enumerate(frameworks):
            runtime_support = _available_selection_metadata()[framework_id]["runtime_support"]
            status = "evaluating" if runtime_support in {"starter", "workflow"} else "active"
            db.execute(
                text(
                    """
                    INSERT INTO tenant_framework_selections (
                        tenant_id, framework_id, status, priority,
                        selected_by, selected_at, source
                    )
                    VALUES (
                        CAST(:tenant_id AS uuid), :framework_id, :status, :priority,
                        'onboarding_trust_profile', NOW(), 'onboarding_trust_profile'
                    )
                    ON CONFLICT (tenant_id, framework_id) DO NOTHING
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "framework_id": framework_id,
                    "status": status,
                    "priority": index + 1,
                },
            )


framework_selection_service = FrameworkSelectionService()
