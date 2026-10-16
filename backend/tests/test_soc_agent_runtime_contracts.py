"""Focused tests for SOC agent runtime contracts."""

from __future__ import annotations

import os
import sys

import pytest
from pydantic import ValidationError


LIBS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "libs"))
if LIBS_PATH not in sys.path:
    sys.path.insert(0, LIBS_PATH)

from sg_agent_runtime.agents import (  # noqa: E402
    BUILTIN_AGENTS,
    RESPONSE_AGENT,
    SOC_CASE_AGENT,
    SOC_INVESTIGATION_AGENT,
    SOC_RESPONSE_PLANNER_AGENT,
    SOC_TICKET_SCRIBE_AGENT,
    SOC_TRIAGE_AGENT,
)
from sg_agent_runtime.models import AgentTask  # noqa: E402
from sg_agent_runtime.soc_tools import SOC_READ_TOOL_NAMES, register_soc_tools  # noqa: E402
from sg_agent_runtime.soc_models import (  # noqa: E402
    SOCCaseContext,
    SOCCaseMemory,
    SOCDocumentationBundle,
    SOCFeedbackRecord,
    SOCRecommendationHistoryEntry,
    SOCRecommendationOutput,
)
from sg_agent_runtime.tool_registry import ToolRegistry  # noqa: E402


def test_soc_case_context_defaults_case_id_and_tracks_case_history() -> None:
    history = SOCRecommendationHistoryEntry(
        recommendation_id="rec-1",
        trigger_type="incident_created",
        response_pack_id="account_takeover",
        top_playbook_keys=["ACCOUNT-COMPROMISE"],
        action_ids=["act-1"],
        confidence=0.82,
        rationale=["Matched suspicious login behavior"],
    )
    feedback = SOCFeedbackRecord(
        recommendation_id="rec-1",
        incident_id="inc-123",
        tenant_id="tenant-123",
        feedback_type="accepted_recommendation",
        actor_id="analyst-1",
        actor_role="L2",
        accepted=True,
    )

    case = SOCCaseContext(
        incident_id="inc-123",
        tenant_id="tenant-123",
        incident_title="Suspicious login from new geography",
        incident_type="account_takeover",
        severity="high",
        status="new",
        phase="detection_and_analysis",
        recommendation_history=[history],
        feedback_history=[feedback],
    )

    assert case.case_id == "inc-123"
    assert case.recommendation_history[0].response_pack_id == "account_takeover"
    assert case.feedback_history[0].actor_role == "L2"


def test_soc_case_memory_defaults_case_id_and_keeps_last_recommendation() -> None:
    documentation_bundle = SOCDocumentationBundle(
        template_kind="triage_note",
        incident_note_draft="AI triage summary: suspicious sign-in activity requires review.",
        ticket_update_draft="SOC AI recommendation: investigate the suspicious sign-in.",
        timeline_event_draft="SOC AI triage completed: ranked account takeover playbooks.",
        analyst_handoff_draft="Suggested L1 handoff: validate the user and linked ticket.",
        closure_checklist=["Ensure the note draft is posted before closure."],
    )
    recommendation = SOCRecommendationOutput(
        case_summary="Likely credential theft with an active session risk.",
        response_pack_id="account_takeover",
        response_pack_label="Account takeover containment",
        incident_note_draft=documentation_bundle.incident_note_draft,
        ticket_update_draft=documentation_bundle.ticket_update_draft,
        timeline_event_draft=documentation_bundle.timeline_event_draft,
        analyst_handoff_draft=documentation_bundle.analyst_handoff_draft,
        closure_checklist=list(documentation_bundle.closure_checklist),
        documentation_bundle=documentation_bundle,
        confidence=0.76,
        rationale=["Observed suspicious sign-in and MFA challenge sequence"],
    )

    memory = SOCCaseMemory(
        tenant_id="tenant-123",
        incident_id="inc-123",
        current_phase="detection_and_analysis",
        current_status="investigating",
        last_recommendation=recommendation,
    )

    assert memory.case_id == "inc-123"
    assert memory.last_recommendation is not None
    assert memory.last_recommendation.response_pack_id == "account_takeover"
    assert memory.last_recommendation.documentation_bundle is not None
    assert memory.last_recommendation.documentation_bundle.template_kind == "triage_note"


def test_soc_recommendation_output_validates_confidence_range() -> None:
    with pytest.raises(ValidationError):
        SOCRecommendationOutput(
            case_summary="Invalid confidence should be rejected.",
            response_pack_id="phishing_mailbox_compromise",
            response_pack_label="Mailbox compromise response",
            confidence=1.2,
        )


def test_agent_task_accepts_incident_and_case_scope() -> None:
    task = AgentTask(
        tenant_id="tenant-123",
        incident_id="inc-123",
        case_id="case-123",
        agent_id="soc_case_agent",
        task_type="triage_new_incident",
    )

    assert task.incident_id == "inc-123"
    assert task.case_id == "case-123"
    assert task.agent_id == "soc_case_agent"


def test_builtin_agents_include_soc_runtime_roles() -> None:
    assert BUILTIN_AGENTS[SOC_CASE_AGENT.agent_id].name == "SOC AI Agent"
    assert SOC_TRIAGE_AGENT.agent_id in BUILTIN_AGENTS
    assert SOC_INVESTIGATION_AGENT.agent_id in BUILTIN_AGENTS
    assert SOC_RESPONSE_PLANNER_AGENT.agent_id in BUILTIN_AGENTS
    assert SOC_TICKET_SCRIBE_AGENT.agent_id in BUILTIN_AGENTS


def test_soc_tool_registry_exposes_read_only_tools_without_high_risk_actions() -> None:
    registry = ToolRegistry()
    register_soc_tools(registry)

    assert registry.names() == set(SOC_READ_TOOL_NAMES)
    assert "lock_account" not in registry.names()
    assert "run_playbook" not in registry.names()
    assert set(RESPONSE_AGENT.tools) - registry.names() == {"lock_account", "run_playbook"}
