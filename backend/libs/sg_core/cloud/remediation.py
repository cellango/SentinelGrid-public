"""Provider-neutral cloud remediation planning."""

from __future__ import annotations

import copy
import ipaddress
from typing import Any

from sg_core.cloud.controls import rule_allows_tcp_port
from sg_core.cloud.types import CloudRemediationPlan, CloudResourceRef, FirewallPolicy, FirewallRule


class CloudRemediationError(ValueError):
    """Raised when a provider-neutral remediation plan cannot be produced."""


def normalize_cidrs(cidrs: list[str] | tuple[str, ...] | str | None) -> list[str]:
    if cidrs is None:
        return []
    if isinstance(cidrs, str):
        raw_items = [item.strip() for item in cidrs.split(",")]
    else:
        raw_items = [str(item).strip() for item in cidrs]

    normalized: list[str] = []
    for item in raw_items:
        if not item:
            continue
        try:
            network = ipaddress.ip_network(item, strict=False)
        except ValueError as exc:
            raise CloudRemediationError(f"Invalid CIDR: {item}") from exc
        text = str(network)
        if text not in normalized:
            normalized.append(text)
    return normalized


def require_cidrs(cidrs: list[str] | tuple[str, ...] | str | None) -> list[str]:
    normalized = normalize_cidrs(cidrs)
    if not normalized:
        raise CloudRemediationError("At least one CIDR is required before apply")
    return normalized


def plan_firewall_source_restriction(
    policy: FirewallPolicy,
    *,
    port: int,
    allowed_source_cidrs: list[str] | tuple[str, ...] | str | None,
    apply_mode: str = "iac_patch",
    action: str = "replace_firewall_rules",
    iac_variable: str | None = None,
) -> CloudRemediationPlan:
    """Plan a firewall rule source restriction while preserving unrelated rules."""

    normalized_cidrs = require_cidrs(allowed_source_cidrs)
    proposed_rules: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []

    for rule in policy.rules:
        raw_rule = _raw_rule_payload(rule)
        if rule_allows_tcp_port(rule, port):
            source_key = _source_key(raw_rule)
            before_sources = list(rule.source_cidrs)
            raw_rule[source_key] = list(normalized_cidrs)
            changed.append(
                {
                    "protocol": rule.protocol,
                    "port": rule.port,
                    "before_source_cidrs": before_sources,
                    "after_source_cidrs": list(normalized_cidrs),
                    "raw_before": rule.raw or _normalized_rule_payload(rule),
                    "raw_after": raw_rule,
                }
            )
        proposed_rules.append(raw_rule)

    if not changed:
        raise CloudRemediationError(f"No inbound TCP/{port} rule was found on the target firewall")

    iac_patch = None
    if apply_mode == "iac_patch":
        iac_patch = {
            "tool": "terraform",
            "variable": iac_variable or f"admin_tcp_{port}_cidrs",
            "value": list(normalized_cidrs),
        }

    return CloudRemediationPlan(
        provider=policy.ref.provider,
        apply_mode=apply_mode,
        resource_ref=policy.ref,
        action=action,
        desired_state={
            "rules": proposed_rules,
            "admin_port": port,
            "allowed_source_cidrs": list(normalized_cidrs),
        },
        diff={
            "changed": changed,
            "preserved": {
                "unchanged_rule_count": len(policy.rules) - len(changed),
            },
        },
        iac_patch=iac_patch,
        raw_plan={
            "provider": policy.ref.provider,
            "action": action,
            "resource_ref": {
                "provider": policy.ref.provider,
                "resource_type": policy.ref.resource_type,
                "external_id": policy.ref.external_id,
                "name": policy.ref.name,
            },
            "admin_port": port,
            "allowed_source_cidrs": list(normalized_cidrs),
            "pre_rules": [_raw_rule_payload(rule) for rule in policy.rules],
            "proposed_rules": proposed_rules,
            "diff": {
                "changed": changed,
                "preserved": {
                    "unchanged_rule_count": len(policy.rules) - len(changed),
                },
            },
        },
    )


def _source_key(raw_rule: dict[str, Any]) -> str:
    if "source_ips" in raw_rule:
        return "source_ips"
    if "sourceIps" in raw_rule:
        return "sourceIps"
    if "source_cidrs" in raw_rule:
        return "source_cidrs"
    return "source_cidrs"


def _raw_rule_payload(rule: FirewallRule) -> dict[str, Any]:
    return copy.deepcopy(rule.raw) if rule.raw else _normalized_rule_payload(rule)


def _normalized_rule_payload(rule: FirewallRule) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "direction": rule.direction,
        "protocol": rule.protocol,
    }
    if rule.port is not None:
        payload["port"] = rule.port
    if rule.source_cidrs:
        payload["source_cidrs"] = list(rule.source_cidrs)
    if rule.destination_cidrs:
        payload["destination_cidrs"] = list(rule.destination_cidrs)
    return payload
