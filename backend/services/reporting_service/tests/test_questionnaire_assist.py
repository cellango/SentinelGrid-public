import os
import sys

import pytest

SERVICE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIBS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs"))

for path in (SERVICE_ROOT, LIBS_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.services.questionnaire_assist import QuestionnaireAssistService


def sample_dashboard():
    return {
        "overall_stats": {
            "overall_score": 84,
            "mapped_detections": 12,
            "control_checks": 8,
            "evidence_items": 17,
        },
        "reporting_summary": {
            "criteria_ready": 6,
            "criteria_needing_attention": 2,
        },
        "priority_criteria": [
            {
                "id": "CC6.1",
                "title": "Logical and Physical Access Controls",
                "status": "partial",
                "open_findings": 2,
                "evidence_items": 4,
                "mapped_nist_controls": ["IA-2", "AC-2"],
            },
            {
                "id": "CC7.2",
                "title": "System Monitoring",
                "status": "compliant",
                "open_findings": 0,
                "evidence_items": 3,
                "mapped_nist_controls": ["SI-4", "AU-6"],
            },
            {
                "id": "CC8.1",
                "title": "Change Management and Cloud Configuration",
                "status": "partial",
                "open_findings": 1,
                "evidence_items": 2,
                "mapped_nist_controls": ["CM-2", "SC-7"],
            },
        ],
        "key_detections": [
            {
                "id": "det-1",
                "title": "Impossible travel on privileged user",
                "source_label": "Identity detection",
                "status": "open",
            },
            {
                "id": "det-2",
                "title": "Suspicious cloud storage exposure",
                "source_label": "Cloud posture",
                "status": "open",
            },
            {
                "id": "det-3",
                "title": "Incident response playbook execution",
                "source_label": "Response automation",
                "status": "resolved",
            },
        ],
        "control_checks": [
            {
                "id": "check-1",
                "title": "MFA coverage check",
                "source_label": "Identity control check",
                "status": "partial",
            },
            {
                "id": "check-2",
                "title": "Cloud configuration baseline",
                "source_label": "Cloud control check",
                "status": "partial",
            },
        ],
    }


@pytest.mark.asyncio
async def test_questionnaire_assist_builds_identity_answer(monkeypatch):
    service = QuestionnaireAssistService()

    async def fake_dashboard(_tenant_id: str):
        return sample_dashboard()

    monkeypatch.setattr(service, "_fetch_compliance_dashboard", fake_dashboard)

    result = await service.build_questionnaire_assist(
        "tenant-1",
        ["How do we evidence MFA and access control coverage?"],
    )

    assert result["summary"]["question_count"] == 1
    answer = result["answers"][0]
    assert answer["category"] == "identity_access"
    assert answer["confidence"] == "high"
    assert "smb_customer_security_review_pack" in [
        artifact["template_key"] for artifact in answer["recommended_artifacts"]
    ]
    assert any(control["id"] == "CC6.1" for control in answer["supporting_controls"])


@pytest.mark.asyncio
async def test_questionnaire_assist_builds_general_questionnaire_answer(monkeypatch):
    service = QuestionnaireAssistService()

    async def fake_dashboard(_tenant_id: str):
        return sample_dashboard()

    monkeypatch.setattr(service, "_fetch_compliance_dashboard", fake_dashboard)

    result = await service.build_questionnaire_assist(
        "tenant-1",
        ["How do we answer customer security questionnaires quickly?"],
    )

    answer = result["answers"][0]
    assert answer["category"] == "evidence_readiness"
    assert "evidence" in answer["answer"].lower() or "questionnaire" in answer["answer"].lower()
    assert result["summary"]["recommended_artifacts"]


@pytest.mark.asyncio
async def test_questionnaire_assist_requires_questions():
    service = QuestionnaireAssistService()

    with pytest.raises(ValueError):
        await service.build_questionnaire_assist("tenant-1", [])


@pytest.mark.asyncio
async def test_security_review_templates_include_sales_ready_templates(monkeypatch):
    service = QuestionnaireAssistService()

    async def fake_dashboard(_tenant_id: str):
        payload = sample_dashboard()
        payload["framework_starter_packs"] = [
            {"framework_key": "soc2", "launch_state": "live"},
            {"framework_key": "iso27001", "launch_state": "starter"},
        ]
        return payload

    monkeypatch.setattr(service, "_fetch_compliance_dashboard", fake_dashboard)

    result = await service.build_security_review_templates("tenant-1")

    assert result["summary"]["framework_pack_states"]["soc2"] == "live"
    assert len(result["templates"]) == 4
    assert result["templates"][0]["key"] == "initial_security_review_reply"
    assert "SentinelGrid" in result["templates"][0]["body"]
    assert any(
        artifact["template_key"] == "smb_customer_security_review_pack"
        for artifact in result["templates"][0]["recommended_artifacts"]
    )
