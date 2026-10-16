"""Canonical playbook IR contracts for SOC planning and execution."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


PlaybookIRStatus = Literal["ready", "manual_review", "deprecated", "draft"]
PlaybookMappingStatus = Literal["exact", "aliased", "derived", "manual_review", "unmapped"]
PlaybookExecutionMode = Literal["manual_only", "human_approved_executor", "read_only_tooling"]
PlaybookValidationSeverity = Literal["warning", "error"]


class PlaybookIRSourceRef(BaseModel):
    """Trace back to the source artifact used to compile the IR."""

    source_type: str
    ref: str
    label: str | None = None


class PlaybookIRValidationIssue(BaseModel):
    """Validation issue attached to a compiled playbook."""

    severity: PlaybookValidationSeverity = "warning"
    code: str
    message: str


class PlaybookCrosswalkEntry(BaseModel):
    """Explicit alias mapping between current playbook sources."""

    canonical_playbook_key: str
    catalog_id: str
    catalog_runbook_ref: str | None = None
    db_playbook_id: str | None = None
    db_playbook_key: str | None = None
    ootb_source_id: str | None = None
    normalized_name: str | None = None
    response_pack_ids: list[str] = Field(default_factory=list)
    incident_families: list[str] = Field(default_factory=list)
    match_strategy: str = "explicit_alias"
    match_confidence: float = 1.0
    mapping_status: PlaybookMappingStatus = "aliased"

    @field_validator("match_confidence")
    @classmethod
    def validate_match_confidence(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("match_confidence must be between 0.0 and 1.0")
        return value


class PlaybookEntryCriterion(BaseModel):
    """Normalized condition for considering a playbook."""

    criterion_id: str
    field: str
    operator: str
    value: str
    confidence_weight: float = 0.5
    required: bool = False
    explanation: str | None = None

    @field_validator("confidence_weight")
    @classmethod
    def validate_confidence_weight(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("confidence_weight must be between 0.0 and 1.0")
        return value


class PlaybookEvidenceRequirement(BaseModel):
    """Evidence or environmental requirement associated with a playbook."""

    evidence_id: str
    label: str
    source_type: str
    query_hint: str | None = None
    required_for: Literal["triage", "playbook_selection", "containment_review", "closure"] = "playbook_selection"
    cardinality: str = "one_or_more"
    freshness_requirement: str | None = None
    blocking: bool = True


class PlaybookDecisionBranch(BaseModel):
    """Branch from a decision point."""

    branch_id: str
    when: str
    next_action_ids: list[str] = Field(default_factory=list)
    next_decision_id: str | None = None
    execution_mode: PlaybookExecutionMode = "manual_only"


class PlaybookDecisionPoint(BaseModel):
    """Decision gate inside a playbook."""

    decision_id: str
    question: str
    condition_type: str = "analyst_review"
    inputs_required: list[str] = Field(default_factory=list)
    branches: list[PlaybookDecisionBranch] = Field(default_factory=list)
    default_branch: str | None = None
    analyst_prompt: str | None = None


class PlaybookExecutionBinding(BaseModel):
    """Deterministic execution binding for an action."""

    executor_binding_id: str
    executor_type: str
    target_ref: str
    input_schema_ref: str | None = None
    approval_policy_id: str | None = None
    dry_run_supported: bool = False
    reversible: bool = False
    timeout_seconds: int = 300
    audit_fields: list[str] = Field(default_factory=list)


class PlaybookAction(BaseModel):
    """Normalized action exposed to planners."""

    action_id: str
    sequence: int
    phase_name: str | None = None
    action_type: str
    label: str
    description: str
    intent: str | None = None
    evidence_required: list[str] = Field(default_factory=list)
    risk_level: Literal["informational", "investigative", "low", "medium", "high", "critical"] = "low"
    requires_approval: bool = False
    default_owner_role: Literal["L1", "L2", "L3", "SOC_MANAGER", "SOC_AI_AGENT", "HUMAN_OWNER"] = "L1"
    execution_mode: PlaybookExecutionMode = "manual_only"
    executor_binding_id: str | None = None
    expected_outcome: str | None = None
    rollback_expectation: str | None = None
    success_signal: str | None = None
    documentation_hint: str | None = None


class PlaybookDocumentationPrompt(BaseModel):
    """Structured drafting prompt emitted by a playbook."""

    prompt_id: str
    artifact_type: Literal["incident_note", "ticket_update", "timeline_event", "analyst_handoff", "closure_summary"]
    required_inputs: list[str] = Field(default_factory=list)
    tone: str = "factual"
    format_expectation: str = "paragraph"
    must_include: list[str] = Field(default_factory=list)


class PlaybookFrameworkMappings(BaseModel):
    """Framework mappings retained for ranking and reporting."""

    nist_controls: list[str] = Field(default_factory=list)
    mitre_tactics: list[str] = Field(default_factory=list)
    mitre_techniques: list[str] = Field(default_factory=list)
    cis_controls: list[str] = Field(default_factory=list)


class PlaybookIR(BaseModel):
    """Canonical compiled playbook contract."""

    playbook_id: str
    playbook_key: str
    name: str
    version: str = "1.0.0"
    status: PlaybookIRStatus = "draft"
    mapping_status: PlaybookMappingStatus = "unmapped"
    owner_domain: str | None = None
    incident_families: list[str] = Field(default_factory=list)
    response_pack_ids: list[str] = Field(default_factory=list)
    summary: str | None = None
    operator_goal: str | None = None
    automation_mode: str = "manual"
    entry_criteria: list[PlaybookEntryCriterion] = Field(default_factory=list)
    required_evidence: list[PlaybookEvidenceRequirement] = Field(default_factory=list)
    enrichment_steps: list[str] = Field(default_factory=list)
    decision_points: list[PlaybookDecisionPoint] = Field(default_factory=list)
    actions: list[PlaybookAction] = Field(default_factory=list)
    success_checks: list[str] = Field(default_factory=list)
    closure_criteria: list[str] = Field(default_factory=list)
    documentation_prompts: list[PlaybookDocumentationPrompt] = Field(default_factory=list)
    approval_policy: dict[str, Any] = Field(default_factory=dict)
    execution_bindings: list[PlaybookExecutionBinding] = Field(default_factory=list)
    rollback_strategy: dict[str, Any] = Field(default_factory=dict)
    framework_mappings: PlaybookFrameworkMappings = Field(default_factory=PlaybookFrameworkMappings)
    source_refs: list[PlaybookIRSourceRef] = Field(default_factory=list)
    validation_issues: list[PlaybookIRValidationIssue] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

