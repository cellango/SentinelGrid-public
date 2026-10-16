from pathlib import Path
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

from app.services.reporting_mapper import (
    SYSTEM_TENANT_ID,
    build_compliance_dashboard_payload,
    build_soc2_coverage_payload,
)
from app.schemas.coverage import CoverageStatus
from app.services.control_signal_mapper import build_soc2_framework_coverage
from sg_core.models import Alert, IAMFinding, Playbook, PlaybookExecution, PostureFinding


def test_build_soc2_coverage_payload_maps_detections_checks_and_playbooks():
    tenant_id = str(uuid4())
    tenant_uuid = uuid4()
    now = datetime.now(timezone.utc)

    playbook = Playbook(
        id=uuid4(),
        tenant_id=SYSTEM_TENANT_ID,
        key="ACCOUNT-COMPROMISE",
        playbook_key="ACCOUNT-COMPROMISE",
        name="Account Compromise",
        target_type="alert",
        workflow_ref="playbook:account-compromise",
        is_enabled=True,
        soc2_criteria=["CC6.1"],
        nist_controls=["AC-2", "IA-2"],
    )

    execution = PlaybookExecution(
        id=uuid4(),
        tenant_id=tenant_uuid,
        playbook_id=playbook.id,
        target_type="alert",
        target_id=uuid4(),
        status="completed",
        triggered_by="rule",
        approval_status="approved",
        started_at=now - timedelta(hours=2),
        finished_at=now - timedelta(hours=1),
        created_at=now - timedelta(hours=2),
        updated_at=now - timedelta(hours=1),
    )

    alert = Alert(
        id=uuid4(),
        tenant_id=tenant_uuid,
        source="wazuh",
        external_id="alert-1",
        title="Impossible travel on executive account",
        description="Suspicious login pattern detected",
        raw_severity="high",
        status="open",
        detection_time=now,
        raw_payload={
            "recommended_playbook_key": "ACCOUNT-COMPROMISE",
            "detection_rule_id": "SG-IDENTITY-001",
        },
        nist_controls=["AC-2", "IA-2"],
        created_at=now,
        updated_at=now,
    )

    iam_finding = IAMFinding(
        id=uuid4(),
        tenant_id=tenant_uuid,
        finding_type="missing_mfa",
        severity="high",
        description="Privileged account missing MFA",
        recommendation="Require MFA for all admins",
        status="open",
        detected_at=now - timedelta(days=1),
        nist_control_id="IA-2",
        soc2_criteria=[{"criterion_id": "CC6.1"}],
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(hours=4),
    )

    posture_finding = PostureFinding(
        id=uuid4(),
        tenant_id=tenant_uuid,
        check_id="aws-logging-disabled",
        title="CloudTrail logging disabled",
        description="Logging coverage is incomplete",
        severity="medium",
        status="open",
        detected_at=now - timedelta(days=2),
        nist_control_id="AU-2",
        created_at=now - timedelta(days=2),
        updated_at=now - timedelta(hours=3),
    )

    payload = build_soc2_coverage_payload(
        tenant_id=tenant_id,
        iam_rows=[iam_finding],
        posture_rows=[posture_finding],
        alerts=[alert],
        playbooks=[playbook],
        executions=[execution],
    )
    framework_coverage = build_soc2_framework_coverage(
        tenant_id=tenant_id,
        iam_rows=[iam_finding],
        posture_rows=[posture_finding],
        alerts=[alert],
        playbooks=[playbook],
        executions=[execution],
    )

    assert payload["summary"]["mapped_detections"] == 1
    assert payload["summary"]["control_checks"] == 2
    assert payload["reporting_summary"]["playbook_execution_count"] == 1
    assert payload["coverage_model"]["framework_id"] == "soc2"
    assert payload["coverage_model"]["status"] == "partially_supported"
    assert payload["coverage_model"]["status_counts"]["partially_supported"] == 2

    cc61 = next(item for item in payload["controls"] if item["id"] == "CC6.1")
    assert cc61["detection_count"] == 1
    assert cc61["control_check_count"] == 1
    assert cc61["playbook_count"] == 1
    assert cc61["playbook_execution_count"] == 1
    assert cc61["coverage_status"] == "partially_supported"
    assert cc61["coverage_severity"] == "high"
    assert cc61["coverage_gaps"][0]["control_id"] == "CC6.1"
    assert any("Mapped signals" in item for item in cc61["coverage_trace"])
    assert any("coverage gap" in item for item in cc61["coverage_trace"])
    assert any(item["title"] == "Impossible travel on executive account" for item in cc61["key_detections"])
    assert any(item["name"] == "Account Compromise" for item in cc61["supporting_playbooks"])
    assert "IA-2" in cc61["mapped_nist_controls"]

    cc71 = next(item for item in payload["controls"] if item["id"] == "CC7.1")
    assert cc71["control_check_count"] == 1
    assert "AU-2" in cc71["mapped_nist_controls"]

    cc61_coverage = next(item for item in framework_coverage.controls if item.control_id == "CC6.1")
    assert cc61_coverage.status == CoverageStatus.PARTIALLY_SUPPORTED
    assert {signal.source_type for signal in cc61_coverage.signals} == {
        "alert",
        "iam_finding",
        "playbook",
        "playbook_execution",
    }
    assert cc61_coverage.gaps[0].source_signal_ids[0].startswith("iam_finding:")


def test_build_compliance_dashboard_payload_reuses_reporting_summary():
    coverage = {
        "overall_score": 72.5,
        "summary": {
            "total_criteria": 9,
            "evidence_items": 12,
            "last_assessment": "2026-03-26T10:00:00",
            "mapped_detections": 4,
            "control_checks": 3,
        },
        "reporting_summary": {
            "criteria_ready": 5,
            "criteria_partial": 2,
            "criteria_needing_attention": 2,
            "criteria_not_assessed": 2,
            "key_detection_count": 4,
            "control_check_count": 3,
            "playbook_count": 2,
            "playbook_execution_count": 6,
            "reportable_evidence_items": 12,
            "top_detection_sources": [{"source": "wazuh", "count": 4}],
        },
        "controls": [
            {"id": "CC6.1", "open_findings": 2, "evidence_items": 4},
            {"id": "CC7.1", "open_findings": 1, "evidence_items": 3},
        ],
        "key_detections": [{"id": "a1", "title": "Alert one"}],
        "control_checks": [{"id": "c1", "title": "Check one"}],
    }

    payload = build_compliance_dashboard_payload(coverage)

    assert payload["overall_stats"]["overall_score"] == 72.5
    assert payload["overall_stats"]["controls_implemented"] == 5
    assert payload["overall_stats"]["mapped_detections"] == 4
    assert payload["reporting_summary"]["criteria_needing_attention"] == 2
    assert payload["priority_criteria"][0]["id"] == "CC6.1"

    starter_packs = payload["framework_starter_packs"]
    assert len(starter_packs) == 2

    soc2_pack = next(pack for pack in starter_packs if pack["framework_key"] == "soc2")
    assert soc2_pack["launch_state"] == "live"
    assert "smb_audit_readiness_pack" in soc2_pack["artifact_template_keys"]

    iso_pack = next(pack for pack in starter_packs if pack["framework_key"] == "iso27001")
    assert iso_pack["launch_state"] == "starter"
    assert "not a full Annex A control tracker yet" in iso_pack["note"]
