"""Questionnaire-assist service for trust reviews and customer security questionnaires."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


STARTER_QUESTIONS = [
    "How do we answer customer security questionnaires quickly?",
    "What can we share for a customer security review?",
    "How do we evidence MFA and access control coverage?",
    "How do we show detection and response coverage?",
]

TRUST_ARTIFACT_REASONS = {
    "smb_customer_security_review_pack": "Best for customer-facing security reviews and vendor questionnaires.",
    "smb_audit_readiness_pack": "Best for audit-prep conversations and readiness summaries.",
    "smb_evidence_attachment_export": "Best when a reviewer asks for supporting evidence or control-specific attachments.",
}

CATEGORY_KEYWORDS = {
    "identity_access": [
        "mfa",
        "sso",
        "identity",
        "access",
        "least privilege",
        "privileged",
        "account",
        "entra",
        "okta",
        "google workspace",
        "review access",
    ],
    "detection_response": [
        "incident",
        "respond",
        "response",
        "detect",
        "detection",
        "monitoring",
        "alert",
        "siem",
        "playbook",
        "mttr",
        "mttd",
    ],
    "cloud_posture": [
        "cloud",
        "aws",
        "azure",
        "gcp",
        "posture",
        "misconfiguration",
        "storage",
        "security group",
        "exposed",
    ],
    "evidence_readiness": [
        "evidence",
        "audit",
        "soc 2",
        "soc2",
        "questionnaire",
        "security review",
        "trust",
        "control",
        "attest",
        "compliance",
    ],
}


class QuestionnaireAssistService:
    """Draft structured answers for trust and questionnaire workflows."""

    def __init__(self) -> None:
        self.internal_token = settings.INTERNAL_SERVICE_TOKEN
        self.compliance_service_url = settings.COMPLIANCE_SERVICE_URL

    async def build_questionnaire_assist(
        self,
        tenant_id: str,
        questions: list[str],
    ) -> dict[str, Any]:
        normalized_questions = [question.strip() for question in questions if question and question.strip()]
        if not normalized_questions:
            raise ValueError("At least one question is required")

        dashboard = await self._fetch_compliance_dashboard(tenant_id)
        answers = [self._draft_answer(question, dashboard) for question in normalized_questions]

        artifact_map: dict[str, str] = {}
        for answer in answers:
            for artifact in answer["recommended_artifacts"]:
                artifact_map[artifact["template_key"]] = artifact["reason"]

        return {
            "summary": self._build_summary(dashboard, normalized_questions, artifact_map),
            "answers": answers,
            "suggested_questions": STARTER_QUESTIONS,
        }

    async def build_security_review_templates(self, tenant_id: str) -> dict[str, Any]:
        dashboard = await self._fetch_compliance_dashboard(tenant_id)
        summary = self._build_template_summary(dashboard)

        return {
            "summary": summary,
            "templates": [
                self._build_initial_review_template(dashboard),
                self._build_questionnaire_handoff_template(dashboard),
                self._build_evidence_follow_up_template(dashboard),
                self._build_framework_positioning_template(dashboard),
            ],
        }

    async def _fetch_compliance_dashboard(self, tenant_id: str) -> dict[str, Any]:
        url = f"{self.compliance_service_url}/api/v1/compliance/dashboard"
        headers = {
            "Authorization": f"Bearer {self.internal_token}",
            "X-Tenant-ID": tenant_id,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    def _build_summary(
        self,
        dashboard: dict[str, Any],
        questions: list[str],
        artifact_map: dict[str, str],
    ) -> dict[str, Any]:
        reporting_summary = dashboard.get("reporting_summary") or {}
        overall_stats = dashboard.get("overall_stats") or {}

        recommended_artifacts = [
            {"template_key": template_key, "reason": artifact_map[template_key]}
            for template_key in artifact_map
        ]

        return {
            "question_count": len(questions),
            "overall_score": round(float(overall_stats.get("overall_score", 0) or 0)),
            "criteria_ready": int(reporting_summary.get("criteria_ready", 0) or 0),
            "criteria_needing_attention": int(reporting_summary.get("criteria_needing_attention", 0) or 0),
            "mapped_detections": int(overall_stats.get("mapped_detections", 0) or 0),
            "control_checks": int(overall_stats.get("control_checks", 0) or 0),
            "evidence_items": int(overall_stats.get("evidence_items", 0) or 0),
            "recommended_artifacts": recommended_artifacts,
        }

    def _build_template_summary(self, dashboard: dict[str, Any]) -> dict[str, Any]:
        overall_stats = dashboard.get("overall_stats") or {}
        reporting_summary = dashboard.get("reporting_summary") or {}
        framework_packs = dashboard.get("framework_starter_packs") or []
        pack_states = {
            pack.get("framework_key"): pack.get("launch_state")
            for pack in framework_packs
            if pack.get("framework_key")
        }

        return {
            "overall_score": round(float(overall_stats.get("overall_score", 0) or 0)),
            "criteria_ready": int(reporting_summary.get("criteria_ready", 0) or 0),
            "criteria_needing_attention": int(reporting_summary.get("criteria_needing_attention", 0) or 0),
            "mapped_detections": int(overall_stats.get("mapped_detections", 0) or 0),
            "control_checks": int(overall_stats.get("control_checks", 0) or 0),
            "evidence_items": int(overall_stats.get("evidence_items", 0) or 0),
            "framework_pack_states": pack_states,
        }

    def _draft_answer(self, question: str, dashboard: dict[str, Any]) -> dict[str, Any]:
        category = self._categorize_question(question)
        controls = self._select_controls(category, dashboard)
        signals = self._select_signals(category, dashboard)
        recommended_artifact_keys = self._recommended_artifact_keys(category)
        answer_text = self._build_answer_text(question, category, dashboard, controls, signals)
        follow_up = self._build_follow_up(category, dashboard)

        return {
            "question": question,
            "category": category,
            "confidence": self._confidence(category, controls, signals),
            "answer": answer_text,
            "recommended_artifacts": [
                {
                    "template_key": template_key,
                    "reason": TRUST_ARTIFACT_REASONS[template_key],
                }
                for template_key in recommended_artifact_keys
            ],
            "supporting_controls": [
                {
                    "id": control.get("id", "Unknown"),
                    "title": control.get("title", "Untitled criterion"),
                    "status": control.get("status", "unknown"),
                    "open_findings": int(control.get("open_findings", 0) or 0),
                    "evidence_items": int(control.get("evidence_items", 0) or 0),
                }
                for control in controls[:3]
            ],
            "supporting_signals": [
                {
                    "id": signal.get("id", signal.get("title", "signal")),
                    "title": signal.get("title", "Untitled signal"),
                    "source_label": signal.get("source_label") or signal.get("source") or "Signal",
                    "status": signal.get("status"),
                    "href": signal.get("href"),
                }
                for signal in signals[:3]
            ],
            "follow_up": follow_up,
        }

    def _categorize_question(self, question: str) -> str:
        normalized = question.lower()

        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in normalized for keyword in keywords):
                return category

        return "general_security_review"

    def _select_controls(self, category: str, dashboard: dict[str, Any]) -> list[dict[str, Any]]:
        controls = list(dashboard.get("priority_criteria") or [])
        if not controls:
            return []

        if category == "identity_access":
            filtered = [
                control
                for control in controls
                if self._matches_any(
                    " ".join(
                        [
                            str(control.get("id", "")),
                            str(control.get("title", "")),
                            " ".join(control.get("mapped_nist_controls") or []),
                        ]
                    ),
                    ["access", "identity", "mfa", "ia-", "ac-", "authentication", "privilege"],
                )
            ]
            return filtered or controls[:3]

        if category == "detection_response":
            filtered = [
                control
                for control in controls
                if self._matches_any(
                    " ".join(
                        [
                            str(control.get("title", "")),
                            " ".join(control.get("mapped_nist_controls") or []),
                        ]
                    ),
                    ["detect", "monitor", "response", "incident", "ir-", "si-", "au-"],
                )
            ]
            return filtered or controls[:3]

        if category == "cloud_posture":
            filtered = [
                control
                for control in controls
                if self._matches_any(
                    " ".join(
                        [
                            str(control.get("title", "")),
                            str(control.get("description", "")),
                            " ".join(control.get("mapped_nist_controls") or []),
                        ]
                    ),
                    ["configuration", "cloud", "storage", "network", "cm-", "sc-", "posture"],
                )
            ]
            return filtered or controls[:3]

        return controls[:3]

    def _select_signals(self, category: str, dashboard: dict[str, Any]) -> list[dict[str, Any]]:
        key_detections = list(dashboard.get("key_detections") or [])
        control_checks = list(dashboard.get("control_checks") or [])
        signals = key_detections + control_checks
        if not signals:
            return []

        if category == "identity_access":
            filtered = [
                signal
                for signal in signals
                if self._matches_any(
                    " ".join(
                        [
                            str(signal.get("title", "")),
                            str(signal.get("description", "")),
                            str(signal.get("source_label", "")),
                            str(signal.get("source", "")),
                        ]
                    ),
                    ["identity", "mfa", "login", "access", "privilege", "user"],
                )
            ]
            return filtered or signals[:3]

        if category == "detection_response":
            filtered = [
                signal
                for signal in signals
                if self._matches_any(
                    " ".join(
                        [
                            str(signal.get("title", "")),
                            str(signal.get("description", "")),
                            str(signal.get("source_label", "")),
                            str(signal.get("source", "")),
                        ]
                    ),
                    ["incident", "alert", "detect", "response", "playbook", "monitor"],
                )
            ]
            return filtered or signals[:3]

        if category == "cloud_posture":
            filtered = [
                signal
                for signal in signals
                if self._matches_any(
                    " ".join(
                        [
                            str(signal.get("title", "")),
                            str(signal.get("description", "")),
                            str(signal.get("source_label", "")),
                            str(signal.get("source", "")),
                        ]
                    ),
                    ["cloud", "aws", "azure", "gcp", "storage", "bucket", "network", "posture"],
                )
            ]
            return filtered or signals[:3]

        return signals[:3]

    def _recommended_artifact_keys(self, category: str) -> list[str]:
        if category == "identity_access":
            return [
                "smb_customer_security_review_pack",
                "smb_evidence_attachment_export",
            ]

        if category == "detection_response":
            return [
                "smb_customer_security_review_pack",
                "smb_audit_readiness_pack",
            ]

        if category == "cloud_posture":
            return [
                "smb_customer_security_review_pack",
                "smb_audit_readiness_pack",
            ]

        if category == "evidence_readiness":
            return [
                "smb_evidence_attachment_export",
                "smb_audit_readiness_pack",
            ]

        return ["smb_customer_security_review_pack"]

    def _build_answer_text(
        self,
        question: str,
        category: str,
        dashboard: dict[str, Any],
        controls: list[dict[str, Any]],
        signals: list[dict[str, Any]],
    ) -> str:
        overall_stats = dashboard.get("overall_stats") or {}
        reporting_summary = dashboard.get("reporting_summary") or {}
        criteria_ready = int(reporting_summary.get("criteria_ready", 0) or 0)
        criteria_attention = int(reporting_summary.get("criteria_needing_attention", 0) or 0)
        evidence_items = int(overall_stats.get("evidence_items", 0) or 0)
        mapped_detections = int(overall_stats.get("mapped_detections", 0) or 0)
        control_checks = int(overall_stats.get("control_checks", 0) or 0)
        score = round(float(overall_stats.get("overall_score", 0) or 0))
        control_labels = ", ".join(control.get("id", "Unknown") for control in controls[:3]) or "the priority criteria currently in view"
        signal_labels = ", ".join(signal.get("title", "supporting signal") for signal in signals[:2]) or "the mapped detections and control checks"

        if category == "identity_access":
            return (
                f"SentinelGrid can answer this with live identity and access evidence rather than a static statement. "
                f"The current compliance view shows {control_checks} mapped control checks and {evidence_items} evidence items supporting "
                f"identity-focused criteria such as {control_labels}. For a customer questionnaire or security review, start with the "
                f"Customer Security Review Pack and attach the Evidence Attachment Export if the reviewer asks for control-specific proof. "
                f"Recent supporting signals include {signal_labels}."
            )

        if category == "detection_response":
            return (
                f"SentinelGrid answers this from active detection and response coverage. The current readiness view includes "
                f"{mapped_detections} mapped detections, {control_checks} mapped control checks, and a compliance score of {score}/100. "
                f"Use the Customer Security Review Pack for a concise response, or the Audit Readiness Pack when the reviewer wants more "
                f"detail on response processes and remediation evidence. Priority criteria in scope include {control_labels}, supported by "
                f"signals such as {signal_labels}."
            )

        if category == "cloud_posture":
            return (
                f"SentinelGrid can frame this as a live cloud-control story instead of a one-off spreadsheet answer. "
                f"The current reporting view shows {criteria_ready} criteria ready for export, {criteria_attention} needing attention, and "
                f"{mapped_detections} mapped detections supporting the trust narrative. Recommended artifacts are the Customer Security Review Pack "
                f"for a concise answer and the Audit Readiness Pack when the reviewer wants deeper control context. Relevant criteria include "
                f"{control_labels}, with supporting signals such as {signal_labels}."
            )

        if category == "evidence_readiness":
            return (
                f"SentinelGrid is set up to answer evidence-heavy questions using the live reporting layer. The current dashboard shows "
                f"{criteria_ready} criteria ready, {criteria_attention} criteria still needing attention, and {evidence_items} evidence items available "
                f"for export. Start with the Evidence Attachment Export when the reviewer asks for supporting proof, and use the Audit Readiness Pack "
                f"for a broader summary. Criteria most relevant right now include {control_labels}."
            )

        return (
            f"SentinelGrid can answer this with a current trust snapshot generated from live platform evidence. The latest readiness view shows "
            f"{criteria_ready} criteria ready for export, {criteria_attention} needing attention, {mapped_detections} mapped detections, "
            f"{control_checks} control checks, and {evidence_items} evidence items. For most prospect and customer reviews, start with the "
            f"Customer Security Review Pack, then attach the Evidence Attachment Export if the reviewer asks follow-up questions."
        )

    def _build_follow_up(self, category: str, dashboard: dict[str, Any]) -> list[str]:
        reporting_summary = dashboard.get("reporting_summary") or {}
        criteria_attention = int(reporting_summary.get("criteria_needing_attention", 0) or 0)
        follow_up = [
            "Generate the recommended trust artifact from the Compliance Reports page before sending a response.",
        ]

        if category in {"identity_access", "evidence_readiness"}:
            follow_up.append("Attach the Evidence Attachment Export if the reviewer asks for control-specific proof.")
        if category in {"detection_response", "cloud_posture"}:
            follow_up.append("Use the Audit Readiness Pack if the reviewer wants deeper remediation or control coverage detail.")
        if criteria_attention > 0:
            follow_up.append(
                f"Review the {criteria_attention} criteria still needing attention so the final response reflects any open gaps."
            )

        return follow_up

    def _build_initial_review_template(self, dashboard: dict[str, Any]) -> dict[str, Any]:
        summary = self._build_template_summary(dashboard)
        criteria_ready = summary["criteria_ready"]
        criteria_attention = summary["criteria_needing_attention"]
        evidence_items = summary["evidence_items"]
        mapped_detections = summary["mapped_detections"]

        return {
            "key": "initial_security_review_reply",
            "title": "Initial security review reply",
            "audience": "Sales, solutions engineering, and customer success",
            "use_when": "Use this when a prospect asks for a concise security overview before sending a full questionnaire.",
            "subject": "SentinelGrid security review materials",
            "body": (
                f"Thanks for the security review request. SentinelGrid uses a live trust-evidence layer rather than a one-off slide deck. "
                f"Right now the platform shows {criteria_ready} criteria ready for export, {criteria_attention} criteria still needing attention, "
                f"{mapped_detections} mapped detections, and {evidence_items} evidence items that can be packaged for review. "
                f"We recommend starting with the Customer Security Review Pack for the high-level overview, then moving to the Audit Readiness Pack "
                f"or Evidence Attachment Export if your team wants deeper control or proof-level detail."
            ),
            "recommended_artifacts": self._artifacts(
                "smb_customer_security_review_pack",
                "smb_audit_readiness_pack",
            ),
            "talking_points": [
                "The trust packet is generated from live product evidence, not static slideware.",
                "Expiring share links are available so sales can share a current packet without distributing stale files.",
                "Open gaps are surfaced explicitly instead of hidden behind generic marketing language.",
            ],
            "follow_up": [
                "Attach the Customer Security Review Pack first.",
                "If the buyer asks for deeper detail, follow with the Audit Readiness Pack.",
            ],
        }

    def _build_questionnaire_handoff_template(self, dashboard: dict[str, Any]) -> dict[str, Any]:
        summary = self._build_template_summary(dashboard)

        return {
            "key": "questionnaire_handoff_reply",
            "title": "Questionnaire handoff reply",
            "audience": "Sales and deal desk workflows",
            "use_when": "Use this when the buyer sends a vendor questionnaire and you need to explain how SentinelGrid will answer it quickly.",
            "subject": "SentinelGrid questionnaire response workflow",
            "body": (
                f"We can work through your questionnaire using SentinelGrid’s live questionnaire-assist workflow. "
                f"The current compliance layer maps {summary['mapped_detections']} detections, {summary['control_checks']} control checks, "
                f"and {summary['evidence_items']} evidence items into response-ready trust artifacts. "
                f"Our team typically starts with the Customer Security Review Pack, drafts question-by-question responses in the questionnaire-assist flow, "
                f"and then attaches the Evidence Attachment Export when specific proof is requested."
            ),
            "recommended_artifacts": self._artifacts(
                "smb_customer_security_review_pack",
                "smb_evidence_attachment_export",
            ),
            "talking_points": [
                "Questionnaire answers are drafted from the live compliance payload, not copied from a generic answer bank.",
                "The same workflow highlights supporting criteria and signals for follow-up.",
                "The evidence export is intended for proof-heavy follow-up items rather than the first reply.",
            ],
            "follow_up": [
                "Run questionnaire assist with the buyer’s questions.",
                "Share the Evidence Attachment Export only for items that require proof-level backup.",
            ],
        }

    def _build_evidence_follow_up_template(self, dashboard: dict[str, Any]) -> dict[str, Any]:
        summary = self._build_template_summary(dashboard)
        criteria_attention = summary["criteria_needing_attention"]

        return {
            "key": "evidence_follow_up_reply",
            "title": "Evidence follow-up reply",
            "audience": "Sales engineers and trust-response owners",
            "use_when": "Use this when a reviewer asks for supporting artifacts after the first trust packet.",
            "subject": "SentinelGrid supporting evidence export",
            "body": (
                f"Following up with supporting evidence from the live SentinelGrid compliance workflow. "
                f"The current trust layer contains {summary['evidence_items']} evidence items and {summary['criteria_ready']} criteria that are ready for export. "
                f"We recommend sending the Evidence Attachment Export for proof-level follow-up. "
                f"{'There are still open criteria that need manual context, so we call those out directly in the packet.' if criteria_attention else 'The current packet does not show open criteria requiring manual qualification.'}"
            ),
            "recommended_artifacts": self._artifacts(
                "smb_evidence_attachment_export",
                "smb_audit_readiness_pack",
            ),
            "talking_points": [
                "Use the evidence export for attachments and screenshots, not for the first-pass overview.",
                "The audit pack is the better follow-on when the reviewer wants a broader control story.",
                "Template language should stay transparent if open criteria still need attention.",
            ],
            "follow_up": [
                "Attach the Evidence Attachment Export.",
                "If the reviewer asks how the evidence maps into the larger program, follow with the Audit Readiness Pack.",
            ],
        }

    def _build_framework_positioning_template(self, dashboard: dict[str, Any]) -> dict[str, Any]:
        summary = self._build_template_summary(dashboard)
        pack_states = summary["framework_pack_states"]
        soc2_state = pack_states.get("soc2", "live")
        iso_state = pack_states.get("iso27001", "starter")

        return {
            "key": "framework_positioning_reply",
            "title": "Framework positioning reply",
            "audience": "Sales and partnership conversations",
            "use_when": "Use this when a buyer asks how SentinelGrid supports SOC 2 today and ISO 27001 next.",
            "subject": "SentinelGrid framework support overview",
            "body": (
                f"SentinelGrid currently supports a {soc2_state} SOC 2 starter pack backed by the live readiness and reporting layer, "
                f"and an {iso_state} ISO 27001 starter pack that uses the same trust evidence to accelerate early Annex A and ISMS conversations. "
                f"The current environment shows an overall readiness score of {summary['overall_score']}/100 with {summary['criteria_ready']} criteria ready for export. "
                f"For most deals, we position SOC 2 as the active reporting workflow and ISO 27001 as a guided starter pack built on the same evidence base."
            ),
            "recommended_artifacts": self._artifacts(
                "smb_customer_security_review_pack",
                "smb_audit_readiness_pack",
            ),
            "talking_points": [
                "SOC 2 is presented as a live pack tied to current product evidence.",
                "ISO 27001 is positioned honestly as a starter pack, not as a full Annex A tracker.",
                "Both motions reuse the same exports, questionnaire assist, and evidence workflows.",
            ],
            "follow_up": [
                "Use the SOC 2 and ISO 27001 starter-pack cards on the compliance dashboard in live demos.",
                "If the buyer asks for evidence, move to the trust kit and questionnaire-assist workflow.",
            ],
        }

    def _artifacts(self, *template_keys: str) -> list[dict[str, str]]:
        return [
            {
                "template_key": template_key,
                "reason": TRUST_ARTIFACT_REASONS[template_key],
            }
            for template_key in template_keys
        ]

    def _confidence(
        self,
        category: str,
        controls: list[dict[str, Any]],
        signals: list[dict[str, Any]],
    ) -> str:
        if controls and signals:
            return "high"
        if controls or signals:
            return "medium"
        if category == "general_security_review":
            return "medium"
        return "low"

    @staticmethod
    def _matches_any(value: str, keywords: list[str]) -> bool:
        normalized = value.lower()
        return any(keyword in normalized for keyword in keywords)
