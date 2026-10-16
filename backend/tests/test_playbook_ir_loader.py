"""Focused tests for Playbook IR compilation and planner loading."""

from __future__ import annotations

import os
import sys


LIBS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "libs"))
if LIBS_PATH not in sys.path:
    sys.path.insert(0, LIBS_PATH)

from sg_agent_runtime.playbook_ir_loader import (  # noqa: E402
    load_compiled_playbook_irs,
    load_planner_playbooks,
)
from sg_agent_runtime.playbook_ir_models import PlaybookIR  # noqa: E402
from sg_agent_runtime.soc_response_planner import SOCResponsePlanner  # noqa: E402


def test_load_compiled_playbook_irs_builds_ready_aliases_for_account_takeover_and_phishing() -> None:
    playbooks = {playbook.playbook_key: playbook for playbook in load_compiled_playbook_irs()}

    assert {"ACCOUNT-COMPROMISE", "PASSWORD-SPRAY", "PHISH-USER", "PHISH-GATEWAY"} <= set(playbooks)

    account_compromise = playbooks["ACCOUNT-COMPROMISE"]
    assert account_compromise.status == "ready"
    assert account_compromise.response_pack_ids == ["account_takeover"]
    assert any(binding.target_ref == "iam:terminate_sessions" for binding in account_compromise.execution_bindings)
    assert any(action.requires_approval for action in account_compromise.actions)

    phish_user = playbooks["PHISH-USER"]
    assert phish_user.status == "ready"
    assert phish_user.response_pack_ids == ["phishing_mailbox_compromise"]
    assert any(binding.target_ref == "workflow:phishing_bulk_delete" for binding in phish_user.execution_bindings)


def test_load_planner_playbooks_merges_compiled_ir_with_raw_catalog_fallback() -> None:
    playbooks = load_planner_playbooks()
    by_key = {str(playbook.get("playbook_key") or playbook.get("id")): playbook for playbook in playbooks}

    assert "ACCOUNT-COMPROMISE" in by_key
    assert isinstance(by_key["ACCOUNT-COMPROMISE"].get("compiled_ir"), PlaybookIR)

    # Unmapped catalog entries should remain available so planner behavior does not regress.
    assert "MFA-BYPASS" in by_key
    assert by_key["MFA-BYPASS"].get("compiled_ir") is None


def test_soc_response_planner_uses_compiled_playbook_actions_when_available() -> None:
    planner = SOCResponsePlanner()
    plan = planner.recommend_response_plan(
        {
            "title": "Impossible travel and suspicious MFA sequence",
            "severity": "high",
            "status": "new",
            "phase": "detection_and_analysis",
            "source": "identity_provider",
            "story_domains": ["identity", "security"],
            "raw_payload": {
                "category": "identity",
                "summary": "Impossible travel followed by suspicious MFA prompts.",
                "sg": {"playbook_id": "ACCOUNT-COMPROMISE"},
            },
            "mitre_tactics": ["TA0006"],
            "mitre_techniques": ["T1078"],
            "related_detections": [{"id": "det-1", "title": "Impossible travel"}],
            "entities": [{"label": "alice@example.com"}],
            "evidence": [{"title": "Risky sign-in timeline"}],
        },
        load_planner_playbooks(),
    )

    labels = [action.label for action in plan.recommended_actions]
    assert plan.response_pack_id == "account_takeover"
    assert plan.recommended_playbooks[0].playbook_key == "ACCOUNT-COMPROMISE"
    assert "Confirm login anomaly" in labels
    assert "Terminate active sessions" in labels
    assert any(action.requires_approval for action in plan.recommended_actions)
