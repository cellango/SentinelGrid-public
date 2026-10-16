"""Provider-neutral cloud control evaluation."""

from __future__ import annotations

from typing import Iterable

from sg_core.cloud.types import CloudControlResult, CloudResourceRef, FirewallPolicy, FirewallRule


WORLD_CIDRS = {"0.0.0.0/0", "::/0"}
ADMIN_PORT_OPEN_TO_WORLD_CONTROL = "network.admin_port_open_to_world"
EXPECTED_PUBLIC_PORTS_CONTROL = "network.expected_public_ports"


def port_spec_matches(port_spec: str | None, port: int) -> bool:
    if not port_spec:
        return True
    spec = str(port_spec).strip()
    if spec in {"any", "*"}:
        return True
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            try:
                if int(start) <= port <= int(end):
                    return True
            except ValueError:
                continue
        else:
            try:
                if int(part) == port:
                    return True
            except ValueError:
                continue
    return False


def rule_allows_tcp_port(rule: FirewallRule, port: int) -> bool:
    return (
        (rule.direction or "in").lower() == "in"
        and (rule.protocol or "").lower() == "tcp"
        and port_spec_matches(rule.port, port)
    )


def rule_has_world_source(rule: FirewallRule) -> bool:
    return any(source in WORLD_CIDRS for source in rule.source_cidrs)


def matching_world_tcp_rules(policy: FirewallPolicy, port: int) -> list[FirewallRule]:
    return [
        rule
        for rule in policy.rules
        if rule_allows_tcp_port(rule, port) and rule_has_world_source(rule)
    ]


def admin_port_open_to_world(
    policy: FirewallPolicy,
    *,
    port: int = 22,
    resource_ref: CloudResourceRef | None = None,
    resource_name: str | None = None,
) -> CloudControlResult:
    """Evaluate whether an administrative TCP port is internet-exposed."""

    matches = matching_world_tcp_rules(policy, port)
    ref = resource_ref or policy.ref
    label = resource_name or ref.name or ref.external_id
    status = "open" if matches else "resolved"
    return CloudControlResult(
        control_id=ADMIN_PORT_OPEN_TO_WORLD_CONTROL,
        provider=ref.provider,
        resource_ref=ref,
        status=status,
        severity="high",
        title=f"Administrative TCP/{port} is open to the world",
        description=f"{label} allows TCP/{port} from 0.0.0.0/0 or ::/0.",
        remediation="Replace administrative source CIDRs with approved operator CIDRs.",
        evidence={
            "port": port,
            "world_cidrs": sorted(WORLD_CIDRS),
            "matching_rules": [rule.raw or _rule_payload(rule) for rule in matches],
        },
    )


def public_tcp_port_expected(policy: FirewallPolicy, port: int) -> bool:
    return bool(matching_world_tcp_rules(policy, port))


def expected_public_tcp_ports(policy: FirewallPolicy, ports: Iterable[int]) -> CloudControlResult:
    missing = [port for port in ports if not public_tcp_port_expected(policy, port)]
    status = "pass" if not missing else "open"
    return CloudControlResult(
        control_id=EXPECTED_PUBLIC_PORTS_CONTROL,
        provider=policy.ref.provider,
        resource_ref=policy.ref,
        status=status,
        severity="info",
        title="Expected public TCP ports are reachable",
        description="Expected public TCP ports should remain internet-facing for this resource.",
        remediation="Restore expected public exposure only when the target is intended to be public.",
        evidence={
            "expected_ports": list(ports),
            "missing_ports": missing,
        },
    )


def _rule_payload(rule: FirewallRule) -> dict:
    return {
        "direction": rule.direction,
        "protocol": rule.protocol,
        "port": rule.port,
        "source_cidrs": rule.source_cidrs,
        "destination_cidrs": rule.destination_cidrs,
    }
