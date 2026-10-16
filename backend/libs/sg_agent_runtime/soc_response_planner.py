"""Shared deterministic SOC response planner."""

from __future__ import annotations

from typing import Any

from .playbook_ir_models import PlaybookIR
from .response_pack_matcher import match_response_packs_for_incident
from .soc_models import (
    SOCActionRecommendation,
    SOCPlaybookRecommendation,
    SOCRecommendationOutput,
)
from .ticket_scribe import SOCTicketScribe


class SOCResponsePlanner:
    """Response-pack-first planner shared across SOAR and the agent runtime."""

    def recommend_response_plan(
        self,
        incident_data: dict[str, Any],
        available_playbooks: list[dict[str, Any]] | None = None,
    ) -> SOCRecommendationOutput:
        playbooks = available_playbooks or []
        heuristic_recommendations = self.score_playbooks(incident_data, playbooks)
        heuristic_by_identity = {
            self._playbook_identity(rec): rec for rec in heuristic_recommendations
        }

        matched_packs = match_response_packs_for_incident(incident_data, playbooks)
        top_pack = matched_packs[0] if matched_packs else None

        if top_pack:
            selected_playbooks = top_pack.playbooks or self.fallback_pack_playbooks(
                top_pack.pack.playbook_keys,
                heuristic_recommendations,
            )
            pack_score = top_pack.score
            pack_reasons = top_pack.reasons
            response_pack_id = top_pack.pack.id
            response_pack_label = top_pack.pack.label
            response_pack_summary = top_pack.pack.summary
            success_checks = list(top_pack.pack.success_checks)
            recommended_actions = self.build_recommended_actions(
                top_pack.pack.first_moves,
                supporting_playbooks=selected_playbooks[:3],
            )
        else:
            selected_playbooks = self.fallback_pack_playbooks((), heuristic_recommendations)
            pack_score = 0
            pack_reasons = ["No strong saved response pack match; manual analyst review required"]
            response_pack_id = "manual_investigation"
            response_pack_label = "Manual investigation"
            response_pack_summary = "No strong saved response pack matched the incident. Review the top ranked playbooks and analyst actions manually."
            success_checks = ["An analyst reviews and confirms the recommended next steps."]
            recommended_actions = self.build_default_actions(incident_data, selected_playbooks[:3])

        recommended_playbooks = self.build_playbook_recommendations(
            selected_playbooks[:3],
            heuristic_by_identity,
            response_pack_id=response_pack_id,
            pack_score=pack_score,
            pack_reasons=pack_reasons,
        )

        confidence = self.plan_confidence(pack_score, recommended_playbooks)
        rationale = list(dict.fromkeys([*pack_reasons, *success_checks]))[:5]
        missing_evidence = self.build_missing_evidence(incident_data)
        documentation = SOCTicketScribe().build_documentation_bundle(
            incident_data=incident_data,
            response_pack_label=response_pack_label,
            response_pack_summary=response_pack_summary,
            recommended_playbooks=recommended_playbooks,
            recommended_actions=recommended_actions,
            missing_evidence=missing_evidence,
            rationale=rationale,
            confidence=confidence,
        )

        incident_title = incident_data.get("title") or incident_data.get("summary") or "Untitled incident"
        severity = str(incident_data.get("severity") or "unknown").lower()
        incident_type = (
            incident_data.get("incident_type")
            or incident_data.get("category")
            or incident_data.get("source")
            or "security incident"
        )

        return SOCRecommendationOutput(
            case_summary=(
                f"{incident_title} is currently being treated as a {severity} {incident_type.replace('_', ' ')} case. "
                f"The planner selected the '{response_pack_label}' response path based on the available incident signals."
            ),
            response_pack_id=response_pack_id,
            response_pack_label=response_pack_label,
            recommended_playbooks=recommended_playbooks,
            recommended_actions=recommended_actions,
            missing_evidence=missing_evidence,
            proposed_phase=incident_data.get("phase") or "detection_and_analysis",
            proposed_status=incident_data.get("status") or "investigating",
            incident_note_draft=documentation.incident_note_draft,
            ticket_update_draft=documentation.ticket_update_draft,
            timeline_event_draft=documentation.timeline_event_draft,
            analyst_handoff_draft=documentation.analyst_handoff_draft,
            closure_checklist=list(documentation.closure_checklist),
            documentation_bundle=documentation,
            confidence=confidence,
            rationale=rationale,
        )

    def score_playbooks(
        self,
        incident_data: dict[str, Any],
        available_playbooks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not available_playbooks:
            return []

        recommendations = []

        category = str(incident_data.get("category") or incident_data.get("incident_type") or "").lower()
        severity = str(incident_data.get("severity") or "").lower()
        nist_controls = incident_data.get("nist_controls", [])
        mitre_tactics = incident_data.get("mitre_tactics", [])
        mitre_techniques = incident_data.get("mitre_techniques", [])
        cve_ids = incident_data.get("cve_ids", [])

        for playbook in available_playbooks:
            score = 0.0
            reasons = []

            playbook_category = str(playbook.get("category") or "").lower()
            if playbook_category and category:
                if playbook_category in category or category in playbook_category:
                    score += 0.3
                    reasons.append(f"Category match: {playbook_category}")

            playbook_nist = playbook.get("nist_controls", [])
            if playbook_nist and nist_controls:
                matching_controls = set(playbook_nist) & set(
                    [c.get("control_id") if isinstance(c, dict) else c for c in nist_controls]
                )
                if matching_controls:
                    score += 0.2 * len(matching_controls)
                    reasons.append(f"NIST control match: {', '.join(sorted(matching_controls))}")

            playbook_mitre_tactics = playbook.get("mitre_tactics", [])
            if playbook_mitre_tactics and mitre_tactics:
                matching_tactics = set(playbook_mitre_tactics) & set(
                    [t.get("tactic_id") if isinstance(t, dict) else t for t in mitre_tactics]
                )
                if matching_tactics:
                    score += 0.2 * len(matching_tactics)
                    reasons.append(f"MITRE tactic match: {', '.join(sorted(matching_tactics))}")

            playbook_mitre_techniques = playbook.get("mitre_techniques", [])
            if playbook_mitre_techniques and mitre_techniques:
                matching_techniques = set(playbook_mitre_techniques) & set(
                    [t.get("technique_id") if isinstance(t, dict) else t for t in mitre_techniques]
                )
                if matching_techniques:
                    score += 0.2 * len(matching_techniques)
                    reasons.append(f"MITRE technique match: {', '.join(sorted(matching_techniques))}")

            if cve_ids and "vulnerability" in playbook_category:
                score += 0.1
                reasons.append("CVE detected in incident")

            if "malware" in category and "malware" in playbook_category:
                score += 0.3
                reasons.append("Malware incident detected")

            if "phishing" in category and "phishing" in playbook_category:
                score += 0.3
                reasons.append("Phishing incident detected")

            if severity in {"high", "critical"} and playbook.get("automation_default") in {"manual", "semi_auto", None}:
                score += 0.1
                reasons.append(f"{severity} severity alignment")

            if score > 0:
                recommendations.append(
                    {
                        "playbook_id": playbook.get("id"),
                        "playbook_key": playbook.get("playbook_key") or playbook.get("key") or playbook.get("id"),
                        "playbook_name": playbook.get("name"),
                        "score": min(score, 1.0),
                        "reasons": reasons,
                        "category": playbook_category,
                        "source_playbook": playbook,
                    }
                )

        recommendations.sort(key=lambda item: item["score"], reverse=True)
        return recommendations[:10]

    def fallback_pack_playbooks(
        self,
        playbook_keys: tuple[str, ...] | list[str],
        heuristic_recommendations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        normalized_keys = {self.normalize_token(key) for key in playbook_keys}
        if normalized_keys:
            matched = [
                item["source_playbook"]
                for item in heuristic_recommendations
                if self.normalize_token(item.get("playbook_key") or item.get("playbook_name")) in normalized_keys
            ]
            if matched:
                return matched
        return [item["source_playbook"] for item in heuristic_recommendations]

    def build_playbook_recommendations(
        self,
        selected_playbooks: list[dict[str, Any]],
        heuristic_by_identity: dict[str, dict[str, Any]],
        *,
        response_pack_id: str,
        pack_score: int,
        pack_reasons: list[str],
    ) -> list[SOCPlaybookRecommendation]:
        recommendations: list[SOCPlaybookRecommendation] = []
        for index, playbook in enumerate(selected_playbooks, start=1):
            identity = self._playbook_identity(playbook)
            heuristic = heuristic_by_identity.get(identity, {})
            heur_score = float(heuristic.get("score", 0.0))
            rationale = list(dict.fromkeys([*pack_reasons, *(heuristic.get("reasons", []))]))[:4]
            recommendations.append(
                SOCPlaybookRecommendation(
                    playbook_id=str(playbook.get("id")) if playbook.get("id") is not None else None,
                    playbook_key=playbook.get("playbook_key") or playbook.get("key"),
                    playbook_name=playbook.get("name") or playbook.get("playbook_key") or f"Playbook {index}",
                    rank=index,
                    confidence=min(1.0, ((pack_score / 10.0) + heur_score) / 1.8) if pack_score else min(1.0, heur_score),
                    rationale=rationale,
                    mapped_response_pack_id=response_pack_id,
                    automation_mode=self._playbook_automation_mode(playbook),  # type: ignore[arg-type]
                )
            )
        return recommendations

    def build_recommended_actions(
        self,
        first_moves: tuple[str, ...] | list[str],
        *,
        supporting_playbooks: list[dict[str, Any]],
    ) -> list[SOCActionRecommendation]:
        primary_playbook = supporting_playbooks[0] if supporting_playbooks else {}
        compiled_actions = self._build_compiled_actions(primary_playbook)
        if compiled_actions:
            return compiled_actions

        actions = []
        for move in first_moves:
            normalized = self.normalize_token(move)
            risk_level = "low"
            action_type = "investigate"
            requires_approval = False
            owner_role = "L1"
            rollback_expectation = "No rollback required"

            if any(token in normalized for token in ("isolate", "revoke", "rotate", "lock", "block", "contain")):
                risk_level = "high"
                action_type = "containment_review"
                requires_approval = True
                owner_role = "L2"
                rollback_expectation = "Verify the action is reversible before execution and record the rollback path."
            elif any(token in normalized for token in ("assign", "route", "schedule", "capture", "document", "attach")):
                risk_level = "informational"
                action_type = "documentation"
                owner_role = "L1"
            elif any(token in normalized for token in ("confirm", "validate", "review", "identify", "prioritize")):
                risk_level = "investigative"
                action_type = "investigate"
                owner_role = "L1"

            actions.append(
                SOCActionRecommendation(
                    action_type=action_type,
                    label=move,
                    description=move,
                    risk_level=risk_level,  # type: ignore[arg-type]
                    requires_approval=requires_approval,
                    recommended_owner_role=owner_role,  # type: ignore[arg-type]
                    evidence_basis=["Response-pack first-move guidance"],
                    expected_outcome="Advance the incident using a supervised analyst-reviewed step.",
                    rollback_expectation=rollback_expectation,
                    supporting_playbook_id=str(primary_playbook.get("id")) if primary_playbook.get("id") is not None else None,
                    supporting_playbook_key=primary_playbook.get("playbook_key") or primary_playbook.get("key"),
                )
            )
        return actions

    def build_default_actions(
        self,
        incident_data: dict[str, Any],
        supporting_playbooks: list[dict[str, Any]],
    ) -> list[SOCActionRecommendation]:
        incident_title = incident_data.get("title") or "incident"
        return self.build_recommended_actions(
            [
                f"Validate the core facts, owner, and blast radius for {incident_title}.",
                "Review the top ranked playbook and decide whether supervised containment planning is needed.",
                "Draft the analyst note and confirm the next human owner before the case stalls.",
            ],
            supporting_playbooks=supporting_playbooks,
        )

    def build_missing_evidence(self, incident_data: dict[str, Any]) -> list[str]:
        missing = []
        if not (incident_data.get("related_detections") or []):
            missing.append("No related detections are linked to the incident yet.")
        if not (incident_data.get("entities") or []):
            missing.append("No impacted identities or assets are attached yet.")
        if not (incident_data.get("evidence") or []):
            missing.append("No evidence artifacts are attached yet.")
        if not (incident_data.get("ticket_id") or incident_data.get("external_ticket_id")):
            missing.append("No downstream ticket reference is linked yet.")
        return missing[:4]

    def plan_confidence(
        self,
        pack_score: int,
        playbooks: list[SOCPlaybookRecommendation],
    ) -> float:
        if not playbooks and pack_score <= 0:
            return 0.2
        top_playbook_confidence = playbooks[0].confidence if playbooks else 0.0
        if pack_score <= 0:
            return round(min(0.6, max(0.3, top_playbook_confidence)), 2)
        return round(min(0.95, max(top_playbook_confidence, pack_score / 10.0)), 2)

    @staticmethod
    def normalize_token(value: Any) -> str:
        return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in str(value or "")).split())

    @staticmethod
    def _playbook_identity(playbook: dict[str, Any]) -> str:
        return str(
            playbook.get("playbook_id")
            or playbook.get("id")
            or playbook.get("playbook_key")
            or playbook.get("key")
            or playbook.get("playbook_name")
            or playbook.get("name")
        )

    @staticmethod
    def _compiled_ir(playbook: dict[str, Any]) -> PlaybookIR | None:
        compiled = playbook.get("compiled_ir")
        if isinstance(compiled, PlaybookIR):
            return compiled
        if isinstance(compiled, dict):
            return PlaybookIR.model_validate(compiled)
        return None

    def _playbook_automation_mode(self, playbook: dict[str, Any]) -> str:
        compiled = self._compiled_ir(playbook)
        if compiled is None or compiled.status != "ready":
            return "manual_review"
        if any(action.requires_approval or action.execution_mode == "human_approved_executor" for action in compiled.actions):
            return "approval_required"
        if any(action.execution_mode == "read_only_tooling" for action in compiled.actions):
            return "automated"
        return "manual_review"

    def _build_compiled_actions(self, playbook: dict[str, Any]) -> list[SOCActionRecommendation]:
        compiled = self._compiled_ir(playbook)
        if compiled is None:
            return []

        actions: list[SOCActionRecommendation] = []
        for action in sorted(compiled.actions, key=lambda candidate: (candidate.sequence, candidate.action_id))[:3]:
            actions.append(
                SOCActionRecommendation(
                    action_type=action.action_type,
                    label=action.label,
                    description=action.description,
                    risk_level=action.risk_level,
                    requires_approval=action.requires_approval,
                    recommended_owner_role=action.default_owner_role,
                    evidence_basis=action.evidence_required or ["Compiled PlaybookIR action guidance"],
                    expected_outcome=action.expected_outcome,
                    rollback_expectation=action.rollback_expectation,
                    supporting_playbook_id=playbook.get("id"),
                    supporting_playbook_key=playbook.get("playbook_key") or playbook.get("key"),
                )
            )
        return actions
