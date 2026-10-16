"""Deterministic response-pack matching shared by SOC planners."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResponsePackDefinition:
    id: str
    label: str
    summary: str
    operator_goal: str
    recommended_owner: str
    recommended_sla: str
    story_domains: tuple[str, ...]
    attack_patterns: tuple[str, ...]
    playbook_keys: tuple[str, ...]
    signal_categories: tuple[str, ...]
    keywords: tuple[str, ...]
    first_moves: tuple[str, ...]
    success_checks: tuple[str, ...]
    finding_types: tuple[str, ...] = ()
    mitre_tactics: tuple[str, ...] = ()


@dataclass(frozen=True)
class MatchedResponsePack:
    pack: ResponsePackDefinition
    score: int
    reasons: list[str] = field(default_factory=list)
    playbooks: list[dict[str, Any]] = field(default_factory=list)
    primary_playbook: dict[str, Any] | None = None


@dataclass(frozen=True)
class ResponsePackContext:
    categories: list[str]
    finding_types: list[str]
    domains: set[str]
    text: str
    playbook_tokens: list[str]
    mitre_tokens: list[str]


RESPONSE_PACKS: tuple[ResponsePackDefinition, ...] = (
    ResponsePackDefinition(
        id="account_takeover",
        label="Account takeover containment",
        summary="Contain risky sign-ins, session abuse, password-spray activity, and MFA bypass attempts before they turn into broader identity compromise.",
        operator_goal="Confirm the identity blast radius, contain live access, and hand off owner actions in one flow.",
        recommended_owner="Identity admin or help desk lead",
        recommended_sla="4 hour containment target",
        story_domains=("identity", "endpoint", "security"),
        attack_patterns=("account takeover", "password spray", "mfa fatigue", "suspicious login"),
        playbook_keys=("ACCOUNT-COMPROMISE", "PASSWORD-SPRAY", "MFA-BYPASS", "SUSPICIOUS-LOGIN", "SUSPICIOUS_LOGIN_BASIC"),
        signal_categories=("identity", "iam", "authentication", "access", "suspicious_login"),
        keywords=("account compromise", "suspicious login", "impossible travel", "password spray", "mfa fatigue", "session hijack", "risky sign-in"),
        mitre_tactics=("Credential Access", "Initial Access", "Persistence"),
        first_moves=(
            "Validate the impacted identity, session history, and recently elevated access.",
            "Require credential reset or revoke the active session if the account is still exposed.",
            "Assign ownership and confirm downstream ticket routing before the case stalls.",
        ),
        success_checks=(
            "The risky identity has a named owner and an SLA.",
            "Live sessions are revoked or the identity is otherwise contained.",
            "Follow-up review is scheduled for related admin roles and affected apps.",
        ),
    ),
    ResponsePackDefinition(
        id="phishing_mailbox_compromise",
        label="Mailbox compromise response",
        summary="Handle phishing-driven mailbox compromise, malicious inbox rules, and email-delivered credential theft with a repeatable SMB play.",
        operator_goal="Contain the mailbox, scope message spread, and coordinate user follow-up quickly.",
        recommended_owner="Email admin or help desk lead",
        recommended_sla="Same-day containment target",
        story_domains=("identity", "application", "security"),
        attack_patterns=("phishing", "mailbox compromise", "malicious inbox rule", "credential theft"),
        playbook_keys=("PHISH-USER", "PHISH-GATEWAY"),
        signal_categories=("email", "phishing", "identity", "application"),
        keywords=("phish", "mailbox", "inbox rule", "oauth consent", "email compromise", "malicious email"),
        mitre_tactics=("Initial Access", "Collection"),
        first_moves=(
            "Confirm the affected mailbox, forwarding rules, and high-risk message activity.",
            "Isolate the compromised user path by rotating credentials and reviewing granted apps.",
            "Coordinate user communications and ticket handoff while preserving evidence.",
        ),
        success_checks=(
            "The compromised mailbox path is contained.",
            "Forwarding or rule abuse is reviewed and cleaned up.",
            "The user-facing follow-up and downstream ticket are already assigned.",
        ),
    ),
    ResponsePackDefinition(
        id="ransomware_containment",
        label="Ransomware containment",
        summary="Drive a fast endpoint-led response for ransomware behaviors, malware execution, beaconing, or an EDR control gap.",
        operator_goal="Isolate the endpoint path, preserve evidence, and move from triage into containment without delay.",
        recommended_owner="Endpoint lead or MSP operator",
        recommended_sla="2 hour containment target",
        story_domains=("endpoint", "identity", "security"),
        attack_patterns=("ransomware", "malware", "beaconing", "agent offline"),
        playbook_keys=("MALWARE-CONTAIN", "ENDPOINT-ISOLATE", "AGENT-OFFLINE", "C2/BEACON"),
        signal_categories=("endpoint", "malware", "ransomware", "edr", "host"),
        keywords=("ransomware", "encryption", "beacon", "malware", "endpoint isolate", "edr offline", "lateral movement"),
        mitre_tactics=("Execution", "Impact", "Command and Control"),
        first_moves=(
            "Identify the affected host and any linked identities before containment starts.",
            "Isolate or contain the endpoint path and escalate when an agent or control is offline.",
            "Capture analyst notes and ownership so containment does not remain tribal knowledge.",
        ),
        success_checks=(
            "The endpoint path is isolated or otherwise contained.",
            "Owner, SLA, and downstream ticket are set for follow-through.",
            "Related identities or additional hosts are reviewed before closing the incident.",
        ),
    ),
    ResponsePackDefinition(
        id="cloud_exposure",
        label="Cloud exposure hardening",
        summary="Use one saved response pack for public storage, internet-exposed data paths, disabled logging, and high-risk cloud misconfigurations.",
        operator_goal="Reduce exposure fast, record the owner, and keep the fix tied to the same evidence story.",
        recommended_owner="Cloud platform owner",
        recommended_sla="24 hour remediation target",
        story_domains=("cloud", "security"),
        attack_patterns=("public storage", "public database", "logging disabled", "privileged pod"),
        playbook_keys=("CLOUD-PUBLIC-STORAGE", "DB-PUBLIC-EXPOSED", "LOGGING-DISABLED", "K8S-PRIV-POD"),
        signal_categories=("cloud", "storage", "database", "kubernetes", "network", "data"),
        keywords=("public bucket", "public storage", "public database", "logging disabled", "privileged pod", "internet exposed"),
        mitre_tactics=("Discovery", "Collection"),
        first_moves=(
            "Confirm the exposed resource, tenant owner, and any linked identity or ticket context.",
            "Prioritize public data paths and disabled telemetry before lower-risk posture gaps.",
            "Create a fix owner and due date so posture findings become actual operator work.",
        ),
        success_checks=(
            "The exposed cloud path has an owner and due date.",
            "A direct remediation path or ticket is already open.",
            "Supporting evidence is ready for trust or audit follow-up if needed.",
        ),
    ),
    ResponsePackDefinition(
        id="secret_exposure",
        label="Secret and code exposure",
        summary="Respond to leaked secrets, high-risk IaC findings, and application-side exposure without splitting the operator story across tools.",
        operator_goal="Contain exposed credentials, route code or IaC fixes, and preserve one evidence trail.",
        recommended_owner="AppSec or platform engineering lead",
        recommended_sla="1 business day remediation target",
        story_domains=("application", "cloud", "security"),
        attack_patterns=("secret exposure", "high-risk IaC", "code leak", "build pipeline risk"),
        playbook_keys=("SECRET-EXPOSURE", "IAC-HIGH-RISK", "SAST-HIGH"),
        signal_categories=("application", "repo", "secret", "iac", "code"),
        keywords=("secret exposure", "hardcoded secret", "repository leak", "iac risk", "pipeline secret", "sast high"),
        mitre_tactics=("Credential Access", "Initial Access"),
        first_moves=(
            "Confirm which secret, repo, or build path is exposed and who owns the fix.",
            "Rotate or revoke exposed credentials before backlog cleanup begins.",
            "Send the right engineering handoff with evidence already attached.",
        ),
        success_checks=(
            "Exposed secrets are rotated or revoked.",
            "The engineering owner has a routed task with linked evidence.",
            "Residual scanning work is tracked to closure, not left as a note.",
        ),
    ),
    ResponsePackDefinition(
        id="ai_prompt_injection_containment",
        label="AI prompt injection containment",
        summary="Respond to prompt injection, jailbreak, and guardrail-bypass activity before unsafe prompts turn into tool execution or data exposure.",
        operator_goal="Confirm the risky prompt path, review downstream tool exposure, and contain repeated abuse quickly.",
        recommended_owner="AI app owner or security lead",
        recommended_sla="4 hour containment target",
        story_domains=("ai", "application", "security"),
        attack_patterns=("prompt injection", "jailbreak", "guardrail bypass", "unsafe prompt"),
        playbook_keys=("AI-PROMPT-INJECTION", "AI-JAILBREAK-BURST"),
        signal_categories=("prompt_injection", "jailbreak", "guardrail_bypass"),
        keywords=("prompt injection", "jailbreak", "unsafe prompt", "guardrail bypass", "adversarial prompt", "system prompt"),
        first_moves=(
            "Confirm the AI app, user path, and the exact prompt or conversation that triggered the finding.",
            "Review whether tools, retrieval, or downstream actions were reachable from the abused prompt path.",
            "Route the case to the AI owner with containment guidance before the same prompt pattern is reused.",
        ),
        success_checks=(
            "The risky prompt path has a named owner and a due date.",
            "Any exposed tool or downstream execution path is contained or explicitly reviewed.",
            "The operator story shows the prompt context, owner handoff, and follow-up action.",
        ),
        finding_types=("prompt_injection",),
        mitre_tactics=("Initial Access", "Execution"),
    ),
    ResponsePackDefinition(
        id="ai_data_leakage_response",
        label="AI data leakage response",
        summary="Use one saved motion for sensitive data exposure, secret leakage, and policy misses that let customer data reach external models.",
        operator_goal="Confirm what data left the boundary, contain the prompt path, and capture the evidence for policy and trust follow-up.",
        recommended_owner="AI app owner or privacy lead",
        recommended_sla="Same-day review target",
        story_domains=("ai", "application", "security"),
        attack_patterns=("sensitive data exposure", "secret leakage", "pii leakage", "external llm exposure"),
        playbook_keys=("AI-DATA-LEAK",),
        signal_categories=("sensitive_data_exposure", "data_leak", "secret_exposure", "pii_exposure"),
        keywords=("sensitive data", "data leak", "secret material", "customer data", "pii", "credential leak", "model output"),
        first_moves=(
            "Confirm which AI app, provider, and user path sent sensitive data outside the expected boundary.",
            "Contain the prompt path or provider route before the same data class is sent again.",
            "Attach the evidence trail so policy owners, privacy, and customer-trust teams can reuse the same story.",
        ),
        success_checks=(
            "The exposed AI path has a named owner and a due date.",
            "The affected prompt or provider route is contained, blocked, or otherwise reviewed.",
            "Evidence is ready for downstream trust, audit, or customer security-review follow-up.",
        ),
        finding_types=("sensitive_data_exposure",),
        mitre_tactics=("Collection", "Exfiltration"),
    ),
    ResponsePackDefinition(
        id="ai_policy_and_tool_misuse",
        label="AI policy and tool misuse",
        summary="Handle blocked policy violations, unsafe tool actions, and model misuse with one operator pack tied to the AI control plane.",
        operator_goal="Decide whether the policy is correct, whether the app is misconfigured, and who owns the fix before violations become normal noise.",
        recommended_owner="AI platform owner or security lead",
        recommended_sla="1 business day remediation target",
        story_domains=("ai", "application", "security"),
        attack_patterns=("policy violation", "unsafe tool action", "tool misuse", "model abuse"),
        playbook_keys=("AI-POLICY-VIOLATION", "AI-UNSAFE-TOOL-ACTION", "AI-TOOL-CALL-ANOMALY"),
        signal_categories=("policy_violation", "unsafe_tool_action", "tool_call_anomaly"),
        keywords=("policy violation", "unsafe tool", "tool misuse", "tool call", "guardrail policy", "blocked model", "unapproved action"),
        first_moves=(
            "Confirm whether the event represents a true policy violation, an unsafe tool call, or a guardrail tuning gap.",
            "Review the app policy and owner workflow before operators normalize the same blocked behavior.",
            "Capture the policy decision, owner, and follow-up task in the same story used for the rest of the platform.",
        ),
        success_checks=(
            "The violated policy or unsafe tool path has an explicit owner.",
            "The fix is routed as a policy change, app change, or operator exception rather than a vague note.",
            "The same issue can be tracked across runtime events, incidents, and leadership reporting.",
        ),
        finding_types=("policy_violation",),
        mitre_tactics=("Defense Evasion", "Execution"),
    ),
)


def normalize_token(value: Any) -> str:
    if value is None:
        return ""
    normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in str(value))
    return " ".join(normalized.split())


def unique_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = normalize_token(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    return ordered


def _string_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (list, tuple, set)):
        return [str(item) for item in values if item is not None]
    return [str(values)]


def _record_labels(values: Any, candidate_keys: tuple[str, ...]) -> list[str]:
    labels: list[str] = []
    if not isinstance(values, list):
        return labels
    for item in values:
        if isinstance(item, dict):
            for key in candidate_keys:
                if item.get(key):
                    labels.append(str(item[key]))
        elif item is not None:
            labels.append(str(item))
    return labels


def playbook_search_text(playbook: dict[str, Any]) -> str:
    return " ".join(
        unique_strings(
            [
                playbook.get("id"),
                playbook.get("name"),
                playbook.get("playbook_key"),
                playbook.get("category"),
                *(_string_list(playbook.get("tags"))),
            ]
        )
    )


def match_pack_playbooks(pack: ResponsePackDefinition, playbooks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matched = [
        playbook
        for playbook in playbooks
        if any(normalize_token(token) in playbook_search_text(playbook) for token in pack.playbook_keys)
    ]
    return sorted(matched, key=lambda playbook: playbook_rank(pack, playbook))


def playbook_rank(pack: ResponsePackDefinition, playbook: dict[str, Any]) -> int:
    primary = normalize_token(playbook.get("playbook_key") or playbook.get("name"))
    for index, token in enumerate(pack.playbook_keys):
        if normalize_token(token) in primary:
            return index
    return 10_000


def score_pack(pack: ResponsePackDefinition, context: ResponsePackContext) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    finding_type_match = next(
        (
            token
            for token in pack.finding_types
            if any(candidate.find(normalize_token(token)) >= 0 for candidate in context.finding_types)
        ),
        None,
    )
    if finding_type_match:
        score += 5
        reasons.append(f"{finding_type_match.replace('_', ' ')} finding")

    playbook_match = next(
        (
            token
            for token in pack.playbook_keys
            if any(candidate.find(normalize_token(token)) >= 0 for candidate in context.playbook_tokens)
        ),
        None,
    )
    if playbook_match:
        score += 6
        reasons.append(f"{playbook_match.lower().replace('-', ' ')} mapping")

    category_match = next(
        (
            token
            for token in pack.signal_categories
            if any(candidate.find(normalize_token(token)) >= 0 for candidate in context.categories)
        ),
        None,
    )
    if category_match:
        score += 3
        reasons.append(f"{category_match.replace('_', ' ')} signal")

    keyword_matches = [keyword for keyword in pack.keywords if normalize_token(keyword) in context.text]
    if keyword_matches:
        score += min(3, len(keyword_matches))
        reasons.append(f"{keyword_matches[0]} indicator")

    domain_match = next((domain for domain in pack.story_domains if normalize_token(domain) in context.domains), None)
    if domain_match:
        score += 2
        reasons.append(f"{domain_match} context")

    tactic_match = next(
        (
            tactic
            for tactic in pack.mitre_tactics
            if any(candidate.find(normalize_token(tactic)) >= 0 for candidate in context.mitre_tokens)
        ),
        None,
    )
    if tactic_match:
        score += 1
        reasons.append(f"{tactic_match.lower()} tactic")

    return score, list(dict.fromkeys(reasons))[:3]


def build_incident_context(incident: dict[str, Any]) -> ResponsePackContext:
    raw_payload = incident.get("raw_payload") or {}
    finding_type = (
        (raw_payload.get("finding") or {}).get("type")
        or (raw_payload.get("sg") or {}).get("finding_type")
        or incident.get("finding_type")
    )

    related_titles = []
    for item in incident.get("related_detections") or []:
        if isinstance(item, dict):
            related_titles.extend([item.get("id"), item.get("title")])
        elif item is not None:
            related_titles.append(str(item))

    return ResponsePackContext(
        categories=unique_strings(
            [
                incident.get("category"),
                incident.get("source"),
                incident.get("incident_type"),
                raw_payload.get("category"),
                raw_payload.get("incident_type"),
                (raw_payload.get("sg") or {}).get("category"),
                raw_payload.get("alert_type"),
                finding_type,
            ]
        ),
        finding_types=unique_strings([finding_type]),
        domains=set(unique_strings(_string_list(incident.get("story_domains")))),
        text=" ".join(
            unique_strings(
                [
                    incident.get("title"),
                    incident.get("description"),
                    raw_payload.get("summary"),
                    raw_payload.get("reason"),
                    raw_payload.get("event_type"),
                    raw_payload.get("violation_reason"),
                    ((raw_payload.get("ai") or {}).get("app_id")),
                    ((raw_payload.get("ai") or {}).get("provider")),
                    ((raw_payload.get("ai") or {}).get("model")),
                    ((raw_payload.get("ai") or {}).get("violation_reason")),
                    finding_type,
                    incident.get("assigned_to"),
                    incident.get("assignee"),
                    incident.get("recommended_playbook"),
                    incident.get("recommended_playbook_key"),
                    *_record_labels(incident.get("entities"), ("label", "name", "value", "id")),
                    *_record_labels(incident.get("evidence"), ("title", "label", "description", "id")),
                    *related_titles,
                ]
            )
        ),
        playbook_tokens=unique_strings(
            [
                incident.get("recommended_playbook"),
                incident.get("recommended_playbook_id"),
                incident.get("recommended_playbook_key"),
                raw_payload.get("recommended_playbook"),
                raw_payload.get("recommended_playbook_id"),
                raw_payload.get("recommended_playbook_key"),
                raw_payload.get("playbook_id"),
                (raw_payload.get("sg") or {}).get("playbook_id"),
            ]
        ),
        mitre_tokens=unique_strings(
            [
                *_string_list(incident.get("mitre_tactics")),
                *_string_list(incident.get("mitre_techniques")),
                *_string_list(raw_payload.get("mitre_tactics")),
                *_string_list(raw_payload.get("mitre_techniques")),
            ]
        ),
    )


def match_response_packs_for_incident(
    incident: dict[str, Any],
    playbooks: list[dict[str, Any]] | None = None,
) -> list[MatchedResponsePack]:
    playbooks = playbooks or []
    context = build_incident_context(incident)

    matches = []
    for pack in RESPONSE_PACKS:
        pack_playbooks = match_pack_playbooks(pack, playbooks)
        score, reasons = score_pack(pack, context)
        if pack_playbooks:
            score += 1
        if score >= 3:
            matches.append(
                MatchedResponsePack(
                    pack=pack,
                    score=score,
                    reasons=reasons,
                    playbooks=pack_playbooks,
                    primary_playbook=pack_playbooks[0] if pack_playbooks else None,
                )
            )

    return sorted(matches, key=lambda item: (item.score, len(item.playbooks)), reverse=True)
