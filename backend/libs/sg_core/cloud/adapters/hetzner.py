"""Hetzner Cloud adapter and single-server pilot helpers.

This module intentionally scopes v1 to the known websites-prod server. The
helpers keep rule parsing and remediation plan generation deterministic across
onboarding, scanning, and approval-gated apply.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from sg_core.cloud.controls import (
    WORLD_CIDRS as GENERIC_WORLD_CIDRS,
    admin_port_open_to_world,
    expected_public_tcp_ports,
    port_spec_matches,
    public_tcp_port_expected as generic_public_tcp_port_expected,
    rule_allows_tcp_port as generic_rule_allows_tcp_port,
    rule_has_world_source as generic_rule_has_world_source,
)
from sg_core.cloud.baseline import (
    active_cloud_findings_from_checks,
    cloud_resource_baseline_checks,
    public_tls_edge,
    public_tls_edge_local_apps_pass,
    summarize_cloud_baseline,
)
from sg_core.cloud.remediation import (
    CloudRemediationError,
    normalize_cidrs as normalize_cloud_cidrs,
    plan_firewall_source_restriction,
)
from sg_core.cloud.targets import cloud_target_context
from sg_core.cloud.types import (
    ApplyResult,
    CloudControlResult,
    CloudProviderAuth,
    CloudRemediationPlan,
    CloudResource,
    CloudResourceRef,
    CloudResourceRelationship,
    CloudTargetSelector,
    FirewallPolicy,
    FirewallRule,
    ProviderHealth,
)


HETZNER_API_BASE = "https://api.hetzner.cloud/v1"
HETZNER_PILOT_SCANNER_ID = "hetzner-single-server-baseline"

# Synthetic preview fixtures; real deployment targets belong in local configuration.
HETZNER_PILOT_SERVER_ID = "123456789"
HETZNER_PILOT_SERVER_NAME = "websites-prod"
HETZNER_PILOT_IPV4 = "203.0.113.42"
HETZNER_PILOT_FIREWALL_ID = "98765432"
HETZNER_PILOT_FIREWALL_NAME = "websites-prod-firewall"
HETZNER_PILOT_LABELS = {"project": "websites", "role": "web"}
HETZNER_PILOT_DOMAINS = ["web-one.example.com", "web-two.example.com"]
WORLD_CIDRS = GENERIC_WORLD_CIDRS


class HetznerValidationError(ValueError):
    """Raised when the single-server pilot scope or remediation input is invalid."""


@dataclass(frozen=True)
class HetznerTarget:
    server_id: str = HETZNER_PILOT_SERVER_ID
    server_name: str = HETZNER_PILOT_SERVER_NAME
    server_ipv4: str = HETZNER_PILOT_IPV4
    firewall_id: str = HETZNER_PILOT_FIREWALL_ID
    firewall_name: str = HETZNER_PILOT_FIREWALL_NAME
    project_label: str = "websites"
    role_label: str = "web"
    target_mode: str = "single_server"

    def metadata(self) -> dict[str, Any]:
        return {
            "target_mode": self.target_mode,
            "server_id": self.server_id,
            "server_name": self.server_name,
            "server_ipv4": self.server_ipv4,
            "firewall_id": self.firewall_id,
            "firewall_name": self.firewall_name,
            "project_label": self.project_label,
            "role_label": self.role_label,
            "domains": list(HETZNER_PILOT_DOMAINS),
            "public_tls_edge": {
                "service": "caddy",
                "public_ports": [80, 443],
                "expected_local_app_ports": [3000, 3001],
            },
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def pilot_target(
    server_id: str | None = None,
    server_name: str | None = None,
    firewall_id: str | None = None,
) -> HetznerTarget:
    """Return the v1 target after enforcing the pilot's explicit scope."""
    sid = str(server_id or HETZNER_PILOT_SERVER_ID)
    name = str(server_name or HETZNER_PILOT_SERVER_NAME)
    fid = str(firewall_id or HETZNER_PILOT_FIREWALL_ID)
    if sid != HETZNER_PILOT_SERVER_ID:
        raise HetznerValidationError(f"Hetzner pilot is limited to server {HETZNER_PILOT_SERVER_ID}")
    if name != HETZNER_PILOT_SERVER_NAME:
        raise HetznerValidationError(f"Hetzner pilot is limited to server name {HETZNER_PILOT_SERVER_NAME}")
    if fid != HETZNER_PILOT_FIREWALL_ID:
        raise HetznerValidationError(f"Hetzner pilot is limited to firewall {HETZNER_PILOT_FIREWALL_ID}")
    return HetznerTarget()


def normalize_cidrs(cidrs: list[str] | tuple[str, ...] | str | None) -> list[str]:
    """Validate and canonicalize admin SSH CIDRs."""
    try:
        return normalize_cloud_cidrs(cidrs)
    except CloudRemediationError as exc:
        raise HetznerValidationError(str(exc)) from exc


def require_admin_cidrs(cidrs: list[str] | tuple[str, ...] | str | None) -> list[str]:
    normalized = normalize_cidrs(cidrs)
    if not normalized:
        raise HetznerValidationError("At least one admin SSH CIDR is required before apply")
    return normalized


def _rule_ports(rule: dict[str, Any]) -> str | None:
    port = rule.get("port")
    return str(port) if port is not None else None


def _port_matches(port_spec: str | None, port: int) -> bool:
    return port_spec_matches(port_spec, port)


def rule_allows_tcp_port(rule: dict[str, Any], port: int) -> bool:
    return generic_rule_allows_tcp_port(_firewall_rule_from_raw(rule), port)


def rule_is_icmp(rule: dict[str, Any]) -> bool:
    return (rule.get("direction") or "in") == "in" and (rule.get("protocol") or "").lower() == "icmp"


def source_ips(rule: dict[str, Any]) -> list[str]:
    values = rule.get("source_ips") or rule.get("sourceIps") or []
    return [str(value) for value in values]


def _firewall_rule_from_raw(rule: dict[str, Any]) -> FirewallRule:
    return FirewallRule(
        direction=str(rule.get("direction") or "in"),
        protocol=str(rule.get("protocol") or ""),
        port=_rule_ports(rule),
        source_cidrs=source_ips(rule),
        destination_cidrs=[str(value) for value in (rule.get("destination_ips") or [])],
        raw=rule,
    )


def _firewall_policy_from_rules(rules: list[dict[str, Any]]) -> FirewallPolicy:
    return FirewallPolicy(
        ref=_hetzner_resource_ref("firewall_policy", HETZNER_PILOT_FIREWALL_ID, HETZNER_PILOT_FIREWALL_NAME),
        rules=[_firewall_rule_from_raw(rule) for rule in rules],
        raw={"rules": rules},
    )


def hetzner_firewall_policy(firewall: dict[str, Any] | None) -> FirewallPolicy:
    firewall = firewall or {}
    return FirewallPolicy(
        ref=_hetzner_resource_ref("firewall_policy", firewall.get("id") or HETZNER_PILOT_FIREWALL_ID, firewall.get("name")),
        rules=[_firewall_rule_from_raw(rule) for rule in firewall_rules(firewall)],
        raw=firewall,
    )


def rule_has_world_source(rule: dict[str, Any]) -> bool:
    return generic_rule_has_world_source(_firewall_rule_from_raw(rule))


def ssh_open_to_world(rules: list[dict[str, Any]]) -> bool:
    policy = _firewall_policy_from_rules(rules)
    return admin_port_open_to_world(policy, port=22).status == "open"


def public_web_access_expected(rules: list[dict[str, Any]]) -> bool:
    return expected_public_tcp_ports(_firewall_policy_from_rules(rules), (80, 443)).status == "pass"


def public_port_expected(rules: list[dict[str, Any]], port: int) -> bool:
    return generic_public_tcp_port_expected(_firewall_policy_from_rules(rules), port)


def firewall_rules(firewall: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not firewall:
        return []
    rules = firewall.get("rules") or []
    return rules if isinstance(rules, list) else []


def server_ipv4(server: dict[str, Any] | None) -> str | None:
    public_net = (server or {}).get("public_net") or {}
    ipv4 = public_net.get("ipv4") or {}
    if isinstance(ipv4, dict):
        return ipv4.get("ip")
    return None


def attached_firewall_ids(server: dict[str, Any] | None) -> set[str]:
    public_net = (server or {}).get("public_net") or {}
    firewalls = public_net.get("firewalls") or []
    ids: set[str] = set()
    for fw in firewalls:
        if isinstance(fw, dict) and fw.get("id") is not None:
            ids.add(str(fw["id"]))
    return ids


def firewall_applies_to_server(firewall: dict[str, Any] | None, server_id: str) -> bool:
    applied_to = (firewall or {}).get("applied_to") or []
    for item in applied_to:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "server":
            continue
        server = item.get("server") or {}
        if str(server.get("id")) == str(server_id):
            return True
    return False


def validate_single_server_scope(
    server: dict[str, Any],
    firewall: dict[str, Any],
    target: HetznerTarget | None = None,
) -> dict[str, Any]:
    """Validate token-visible Hetzner state against the v1 pilot contract."""
    target = target or HetznerTarget()
    warnings: list[str] = []
    errors: list[str] = []

    if str(server.get("id")) != target.server_id:
        errors.append(f"Server id mismatch: expected {target.server_id}")
    if server.get("name") != target.server_name:
        errors.append(f"Server name mismatch: expected {target.server_name}")

    labels = server.get("labels") or {}
    if labels.get("project") != target.project_label:
        errors.append("Server label project=websites is missing")
    if labels.get("role") != target.role_label:
        errors.append("Server label role=web is missing")

    ipv4 = server_ipv4(server)
    if ipv4 and ipv4 != target.server_ipv4:
        warnings.append(f"Server IPv4 differs from expected {target.server_ipv4}: {ipv4}")

    if str(firewall.get("id")) != target.firewall_id:
        errors.append(f"Firewall id mismatch: expected {target.firewall_id}")
    if firewall.get("name") and firewall.get("name") != target.firewall_name:
        warnings.append(f"Firewall name differs from expected {target.firewall_name}: {firewall.get('name')}")

    attached = target.firewall_id in attached_firewall_ids(server) or firewall_applies_to_server(firewall, target.server_id)
    if not attached:
        errors.append(f"Firewall {target.firewall_id} is not attached to server {target.server_id}")

    return {
        "success": not errors,
        "status": "healthy" if not errors else "unhealthy",
        "errors": errors,
        "warnings": warnings,
    }


def scope_hash(server: dict[str, Any], firewall: dict[str, Any]) -> str:
    """Hash the server/firewall scope that must remain stable between plan and apply."""
    payload = {
        "server": {
            "id": server.get("id"),
            "name": server.get("name"),
            "labels": server.get("labels") or {},
            "ipv4": server_ipv4(server),
            "attached_firewalls": sorted(attached_firewall_ids(server)),
        },
        "firewall": {
            "id": firewall.get("id"),
            "name": firewall.get("name"),
            "rules": firewall_rules(firewall),
            "applied_to": firewall.get("applied_to") or [],
        },
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_firewall_plan(
    firewall: dict[str, Any],
    admin_ssh_cidrs: list[str] | tuple[str, ...] | str | None,
) -> dict[str, Any]:
    """Build an approval-gated firewall update plan for SSH narrowing."""
    try:
        remediation_plan = plan_firewall_source_restriction(
            hetzner_firewall_policy(firewall),
            port=22,
            allowed_source_cidrs=admin_ssh_cidrs,
            apply_mode="iac_patch",
            iac_variable="admin_ssh_cidrs",
        )
    except CloudRemediationError as exc:
        raise HetznerValidationError(str(exc)) from exc

    normalized_cidrs = remediation_plan.raw_plan["allowed_source_cidrs"]
    current_rules = firewall_rules(firewall)
    proposed_rules = remediation_plan.raw_plan["proposed_rules"]
    changed = [
        {
            "protocol": item["protocol"],
            "port": item["port"],
            "before_source_ips": item["before_source_cidrs"],
            "after_source_ips": item["after_source_cidrs"],
            "before_source_cidrs": item["before_source_cidrs"],
            "after_source_cidrs": item["after_source_cidrs"],
        }
        for item in remediation_plan.diff["changed"]
    ]

    return {
        "provider": "hetzner",
        "action": "replace_firewall_rules",
        "server_id": HETZNER_PILOT_SERVER_ID,
        "firewall_id": HETZNER_PILOT_FIREWALL_ID,
        "resource_ref": remediation_plan.raw_plan["resource_ref"],
        "apply_mode": remediation_plan.apply_mode,
        "iac_patch": remediation_plan.iac_patch,
        "admin_ssh_cidrs": list(normalized_cidrs),
        "pre_rules": current_rules,
        "proposed_rules": proposed_rules,
        "diff": {
            "changed": changed,
            "preserved": {
                **remediation_plan.diff["preserved"],
                "http_public": public_port_expected(current_rules, 80),
                "https_public": public_port_expected(current_rules, 443),
                "icmp_rules": [rule for rule in current_rules if rule_is_icmp(rule)],
            },
        },
        "recommendations": [
            {
                "id": "hetzner-backups-disabled",
                "severity": "medium",
                "title": "Backups are disabled",
                "automatic": False,
                "reason": "Hetzner backups change monthly cost, so v1 records this as approval-only guidance.",
            }
        ],
    }


def caddy_tls_edge_pass(metadata: dict[str, Any] | None = None) -> bool:
    edge = public_tls_edge(metadata=metadata)
    return (edge.get("service") or "").lower() == "caddy" and public_tls_edge_local_apps_pass(metadata)


def baseline_checks(
    server: dict[str, Any],
    firewall: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return cloud_resource_baseline_checks(
        HetznerCloudAdapter(),
        server,
        firewall,
        _pilot_target_context(),
        metadata or HetznerTarget().metadata(),
    )


def failing_findings_from_checks(
    checks: list[dict[str, Any]],
    server: dict[str, Any],
    firewall: dict[str, Any],
    scanner_id: str = HETZNER_PILOT_SCANNER_ID,
) -> list[dict[str, Any]]:
    return active_cloud_findings_from_checks(
        checks,
        _pilot_target_context(),
        scanner_id=scanner_id,
        server=server,
        firewall=firewall,
    )


def summarize_baseline(
    checks: list[dict[str, Any]],
    change_request_id: str | None = None,
    scope: str | None = None,
    scanner_id: str = HETZNER_PILOT_SCANNER_ID,
) -> dict[str, Any]:
    return summarize_cloud_baseline(
        checks,
        _pilot_target_context(),
        change_request_id=change_request_id,
        scope=scope,
        scanner_id=scanner_id,
    )


def _pilot_target_context():
    return cloud_target_context("websites-prod", provider_id="hetzner")


class HetznerClient:
    """Minimal Hetzner Cloud API client used by the pilot."""

    def __init__(self, api_token: str, base_url: str = HETZNER_API_BASE, timeout: float = 10.0):
        if not api_token:
            raise HetznerValidationError("Hetzner API token is required")
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(method, f"{self.base_url}{path}", headers=self._headers(), **kwargs)
        if response.status_code >= 300:
            raise HetznerValidationError(f"Hetzner API {method} {path} failed: {response.status_code} {response.text[:200]}")
        data = response.json()
        return data if isinstance(data, dict) else {}

    def get_server(self, server_id: str) -> dict[str, Any]:
        data = self._request("GET", f"/servers/{server_id}")
        server = data.get("server") or {}
        if not server:
            raise HetznerValidationError(f"Hetzner server {server_id} was not found")
        return server

    def get_firewall(self, firewall_id: str) -> dict[str, Any]:
        data = self._request("GET", f"/firewalls/{firewall_id}")
        firewall = data.get("firewall") or {}
        if not firewall:
            raise HetznerValidationError(f"Hetzner firewall {firewall_id} was not found")
        return firewall

    def set_firewall_rules(self, firewall_id: str, rules: list[dict[str, Any]]) -> dict[str, Any]:
        return self._request("POST", f"/firewalls/{firewall_id}/actions/set_rules", json={"rules": rules})


def health_from_state(server: dict[str, Any], firewall: dict[str, Any], target: HetznerTarget | None = None) -> dict[str, Any]:
    target = target or HetznerTarget()
    validation = validate_single_server_scope(server, firewall, target)
    metadata = target.metadata()
    scope = scope_hash(server, firewall)
    checks = baseline_checks(server, firewall, metadata)
    return {
        **validation,
        "provider": "hetzner",
        "target_mode": "single_server",
        "server": {
            "id": str(server.get("id")),
            "name": server.get("name"),
            "ipv4": server_ipv4(server),
            "labels": server.get("labels") or {},
            "backups_enabled": bool(server.get("backups") or server.get("backup_window")),
        },
        "firewall": {
            "id": str(firewall.get("id")),
            "name": firewall.get("name"),
            "rules": firewall_rules(firewall),
            "attached": target.firewall_id in attached_firewall_ids(server)
            or firewall_applies_to_server(firewall, target.server_id),
        },
        "checks": checks,
        "scope_hash": scope,
        "checked_at": utc_now_iso(),
    }


def _hetzner_resource_ref(resource_type: str, external_id: str | int, name: str | None = None) -> CloudResourceRef:
    return CloudResourceRef(
        provider="hetzner",
        resource_type=resource_type,
        external_id=str(external_id),
        name=name,
    )


def _token_from_auth(auth: CloudProviderAuth | dict[str, Any] | None) -> str | None:
    if auth is None:
        return None
    if isinstance(auth, CloudProviderAuth):
        return auth.secret
    return auth.get("secret") or auth.get("api_token") or auth.get("token")


class HetznerCloudAdapter:
    """Hetzner implementation of the provider-neutral cloud adapter contract."""

    provider = "hetzner"

    def __init__(
        self,
        api_token: str | None = None,
        client: HetznerClient | None = None,
        target: HetznerTarget | None = None,
    ):
        self.api_token = api_token
        self.client = client
        self.target = target or HetznerTarget()

    def _client(self, auth: CloudProviderAuth | dict[str, Any] | None = None) -> HetznerClient:
        if self.client is not None:
            return self.client
        token = _token_from_auth(auth) or self.api_token
        if not token:
            raise HetznerValidationError("Hetzner API token is required")
        return HetznerClient(token)

    def validate_auth(self, auth: CloudProviderAuth | dict[str, Any]) -> ProviderHealth:
        try:
            state = self.read_target_state(auth)
            health = state["health"]
            return ProviderHealth(
                success=bool(health.get("success")),
                status=str(health.get("status") or "unknown"),
                provider=self.provider,
                errors=list(health.get("errors") or []),
                warnings=list(health.get("warnings") or []),
                metadata=health,
            )
        except HetznerValidationError as exc:
            return ProviderHealth(
                success=False,
                status="unhealthy",
                provider=self.provider,
                errors=[str(exc)],
            )

    def read_target_state(self, auth: CloudProviderAuth | dict[str, Any] | None = None) -> dict[str, Any]:
        """Read the pilot target server, firewall, and derived health in one adapter call."""

        client = self._client(auth)
        server = client.get_server(self.target.server_id)
        firewall = client.get_firewall(self.target.firewall_id)
        health = health_from_state(server, firewall, self.target)
        return {"server": server, "firewall": firewall, "health": health}

    def discover(self, selector: CloudTargetSelector) -> list[CloudResource]:
        target = pilot_target(
            server_id=selector.external_id or self.target.server_id,
            server_name=selector.name or self.target.server_name,
            firewall_id=selector.relationships.get("firewall_policy") or self.target.firewall_id,
        )
        client = self._client()
        server = client.get_server(target.server_id)
        firewall = client.get_firewall(target.firewall_id)
        return [
            CloudResource(
                ref=_hetzner_resource_ref("compute_instance", server.get("id"), server.get("name")),
                raw=server,
                labels={str(k): str(v) for k, v in (server.get("labels") or {}).items()},
                metadata=target.metadata(),
            ),
            CloudResource(
                ref=_hetzner_resource_ref("firewall_policy", firewall.get("id"), firewall.get("name")),
                raw=firewall,
                metadata={"target_server_id": target.server_id},
            ),
        ]

    def read_resource(self, resource_ref: CloudResourceRef) -> CloudResource:
        client = self._client()
        if resource_ref.resource_type in {"compute_instance", "server"}:
            server = client.get_server(resource_ref.external_id)
            return CloudResource(
                ref=_hetzner_resource_ref("compute_instance", server.get("id"), server.get("name")),
                raw=server,
                labels={str(k): str(v) for k, v in (server.get("labels") or {}).items()},
            )
        if resource_ref.resource_type in {"firewall_policy", "firewall"}:
            firewall = client.get_firewall(resource_ref.external_id)
            return CloudResource(
                ref=_hetzner_resource_ref("firewall_policy", firewall.get("id"), firewall.get("name")),
                raw=firewall,
            )
        raise HetznerValidationError(f"Unsupported Hetzner resource type: {resource_ref.resource_type}")

    def read_relationships(self, resource_ref: CloudResourceRef) -> list[CloudResourceRelationship]:
        if resource_ref.resource_type not in {"compute_instance", "server"}:
            return []
        server = self._client().get_server(resource_ref.external_id)
        source = _hetzner_resource_ref("compute_instance", server.get("id"), server.get("name"))
        relationships: list[CloudResourceRelationship] = []
        for firewall_id in sorted(attached_firewall_ids(server)):
            relationships.append(
                CloudResourceRelationship(
                    source=source,
                    relationship_type="attached_firewall",
                    target=_hetzner_resource_ref("firewall_policy", firewall_id),
                )
            )
        return relationships

    def normalize_firewall(self, raw: dict[str, Any]) -> FirewallPolicy:
        return hetzner_firewall_policy(raw)

    def plan_change(
        self,
        control_result: CloudControlResult | dict[str, Any],
        desired_state: dict[str, Any],
    ) -> CloudRemediationPlan:
        firewall = (
            desired_state.get("firewall")
            or (desired_state.get("pre_state") or {}).get("firewall")
            or (desired_state.get("evidence") or {}).get("firewall")
        )
        if not firewall:
            raise HetznerValidationError("Firewall state is required to plan a Hetzner network change")
        admin_cidrs = (
            desired_state.get("admin_ssh_cidrs")
            or desired_state.get("source_cidrs")
            or desired_state.get("source_ips")
        )
        plan = build_firewall_plan(firewall, admin_cidrs)
        resource_ref = _hetzner_resource_ref("firewall_policy", plan["firewall_id"])
        apply_mode = desired_state.get("apply_mode") or "iac_patch"
        iac_patch = desired_state.get("iac_patch")
        if iac_patch is None and apply_mode == "iac_patch":
            iac_patch = {
                "tool": "terraform",
                "variable": "admin_ssh_cidrs",
                "value": plan["admin_ssh_cidrs"],
            }
        return CloudRemediationPlan(
            provider=self.provider,
            apply_mode=apply_mode,
            resource_ref=resource_ref,
            action=plan["action"],
            desired_state={"rules": plan["proposed_rules"]},
            diff=plan["diff"],
            iac_patch=iac_patch,
            raw_plan=plan,
        )

    def apply_change(self, change_request: CloudRemediationPlan | dict[str, Any]) -> ApplyResult:
        try:
            if isinstance(change_request, CloudRemediationPlan):
                resource_ref = change_request.resource_ref
                rules = change_request.raw_plan.get("proposed_rules") or change_request.desired_state.get("rules")
            else:
                resource_ref = _hetzner_resource_ref(
                    "firewall_policy",
                    change_request.get("firewall_id") or change_request.get("resource_ref", {}).get("external_id"),
                )
                rules = (
                    change_request.get("proposed_rules")
                    or (change_request.get("desired_state") or {}).get("rules")
                    or (change_request.get("proposed_diff") or {}).get("proposed_rules")
                )
            if not rules:
                raise HetznerValidationError("Proposed firewall rules are required for direct Hetzner apply")
            result = self._client().set_firewall_rules(resource_ref.external_id, rules)
            return ApplyResult(
                success=True,
                provider=self.provider,
                resource_ref=resource_ref,
                status="applied",
                raw=result,
            )
        except Exception as exc:
            return ApplyResult(
                success=False,
                provider=self.provider,
                status="failed",
                error=str(exc),
            )
