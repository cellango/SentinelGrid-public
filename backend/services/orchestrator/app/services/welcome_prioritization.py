"""Backend prioritization helpers for the welcome dashboard."""

from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import quote


_SEVERITY_WEIGHT = {
    "critical": 400,
    "high": 300,
    "medium": 200,
    "low": 100,
    "info": 50,
}

_DOMAIN_LABEL = {
    "cloud": "Cloud",
    "data": "Data",
    "identity": "Identity",
    "endpoint": "Endpoint",
    "app": "Application",
    "ai": "AI",
}

_DOMAIN_HREF = {
    "cloud": "/dashboard/compliance",
    "data": "/dashboard/compliance",
    "identity": "/dashboard/iam/people",
    "endpoint": "/dashboard/endpoint-protection",
    "app": "/dashboard/posture",
    "ai": "/dashboard/compliance/ai-activity",
}


def _severity_rank(severity: str | None) -> int:
    return _SEVERITY_WEIGHT.get((severity or "medium").lower(), 150)


def _domain_label(domain: str | None) -> str:
    return _DOMAIN_LABEL.get((domain or "").lower(), "Security")


def _domain_href(domain: str | None) -> str:
    return _DOMAIN_HREF.get((domain or "").lower(), "/dashboard/posture")


def _health_status(health_payload: Any) -> str:
    if not isinstance(health_payload, dict):
        return "unknown"
    return str(health_payload.get("status") or health_payload.get("health_status") or "unknown").lower()


def _integration_status(connected: bool, health_payload: Any = None) -> str:
    status = _health_status(health_payload)
    if connected and status in {"healthy", "connected", "ok", "unknown"}:
        return "connected"
    if connected or status in {"degraded", "partial", "warning", "unknown", "testing"}:
        return "partial"
    return "disconnected"


def build_cloud_posture_snapshot(posture_score: Dict[str, Any]) -> Dict[str, Any]:
    """Shape cloud posture summary from the posture scoring payload."""
    domain_scores = posture_score.get("domain_scores") or {}
    coverage_details = posture_score.get("coverage_details") or {}
    cloud_scores = domain_scores.get("cloud") or {}
    counts = cloud_scores.get("counts") or {}
    top_risks = posture_score.get("top_risks") or []

    biggest_risk = next(
        (risk for risk in top_risks if risk.get("domain") in {"cloud", "data"}),
        top_risks[0] if top_risks else None,
    )
    total_issues = int(cloud_scores.get("open") or sum(int(value or 0) for value in counts.values()))
    cloud_coverage = coverage_details.get("cloud") or {}
    cloud_accounts_connected = int(cloud_coverage.get("total") or 0)

    biggest_risk_payload = {
        "title": biggest_risk.get("title") if biggest_risk else "No major cloud findings yet",
        "description": (
            "SentinelGrid will surface the first cloud exposure here once posture findings arrive."
            if not biggest_risk
            else (
                "Highest-weight cloud or data exposure based on the current posture model."
                + (
                    f" Asset criticality is tagged {biggest_risk['criticality']}."
                    if biggest_risk.get("criticality")
                    else ""
                )
                + (
                    f" Data classification is {biggest_risk['data_classification']}."
                    if biggest_risk.get("data_classification")
                    else ""
                )
            )
        ),
        "severity": (biggest_risk.get("severity") if biggest_risk else "low") or "low",
    }

    return {
        "cloud_accounts_connected": cloud_accounts_connected,
        "critical_misconfigs": int(counts.get("critical") or 0),
        "high_misconfigs": int(counts.get("high") or 0),
        "medium_misconfigs": int(counts.get("medium") or 0),
        "low_misconfigs": int(counts.get("low") or 0),
        "total_issues": total_issues,
        "biggest_risk": biggest_risk_payload,
        "posture_score": int(cloud_scores.get("score_adjusted") or cloud_scores.get("score") or 0),
    }


def build_dashboard_health(
    onboarding_status: Dict[str, Any],
    posture_score: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a backend-derived health summary for the welcome dashboard."""
    coverage_details = posture_score.get("coverage_details") or {}
    endpoint_coverage = coverage_details.get("endpoint") or {}
    endpoint_total = int(endpoint_coverage.get("total") or 0)
    endpoint_online = int(endpoint_coverage.get("scanned") or 0)
    endpoint_pct = round((endpoint_online / endpoint_total) * 100) if endpoint_total > 0 else 0

    integrations = {
        "aws": _integration_status(
            bool(onboarding_status.get("cloud_connected")),
            onboarding_status.get("cloud_health"),
        ),
        "idp": _integration_status(bool(onboarding_status.get("idp_connected"))),
        "endpoint": _integration_status(
            bool(onboarding_status.get("endpoint_deployed")),
            {"status": "healthy" if endpoint_pct >= 80 else "partial" if endpoint_pct > 0 else "unknown"},
        ),
    }

    health_status = "healthy"
    if integrations["aws"] == "disconnected" or integrations["idp"] == "disconnected":
        health_status = "degraded"
    if integrations["aws"] == "disconnected" and integrations["idp"] == "disconnected":
        health_status = "critical"

    return {
        "log_usage": {
            "current_gb_per_day": 0.0,
            "limit_gb_per_day": 100.0,
            "percentage_used": 0.0,
        },
        "agents": {
            "online": endpoint_online,
            "total": endpoint_total,
            "percentage_online": endpoint_pct,
        },
        "integrations": integrations,
        "health_status": health_status,
    }


def _risk_description(risk: Dict[str, Any]) -> str:
    parts: List[str] = []
    if risk.get("exposed"):
        parts.append("The affected asset appears externally exposed.")
    if risk.get("criticality"):
        parts.append(f"Criticality is tagged {risk['criticality']}.")
    if risk.get("data_classification"):
        parts.append(f"Data classification is {risk['data_classification']}.")
    parts.append("This is one of the highest-weight findings in the current posture model.")
    return " ".join(parts)


def _normalize_priority(value: str | None) -> str:
    priority = (value or "medium").lower()
    return priority if priority in {"critical", "high", "medium", "low"} else "medium"


def _playbook_deeplink(playbook_id: str) -> str:
    return f"/dashboard/playbooks?playbook_id={quote(playbook_id)}"


def _remediation_step(title: str, description: str) -> Dict[str, str]:
    return {
        "title": title,
        "description": description,
    }


def _remediation_prompt(
    class_id: str,
    title: str,
    owner: str,
    why_now: str,
    steps: List[Dict[str, str]],
    success_criteria: str,
) -> Dict[str, Any]:
    return {
        "class_id": class_id,
        "title": title,
        "owner": owner,
        "why_now": why_now,
        "steps": steps,
        "success_criteria": success_criteria,
    }


def _cloud_playbook_id(posture_score: Dict[str, Any]) -> str | None:
    top_risks = posture_score.get("top_risks") or []
    cloud_risk = next(
        (risk for risk in top_risks if str(risk.get("domain") or "").lower() in {"cloud", "data"}),
        None,
    )
    title = str(cloud_risk.get("title") or "").lower() if cloud_risk else ""
    if any(token in title for token in {"bucket", "storage", "object", "public storage"}):
        return "CLOUD-PUBLIC-STORAGE"
    if any(token in title for token in {"security group", "sg ", "0.0.0.0", "firewall", "ingress"}):
        return "SG-OPEN-CRITICAL"
    return None


def build_first_value_findings(
    tenant_id: str,
    posture_score: Dict[str, Any],
    people_access: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Rank the first findings to surface on the welcome dashboard."""
    del tenant_id  # Tenant-aware ranking can expand later without changing the public contract.

    candidates: List[Dict[str, Any]] = []
    top_risks = posture_score.get("top_risks") or []
    for risk in top_risks[:5]:
        severity = _normalize_priority(risk.get("severity"))
        domain = (risk.get("domain") or "cloud").lower()
        candidates.append(
            {
                "id": f"risk-{risk.get('id') or risk.get('title')}",
                "priority": severity,
                "eyebrow": f"{severity.title()} {_domain_label(domain)} finding",
                "title": risk.get("title") or "Prioritized finding",
                "description": _risk_description(risk),
                "href": _domain_href(domain),
                "cta_label": "Review finding",
                "category": domain,
                "_rank": _severity_rank(severity)
                + (40 if risk.get("exposed") else 0)
                + (20 if risk.get("criticality") == "critical" else 0),
            }
        )

    mfa_missing = int(people_access.get("mfa_missing_count") or 0)
    users_admins = int(people_access.get("users_admins") or 0)
    if mfa_missing > 0:
        admin_gap = min(mfa_missing, users_admins)
        candidates.append(
            {
                "id": "identity-mfa-gap",
                "priority": "high" if admin_gap else "medium",
                "eyebrow": "Identity gap",
                "title": (
                    f"{admin_gap} admin account{'s' if admin_gap != 1 else ''} missing MFA"
                    if admin_gap
                    else f"{mfa_missing} user account{'s' if mfa_missing != 1 else ''} missing MFA"
                ),
                "description": (
                    "Admin MFA gaps are one of the fastest, highest-signal fixes for a newly connected tenant."
                    if admin_gap
                    else "SentinelGrid detected user accounts without MFA. Close those gaps before expanding coverage."
                ),
                "href": "/dashboard/iam/people",
                "cta_label": "Review users",
                "category": "identity",
                "_rank": 360 + min(mfa_missing, 25) + (40 if admin_gap else 0),
            }
        )

    anomalies_critical = int(people_access.get("anomalies_critical") or 0)
    if anomalies_critical > 0:
        candidates.append(
            {
                "id": "identity-critical-anomalies",
                "priority": "critical",
                "eyebrow": "Identity anomaly",
                "title": f"{anomalies_critical} critical identity anomal{'y' if anomalies_critical == 1 else 'ies'} need review",
                "description": "Identity telemetry has already flagged high-severity anomalies that should be triaged before routine hygiene work.",
                "href": "/dashboard/iam/security-events",
                "cta_label": "Open identity events",
                "category": "identity",
                "_rank": 430 + min(anomalies_critical, 10) * 5,
            }
        )

    candidates.sort(key=lambda item: item["_rank"], reverse=True)

    deduped: List[Dict[str, Any]] = []
    seen_titles: set[str] = set()
    for candidate in candidates:
        title = candidate["title"].lower()
        if title in seen_titles:
            continue
        seen_titles.add(title)
        item = dict(candidate)
        item.pop("_rank", None)
        deduped.append(item)
        if len(deduped) == 3:
            break

    return deduped


def build_recommendations(
    posture_score: Dict[str, Any],
    people_access: Dict[str, Any],
    onboarding_status: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build prioritized welcome recommendations from real backend state."""
    candidates: List[Dict[str, Any]] = []
    coverage_details = posture_score.get("coverage_details") or {}
    endpoint_coverage = coverage_details.get("endpoint") or {}
    endpoint_total = int(endpoint_coverage.get("total") or 0)
    endpoint_online = int(endpoint_coverage.get("scanned") or 0)
    endpoint_pct = (endpoint_online / endpoint_total) if endpoint_total > 0 else 0.0
    services_selected = onboarding_status.get("services_selected") or {}
    ticketing_health_status = _health_status(onboarding_status.get("ticketing_health"))
    cloud_posture = build_cloud_posture_snapshot(posture_score)
    cloud_playbook_id = _cloud_playbook_id(posture_score)

    def add_candidate(
        rec_id: str,
        rank: int,
        priority: str,
        title: str,
        description: str,
        estimated_time_minutes: int,
        category: str,
        finding_class: str,
        remediation: Dict[str, Any],
        actions: List[Dict[str, Any]],
    ) -> None:
        candidates.append(
            {
                "id": rec_id,
                "priority": _normalize_priority(priority),
                "title": title,
                "description": description,
                "estimated_time_minutes": estimated_time_minutes,
                "actions": actions,
                "category": category,
                "finding_class": finding_class,
                "remediation": remediation,
                "_rank": rank,
            }
        )

    if not onboarding_status.get("idp_connected"):
        add_candidate(
            "activation-idp",
            520,
            "high",
            "Connect Microsoft 365 / Entra first",
            "Identity telemetry unlocks MFA gaps, risky sign-ins, and admin exposure. It is still the fastest path to a useful first finding.",
            10,
            "activation",
            "activation.identity_connection",
            _remediation_prompt(
                "activation.identity_connection",
                "Identity connection workflow",
                "Security admin",
                "Without identity data, SentinelGrid cannot rank MFA gaps, risky sign-ins, or privileged-user issues for the first-week queue.",
                [
                    _remediation_step("Connect Microsoft 365 / Entra", "Authorize the tenant and complete the identity setup step so users, admins, and sign-in telemetry start syncing."),
                    _remediation_step("Validate imported users and admins", "Confirm that privileged accounts are visible so the first findings represent real operator risk."),
                    _remediation_step("Wait for the first identity findings", "Return to the welcome queue after sync completes to review MFA gaps and anomalies."),
                ],
                "The People & Access view shows real users and admins, and the welcome dashboard begins surfacing identity findings.",
            ),
            [
                {"label": "Connect identity", "type": "view_details", "endpoint": "/onboarding?step=1"},
                {"label": "Open onboarding", "type": "view_details", "endpoint": "/onboarding"},
            ],
        )

    if not onboarding_status.get("cloud_connected"):
        add_candidate(
            "activation-cloud",
            500,
            "high",
            "Connect AWS next",
            "Cloud posture findings, asset coverage, and attack-surface evidence all depend on the first cloud account connection.",
            15,
            "activation",
            "activation.cloud_connection",
            _remediation_prompt(
                "activation.cloud_connection",
                "Cloud connection workflow",
                "Cloud platform owner",
                "The cloud account connection is what turns posture scoring and first-value findings from synthetic placeholders into real exposure data.",
                [
                    _remediation_step("Authorize the first AWS account", "Complete the AWS onboarding step so SentinelGrid can ingest posture findings and inventory context."),
                    _remediation_step("Verify cloud health", "Confirm the connection is healthy and that the account is showing up in connected cloud coverage."),
                    _remediation_step("Review the first cloud issues", "Return to the welcome queue and posture views once the first critical findings land."),
                ],
                "Cloud coverage is visible, posture findings are arriving, and the first cloud recommendation is based on a real asset or exposure.",
            ),
            [
                {"label": "Connect AWS", "type": "view_details", "endpoint": "/onboarding?step=2"},
                {"label": "Open onboarding", "type": "view_details", "endpoint": "/onboarding"},
            ],
        )

    if cloud_posture["critical_misconfigs"] > 0:
        cloud_actions = [
            {"label": "Open remediation board", "type": "view_details", "endpoint": "/dashboard/compliance/remediation"},
            {"label": "Review posture", "type": "view_details", "endpoint": "/dashboard/compliance"},
        ]
        if cloud_playbook_id:
            cloud_actions.insert(
                0,
                {"label": "Open playbook", "type": "fix_now", "playbook_id": cloud_playbook_id},
            )
        add_candidate(
            "cloud-critical-misconfig",
            470,
            "high",
            f"Review {cloud_posture['critical_misconfigs']} critical cloud issue{'s' if cloud_posture['critical_misconfigs'] != 1 else ''}",
            "The posture model is already flagging critical cloud exposure. Triage those issues before broadening lower-signal hygiene work.",
            10,
            "cloud",
            "cloud.critical_exposure",
            _remediation_prompt(
                "cloud.critical_exposure",
                "Critical cloud exposure triage",
                "Cloud platform owner",
                "These are the highest-weight cloud findings in the current posture model and are usually the fastest path to material risk reduction.",
                [
                    _remediation_step("Confirm the exposed asset and severity", "Use the posture and remediation views to verify which resource is exposed and why it ranked as critical."),
                    _remediation_step("Restrict exposure or apply the playbook", "Remove public access, tighten the security group or bucket policy, or start the mapped response playbook if it fits the finding."),
                    _remediation_step("Rescan and verify closure", "Re-run validation or wait for the next scan cycle so the welcome queue reflects the fix instead of stale exposure data."),
                ],
                "The critical cloud issue no longer appears in the posture queue and the asset is no longer externally exposed.",
            ),
            cloud_actions,
        )

    mfa_missing = int(people_access.get("mfa_missing_count") or 0)
    users_admins = int(people_access.get("users_admins") or 0)
    if mfa_missing > 0:
        admin_gap = min(mfa_missing, users_admins)
        add_candidate(
            "identity-mfa-enforcement",
            455 + (25 if admin_gap else 0),
            "high" if admin_gap else "medium",
            (
                f"Enable MFA for {admin_gap} admin account{'s' if admin_gap != 1 else ''}"
                if admin_gap
                else f"Close MFA gaps for {mfa_missing} user{'s' if mfa_missing != 1 else ''}"
            ),
            (
                "Admin MFA coverage is still the fastest risk reduction move after identity is connected."
                if admin_gap
                else "SentinelGrid already has enough identity data to start shrinking MFA gaps."
            ),
            10,
            "identity",
            "identity.mfa_gap",
            _remediation_prompt(
                "identity.mfa_gap",
                "MFA gap remediation",
                "Identity admin",
                "MFA gaps on privileged or sensitive users are one of the most defensible first-week fixes for an SMB deployment.",
                [
                    _remediation_step("Review the affected users", "Open the People & Access view and confirm which privileged or sensitive users are still missing MFA."),
                    _remediation_step("Enforce enrollment or conditional access", "Apply the tenant’s MFA policy to the identified users and remove exceptions that no longer need to exist."),
                    _remediation_step("Validate coverage after enrollment", "Confirm the missing-MFA count drops and that the welcome queue reflects the new baseline."),
                ],
                "The privileged users now have MFA enabled and the missing-MFA count is materially reduced.",
            ),
            [
                {"label": "Review users", "type": "view_details", "endpoint": "/dashboard/iam/people"},
                {"label": "Open identity events", "type": "view_details", "endpoint": "/dashboard/iam/security-events"},
            ],
        )

    if endpoint_pct < 0.7:
        add_candidate(
            "endpoint-coverage",
            390 if onboarding_status.get("cloud_connected") else 260,
            "medium",
            "Deploy endpoint coverage next",
            "Endpoint coverage closes the loop between posture findings, detections, and response playbooks once cloud and identity are in place.",
            20,
            "endpoint",
            "endpoint.coverage_gap",
            _remediation_prompt(
                "endpoint.coverage_gap",
                "Endpoint coverage rollout",
                "IT or endpoint owner",
                "Without enough endpoint coverage, detections and remediation playbooks stay partially blind even if identity and cloud are connected.",
                [
                    _remediation_step("Identify the missing critical systems", "Start with production hosts, admin workstations, and the systems most likely to receive detections first."),
                    _remediation_step("Deploy the SentinelGrid agent bundle", "Roll out endpoint coverage to the highest-priority systems before expanding to lower-risk environments."),
                    _remediation_step("Verify healthy check-ins", "Confirm the endpoint coverage page shows those systems online so detections can trigger richer response workflows."),
                ],
                "Endpoint coverage reaches the important production systems and the agent health view shows them online.",
            ),
            [
                {"label": "Open endpoint coverage", "type": "view_details", "endpoint": "/dashboard/endpoint-protection"},
                {"label": "Resume onboarding", "type": "view_details", "endpoint": "/onboarding?step=3"},
            ],
        )

    if services_selected.get("socManaged") is False and ticketing_health_status != "healthy":
        add_candidate(
            "ticketing-handoff",
            380,
            "medium",
            "Finish the incident handoff",
            "Define where incidents land, who owns them, and whether Slack should receive first-week escalation notifications.",
            10,
            "collaboration",
            "collaboration.ticketing_handoff",
            _remediation_prompt(
                "collaboration.ticketing_handoff",
                "Incident handoff setup",
                "Security lead",
                "Early detections are far less useful if they do not land in the team’s real ticketing and escalation workflow.",
                [
                    _remediation_step("Choose the downstream system", "Decide whether Jira or ServiceNow should receive the first-week issues and who owns them."),
                    _remediation_step("Set routing and Slack notification behavior", "Define the default owner, assignment mode, and whether Slack should receive first-week handoff alerts."),
                    _remediation_step("Test the handoff health", "Confirm the integration reports healthy so the first real incidents do not stop at the SentinelGrid UI."),
                ],
                "Ticketing health is healthy and first-week issues can flow into the team’s normal operating process.",
            ),
            [
                {"label": "Configure handoff", "type": "view_details", "endpoint": "/onboarding"},
                {"label": "Open tickets", "type": "view_details", "endpoint": "/dashboard/tickets"},
            ],
        )

    if services_selected.get("git") and not onboarding_status.get("git_connected"):
        add_candidate(
            "activation-git",
            240,
            "low",
            "Connect Git for owner-aware remediation",
            "Git context lets SentinelGrid point findings at the right repo and code owner instead of stopping at infrastructure evidence.",
            12,
            "app",
            "activation.git_connection",
            _remediation_prompt(
                "activation.git_connection",
                "Git connection workflow",
                "Engineering platform owner",
                "Git metadata is what turns findings into owner-aware remediation work instead of another security queue with no code context.",
                [
                    _remediation_step("Authorize the Git provider", "Connect the source control provider so repos and owners can be associated with findings."),
                    _remediation_step("Verify repository visibility", "Confirm the expected repositories are visible before asking engineers to act on findings."),
                    _remediation_step("Use repo context in the queue", "Return to the dashboard once repositories are synced so remediation links can point at code owners and source paths."),
                ],
                "The product can connect findings to repositories and code owners instead of stopping at infrastructure evidence.",
            ),
            [
                {"label": "Connect Git", "type": "view_details", "endpoint": "/onboarding"},
                {"label": "Open posture", "type": "view_details", "endpoint": "/dashboard/posture"},
            ],
        )

    if services_selected.get("appsec") and not onboarding_status.get("appsec_connected"):
        add_candidate(
            "activation-appsec",
            235,
            "low",
            "Bring AppSec findings into the same queue",
            "AppSec context makes the first-week queue more actionable for engineering teams that already own code remediation.",
            12,
            "app",
            "activation.appsec_connection",
            _remediation_prompt(
                "activation.appsec_connection",
                "AppSec connection workflow",
                "Application security owner",
                "AppSec findings help the welcome queue explain which issues already have code and repo context instead of leaving them as isolated posture evidence.",
                [
                    _remediation_step("Connect the AppSec source", "Provide the app security integration so findings can be imported into the shared operator queue."),
                    _remediation_step("Validate health and recent findings", "Confirm the integration is healthy and that recent application findings are present."),
                    _remediation_step("Review the first owner-aware issues", "Use the shared queue once AppSec findings are correlated with repos and incidents."),
                ],
                "Application findings are visible in the same queue as cloud and identity work.",
            ),
            [
                {"label": "Connect AppSec", "type": "view_details", "endpoint": "/onboarding"},
                {"label": "Open posture", "type": "view_details", "endpoint": "/dashboard/posture"},
            ],
        )

    if services_selected.get("aiShield") and not onboarding_status.get("ai_connected"):
        add_candidate(
            "activation-ai-shield",
            225,
            "low",
            "Connect AI Shield telemetry",
            "AI runtime events should land in the same operator workflow so data leakage and prompt abuse are not isolated in a side tool.",
            12,
            "ai",
            "activation.ai_shield_connection",
            _remediation_prompt(
                "activation.ai_shield_connection",
                "AI Shield connection workflow",
                "AI or platform owner",
                "AI telemetry only becomes useful to the core operator workflow once those events land in the same incident and policy queue.",
                [
                    _remediation_step("Connect AI Shield", "Finish the AI Shield onboarding step so runtime events can reach the shared platform views."),
                    _remediation_step("Validate AI event flow", "Confirm events are landing in the AI activity view and that policy signals look healthy."),
                    _remediation_step("Review AI policy findings with the core queue", "Use the same operator workflow for AI leakage or prompt abuse issues instead of splitting teams across tools."),
                ],
                "AI runtime events are visible in SentinelGrid and can be triaged alongside the rest of the platform findings.",
            ),
            [
                {"label": "Connect AI Shield", "type": "view_details", "endpoint": "/onboarding"},
                {"label": "Open AI activity", "type": "view_details", "endpoint": "/dashboard/compliance/ai-activity"},
            ],
        )

    candidates.sort(key=lambda item: item["_rank"], reverse=True)

    recommendations: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    for candidate in candidates:
        if candidate["id"] in seen_ids:
            continue
        seen_ids.add(candidate["id"])
        item = dict(candidate)
        item.pop("_rank", None)
        recommendations.append(item)
        if len(recommendations) == 6:
            break

    return recommendations


def build_first_value_section(
    tenant_id: str,
    posture_score: Dict[str, Any],
    people_access: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the welcome first-value section payload."""
    return {
        "findings": build_first_value_findings(tenant_id, posture_score, people_access),
    }


def _recommendation_domain(category: str | None) -> str:
    normalized = (category or "security").lower()
    if normalized in {"identity", "activation"}:
        return "identity"
    if normalized in {"cloud", "collaboration"}:
        return "cloud" if normalized == "cloud" else "security"
    if normalized in {"endpoint"}:
        return "endpoint"
    if normalized in {"ai"}:
        return "ai"
    if normalized in {"app"}:
        return "application"
    return "security"


def build_now_queue(
    incidents: List[Dict[str, Any]],
    alerts: List[Dict[str, Any]],
    recommendations: List[Dict[str, Any]],
    *,
    limit: int = 8,
) -> Dict[str, Any]:
    """Build the cross-domain Now queue for the main dashboard."""
    candidates: List[Dict[str, Any]] = []

    for index, item in enumerate(incidents):
        candidate = dict(item)
        candidate["_rank"] = _severity_rank(candidate.get("priority")) + 140 - index * 3
        candidates.append(candidate)

    for index, item in enumerate(alerts):
        candidate = dict(item)
        candidate["_rank"] = _severity_rank(candidate.get("priority")) + 80 - index * 2
        candidates.append(candidate)

    for index, rec in enumerate(recommendations):
        primary_action = next(
            (action for action in rec.get("actions", []) if action.get("endpoint")),
            rec.get("actions", [{}])[0] if rec.get("actions") else {},
        )
        domain = _recommendation_domain(rec.get("category"))
        candidates.append(
            {
                "id": f"recommendation:{rec['id']}",
                "item_type": "recommendation",
                "priority": rec.get("priority", "medium"),
                "title": rec.get("title") or "Recommended next action",
                "summary": rec.get("description") or "Recommended next action for the tenant.",
                "why_now": rec.get("remediation", {}).get("why_now") or rec.get("description") or "This work item is currently prioritized by SentinelGrid.",
                "status": "queued",
                "owner": rec.get("remediation", {}).get("owner"),
                "source_label": "Recommendation",
                "href": primary_action.get("endpoint") or "/dashboard",
                "action_label": primary_action.get("label") or "Review action",
                "action_href": primary_action.get("endpoint") or "/dashboard",
                "updated_at": None,
                "domains": [domain],
                "entities": [],
                "evidence": [],
                "estimated_time_minutes": rec.get("estimated_time_minutes"),
                "_rank": _severity_rank(rec.get("priority")) + 20 - index,
            }
        )

    candidates.sort(key=lambda item: item["_rank"], reverse=True)

    items: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()
    for candidate in candidates:
        candidate_id = candidate["id"]
        if candidate_id in seen_ids:
            continue
        seen_ids.add(candidate_id)
        item = dict(candidate)
        item.pop("_rank", None)
        items.append(item)
        if len(items) == limit:
            break

    domain_counts: Dict[str, int] = {}
    for item in items:
        for domain in item.get("domains", []) or []:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

    return {
        "items": items,
        "summary": {
            "total_items": len(items),
            "urgent_items": sum(1 for item in items if item.get("priority") in {"critical", "high"}),
            "incidents": sum(1 for item in items if item.get("item_type") == "incident"),
            "alerts": sum(1 for item in items if item.get("item_type") == "alert"),
            "recommendations": sum(1 for item in items if item.get("item_type") == "recommendation"),
            "domains": [
                {"domain": domain, "count": count}
                for domain, count in sorted(domain_counts.items(), key=lambda item: item[1], reverse=True)
            ],
        },
    }
