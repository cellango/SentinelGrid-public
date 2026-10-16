"""Deterministic ticket and incident draft generation for SOC cases."""

from __future__ import annotations

from typing import Any

from .soc_models import (
    SOCActionRecommendation,
    SOCDocumentationBundle,
    SOCDocumentationTemplateKind,
    SOCPlaybookRecommendation,
)


class SOCTicketScribe:
    """Generate reusable documentation drafts for SOC case recommendation cycles."""

    def build_documentation_bundle(
        self,
        *,
        incident_data: dict[str, Any],
        response_pack_label: str,
        response_pack_summary: str,
        recommended_playbooks: list[SOCPlaybookRecommendation],
        recommended_actions: list[SOCActionRecommendation],
        missing_evidence: list[str],
        rationale: list[str],
        confidence: float,
    ) -> SOCDocumentationBundle:
        template_kind = self.resolve_template_kind(
            trigger_type=self._trigger_type(incident_data),
            proposed_phase=str(incident_data.get("phase") or ""),
            proposed_status=str(incident_data.get("status") or ""),
            recommended_actions=recommended_actions,
        )
        incident_title = str(incident_data.get("title") or incident_data.get("summary") or "Untitled incident")
        severity = str(incident_data.get("severity") or "unknown").upper()
        playbook_line = self._playbook_line(recommended_playbooks)
        action_line = self._action_line(recommended_actions)
        evidence_line = self._missing_evidence_line(missing_evidence)
        owner = str(incident_data.get("assigned_to") or incident_data.get("current_owner") or "SOC analyst")

        incident_note = self._incident_note(
            template_kind=template_kind,
            incident_title=incident_title,
            severity=severity,
            response_pack_label=response_pack_label,
            response_pack_summary=response_pack_summary,
            playbook_line=playbook_line,
            action_line=action_line,
            evidence_line=evidence_line,
            rationale=rationale,
            confidence=confidence,
        )
        ticket_update = self._ticket_update(
            template_kind=template_kind,
            response_pack_label=response_pack_label,
            action_line=action_line,
            evidence_line=evidence_line,
        )
        timeline_event = self._timeline_event(
            template_kind=template_kind,
            response_pack_label=response_pack_label,
            playbook_line=playbook_line,
            action_line=action_line,
        )
        handoff = self._handoff_note(
            template_kind=template_kind,
            owner=owner,
            response_pack_label=response_pack_label,
            action_line=action_line,
            evidence_line=evidence_line,
        )
        checklist = self._closure_checklist(
            template_kind=template_kind,
            response_pack_label=response_pack_label,
            missing_evidence=missing_evidence,
        )

        return SOCDocumentationBundle(
            template_kind=template_kind,
            incident_note_draft=incident_note,
            ticket_update_draft=ticket_update,
            timeline_event_draft=timeline_event,
            analyst_handoff_draft=handoff,
            closure_checklist=checklist,
        )

    def resolve_template_kind(
        self,
        *,
        trigger_type: str | None,
        proposed_phase: str,
        proposed_status: str,
        recommended_actions: list[SOCActionRecommendation],
    ) -> SOCDocumentationTemplateKind:
        phase = proposed_phase.lower()
        status = proposed_status.lower()
        if status in {"resolved", "closed"} or "closed" in phase or "lessons" in phase:
            return "closure_ready"
        if trigger_type == "playbook_execution_completed":
            return "post_action_update"
        if trigger_type in {"incident_created", None, ""}:
            return "triage_note"
        if "contain" in phase or any(action.requires_approval for action in recommended_actions):
            return "containment_recommendation"
        return "investigation_update"

    @staticmethod
    def _trigger_type(incident_data: dict[str, Any]) -> str | None:
        raw_payload = incident_data.get("raw_payload") or {}
        if isinstance(raw_payload, dict):
            value = raw_payload.get("trigger_type")
            if value is not None:
                return str(value)
        return None

    @staticmethod
    def _playbook_line(recommended_playbooks: list[SOCPlaybookRecommendation]) -> str:
        return ", ".join(playbook.playbook_name for playbook in recommended_playbooks[:3]) or "manual analyst review"

    @staticmethod
    def _action_line(recommended_actions: list[SOCActionRecommendation]) -> str:
        return "; ".join(action.label for action in recommended_actions[:3]) or "manual analyst review"

    @staticmethod
    def _missing_evidence_line(missing_evidence: list[str]) -> str:
        return "; ".join(missing_evidence[:3]) or "No major evidence gaps are currently blocking analyst progress."

    def _incident_note(
        self,
        *,
        template_kind: SOCDocumentationTemplateKind,
        incident_title: str,
        severity: str,
        response_pack_label: str,
        response_pack_summary: str,
        playbook_line: str,
        action_line: str,
        evidence_line: str,
        rationale: list[str],
        confidence: float,
    ) -> str:
        rationale_line = "; ".join(rationale[:3]) or "The current evidence supports this response path."
        prefix = {
            "triage_note": "AI triage summary",
            "investigation_update": "AI investigation update",
            "containment_recommendation": "AI containment recommendation",
            "post_action_update": "AI post-action update",
            "closure_ready": "AI closure summary",
        }[template_kind]
        return (
            f"{prefix}: {incident_title} is being handled as a {severity} case. "
            f"Selected response pack: '{response_pack_label}'. {response_pack_summary} "
            f"Recommended playbooks: {playbook_line}. "
            f"Recommended next actions: {action_line}. "
            f"Reasoning: {rationale_line}. "
            f"Confidence: {round(confidence * 100)}%. "
            f"Open evidence gaps: {evidence_line}."
        )

    def _ticket_update(
        self,
        *,
        template_kind: SOCDocumentationTemplateKind,
        response_pack_label: str,
        action_line: str,
        evidence_line: str,
    ) -> str:
        update_prefix = {
            "triage_note": "SOC AI recommendation",
            "investigation_update": "SOC AI investigation update",
            "containment_recommendation": "SOC AI containment recommendation",
            "post_action_update": "SOC AI post-action update",
            "closure_ready": "SOC AI closure recommendation",
        }[template_kind]
        return (
            f"{update_prefix}: use the '{response_pack_label}' response path. "
            f"Next analyst actions: {action_line}. "
            f"Evidence gaps to close: {evidence_line}."
        )

    def _timeline_event(
        self,
        *,
        template_kind: SOCDocumentationTemplateKind,
        response_pack_label: str,
        playbook_line: str,
        action_line: str,
    ) -> str:
        event_prefix = {
            "triage_note": "SOC AI triage completed",
            "investigation_update": "SOC AI investigation refreshed",
            "containment_recommendation": "SOC AI containment plan refreshed",
            "post_action_update": "SOC AI post-action review completed",
            "closure_ready": "SOC AI closure review completed",
        }[template_kind]
        return (
            f"{event_prefix}: selected '{response_pack_label}', ranked playbooks [{playbook_line}], "
            f"and recommended actions [{action_line}]."
        )

    def _handoff_note(
        self,
        *,
        template_kind: SOCDocumentationTemplateKind,
        owner: str,
        response_pack_label: str,
        action_line: str,
        evidence_line: str,
    ) -> str:
        handoff_prefix = {
            "triage_note": "Suggested L1 handoff",
            "investigation_update": "Suggested L2 handoff",
            "containment_recommendation": "Suggested containment approval handoff",
            "post_action_update": "Suggested post-action handoff",
            "closure_ready": "Suggested closure handoff",
        }[template_kind]
        return (
            f"{handoff_prefix}: route the case to {owner}. "
            f"Keep the '{response_pack_label}' response path active, complete these next actions [{action_line}], "
            f"and close the remaining evidence gaps [{evidence_line}]."
        )

    def _closure_checklist(
        self,
        *,
        template_kind: SOCDocumentationTemplateKind,
        response_pack_label: str,
        missing_evidence: list[str],
    ) -> list[str]:
        base = [
            f"Confirm the '{response_pack_label}' response path is still the active case path.",
            "Ensure the incident note and downstream ticket update are posted by a human analyst.",
            "Record whether recommended actions were accepted, rejected, or deferred.",
        ]
        if template_kind in {"containment_recommendation", "post_action_update"}:
            base.append("Verify any containment action has an approval record and rollback path.")
        if template_kind == "closure_ready":
            base.extend(
                [
                    "Confirm the incident owner documented the outcome, impact, and lessons learned.",
                    "Confirm linked evidence and ticket references are complete before closure.",
                ]
            )
        if missing_evidence:
            base.append("Resolve or explicitly waive the remaining evidence gaps before final closure.")
        return base[:5]
