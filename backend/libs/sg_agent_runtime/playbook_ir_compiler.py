"""Compile current playbook sources into the canonical Playbook IR."""

from __future__ import annotations

from typing import Any

from .playbook_ir_models import (
    PlaybookAction,
    PlaybookCrosswalkEntry,
    PlaybookDecisionBranch,
    PlaybookDecisionPoint,
    PlaybookDocumentationPrompt,
    PlaybookEntryCriterion,
    PlaybookEvidenceRequirement,
    PlaybookExecutionBinding,
    PlaybookFrameworkMappings,
    PlaybookIR,
    PlaybookIRSourceRef,
    PlaybookIRValidationIssue,
)
from .response_pack_matcher import RESPONSE_PACKS, normalize_token


def compile_playbook_irs(
    *,
    catalog_playbooks: list[dict[str, Any]],
    ootb_playbooks: list[dict[str, Any]],
    crosswalk_entries: list[PlaybookCrosswalkEntry],
    executor_aliases: dict[str, dict[str, Any]],
) -> list[PlaybookIR]:
    """Compile explicit playbook mappings into canonical IR objects."""
    catalog_by_id = {str(playbook.get("id")): playbook for playbook in catalog_playbooks}
    ootb_by_id = {str(playbook.get("id")): playbook for playbook in ootb_playbooks}
    pack_by_id = {pack.id: pack for pack in RESPONSE_PACKS}

    compiled: list[PlaybookIR] = []
    for crosswalk in crosswalk_entries:
        catalog = catalog_by_id.get(crosswalk.catalog_id)
        ootb = ootb_by_id.get(crosswalk.ootb_source_id or "")
        playbook = _compile_single_playbook(
            crosswalk=crosswalk,
            catalog=catalog,
            ootb=ootb,
            executor_aliases=executor_aliases,
            response_packs=pack_by_id,
        )
        compiled.append(playbook)
    return compiled


def _compile_single_playbook(
    *,
    crosswalk: PlaybookCrosswalkEntry,
    catalog: dict[str, Any] | None,
    ootb: dict[str, Any] | None,
    executor_aliases: dict[str, dict[str, Any]],
    response_packs: dict[str, Any],
) -> PlaybookIR:
    issues: list[PlaybookIRValidationIssue] = []

    if catalog is None:
        issues.append(
            PlaybookIRValidationIssue(
                severity="error",
                code="missing_catalog_playbook",
                message=f"Catalog playbook '{crosswalk.catalog_id}' is missing.",
            )
        )
    if ootb is None:
        issues.append(
            PlaybookIRValidationIssue(
                severity="error",
                code="missing_ootb_playbook",
                message=f"OOTB playbook '{crosswalk.ootb_source_id}' is missing.",
            )
        )

    response_pack_ids = crosswalk.response_pack_ids or _infer_response_pack_ids(crosswalk.canonical_playbook_key)
    response_packs_for_playbook = [
        response_packs[pack_id] for pack_id in response_pack_ids if pack_id in response_packs
    ]
    primary_pack = response_packs_for_playbook[0] if response_packs_for_playbook else None

    entry_criteria = _build_entry_criteria(catalog, ootb, primary_pack)
    required_evidence = _build_required_evidence(ootb)
    actions, decision_points, execution_bindings, enrichment_steps, action_issues = _build_actions_and_decisions(
        ootb=ootb,
        executor_aliases=executor_aliases,
    )
    issues.extend(action_issues)

    success_checks = list(primary_pack.success_checks) if primary_pack else []
    closure_criteria = success_checks or _build_closure_criteria(ootb)
    documentation_prompts = _build_documentation_prompts(primary_pack, ootb)

    framework_mappings = PlaybookFrameworkMappings(
        nist_controls=_string_list((catalog or ootb or {}).get("nist_controls")),
        mitre_tactics=_string_list((catalog or ootb or {}).get("mitre_tactics")),
        mitre_techniques=_string_list((catalog or ootb or {}).get("mitre_techniques")),
        cis_controls=_string_list((ootb or {}).get("cis_controls")),
    )

    if not closure_criteria:
        issues.append(
            PlaybookIRValidationIssue(
                severity="warning",
                code="missing_closure_criteria",
                message="No explicit closure criteria were derived for this playbook.",
            )
        )

    status = _compiled_status(
        catalog_status=str((catalog or {}).get("status") or ""),
        issues=issues,
        actions=actions,
    )
    automation_mode = str((catalog or {}).get("automation_default") or "manual")
    if status != "ready":
        automation_mode = "supervised_recommendation_only"

    approval_required_ids = [action.action_id for action in actions if action.requires_approval]
    approval_policy = {
        "default_owner_domain": str((catalog or {}).get("owner") or ""),
        "approval_required_action_ids": approval_required_ids,
    }
    rollback_required_ids = [action.action_id for action in actions if action.rollback_expectation]
    rollback_strategy = {"action_ids": rollback_required_ids}

    source_refs = [
        PlaybookIRSourceRef(source_type="catalog", ref=crosswalk.catalog_id),
    ]
    if crosswalk.ootb_source_id:
        source_refs.append(PlaybookIRSourceRef(source_type="ootb_yaml", ref=crosswalk.ootb_source_id))
    for pack_id in response_pack_ids:
        source_refs.append(PlaybookIRSourceRef(source_type="response_pack", ref=pack_id))

    return PlaybookIR(
        playbook_id=crosswalk.catalog_id,
        playbook_key=crosswalk.canonical_playbook_key,
        name=str((catalog or ootb or {}).get("name") or crosswalk.canonical_playbook_key),
        version=str((ootb or catalog or {}).get("version") or "1.0.0"),
        status=status,
        mapping_status=crosswalk.mapping_status,
        owner_domain=str((catalog or {}).get("owner") or ""),
        incident_families=crosswalk.incident_families or _string_list((catalog or {}).get("incident_type")),
        response_pack_ids=response_pack_ids,
        summary=str((ootb or catalog or {}).get("description") or (catalog or {}).get("name") or ""),
        operator_goal=getattr(primary_pack, "operator_goal", None),
        automation_mode=automation_mode,
        entry_criteria=entry_criteria,
        required_evidence=required_evidence,
        enrichment_steps=enrichment_steps,
        decision_points=decision_points,
        actions=actions,
        success_checks=success_checks,
        closure_criteria=closure_criteria,
        documentation_prompts=documentation_prompts,
        approval_policy=approval_policy,
        execution_bindings=execution_bindings,
        rollback_strategy=rollback_strategy,
        framework_mappings=framework_mappings,
        source_refs=source_refs,
        validation_issues=issues,
        tags=_string_list((ootb or {}).get("tags")),
    )


def _infer_response_pack_ids(playbook_key: str) -> list[str]:
    normalized = normalize_token(playbook_key)
    pack_ids: list[str] = []
    for pack in RESPONSE_PACKS:
        if any(normalize_token(token) == normalized for token in pack.playbook_keys):
            pack_ids.append(pack.id)
    return pack_ids


def _build_entry_criteria(catalog: dict[str, Any] | None, ootb: dict[str, Any] | None, primary_pack: Any) -> list[PlaybookEntryCriterion]:
    criteria: list[PlaybookEntryCriterion] = []
    incident_type = str((catalog or {}).get("incident_type") or "").strip()
    if incident_type:
        criteria.append(
            PlaybookEntryCriterion(
                criterion_id="incident_type",
                field="incident_type",
                operator="equals",
                value=incident_type,
                confidence_weight=1.0,
                required=True,
                explanation="Catalog incident-family mapping",
            )
        )

    for index, trigger in enumerate(_string_list((catalog or {}).get("triggers")), start=1):
        criteria.append(
            PlaybookEntryCriterion(
                criterion_id=f"trigger_{index}",
                field="trigger_text",
                operator="contains",
                value=trigger,
                confidence_weight=0.35,
                explanation="Catalog trigger hint",
            )
        )

    for index, source in enumerate(_string_list((ootb or {}).get("applicable_sources")), start=1):
        criteria.append(
            PlaybookEntryCriterion(
                criterion_id=f"source_{index}",
                field="source_type",
                operator="contains",
                value=source,
                confidence_weight=0.4,
                explanation="OOTB applicable source hint",
            )
        )

    if primary_pack is not None:
        for index, signal in enumerate(getattr(primary_pack, "signal_categories", ()), start=1):
            criteria.append(
                PlaybookEntryCriterion(
                    criterion_id=f"pack_signal_{index}",
                    field="signal_category",
                    operator="contains",
                    value=signal,
                    confidence_weight=0.25,
                    explanation="Response-pack signal hint",
                )
            )

    return criteria


def _build_required_evidence(ootb: dict[str, Any] | None) -> list[PlaybookEvidenceRequirement]:
    requirements: list[PlaybookEvidenceRequirement] = []
    if ootb is None:
        return requirements

    for index, artifact in enumerate(_string_list(ootb.get("artifacts_required")), start=1):
        requirements.append(
            PlaybookEvidenceRequirement(
                evidence_id=f"artifact_{index}",
                label=artifact,
                source_type=_guess_source_type(artifact),
                query_hint=f"Collect {artifact.lower()}",
                required_for="playbook_selection",
                blocking=True,
            )
        )

    for index, prerequisite in enumerate(_string_list(ootb.get("prerequisites")), start=1):
        requirements.append(
            PlaybookEvidenceRequirement(
                evidence_id=f"prerequisite_{index}",
                label=prerequisite,
                source_type="environment_requirement",
                query_hint=None,
                required_for="triage",
                blocking=False,
            )
        )

    return requirements


def _build_actions_and_decisions(
    *,
    ootb: dict[str, Any] | None,
    executor_aliases: dict[str, dict[str, Any]],
) -> tuple[
    list[PlaybookAction],
    list[PlaybookDecisionPoint],
    list[PlaybookExecutionBinding],
    list[str],
    list[PlaybookIRValidationIssue],
]:
    if ootb is None:
        return [], [], [], [], []

    issues: list[PlaybookIRValidationIssue] = []
    actions: list[PlaybookAction] = []
    decisions: list[PlaybookDecisionPoint] = []
    bindings: list[PlaybookExecutionBinding] = []
    enrichment_steps: list[str] = []

    phases = ootb.get("phases") or []
    flattened_steps: list[dict[str, Any]] = []
    for phase in phases:
        phase_name = str(phase.get("name") or "")
        for step in phase.get("steps") or []:
            flattened_steps.append({"phase_name": phase_name, "step": step})

    # Preserve legacy manual steps with omitted type, but never silently treat
    # an unsupported control node as an ordinary action. This is validation for
    # recommendation IR, not authorization or executable graph qualification.
    seen_step_ids: set[str] = set()
    for index, item in enumerate(flattened_steps):
        step = item["step"]
        step_type = step.get("type", "manual")
        if step_type not in ("manual", "automated", "decision"):
            issues.append(PlaybookIRValidationIssue(
                severity="error", code="unsupported_step_type",
                message=f"Step {index + 1} has unsupported type {step_type!r}.",
            ))
        if "id" in step and (not isinstance(step["id"], str) or not step["id"].strip()):
            issues.append(PlaybookIRValidationIssue(
                severity="error", code="invalid_step_id",
                message=f"Step {index + 1} requires a nonblank string ID when supplied.",
            ))
        prefix = "decision" if step_type == "decision" else "action"
        step_id = str(step.get("id") or f"{prefix}_{index + 1}")
        if step_id in seen_step_ids:
            issues.append(PlaybookIRValidationIssue(
                severity="error", code="duplicate_step_id",
                message=f"Step ID {step_id!r} is repeated across the playbook.",
            ))
        seen_step_ids.add(step_id)

    sequence = 1
    action_index: dict[int, str] = {}
    for index, item in enumerate(flattened_steps):
        step = item["step"]
        step_type = str(step.get("type") or "manual")
        if step_type == "decision":
            continue
        action_id = str(step.get("id") or f"action_{index + 1}")
        action_index[index] = action_id
        alias = _alias_for_action_ref(str(step.get("action_ref") or ""), executor_aliases)
        action, binding, action_issues = _compile_action(
            action_id=action_id,
            sequence=sequence,
            phase_name=item["phase_name"],
            step=step,
            alias=alias,
        )
        actions.append(action)
        issues.extend(action_issues)
        if binding is not None:
            bindings.append(binding)
        if action.execution_mode == "read_only_tooling" or (
            item["phase_name"].lower().startswith("detection") and action.action_type in {"investigate", "enrich", "validation"}
        ):
            enrichment_steps.append(action.label)
        sequence += 1

    for index, item in enumerate(flattened_steps):
        step = item["step"]
        if str(step.get("type") or "") != "decision":
            continue
        next_action_ids: list[str] = []
        for next_index in range(index + 1, len(flattened_steps)):
            candidate = action_index.get(next_index)
            if candidate:
                next_action_ids.append(candidate)
                break
        branch = PlaybookDecisionBranch(
            branch_id=f"{step.get('id', f'decision_{index + 1}')}_default",
            when="Analyst confirms the case path should continue.",
            next_action_ids=next_action_ids,
            execution_mode="manual_only",
        )
        decisions.append(
            PlaybookDecisionPoint(
                decision_id=str(step.get("id") or f"decision_{index + 1}"),
                question=str(step.get("label") or step.get("description") or "Analyst decision required"),
                condition_type="analyst_review",
                inputs_required=[],
                branches=[branch],
                default_branch=branch.branch_id,
                analyst_prompt=str(step.get("description") or ""),
            )
        )

    return actions, decisions, bindings, enrichment_steps, issues


def _compile_action(
    *,
    action_id: str,
    sequence: int,
    phase_name: str,
    step: dict[str, Any],
    alias: dict[str, Any] | None,
) -> tuple[PlaybookAction, PlaybookExecutionBinding | None, list[PlaybookIRValidationIssue]]:
    step_type = str(step.get("type") or "manual")
    label = str(step.get("label") or action_id)
    description = str(step.get("description") or label)
    actor = str(step.get("actor") or "analyst")
    action_ref = str(step.get("action_ref") or "")
    issues: list[PlaybookIRValidationIssue] = []

    binding: PlaybookExecutionBinding | None = None
    if alias is None and step_type == "automated":
        issues.append(
            PlaybookIRValidationIssue(
                severity="error",
                code="missing_executor_alias",
                message=f"Automated step '{label}' has no executor alias for '{action_ref}'.",
            )
        )

    action_type = _default_action_type(label, description, phase_name, action_ref)
    execution_mode = "manual_only"
    risk_level = _default_risk_level(label, description, phase_name)
    requires_approval = False
    default_owner_role = _owner_role_for_actor(actor)
    expected_outcome = description
    rollback_expectation = "No rollback required"
    success_signal = f"Step '{label}' is completed."
    documentation_hint = f"Document outcome of '{label}'."
    executor_binding_id: str | None = None

    if alias is not None:
        action_type = str(alias.get("action_type") or action_type)
        execution_mode = str(alias.get("execution_mode") or execution_mode)
        risk_level = str(alias.get("risk_level") or risk_level)
        requires_approval = bool(alias.get("requires_approval", False))
        default_owner_role = str(alias.get("default_owner_role") or default_owner_role)
        expected_outcome = str(alias.get("expected_outcome") or expected_outcome)
        rollback_expectation = str(alias.get("rollback_expectation") or rollback_expectation)
        success_signal = str(alias.get("success_signal") or success_signal)
        documentation_hint = str(alias.get("documentation_hint") or documentation_hint)
        executor_binding_id = str(alias.get("executor_binding_id") or action_ref or action_id)
        binding = PlaybookExecutionBinding(
            executor_binding_id=executor_binding_id,
            executor_type=str(alias.get("executor_type") or "manual_step"),
            target_ref=str(alias.get("target_ref") or action_ref or label),
            input_schema_ref=alias.get("input_schema_ref"),
            approval_policy_id=alias.get("approval_policy_id"),
            dry_run_supported=bool(alias.get("dry_run_supported", False)),
            reversible=bool(alias.get("reversible", False)),
            timeout_seconds=int(alias.get("timeout_seconds", 300)),
            audit_fields=[str(field) for field in alias.get("audit_fields", [])],
        )

    action = PlaybookAction(
        action_id=action_id,
        sequence=sequence,
        phase_name=phase_name,
        action_type=action_type,
        label=label,
        description=description,
        intent=str(step.get("action_ref") or step.get("description") or label),
        evidence_required=[],
        risk_level=risk_level,  # type: ignore[arg-type]
        requires_approval=requires_approval,
        default_owner_role=default_owner_role,  # type: ignore[arg-type]
        execution_mode=execution_mode,  # type: ignore[arg-type]
        executor_binding_id=executor_binding_id,
        expected_outcome=expected_outcome,
        rollback_expectation=rollback_expectation,
        success_signal=success_signal,
        documentation_hint=documentation_hint,
    )
    return action, binding, issues


def _build_closure_criteria(ootb: dict[str, Any] | None) -> list[str]:
    if ootb is None:
        return []
    criteria: list[str] = []
    for phase in ootb.get("phases") or []:
        if "post" not in str(phase.get("name") or "").lower():
            continue
        for step in phase.get("steps") or []:
            label = str(step.get("label") or "").strip()
            if label:
                criteria.append(f"Complete '{label}'.")
    return criteria


def _build_documentation_prompts(primary_pack: Any, ootb: dict[str, Any] | None) -> list[PlaybookDocumentationPrompt]:
    must_include = list(getattr(primary_pack, "success_checks", ())) or _build_closure_criteria(ootb)
    required_inputs = ["case_summary", "recommended_actions", "evidence_summary"]
    return [
        PlaybookDocumentationPrompt(
            prompt_id="incident_note",
            artifact_type="incident_note",
            required_inputs=required_inputs,
            must_include=must_include[:3],
        ),
        PlaybookDocumentationPrompt(
            prompt_id="ticket_update",
            artifact_type="ticket_update",
            required_inputs=required_inputs,
            must_include=must_include[:3],
        ),
        PlaybookDocumentationPrompt(
            prompt_id="timeline_event",
            artifact_type="timeline_event",
            required_inputs=["case_summary", "recommended_actions"],
            must_include=must_include[:2],
        ),
        PlaybookDocumentationPrompt(
            prompt_id="analyst_handoff",
            artifact_type="analyst_handoff",
            required_inputs=["case_summary", "missing_evidence", "next_owner"],
            must_include=list(getattr(primary_pack, "first_moves", ()))[:2],
        ),
        PlaybookDocumentationPrompt(
            prompt_id="closure_summary",
            artifact_type="closure_summary",
            required_inputs=["case_summary", "executed_actions", "residual_risk"],
            must_include=must_include[:3],
        ),
    ]


def _compiled_status(*, catalog_status: str, issues: list[PlaybookIRValidationIssue], actions: list[PlaybookAction]) -> str:
    if catalog_status == "deprecated":
        return "deprecated"
    if not actions:
        return "manual_review"
    if any(issue.severity == "error" for issue in issues):
        return "manual_review"
    return "ready"


def _owner_role_for_actor(actor: str) -> str:
    normalized = normalize_token(actor)
    if normalized == "system":
        return "SOC_AI_AGENT"
    if normalized == "manager":
        return "SOC_MANAGER"
    if normalized == "analyst":
        return "L1"
    return "HUMAN_OWNER"


def _default_action_type(label: str, description: str, phase_name: str, action_ref: str) -> str:
    normalized = normalize_token(" ".join([label, description, phase_name, action_ref]))
    if any(token in normalized for token in ("lock", "block", "disable", "terminate", "restrict", "isolate", "reset", "purge", "remove")):
        return "containment_review"
    if any(token in normalized for token in ("notify", "advisory", "awareness", "communicate")):
        return "notify"
    if any(token in normalized for token in ("document", "ticket", "record")):
        return "document"
    if any(token in normalized for token in ("confirm", "validate", "classify", "assess")):
        return "validation"
    if any(token in normalized for token in ("search", "collect", "identify", "review", "gather", "scope", "analyze")):
        return "investigate"
    return "coordinate"


def _default_risk_level(label: str, description: str, phase_name: str) -> str:
    normalized = normalize_token(" ".join([label, description, phase_name]))
    if any(token in normalized for token in ("lock", "block", "disable", "isolate", "reset", "purge", "restrict")):
        return "high"
    if any(token in normalized for token in ("confirm", "validate", "review", "collect", "search", "identify", "analyze")):
        return "investigative"
    if any(token in normalized for token in ("document", "ticket", "record", "notify", "communicate")):
        return "informational"
    return "low"


def _alias_for_action_ref(action_ref: str, executor_aliases: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if not action_ref:
        return None
    if action_ref in executor_aliases:
        return executor_aliases[action_ref]
    for prefix, alias in executor_aliases.items():
        if prefix.endswith("*") and action_ref.startswith(prefix[:-1]):
            return alias
    return None


def _guess_source_type(label: str) -> str:
    normalized = normalize_token(label)
    if any(token in normalized for token in ("email", "mail")):
        return "email"
    if any(token in normalized for token in ("log", "siem")):
        return "log"
    if any(token in normalized for token in ("bucket", "storage", "cloud")):
        return "cloud"
    if any(token in normalized for token in ("user", "account", "auth")):
        return "identity"
    return "artifact"


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item is not None]
    if value == "":
        return []
    return [str(value)]

