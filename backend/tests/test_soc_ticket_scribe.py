"""Focused tests for deterministic SOC ticket-scribe templates."""

from __future__ import annotations

import os
import sys


LIBS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "libs"))
if LIBS_PATH not in sys.path:
    sys.path.insert(0, LIBS_PATH)

from sg_agent_runtime.soc_models import SOCActionRecommendation, SOCPlaybookRecommendation  # noqa: E402
from sg_agent_runtime.ticket_scribe import SOCTicketScribe  # noqa: E402


def test_ticket_scribe_builds_triage_bundle_with_handoff_and_timeline() -> None:
    bundle = SOCTicketScribe().build_documentation_bundle(
        incident_data={
            "title": "Suspicious login from new geography",
            "severity": "high",
            "phase": "detection_and_analysis",
            "status": "new",
            "assigned_to": "L1 Analyst",
            "raw_payload": {"trigger_type": "incident_created"},
        },
        response_pack_label="Account takeover containment",
        response_pack_summary="Contain the active session and validate the compromised identity.",
        recommended_playbooks=[
            SOCPlaybookRecommendation(
                playbook_id="pb-1",
                playbook_key="ACCOUNT-COMPROMISE",
                playbook_name="Account compromise investigation",
                confidence=0.9,
            )
        ],
        recommended_actions=[
            SOCActionRecommendation(
                action_type="investigate",
                label="Review identity sign-in history",
                description="Check the recent identity activity for suspicious sign-ins.",
                risk_level="investigative",
                recommended_owner_role="L1",
            )
        ],
        missing_evidence=["No downstream ticket reference is linked yet."],
        rationale=["Impossible travel and MFA challenge failures were observed."],
        confidence=0.86,
    )

    assert bundle.template_kind == "triage_note"
    assert "AI triage summary" in bundle.incident_note_draft
    assert "SOC AI triage completed" in bundle.timeline_event_draft
    assert "Suggested L1 handoff" in (bundle.analyst_handoff_draft or "")
    assert bundle.closure_checklist


def test_ticket_scribe_uses_post_action_template_for_playbook_completion() -> None:
    bundle = SOCTicketScribe().build_documentation_bundle(
        incident_data={
            "title": "Mailbox compromise suspected",
            "severity": "high",
            "phase": "containment",
            "status": "investigating",
            "assigned_to": "L2 Analyst",
            "raw_payload": {"trigger_type": "playbook_execution_completed"},
        },
        response_pack_label="Mailbox compromise response",
        response_pack_summary="Lock down mailbox rules and validate user impact.",
        recommended_playbooks=[],
        recommended_actions=[
            SOCActionRecommendation(
                action_type="containment_review",
                label="Review mailbox rule containment outcome",
                description="Confirm whether the suspicious inbox rules were removed.",
                risk_level="high",
                requires_approval=True,
                recommended_owner_role="L2",
            )
        ],
        missing_evidence=[],
        rationale=["The playbook completed and analyst review is needed."],
        confidence=0.79,
    )

    assert bundle.template_kind == "post_action_update"
    assert "AI post-action update" in bundle.incident_note_draft
    assert "post-action review completed" in bundle.timeline_event_draft
    assert any("approval record" in item.lower() for item in bundle.closure_checklist)
