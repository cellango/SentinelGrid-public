from pathlib import Path
import json
import os
import sys

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

os.environ.setdefault("DB_HOST", "localhost")

from app.schemas.coverage import (
    ControlCoverage,
    ControlGap,
    ControlSignal,
    CoverageSeverity,
    CoverageStatus,
    EvidenceRequirementStatus,
)
from app.services.coverage_domain import (
    derive_control_status,
    most_severe,
    normalize_coverage_status,
    summarize_framework_coverage,
)
from app.services.coverage_status_repository import control_coverage_to_db_params


def test_normalize_coverage_status_supports_legacy_values():
    assert normalize_coverage_status("compliant") == CoverageStatus.ACCEPTED
    assert normalize_coverage_status("partial") == CoverageStatus.PARTIALLY_SUPPORTED
    assert normalize_coverage_status("non_compliant") == CoverageStatus.NEEDS_EVIDENCE
    assert normalize_coverage_status("not_assessed") == CoverageStatus.NOT_STARTED
    assert normalize_coverage_status("not_applicable") == CoverageStatus.NOT_APPLICABLE
    assert normalize_coverage_status("unexpected") == CoverageStatus.NOT_STARTED


def test_derive_control_status_from_requirements_signals_and_gaps():
    assert derive_control_status([], signal_count=0, gap_count=0) == CoverageStatus.NOT_STARTED
    assert derive_control_status([], signal_count=2, gap_count=0) == CoverageStatus.READY_FOR_REVIEW
    assert derive_control_status([], signal_count=0, gap_count=1) == CoverageStatus.NEEDS_EVIDENCE
    assert derive_control_status([], signal_count=1, gap_count=1) == CoverageStatus.PARTIALLY_SUPPORTED

    accepted_requirement = EvidenceRequirementStatus(
        requirement_key="access-review",
        title="Access review evidence",
        status=CoverageStatus.ACCEPTED,
        evidence_item_ids=["ev-1"],
    )
    not_applicable_requirement = EvidenceRequirementStatus(
        requirement_key="legacy-system-export",
        title="Legacy system export",
        status=CoverageStatus.NOT_APPLICABLE,
    )
    review_requirement = EvidenceRequirementStatus(
        requirement_key="policy-review",
        title="Policy review",
        status=CoverageStatus.READY_FOR_REVIEW,
    )
    missing_requirement = EvidenceRequirementStatus(
        requirement_key="mfa-export",
        title="MFA export",
        status=CoverageStatus.NEEDS_EVIDENCE,
        missing_reason="Connector has not collected MFA state.",
    )

    assert derive_control_status([accepted_requirement]) == CoverageStatus.ACCEPTED
    assert derive_control_status([accepted_requirement, not_applicable_requirement]) == CoverageStatus.ACCEPTED
    assert derive_control_status([review_requirement]) == CoverageStatus.READY_FOR_REVIEW
    assert derive_control_status([accepted_requirement, review_requirement]) == CoverageStatus.PARTIALLY_SUPPORTED
    assert derive_control_status([accepted_requirement, missing_requirement]) == CoverageStatus.NEEDS_EVIDENCE
    assert (
        derive_control_status([accepted_requirement], explicit_status=CoverageStatus.EXCEPTION)
        == CoverageStatus.EXCEPTION
    )


def test_most_severe_returns_highest_ranked_severity():
    assert most_severe([CoverageSeverity.LOW, CoverageSeverity.HIGH, None]) == CoverageSeverity.HIGH
    assert most_severe([None]) is None


def test_summarize_framework_coverage_counts_status_and_confidence():
    controls = [
        ControlCoverage(
            tenant_id="tenant-1",
            framework_id="soc2",
            control_id="CC6.1",
            title="Access controls",
            status=CoverageStatus.ACCEPTED,
            confidence=0.9,
        ),
        ControlCoverage(
            tenant_id="tenant-1",
            framework_id="soc2",
            control_id="CC7.1",
            title="Operations",
            status=CoverageStatus.NEEDS_EVIDENCE,
            confidence=0.4,
        ),
    ]

    payload = summarize_framework_coverage("tenant-1", "soc2", controls)

    assert payload.status == CoverageStatus.NEEDS_EVIDENCE
    assert payload.status_counts == {"accepted": 1, "needs_evidence": 1}
    assert payload.average_confidence == 0.65


def test_summarize_framework_coverage_treats_not_applicable_as_accepted_rollup():
    controls = [
        ControlCoverage(
            tenant_id="tenant-1",
            framework_id="soc2",
            control_id="CC6.1",
            title="Access controls",
            status=CoverageStatus.ACCEPTED,
            confidence=1,
        ),
        ControlCoverage(
            tenant_id="tenant-1",
            framework_id="soc2",
            control_id="CC9.9",
            title="Unused control",
            status=CoverageStatus.NOT_APPLICABLE,
            confidence=0.5,
        ),
    ]

    payload = summarize_framework_coverage("tenant-1", "soc2", controls)

    assert payload.status == CoverageStatus.ACCEPTED
    assert payload.status_counts == {"accepted": 1, "not_applicable": 1}
    assert payload.average_confidence == 0.75


def test_control_coverage_to_db_params_serializes_arrays_for_jsonb_columns():
    coverage = ControlCoverage(
        tenant_id="00000000-0000-0000-0000-000000000111",
        framework_id="soc2",
        control_id="CC6.1",
        title="Access controls",
        status=CoverageStatus.PARTIALLY_SUPPORTED,
        severity=CoverageSeverity.HIGH,
        confidence=0.87654,
        signals=[
            ControlSignal(
                id="sig-1",
                source="iam",
                source_type="finding",
                title="Privileged account missing MFA",
                severity=CoverageSeverity.HIGH,
                confidence=0.8,
            )
        ],
        gaps=[
            ControlGap(
                id="gap-1",
                control_id="CC6.1",
                title="MFA evidence missing",
                severity=CoverageSeverity.HIGH,
            )
        ],
        evidence_requirements=[
            EvidenceRequirementStatus(
                requirement_key="mfa-export",
                title="MFA export",
                status=CoverageStatus.NEEDS_EVIDENCE,
            )
        ],
    )

    params = control_coverage_to_db_params(
        coverage,
        control_db_id="00000000-0000-0000-0000-000000000222",
        realm_name="demo",
    )

    assert params["coverage_status"] == "partially_supported"
    assert params["coverage_severity"] == "high"
    assert params["coverage_confidence"] == 0.8765
    assert json.loads(params["coverage_signals"])[0]["id"] == "sig-1"
    assert json.loads(params["coverage_gaps"])[0]["id"] == "gap-1"
    assert json.loads(params["evidence_requirement_statuses"])[0]["status"] == "needs_evidence"
