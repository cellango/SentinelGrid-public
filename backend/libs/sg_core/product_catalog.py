"""Canonical product and signup-selection helpers."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


PLAN_TIER_PROTECT = "protect"
PLAN_TIER_PROTECT_DEFEND = "protect_defend"
PLAN_TIER_PROTECT_DEFEND_COMPLY = "protect_defend_comply"

PLAN_TIER_ORDER = (
    PLAN_TIER_PROTECT,
    PLAN_TIER_PROTECT_DEFEND,
    PLAN_TIER_PROTECT_DEFEND_COMPLY,
)

VALID_TICKETING_PROVIDERS = {"internal", "jira", "servicenow"}
VALID_AI_SHIELD_MODES = {"hosted", "self"}

LEGACY_PACKAGE_NAME_ALIASES = {
    "protect": PLAN_TIER_PROTECT,
    "protect_defend": PLAN_TIER_PROTECT_DEFEND,
    "protect_defend_comply": PLAN_TIER_PROTECT_DEFEND_COMPLY,
    "protect_comply": PLAN_TIER_PROTECT_DEFEND_COMPLY,
}

PLAN_TIER_RANK = {
    PLAN_TIER_PROTECT: 1,
    PLAN_TIER_PROTECT_DEFEND: 2,
    PLAN_TIER_PROTECT_DEFEND_COMPLY: 3,
}

PLAN_DISPLAY_NAMES = {
    PLAN_TIER_PROTECT: "SentinelGrid Protect",
    PLAN_TIER_PROTECT_DEFEND: "SentinelGrid Protect + Defend",
    PLAN_TIER_PROTECT_DEFEND_COMPLY: "SentinelGrid Protect + Defend + Comply",
}


def _clean_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_string_list(values: Any) -> list[str]:
    if not isinstance(values, Iterable) or isinstance(values, (str, bytes, dict)):
        return []
    cleaned: list[str] = []
    for value in values:
        item = _clean_string(value)
        if item:
            cleaned.append(item)
    return cleaned


def normalize_plan_tier(value: Any) -> Optional[str]:
    candidate = _clean_string(value)
    if not candidate:
        return None
    return LEGACY_PACKAGE_NAME_ALIASES.get(candidate.lower())


def is_plan_tier(value: Any) -> bool:
    return normalize_plan_tier(value) in PLAN_TIER_ORDER


def get_plan_rank(value: Any) -> int:
    normalized = normalize_plan_tier(value)
    if not normalized:
        return 0
    return PLAN_TIER_RANK[normalized]


def plan_includes_compliance(value: Any) -> bool:
    return normalize_plan_tier(value) == PLAN_TIER_PROTECT_DEFEND_COMPLY


def get_plan_display_name(value: Any) -> str:
    normalized = normalize_plan_tier(value) or PLAN_TIER_PROTECT
    return PLAN_DISPLAY_NAMES[normalized]


def normalize_services_selected(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {}

    normalized: Dict[str, Any] = {}

    for key in ("cloud", "git", "appsec", "socManaged"):
        value = raw.get(key)
        if isinstance(value, bool):
            normalized[key] = value

    ai_mode = _clean_string(raw.get("aiShield"))
    if ai_mode and ai_mode.lower() in VALID_AI_SHIELD_MODES:
        normalized["aiShield"] = ai_mode.lower()

    ticketing = _clean_string(raw.get("ticketing"))
    if ticketing and ticketing.lower() in VALID_TICKETING_PROVIDERS:
        normalized["ticketing"] = ticketing.lower()

    ticketing_project = _clean_string(raw.get("ticketingProject"))
    if ticketing_project:
        normalized["ticketingProject"] = ticketing_project

    idp_provider = _clean_string(raw.get("idpProvider"))
    if idp_provider:
        normalized["idpProvider"] = idp_provider

    trust_profile = raw.get("trustProfile")
    if isinstance(trust_profile, dict):
        normalized_trust_profile: Dict[str, Any] = {}
        if isinstance(trust_profile.get("enabled"), bool):
            normalized_trust_profile["enabled"] = trust_profile["enabled"]
        frameworks = _clean_string_list(trust_profile.get("frameworks"))
        if frameworks:
            normalized_trust_profile["frameworks"] = frameworks
        primary_driver = _clean_string(trust_profile.get("primaryDriver"))
        if primary_driver:
            normalized_trust_profile["primaryDriver"] = primary_driver
        target_timeline = _clean_string(trust_profile.get("targetTimeline"))
        if target_timeline:
            normalized_trust_profile["targetTimeline"] = target_timeline
        if normalized_trust_profile:
            normalized["trustProfile"] = normalized_trust_profile

    return normalized


def apply_plan_defaults(plan_tier: Any, services_selected: Any) -> Dict[str, Any]:
    normalized_plan_tier = normalize_plan_tier(plan_tier) or PLAN_TIER_PROTECT
    services = normalize_services_selected(services_selected)

    if normalized_plan_tier == PLAN_TIER_PROTECT_DEFEND_COMPLY:
        trust_profile = dict(services.get("trustProfile") or {})
        trust_profile["enabled"] = True
        services["trustProfile"] = trust_profile

    return services


def derive_plan_tier(
    *,
    plan_tier: Any = None,
    package_name: Any = None,
    compliance_required: bool = False,
    services_selected: Any = None,
) -> str:
    normalized_plan_tier = normalize_plan_tier(plan_tier) or normalize_plan_tier(package_name)
    if normalized_plan_tier:
        return normalized_plan_tier

    services = normalize_services_selected(services_selected)
    trust_profile = services.get("trustProfile") or {}

    if compliance_required or trust_profile.get("enabled") is True:
        return PLAN_TIER_PROTECT_DEFEND_COMPLY

    if (
        "socManaged" in services
        or "ticketing" in services
        or "ticketingProject" in services
    ):
        return PLAN_TIER_PROTECT_DEFEND

    return PLAN_TIER_PROTECT


def requires_dedicated_realm(plan_tier: Any, services_selected: Any) -> bool:
    normalized_plan_tier = normalize_plan_tier(plan_tier)
    if normalized_plan_tier != PLAN_TIER_PROTECT_DEFEND_COMPLY:
        return False
    services = normalize_services_selected(services_selected)
    return services.get("socManaged") is False
