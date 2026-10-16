import csv
import io
import os
import sys

SERVICE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIBS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs"))

for path in (SERVICE_ROOT, LIBS_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.services.csv_generator import CSVGenerator
from app.services.pdf_generator import PDFGenerator


def test_pdf_generator_renders_audit_readiness_overview():
    generator = PDFGenerator()

    html = generator._render_section_content(  # noqa: SLF001
        {
            "widget": "audit_readiness_overview",
            "data": {
                "overall_stats": {
                    "overall_score": 82,
                    "mapped_detections": 7,
                    "control_checks": 5,
                    "evidence_items": 11,
                },
                "reporting_summary": {
                    "criteria_ready": 4,
                    "criteria_partial": 3,
                    "criteria_needing_attention": 2,
                },
            },
        }
    )

    assert "Audit Readiness Score" in html
    assert "Criteria Ready" in html
    assert "Mapped Detections" in html


def test_csv_generator_writes_priority_criteria_table():
    generator = CSVGenerator()
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    generator._write_section_data(  # noqa: SLF001
        writer,
        {
            "widget": "priority_criteria_table",
            "config": {"source_field": "priority_criteria", "limit": 5},
            "data": {
                "priority_criteria": [
                    {
                        "id": "CC6.1",
                        "title": "Logical and Physical Access Controls",
                        "status": "partial",
                        "open_findings": 2,
                        "detection_count": 3,
                        "control_check_count": 1,
                        "evidence_items": 4,
                    }
                ]
            },
        },
    )

    content = buffer.getvalue()
    assert "Criterion,Title,Status,Open Findings,Detections,Control Checks,Evidence Items" in content
    assert "CC6.1,Logical and Physical Access Controls,partial,2,3,1,4" in content


def test_csv_generator_writes_compliance_signal_table():
    generator = CSVGenerator()
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    generator._write_section_data(  # noqa: SLF001
        writer,
        {
            "widget": "compliance_signal_table",
            "config": {"signal_type": "key_detections", "limit": 5},
            "data": {
                "key_detections": [
                    {
                        "title": "Impossible travel on executive account",
                        "description": "Suspicious login pattern detected",
                        "severity": "high",
                        "status": "open",
                        "source_label": "Identity detection",
                        "nist_control_id": "IA-2",
                        "detected_at": "2026-03-26T09:00:00Z",
                    }
                ]
            },
        },
    )

    content = buffer.getvalue()
    assert "Signal,Description,Severity,Status,Source,NIST Control,Detected At" in content
    assert "Impossible travel on executive account,Suspicious login pattern detected,high,open,Identity detection,IA-2,2026-03-26T09:00:00Z" in content


def test_pdf_generator_renders_control_evidence_mapping():
    generator = PDFGenerator()

    html = generator._render_section_content(  # noqa: SLF001
        {
            "widget": "control_evidence_mapping",
            "data": {
                "summary": {
                    "control_count": 1,
                    "mapped_control_count": 1,
                    "evidence_item_count": 1,
                },
                "rows": [
                    {
                        "framework_name": "SOC 2",
                        "control_id": "CC6.1",
                        "control_title": "Logical access",
                        "coverage_status": "accepted",
                        "evidence_title": "MFA configuration export",
                        "review_status": "accepted",
                        "package_name": "SOC 2 Q2 Evidence",
                    }
                ],
            },
        }
    )

    assert "Control Count" in html
    assert "CC6.1" in html
    assert "MFA configuration export" in html


def test_csv_generator_writes_control_evidence_mapping():
    generator = CSVGenerator()
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    generator._write_section_data(  # noqa: SLF001
        writer,
        {
            "widget": "control_evidence_mapping",
            "data": {
                "summary": {"control_count": 1, "mapped_control_count": 1},
                "rows": [
                    {
                        "framework_id": "soc2",
                        "framework_name": "SOC 2",
                        "control_id": "CC6.1",
                        "control_title": "Logical access",
                        "coverage_status": "accepted",
                        "gap_count": 0,
                        "evidence_item_id": "ev-1",
                        "evidence_title": "MFA configuration export",
                        "evidence_type": "configuration",
                        "review_status": "accepted",
                        "valid_until": "2026-07-01T00:00:00Z",
                        "package_id": "pkg-1",
                        "package_name": "SOC 2 Q2 Evidence",
                        "source_system": "iam_agent",
                    }
                ],
            },
        },
    )

    content = buffer.getvalue()
    assert "Framework ID,Framework Name,Control ID,Control Title,Coverage Status" in content
    assert "soc2,SOC 2,CC6.1,Logical access,accepted,0,ev-1,MFA configuration export" in content


def test_pdf_generator_renders_ai_governance_overview():
    generator = PDFGenerator()

    html = generator._render_section_content(  # noqa: SLF001
        {
            "widget": "ai_governance_overview",
            "data": {
                "overview": {
                    "governance_score": 74,
                    "active_apps": 5,
                    "active_users": 28,
                    "requests_in_window": 904,
                    "open_ai_alerts": 3,
                    "active_ai_incidents": 1,
                    "apps_needing_review": 2,
                    "unclassified_apps": 1,
                }
            },
        }
    )

    assert "Governance Score" in html
    assert "Active AI Apps" in html
    assert "Apps Needing Review" in html


def test_csv_generator_writes_ai_governance_app_inventory():
    generator = CSVGenerator()
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    generator._write_section_data(  # noqa: SLF001
        writer,
        {
            "widget": "ai_governance_app_inventory",
            "data": {
                "app_inventory": [
                    {
                        "label": "Internal Copilot",
                        "governance_state": "needs_review",
                        "requests_in_window": 400,
                        "unique_users": 18,
                        "open_alerts": 2,
                        "active_incidents": 1,
                        "highest_severity": "critical",
                        "models": ["gpt-4.1"],
                    }
                ]
            },
        },
    )

    content = buffer.getvalue()
    assert "Application,Governance State,Requests,Users,Open Alerts,Active Incidents,Risk,Models" in content
    assert "Internal Copilot,needs_review,400,18,2,1,critical,gpt-4.1" in content
