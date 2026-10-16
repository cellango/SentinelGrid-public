"""Provider-neutral cloud baseline evaluation, persistence, and remediation helpers."""

from __future__ import annotations

from typing import Any

from sg_core.cloud.controls import (
    ADMIN_PORT_OPEN_TO_WORLD_CONTROL,
    EXPECTED_PUBLIC_PORTS_CONTROL,
    WORLD_CIDRS,
    admin_port_open_to_world,
    expected_public_tcp_ports,
    rule_allows_tcp_port,
)
from sg_core.cloud.targets import CloudTargetContext
from sg_core.cloud.types import CloudControlResult, CloudProviderAdapter, FirewallPolicy, FirewallRule


ADMIN_PORT_RESTRICT_ACTION = "network_admin_port_restrict"
BACKUPS_DISABLED_CONTROL = "resilience.backups_disabled"
PUBLIC_TLS_PROXY_LOCAL_APPS_CONTROL = "edge.public_tls_proxy_local_apps"


def cloud_resource_baseline_checks(
    adapter: CloudProviderAdapter,
    server: dict[str, Any],
    firewall: dict[str, Any],
    target_context: CloudTargetContext,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate the first provider-neutral cloud resource baseline controls."""

    metadata = metadata or {}
    policy = adapter.normalize_firewall(firewall)
    resource_name = _resource_name(server, target_context)
    admin_port = admin_tcp_port_for_target(target_context, metadata)
    expected_public_ports = expected_public_tcp_ports_for_target(target_context, metadata)

    admin_control = admin_port_open_to_world(
        policy,
        port=admin_port,
        resource_ref=target_context.resource_ref,
        resource_name=resource_name,
    )
    public_ports_control = expected_public_tcp_ports(policy, expected_public_ports)
    backups_enabled = bool(
        metadata.get("backups_enabled")
        or server.get("backups")
        or server.get("backup_window")
    )

    edge_service = public_tls_edge_service(metadata, target_context)
    return [
        _control_check(
            admin_control,
            check_id=admin_port_world_check_id(target_context.provider, admin_port),
            title=admin_port_world_title(resource_name, admin_port),
            category="network_exposure",
            service=f"{target_context.provider}_firewall",
        ),
        {
            "check_id": f"{target_context.provider}-backups-disabled",
            "control_id": BACKUPS_DISABLED_CONTROL,
            "severity": "medium",
            "status": "pass" if backups_enabled else "recommendation",
            "title": f"Backups are disabled for {resource_name}",
            "description": f"Backups are disabled for {resource_name}.",
            "remediation": "Review monthly cost impact before enabling backups.",
            "category": "resilience",
            "service": f"{target_context.provider}_server",
            "finding_enabled": False,
        },
        _control_check(
            public_ports_control,
            check_id=expected_public_ports_check_id(target_context.provider, expected_public_ports),
            title=expected_public_ports_title(expected_public_ports),
            description=expected_public_ports_description(target_context, expected_public_ports),
            remediation="No action required while this resource remains an expected public edge.",
            category="expected_exposure",
            service=f"{target_context.provider}_firewall",
        ),
        {
            "check_id": tls_edge_local_apps_check_id(target_context.provider, edge_service),
            "control_id": PUBLIC_TLS_PROXY_LOCAL_APPS_CONTROL,
            "severity": "info",
            "status": "pass" if public_tls_edge_local_apps_pass(metadata, target_context) else "unknown",
            "title": tls_edge_local_apps_title(edge_service),
            "description": tls_edge_local_apps_description(edge_service),
            "remediation": f"Verify {edge_service or 'edge proxy'} and app port metadata if this check is unknown.",
            "category": "edge_architecture",
            "service": edge_service or "edge_proxy",
            "finding_enabled": False,
        },
    ]


def active_cloud_findings_from_checks(
    checks: list[dict[str, Any]],
    target_context: CloudTargetContext,
    *,
    scanner_id: str,
    server: dict[str, Any] | None = None,
    firewall: dict[str, Any] | None = None,
    firewall_policy: FirewallPolicy | None = None,
) -> list[dict[str, Any]]:
    """Build findings from non-passing cloud baseline checks."""

    server = server or {}
    firewall = firewall or {}
    firewall_id = (
        target_context.relationship_external_id("firewall_policy")
        or str(firewall.get("id") or "")
        or None
    )
    resource_id = target_context.asset_external_id
    if firewall_id:
        resource_id = f"{resource_id}:firewall:{firewall_id}"

    rules = firewall.get("rules")
    if rules is None and firewall_policy is not None:
        rules = firewall_rule_payloads(firewall_policy)

    findings: list[dict[str, Any]] = []
    for check in checks:
        if check.get("status") not in {"open", "recommendation"}:
            continue
        if check.get("finding_enabled") is False:
            continue
        findings.append(
            {
                "source_tool": scanner_id,
                "severity": check.get("severity"),
                "category": check.get("category"),
                "title": check.get("title"),
                "description": check.get("description"),
                "remediation": check.get("remediation"),
                "asset_type": target_context.asset_type,
                "external_id": resource_id,
                "fingerprint": f"{check.get('check_id')}:{resource_id}",
                "tags": {
                    "provider": target_context.provider,
                    "target_id": target_context.target_id,
                    "resource": target_context.account_name or target_context.account_id,
                    "server": target_context.account_name or target_context.account_id,
                },
                "raw_payload": {
                    "check": check,
                    "resource_ref": {
                        "provider": target_context.resource_ref.provider,
                        "resource_type": target_context.resource_ref.resource_type,
                        "external_id": target_context.resource_ref.external_id,
                        "name": target_context.resource_ref.name,
                    },
                    "server_id": server.get("id") or target_context.account_id,
                    "firewall_id": firewall_id,
                    "rules": rules or [],
                },
                "evidence": {
                    "server_id": server.get("id") or target_context.account_id,
                    "server_name": server.get("name") or target_context.account_name,
                    "firewall_id": firewall_id,
                    "world_cidrs": sorted(WORLD_CIDRS),
                    **(check.get("evidence") or {}),
                },
            }
        )
    return findings


def summarize_cloud_baseline(
    checks: list[dict[str, Any]],
    target_context: CloudTargetContext,
    *,
    change_request_id: str | None = None,
    scope: str | None = None,
    scanner_id: str,
) -> dict[str, Any]:
    active = [check for check in checks if check.get("status") == "open"]
    recommendations = [check for check in checks if check.get("status") == "recommendation"]
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
    severity = "info"
    if active:
        severity = max(active, key=lambda item: severity_rank.get(item.get("severity"), 0)).get("severity") or "info"

    return {
        "scanner_id": scanner_id,
        "provider": target_context.provider,
        "server_id": target_context.account_id,
        "server_name": target_context.account_name,
        "firewall_id": target_context.relationship_external_id("firewall_policy"),
        "target_ref": target_context.target_id,
        "findings": len(active),
        "recommendations": len(recommendations),
        "severity": severity,
        "checks": checks,
        "change_request_id": change_request_id,
        "scope_hash": scope,
    }


def admin_port_open_from_checks(checks: list[dict[str, Any]], *, port: int = 22) -> bool:
    return any(
        check.get("control_id") == ADMIN_PORT_OPEN_TO_WORLD_CONTROL
        and check.get("status") == "open"
        and (check.get("evidence") or {}).get("port", port) == port
        for check in checks
    )


def admin_tcp_port_for_target(
    target_context: CloudTargetContext,
    metadata: dict[str, Any] | None = None,
) -> int:
    exposure = _expected_exposure(target_context, metadata)
    for rule in exposure.get("admin") or []:
        if not isinstance(rule, dict):
            continue
        if str(rule.get("protocol") or "").lower() != "tcp":
            continue
        port = _int_or_none(rule.get("port"))
        if port is not None:
            return port
    return 22


def expected_public_tcp_ports_for_target(
    target_context: CloudTargetContext,
    metadata: dict[str, Any] | None = None,
) -> tuple[int, ...]:
    exposure = _expected_exposure(target_context, metadata)
    ports: list[int] = []
    for rule in exposure.get("public") or []:
        if not isinstance(rule, dict):
            continue
        if str(rule.get("protocol") or "").lower() != "tcp":
            continue
        port = _int_or_none(rule.get("port"))
        if port is not None:
            ports.append(port)

    if not ports:
        edge_ports = public_tls_edge(target_context, metadata).get("public_ports") or []
        ports = [port for port in (_int_or_none(value) for value in edge_ports) if port is not None]

    return tuple(sorted(set(ports or [80, 443])))


def public_tls_edge_local_apps_pass(
    metadata: dict[str, Any] | None = None,
    target_context: CloudTargetContext | None = None,
) -> bool:
    edge = public_tls_edge(target_context, metadata)
    return (
        bool(edge.get("service"))
        and bool(edge.get("public_ports"))
        and bool(edge.get("expected_local_app_ports"))
    )


def public_tls_edge_service(
    metadata: dict[str, Any] | None = None,
    target_context: CloudTargetContext | None = None,
) -> str | None:
    service = public_tls_edge(target_context, metadata).get("service")
    return str(service) if service else None


def public_tls_edge(
    target_context: CloudTargetContext | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    edge = metadata.get("public_tls_edge")
    if isinstance(edge, dict):
        return edge
    edge = (metadata.get("edge") or {}).get("tls_proxy")
    if isinstance(edge, dict):
        return edge
    if target_context is not None:
        edge = (target_context.edge or {}).get("tls_proxy")
        if isinstance(edge, dict):
            return edge
    return {}


def admin_port_world_check_id(provider: str, port: int) -> str:
    if port == 22:
        return f"{provider}-ssh-world"
    return f"{provider}-admin-port-{port}-world"


def expected_public_ports_check_id(provider: str, ports: tuple[int, ...]) -> str:
    if set(ports) == {80, 443}:
        return f"{provider}-web-public-expected"
    suffix = "-".join(str(port) for port in ports)
    return f"{provider}-public-ports-{suffix}-expected"


def tls_edge_local_apps_check_id(provider: str, service: str | None) -> str:
    if service:
        return f"{provider}-{service.lower()}-local-app-ports"
    return f"{provider}-tls-edge-local-app-ports"


def admin_port_world_title(resource_name: str, port: int) -> str:
    if port == 22:
        return f"SSH is open to the world on {resource_name}"
    return f"Administrative TCP/{port} is open to the world on {resource_name}"


def expected_public_ports_title(ports: tuple[int, ...]) -> str:
    if set(ports) == {80, 443}:
        return "HTTP and HTTPS public access is expected"
    return f"Expected public TCP ports are declared: {', '.join(str(port) for port in ports)}"


def tls_edge_local_apps_title(service: str | None) -> str:
    if service:
        return f"{service.title()} terminates public TLS while app ports stay local-only"
    return "Public TLS edge proxies only to declared local app ports"


def tls_edge_local_apps_description(service: str | None) -> str:
    if service:
        return f"{service.title()} is expected to publish TLS and proxy to local application ports."
    return "The public TLS edge is expected to proxy traffic to local application ports."


def expected_public_ports_description(
    target_context: CloudTargetContext,
    ports: tuple[int, ...],
) -> str:
    resource_name = target_context.account_name or target_context.account_id
    port_list = ", ".join(f"TCP/{port}" for port in ports)
    return f"{resource_name} is declared as a public resource and should keep {port_list} internet-facing."


def _control_check(
    control: CloudControlResult,
    *,
    check_id: str,
    title: str | None = None,
    description: str | None = None,
    remediation: str | None = None,
    category: str,
    service: str,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "control_id": control.control_id,
        "severity": control.severity,
        "status": control.status,
        "title": title or control.title,
        "description": description or control.description,
        "remediation": remediation if remediation is not None else control.remediation,
        "category": category,
        "service": service,
        "evidence": control.evidence,
        "finding_enabled": True,
    }


def _resource_name(server: dict[str, Any], target_context: CloudTargetContext) -> str:
    return str(server.get("name") or target_context.account_name or target_context.account_id)


def _expected_exposure(
    target_context: CloudTargetContext,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    exposure = metadata.get("expected_exposure")
    if isinstance(exposure, dict):
        return exposure
    return target_context.expected_exposure or {}


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def posture_status(check: dict[str, Any]) -> str:
    """Map a normalized control check status to persisted posture status."""

    return "open" if check.get("status") in {"open", "recommendation"} else "resolved"


def posture_remediation_status(check: dict[str, Any]) -> str:
    status = check.get("status")
    if status == "recommendation":
        return "recommendation"
    return posture_status(check)


def posture_framework(target_context: CloudTargetContext) -> str:
    return f"SentinelGrid {target_context.provider.title()} Baseline"


def posture_remediation_plan(check: dict[str, Any], target_context: CloudTargetContext) -> dict[str, Any]:
    return {
        "source": f"{target_context.provider}_{target_context.mode or 'target'}_baseline",
        "target_id": target_context.target_id,
        "provider": target_context.provider,
        "resource_ref": {
            "provider": target_context.resource_ref.provider,
            "resource_type": target_context.resource_ref.resource_type,
            "external_id": target_context.resource_ref.external_id,
            "name": target_context.resource_ref.name,
        },
        "check_status": check.get("status"),
    }


def fixed_target_ref(target_context: CloudTargetContext, relationship_type: str = "firewall_policy") -> str:
    relationship_id = target_context.relationship_external_id(relationship_type)
    if relationship_id:
        return f"{relationship_type}:{relationship_id}"
    return f"{target_context.resource_ref.resource_type}:{target_context.resource_ref.external_id}"


def admin_port_change_guidance(
    target_context: CloudTargetContext,
    change_request_id: str,
    *,
    port: int = 22,
) -> dict[str, Any]:
    resource_name = target_context.account_name or target_context.account_id
    return {
        "summary": f"Narrow admin access on {resource_name} to approved CIDRs.",
        "steps": [
            "Confirm the admin access CIDRs for operators.",
            "Approve the infrastructure change request.",
            "Apply the firewall update and re-run the cloud baseline scan.",
        ],
        "validation": [
            f"TCP/{port} no longer allows 0.0.0.0/0 or ::/0.",
            "Expected public web and ICMP exposure remains present where declared.",
        ],
        "change_request_id": change_request_id,
        "target_id": target_context.target_id,
        "provider": target_context.provider,
    }


def admin_port_change_description(target_context: CloudTargetContext) -> str:
    resource_name = target_context.account_name or target_context.account_id
    return f"Narrow admin network exposure for {resource_name}"


def admin_port_cidrs_required_plan(
    adapter: CloudProviderAdapter,
    firewall: dict[str, Any],
    target_context: CloudTargetContext,
    *,
    port: int = 22,
) -> dict[str, Any]:
    """Build a plan shell when admin CIDRs are not known yet."""

    policy = adapter.normalize_firewall(firewall)
    changed = []
    for rule in policy.rules:
        if rule_allows_tcp_port(rule, port):
            changed.append(
                {
                    "protocol": rule.protocol,
                    "port": rule.port,
                    "before_source_ips": list(rule.source_cidrs),
                    "before_source_cidrs": list(rule.source_cidrs),
                    "after_source_ips": [],
                    "after_source_cidrs": [],
                    "requires_admin_cidrs": True,
                }
            )

    return {
        "provider": target_context.provider,
        "action": "replace_firewall_rules",
        "resource_ref": {
            "provider": policy.ref.provider,
            "resource_type": policy.ref.resource_type,
            "external_id": policy.ref.external_id,
            "name": policy.ref.name,
        },
        "server_id": target_context.account_id,
        "firewall_id": target_context.relationship_external_id("firewall_policy"),
        "admin_port": port,
        "admin_cidrs_required": True,
        "admin_ssh_cidrs_required": port == 22,
        "pre_rules": firewall_rule_payloads(policy),
        "proposed_rules": None,
        "diff": {"changed": changed},
        "recommendations": [
            {
                "id": f"{target_context.provider}-backups-disabled",
                "severity": "medium",
                "automatic": False,
                "reason": "Backups are recommendation-only in v1 because enabling them can change monthly cost.",
            }
        ],
    }


def firewall_rule_payloads(policy: FirewallPolicy) -> list[dict[str, Any]]:
    return [_firewall_rule_payload(rule) for rule in policy.rules]


def _firewall_rule_payload(rule: FirewallRule) -> dict[str, Any]:
    if rule.raw:
        return dict(rule.raw)
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
