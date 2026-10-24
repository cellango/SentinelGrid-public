"""Focused tests for Playbook IR compilation and planner loading."""

from __future__ import annotations

import os
import sys
from copy import deepcopy

import pytest
import yaml


LIBS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "libs"))
if LIBS_PATH not in sys.path:
    sys.path.insert(0, LIBS_PATH)

from sg_agent_runtime.playbook_ir_loader import (  # noqa: E402
    load_compiled_playbook_irs,
    load_planner_playbooks,
    load_crosswalk_entries,
    load_executor_aliases,
    playbook_ir_to_planner_dict,
)
from sg_agent_runtime.playbook_catalog import load_playbook_catalog  # noqa: E402
from sg_agent_runtime.playbook_ir_compiler import compile_playbook_irs  # noqa: E402
from sg_agent_runtime.playbook_ir_models import PlaybookIR  # noqa: E402
from sg_agent_runtime.soc_response_planner import SOCResponsePlanner  # noqa: E402


@pytest.fixture
def synthetic_sources():
    """Synthetic compiler input, never a substitute for absent published content."""
    return [
        {"id": entry.ootb_source_id, "version": "synthetic-test-v1", "phases": [
            {"name": "Detection", "steps": [
                {"id": "confirm", "type": "manual", "label": "Confirm login anomaly"},
                {"id": "contain", "type": "automated", "label": "Terminate active sessions",
                 "action_ref": "iam:terminate_sessions" if entry.canonical_playbook_key.startswith(("ACCOUNT", "PASSWORD")) else "workflow:phishing_bulk_delete"},
            ]}
        ]}
        for entry in load_crosswalk_entries()
    ]


def compile_sources(sources):
    return compile_playbook_irs(
        catalog_playbooks=load_playbook_catalog(), ootb_playbooks=sources,
        crosswalk_entries=load_crosswalk_entries(), executor_aliases=load_executor_aliases(),
    )


@pytest.fixture
def synthetic_playbooks(tmp_path, synthetic_sources):
    source = tmp_path / "synthetic-playbooks.yaml"
    source.write_text(yaml.safe_dump({"playbooks": synthetic_sources}))
    return load_compiled_playbook_irs(ootb_path=str(source))


def test_synthetic_compilation_preserves_account_and_phishing_aliases(synthetic_playbooks) -> None:
    playbooks = {playbook.playbook_key: playbook for playbook in synthetic_playbooks}

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


def test_soc_response_planner_uses_compiled_playbook_actions_when_available(synthetic_playbooks) -> None:
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
        [playbook_ir_to_planner_dict(item) for item in synthetic_playbooks],
    )

    labels = [action.label for action in plan.recommended_actions]
    assert plan.response_pack_id == "account_takeover"
    assert plan.recommended_playbooks[0].playbook_key == "ACCOUNT-COMPROMISE"
    assert "Confirm login anomaly" in labels
    assert "Terminate active sessions" in labels
    assert any(action.requires_approval for action in plan.recommended_actions)


def test_missing_source_is_manual_review_without_invented_actions(tmp_path):
    compiled = load_compiled_playbook_irs(ootb_path=str(tmp_path / "absent.yaml"))
    assert compiled
    for item in compiled:
        assert item.status == "manual_review"
        assert item.actions == []
        assert item.automation_mode == "supervised_recommendation_only"
        assert "missing_ootb_playbook" in {issue.code for issue in item.validation_issues}
        assert SOCResponsePlanner()._playbook_automation_mode(playbook_ir_to_planner_dict(item)) == "manual_review"


@pytest.mark.parametrize("step_type", ["parallel", "loop", "Automated", "", None, 17])
def test_unsupported_nodes_cannot_be_ready(synthetic_sources, step_type):
    synthetic_sources[0]["phases"][0]["steps"][0]["type"] = step_type
    item = compile_sources(synthetic_sources)[0]
    assert item.status == "manual_review"
    assert item.automation_mode == "supervised_recommendation_only"
    assert "unsupported_step_type" in {issue.code for issue in item.validation_issues}
    assert SOCResponsePlanner()._playbook_automation_mode(playbook_ir_to_planner_dict(item)) == "manual_review"


@pytest.mark.parametrize("other_type", ["manual", "automated", "decision"])
def test_duplicate_ids_across_phases_and_node_kinds_require_review(synthetic_sources, other_type):
    synthetic_sources[0]["phases"].append({"name": "Later", "steps": [
        {"id": "confirm", "type": other_type, "action_ref": "iam:terminate_sessions"}
    ]})
    item = compile_sources(synthetic_sources)[0]
    assert item.status == "manual_review"
    assert "duplicate_step_id" in {issue.code for issue in item.validation_issues}


def test_generated_id_collision_requires_review(synthetic_sources):
    steps = synthetic_sources[0]["phases"][0]["steps"]
    del steps[0]["id"]
    steps[1]["id"] = "action_1"
    assert "duplicate_step_id" in {issue.code for issue in compile_sources(synthetic_sources)[0].validation_issues}


@pytest.mark.parametrize("identifier", ["", " ", None, 12])
def test_invalid_explicit_ids_require_review(synthetic_sources, identifier):
    synthetic_sources[0]["phases"][0]["steps"][0]["id"] = identifier
    item = compile_sources(synthetic_sources)[0]
    assert item.status == "manual_review"
    assert "invalid_step_id" in {issue.code for issue in item.validation_issues}


def test_unknown_executor_remains_blocked(synthetic_sources):
    synthetic_sources[0]["phases"][0]["steps"][1]["action_ref"] = "unregistered:operation"
    item = compile_sources(synthetic_sources)[0]
    assert item.status == "manual_review"
    assert "missing_executor_alias" in {issue.code for issue in item.validation_issues}


def test_legacy_defaults_decisions_and_compilation_are_stable(synthetic_sources):
    steps = synthetic_sources[0]["phases"][0]["steps"]
    del steps[0]["id"]
    del steps[0]["type"]
    steps.insert(1, {"id": "review", "type": "decision"})
    original = deepcopy(synthetic_sources)
    first = compile_sources(synthetic_sources)[0]
    assert first.status == "ready"
    assert first.actions[0].action_id == "action_1"
    assert first.decision_points[0].branches[0].next_action_ids == ["contain"]
    assert first.model_dump() == compile_sources(synthetic_sources)[0].model_dump()
    assert synthetic_sources == original


def test_empty_definition_cannot_be_ready(synthetic_sources):
    synthetic_sources[0]["phases"] = []
    assert compile_sources(synthetic_sources)[0].status == "manual_review"
