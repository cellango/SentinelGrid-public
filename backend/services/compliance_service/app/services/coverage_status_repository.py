"""Persistence helpers for generalized tenant control coverage status."""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.coverage import ControlCoverage


UPSERT_CONTROL_COVERAGE_SQL = """
INSERT INTO tenant_control_status (
    tenant_id,
    realm_name,
    control_id,
    coverage_status,
    coverage_severity,
    coverage_confidence,
    coverage_signals,
    coverage_gaps,
    evidence_requirement_statuses,
    last_coverage_refresh_at,
    last_assessed_at
)
VALUES (
    CAST(:tenant_id AS uuid),
    :realm_name,
    CAST(:control_db_id AS uuid),
    :coverage_status,
    :coverage_severity,
    :coverage_confidence,
    CAST(:coverage_signals AS jsonb),
    CAST(:coverage_gaps AS jsonb),
    CAST(:evidence_requirement_statuses AS jsonb),
    NOW(),
    NOW()
)
ON CONFLICT (tenant_id, realm_name, control_id)
DO UPDATE SET
    coverage_status = EXCLUDED.coverage_status,
    coverage_severity = EXCLUDED.coverage_severity,
    coverage_confidence = EXCLUDED.coverage_confidence,
    coverage_signals = EXCLUDED.coverage_signals,
    coverage_gaps = EXCLUDED.coverage_gaps,
    evidence_requirement_statuses = EXCLUDED.evidence_requirement_statuses,
    last_coverage_refresh_at = NOW(),
    last_assessed_at = NOW(),
    updated_at = NOW()
"""


def control_coverage_to_db_params(
    coverage: ControlCoverage,
    control_db_id: str,
    realm_name: str,
) -> dict:
    return {
        "tenant_id": coverage.tenant_id,
        "realm_name": realm_name,
        "control_db_id": control_db_id,
        "coverage_status": coverage.status.value,
        "coverage_severity": coverage.severity.value if coverage.severity else None,
        "coverage_confidence": round(coverage.confidence, 4),
        "coverage_signals": json.dumps([item.model_dump(mode="json") for item in coverage.signals]),
        "coverage_gaps": json.dumps([item.model_dump(mode="json") for item in coverage.gaps]),
        "evidence_requirement_statuses": json.dumps(
            [item.model_dump(mode="json") for item in coverage.evidence_requirements]
        ),
    }


def upsert_control_coverage_status(
    db: Session,
    coverage: ControlCoverage,
    control_db_id: str,
    realm_name: str,
) -> None:
    db.execute(
        text(UPSERT_CONTROL_COVERAGE_SQL),
        control_coverage_to_db_params(coverage, control_db_id=control_db_id, realm_name=realm_name),
    )
