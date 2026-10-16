"""SOC-specific case and recommendation contracts for the agent runtime."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid4())


SOCOwnerRole = Literal[
    "L1",
    "L2",
    "L3",
    "SOC_MANAGER",
    "SOC_AI_AGENT",
    "HUMAN_OWNER",
]
SOCRiskLevel = Literal["informational", "investigative", "low", "medium", "high", "critical"]
SOCActionStatus = Literal["recommended", "accepted", "rejected", "executed", "skipped"]
SOCFeedbackType = Literal[
    "accepted_recommendation",
    "rejected_recommendation",
    "edited_note",
    "playbook_override",
    "response_pack_override",
    "incorrect_recommendation",
]
SOCDocumentationTemplateKind = Literal[
    "triage_note",
    "investigation_update",
    "containment_recommendation",
    "post_action_update",
    "closure_ready",
]
SOCTriggerType = Literal[
    "incident_created",
    "analyst_action_recorded",
    "playbook_execution_completed",
    "ticket_updated",
    "incident_status_changed",
    "new_evidence_observed",
]


class SOCRecordRef(BaseModel):
    """Reference to a platform object that informs the case."""

    id: str
    source: str
    label: str | None = None
    record_type: str | None = None
    url: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class SOCPlaybookRecommendation(BaseModel):
    """Ranked playbook option for a case."""

    playbook_id: str | None = None
    playbook_key: str | None = None
    playbook_name: str
    rank: int = 1
    confidence: float = 0.0
    rationale: list[str] = Field(default_factory=list)
    mapped_response_pack_id: str | None = None
    automation_mode: Literal["manual_review", "approval_required", "automated"] = "manual_review"
    status: SOCActionStatus = "recommended"

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value


class SOCActionRecommendation(BaseModel):
    """Recommended analyst action derived from case reasoning."""

    action_id: str = Field(default_factory=_new_id)
    action_type: str
    label: str
    description: str
    risk_level: SOCRiskLevel = "low"
    requires_approval: bool = False
    recommended_owner_role: SOCOwnerRole = "L1"
    evidence_basis: list[str] = Field(default_factory=list)
    expected_outcome: str | None = None
    rollback_expectation: str | None = None
    status: SOCActionStatus = "recommended"
    supporting_playbook_id: str | None = None
    supporting_playbook_key: str | None = None


class SOCDocumentationBundle(BaseModel):
    """Reusable documentation drafts emitted by the Ticket Scribe layer."""

    template_kind: SOCDocumentationTemplateKind
    incident_note_draft: str
    ticket_update_draft: str
    timeline_event_draft: str
    analyst_handoff_draft: str | None = None
    closure_checklist: list[str] = Field(default_factory=list)


class SOCRecommendationOutput(BaseModel):
    """Canonical output contract for each SOC agent recommendation cycle."""

    recommendation_id: str = Field(default_factory=_new_id)
    generated_at: datetime = Field(default_factory=_utcnow)
    case_summary: str
    response_pack_id: str
    response_pack_label: str
    recommended_playbooks: list[SOCPlaybookRecommendation] = Field(default_factory=list)
    recommended_actions: list[SOCActionRecommendation] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    proposed_phase: str | None = None
    proposed_status: str | None = None
    incident_note_draft: str | None = None
    ticket_update_draft: str | None = None
    timeline_event_draft: str | None = None
    analyst_handoff_draft: str | None = None
    closure_checklist: list[str] = Field(default_factory=list)
    documentation_bundle: SOCDocumentationBundle | None = None
    confidence: float = 0.0
    rationale: list[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value


class SOCRecommendationHistoryEntry(BaseModel):
    """Historical record of a recommendation cycle."""

    recommendation_id: str
    trigger_type: SOCTriggerType
    generated_at: datetime = Field(default_factory=_utcnow)
    response_pack_id: str
    top_playbook_keys: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    rationale: list[str] = Field(default_factory=list)


class SOCFeedbackRecord(BaseModel):
    """Structured analyst feedback for tuning and evaluation."""

    feedback_id: str = Field(default_factory=_new_id)
    recommendation_id: str
    incident_id: str
    tenant_id: str
    feedback_type: SOCFeedbackType
    actor_id: str
    actor_role: SOCOwnerRole
    accepted: bool
    action_id: str | None = None
    playbook_id: str | None = None
    playbook_key: str | None = None
    playbook_name: str | None = None
    notes: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class SOCIncidentTriggerEvent(BaseModel):
    """Case-agent trigger event emitted by incident lifecycle changes."""

    event_id: str = Field(default_factory=_new_id)
    trigger_type: SOCTriggerType
    incident_id: str
    tenant_id: str
    source_kind: str
    source_event_id: str | None = None
    changed_fields: list[str] = Field(default_factory=list)
    initiated_at: datetime = Field(default_factory=_utcnow)
    reason: str | None = None


class SOCCaseContext(BaseModel):
    """Canonical incident-scoped context used by the SOC AI system."""

    incident_id: str
    tenant_id: str
    case_id: str | None = None
    incident_title: str
    incident_type: str
    severity: str
    status: str
    phase: str
    current_owner: str | None = None
    related_alerts: list[SOCRecordRef] = Field(default_factory=list)
    related_detections: list[SOCRecordRef] = Field(default_factory=list)
    related_observables: list[SOCRecordRef] = Field(default_factory=list)
    entities: list[SOCRecordRef] = Field(default_factory=list)
    mitre_tactics: list[str] = Field(default_factory=list)
    mitre_techniques: list[str] = Field(default_factory=list)
    nist_controls: list[str] = Field(default_factory=list)
    ticket_refs: list[SOCRecordRef] = Field(default_factory=list)
    recommended_response_pack: str | None = None
    recommended_playbooks: list[SOCPlaybookRecommendation] = Field(default_factory=list)
    executed_playbooks: list[SOCRecordRef] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    recommendation_history: list[SOCRecommendationHistoryEntry] = Field(default_factory=list)
    feedback_history: list[SOCFeedbackRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    @model_validator(mode="after")
    def default_case_id(self) -> "SOCCaseContext":
        if not self.case_id:
            self.case_id = self.incident_id
        return self


class SOCCaseMemory(BaseModel):
    """Durable, incident-scoped working memory for the SOC case agent."""

    memory_id: str = Field(default_factory=_new_id)
    tenant_id: str
    incident_id: str
    case_id: str | None = None
    summary: str | None = None
    current_phase: str | None = None
    current_status: str | None = None
    open_questions: list[str] = Field(default_factory=list)
    evidence_snapshot: list[str] = Field(default_factory=list)
    pending_approvals: list[str] = Field(default_factory=list)
    recommendation_history: list[SOCRecommendationHistoryEntry] = Field(default_factory=list)
    recommendation_versions: list[SOCRecommendationOutput] = Field(default_factory=list)
    feedback_history: list[SOCFeedbackRecord] = Field(default_factory=list)
    last_recommendation: SOCRecommendationOutput | None = None
    last_refreshed_at: datetime = Field(default_factory=_utcnow)

    @model_validator(mode="after")
    def default_case_id(self) -> "SOCCaseMemory":
        if not self.case_id:
            self.case_id = self.incident_id
        return self
