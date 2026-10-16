"""Multi-framework compliance coverage read model."""

from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.schemas.coverage import ControlCoverage, CoverageStatus, FrameworkCoverage
from app.services.control_signal_mapper import build_soc2_framework_coverage
from app.services.framework_catalog import load_framework_catalog, normalize_framework_id
from app.services.framework_selection import available_framework_options, framework_selection_service
from app.services.coverage_domain import summarize_framework_coverage


ACTIVE_SELECTION_STATUSES = {"active", "evaluating"}


def _option_metadata() -> dict[str, dict[str, Any]]:
    return {item["framework_id"]: item for item in available_framework_options()}


def _fallback_soc2_selection() -> dict[str, Any]:
    metadata = _option_metadata()["soc2"]
    return {
        **metadata,
        "status": "active",
        "priority": 1,
        "source": "default_soc2_readiness",
    }


def _selected_frameworks(db: Session, tenant_id: str) -> list[dict[str, Any]]:
    selection_payload = framework_selection_service.list_selections(db, tenant_id)
    selected = [
        item
        for item in selection_payload.get("items", [])
        if item.get("status") in ACTIVE_SELECTION_STATUSES
    ]
    return selected or [_fallback_soc2_selection()]


def _selection_for_framework(db: Session, tenant_id: str, framework_id: str) -> dict[str, Any] | None:
    normalized = normalize_framework_id(framework_id)
    for item in framework_selection_service.list_selections(db, tenant_id).get("items", []):
        if item.get("framework_id") == normalized:
            return item
    metadata = _option_metadata().get(normalized)
    if metadata:
        return {
            **metadata,
            "status": "available",
            "priority": None,
            "source": "framework_catalog",
        }
    return None


def _catalog_framework_coverage(
    tenant_id: str,
    framework_id: str,
) -> FrameworkCoverage | None:
    normalized = normalize_framework_id(framework_id)
    catalog = load_framework_catalog()
    framework = catalog.get(normalized)
    metadata = _option_metadata().get(normalized)
    if not framework and not metadata:
        return None

    controls = []
    for control in (framework or {}).get("controls", []):
        controls.append(
            ControlCoverage(
                tenant_id=tenant_id,
                framework_id=normalized,
                control_id=control["control_id"],
                title=control["title"],
                status=CoverageStatus.NOT_STARTED,
                confidence=0,
                metadata={
                    "description": control.get("description"),
                    "category": control.get("category"),
                    "priority": control.get("priority"),
                    "coverage_level": control.get("coverage_level"),
                    "runtime_support": (framework or metadata or {}).get("runtime_support", "catalog"),
                    "trace": [
                        "Framework catalog is selected, but signal and evidence mapping are not active for this framework yet.",
                        "Derived coverage status: not_started.",
                    ],
                },
            )
        )

    return summarize_framework_coverage(tenant_id=tenant_id, framework_id=normalized, controls=controls)


def _framework_coverage(
    tenant_id: str,
    framework_id: str,
    inputs: dict[str, list],
) -> FrameworkCoverage | None:
    normalized = normalize_framework_id(framework_id)
    if normalized == "soc2":
        return build_soc2_framework_coverage(
            tenant_id=tenant_id,
            iam_rows=inputs.get("iam_rows", []),
            posture_rows=inputs.get("posture_rows", []),
            alerts=inputs.get("alerts", []),
            playbooks=inputs.get("playbooks", []),
            executions=inputs.get("executions", []),
        )
    return _catalog_framework_coverage(tenant_id, normalized)


def _control_payload(control: ControlCoverage) -> dict[str, Any]:
    metadata = control.metadata or {}
    return {
        "id": control.control_id,
        "framework_id": control.framework_id,
        "control_id": control.control_id,
        "title": control.title,
        "description": metadata.get("description"),
        "status": control.status.value,
        "severity": control.severity.value if control.severity else None,
        "confidence": control.confidence,
        "signals": [item.model_dump(mode="json") for item in control.signals],
        "gaps": [item.model_dump(mode="json") for item in control.gaps],
        "evidence_requirements": [
            item.model_dump(mode="json") for item in control.evidence_requirements
        ],
        "last_activity": control.last_activity.isoformat() if control.last_activity else None,
        "trace": metadata.get("trace", []),
        "metadata": {
            key: value
            for key, value in metadata.items()
            if key not in {"trace", "key_detections", "control_checks", "supporting_playbooks"}
        },
    }


def _paginate_controls(
    controls: Iterable[ControlCoverage],
    *,
    limit: int,
    offset: int,
) -> tuple[list[ControlCoverage], int]:
    control_list = list(controls)
    return control_list[offset: offset + limit], len(control_list)


def _framework_payload(
    framework_coverage: FrameworkCoverage,
    selection: dict[str, Any],
    *,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    controls, total_controls = _paginate_controls(framework_coverage.controls, limit=limit, offset=offset)
    metadata = _option_metadata().get(framework_coverage.framework_id, {})
    return {
        "tenant_id": framework_coverage.tenant_id,
        "framework_id": framework_coverage.framework_id,
        "framework_code": selection.get("framework_code") or metadata.get("framework_code"),
        "framework_name": selection.get("framework_name") or metadata.get("framework_name", framework_coverage.framework_id),
        "runtime_support": selection.get("runtime_support") or metadata.get("runtime_support", "unknown"),
        "selection_status": selection.get("status", "available"),
        "selection_source": selection.get("source"),
        "status": framework_coverage.status.value,
        "status_counts": framework_coverage.status_counts,
        "average_confidence": framework_coverage.average_confidence,
        "control_count": total_controls,
        "returned_control_count": len(controls),
        "limit": limit,
        "offset": offset,
        "generated_at": framework_coverage.generated_at.isoformat(),
        "controls": [_control_payload(control) for control in controls],
    }


def build_multi_framework_coverage_payload(
    db: Session,
    tenant_id: str,
    inputs: dict[str, list],
    *,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    selections = _selected_frameworks(db, tenant_id)
    items: list[dict[str, Any]] = []

    for selection in selections:
        coverage = _framework_coverage(tenant_id, selection["framework_id"], inputs)
        if coverage:
            items.append(_framework_payload(coverage, selection, limit=limit, offset=offset))

    return {
        "tenant_id": tenant_id,
        "items": items,
        "count": len(items),
        "limit": limit,
        "offset": offset,
        "source": "generalized_coverage_engine",
    }


def build_framework_coverage_payload(
    db: Session,
    tenant_id: str,
    framework_id: str,
    inputs: dict[str, list],
    *,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any] | None:
    selection = _selection_for_framework(db, tenant_id, framework_id)
    if not selection:
        return None
    coverage = _framework_coverage(tenant_id, framework_id, inputs)
    if not coverage:
        return None
    return _framework_payload(coverage, selection, limit=limit, offset=offset)


def build_control_status_payload(
    db: Session,
    tenant_id: str,
    control_id: str,
    inputs: dict[str, list],
    *,
    framework_id: str | None = None,
) -> dict[str, Any] | None:
    requested_control_id = control_id.strip().lower()
    if framework_id:
        selection = _selection_for_framework(db, tenant_id, framework_id)
        selections = [selection] if selection else []
    else:
        selections = _selected_frameworks(db, tenant_id)

    matches: list[dict[str, Any]] = []
    for selection in selections:
        if not selection:
            continue
        coverage = _framework_coverage(tenant_id, selection["framework_id"], inputs)
        if not coverage:
            continue
        for control in coverage.controls:
            if control.control_id.lower() == requested_control_id:
                payload = _control_payload(control)
                payload["framework_name"] = selection.get("framework_name")
                payload["runtime_support"] = selection.get("runtime_support")
                payload["selection_status"] = selection.get("status")
                matches.append(payload)

    if not matches:
        return None

    return {
        "tenant_id": tenant_id,
        "control_id": control_id,
        "framework_id": normalize_framework_id(framework_id) if framework_id else None,
        "items": matches,
        "count": len(matches),
        "source": "generalized_coverage_engine",
    }

