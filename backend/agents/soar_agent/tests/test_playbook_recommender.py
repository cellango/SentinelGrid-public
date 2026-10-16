"""Focused tests for response-pack-first playbook planning."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
LIBS = ROOT.parent.parent / "libs"
for candidate in (ROOT, LIBS):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from app.services.playbook_recommender import PlaybookRecommender


def _sample_playbooks() -> list[dict]:
    return [
        {
            "id": "pb-1",
            "playbook_key": "ACCOUNT-COMPROMISE",
            "key": "account-compromise",
            "name": "Account Compromise / Suspicious Login",
            "category": "identity",
            "tags": ["identity", "suspicious_login"],
            "mitre_tactics": ["TA0003"],
            "mitre_techniques": ["T1078"],
            "nist_controls": ["AC-2", "IR-4"],
        },
        {
            "id": "pb-2",
            "playbook_key": "PASSWORD-SPRAY",
            "key": "password-spray",
            "name": "Password Spray Response",
            "category": "identity",
            "tags": ["password spray"],
            "mitre_tactics": ["TA0006"],
            "mitre_techniques": ["T1110.003"],
            "nist_controls": ["AC-7", "IR-4"],
        },
        {
            "id": "pb-3",
            "playbook_key": "PHISH-USER",
            "key": "phish-user",
            "name": "Phishing – User Reported",
            "category": "phishing",
            "tags": ["email", "phishing"],
            "mitre_tactics": ["TA0001"],
            "mitre_techniques": ["T1566"],
            "nist_controls": ["IR-4", "IR-5"],
        },
        {
            "id": "pb-4",
            "playbook_key": "CLOUD-PUBLIC-STORAGE",
            "key": "cloud-public-storage",
            "name": "Cloud Public Storage Remediation",
            "category": "cloud",
            "tags": ["cloud", "public storage"],
            "mitre_tactics": ["TA0009"],
            "mitre_techniques": ["T1530"],
            "nist_controls": ["SC-7", "IR-4"],
        },
        {
            "id": "pb-5",
            "playbook_key": "MALWARE-CONTAIN",
            "key": "malware-contain",
            "name": "Malware Containment",
            "category": "malware",
            "tags": ["endpoint", "malware"],
            "mitre_tactics": ["TA0002"],
            "mitre_techniques": ["T1059"],
            "nist_controls": ["DE.CM", "RS.MI"],
        },
    ]


@pytest.mark.asyncio
async def test_recommend_response_plan_prefers_account_takeover_pack() -> None:
    recommender = PlaybookRecommender()

    plan = await recommender.recommend_response_plan(
        {
            "title": "Suspicious login from new geography",
            "severity": "high",
            "status": "new",
            "phase": "detection_and_analysis",
            "source": "identity_provider",
            "story_domains": ["identity", "security"],
            "raw_payload": {
                "category": "identity",
                "summary": "Impossible travel followed by MFA fatigue attempts.",
                "sg": {"playbook_id": "ACCOUNT-COMPROMISE"},
            },
            "mitre_tactics": ["TA0006"],
            "mitre_techniques": ["T1078"],
            "related_detections": [{"id": "det-1", "title": "Impossible travel"}],
            "entities": [{"label": "alice@example.com"}],
            "evidence": [{"title": "Risky sign-in timeline"}],
        },
        _sample_playbooks(),
        "tenant-1",
    )

    assert plan.response_pack_id == "account_takeover"
    assert plan.recommended_playbooks[0].playbook_key == "ACCOUNT-COMPROMISE"
    assert any(action.requires_approval for action in plan.recommended_actions)
    assert plan.confidence >= 0.7
    assert plan.documentation_bundle is not None
    assert plan.documentation_bundle.template_kind == "triage_note"
    assert "SOC AI triage completed" in (plan.timeline_event_draft or "")


@pytest.mark.asyncio
async def test_recommend_response_plan_prefers_phishing_pack_and_drafts_notes() -> None:
    recommender = PlaybookRecommender()

    plan = await recommender.recommend_response_plan(
        {
            "title": "Mailbox compromise suspected",
            "description": "User reported a suspicious email and forwarding rule creation.",
            "severity": "high",
            "status": "investigating",
            "source": "email_gateway",
            "story_domains": ["identity", "application", "security"],
            "raw_payload": {
                "category": "phishing",
                "summary": "Malicious inbox rule and OAuth consent were observed.",
                "sg": {"playbook_id": "PHISH-USER"},
            },
            "related_detections": [{"id": "det-2", "title": "Inbox rule created"}],
            "entities": [{"label": "bob@example.com"}],
            "evidence": [{"title": "Suspicious message trace"}],
        },
        _sample_playbooks(),
        "tenant-1",
    )

    assert plan.response_pack_id == "phishing_mailbox_compromise"
    assert plan.recommended_playbooks[0].playbook_key == "PHISH-USER"
    assert "Mailbox compromise response" in (plan.incident_note_draft or "")
    assert "SOC AI recommendation" in (plan.ticket_update_draft or "")
    assert plan.documentation_bundle is not None
    assert "Suggested L1 handoff" in (plan.analyst_handoff_draft or "")
    assert plan.closure_checklist


@pytest.mark.asyncio
async def test_recommend_response_plan_reports_missing_evidence_for_cloud_exposure() -> None:
    recommender = PlaybookRecommender()

    plan = await recommender.recommend_response_plan(
        {
            "title": "Public bucket exposure",
            "severity": "medium",
            "status": "new",
            "source": "cloud_scanner",
            "story_domains": ["cloud", "security"],
            "raw_payload": {
                "category": "cloud",
                "summary": "Storage bucket appears public and internet exposed.",
                "sg": {"playbook_id": "CLOUD-PUBLIC-STORAGE"},
            },
        },
        _sample_playbooks(),
        "tenant-1",
    )

    assert plan.response_pack_id == "cloud_exposure"
    assert plan.recommended_playbooks[0].playbook_key == "CLOUD-PUBLIC-STORAGE"
    assert "No related detections are linked to the incident yet." in plan.missing_evidence
    assert "No impacted identities or assets are attached yet." in plan.missing_evidence
    assert plan.documentation_bundle is not None
    assert "Resolve or explicitly waive" in " ".join(plan.closure_checklist)


@pytest.mark.asyncio
async def test_legacy_recommend_playbooks_preserves_response_pack_metadata() -> None:
    recommender = PlaybookRecommender()

    recommendations = await recommender.recommend_playbooks(
        {
            "title": "Suspicious login from new geography",
            "severity": "high",
            "source": "identity_provider",
            "story_domains": ["identity", "security"],
            "raw_payload": {
                "category": "identity",
                "sg": {"playbook_id": "ACCOUNT-COMPROMISE"},
            },
        },
        _sample_playbooks(),
        "tenant-1",
    )

    assert recommendations[0]["response_pack_id"] == "account_takeover"
    assert recommendations[0]["response_pack_label"] == "Account takeover containment"
