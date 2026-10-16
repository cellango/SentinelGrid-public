"""Provider baseline state loading for cloud-resource scans."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping

from sg_core.cloud.targets import CloudTargetContext


@dataclass(frozen=True)
class CloudBaselineState:
    """Resolved cloud state for one provider target baseline scan."""

    cloud_account_id: str
    account_metadata: dict[str, Any]
    target_metadata: dict[str, Any]
    server: dict[str, Any]
    firewall: dict[str, Any]
    scope_hash: str


def load_cloud_baseline_state(
    provider: str,
    account: Mapping[str, Any],
    payload: dict[str, Any],
    target_context: CloudTargetContext,
) -> CloudBaselineState:
    """Resolve resource/firewall state for a cloud resource baseline scan."""

    metadata = as_dict(account.get("metadata"))
    loader = CLOUD_BASELINE_STATE_LOADERS.get(provider)
    if loader is not None:
        return loader(account, metadata, payload, target_context)
    return metadata_cloud_baseline_state(account, metadata, payload, target_context)


def metadata_cloud_baseline_state(
    account: Mapping[str, Any],
    metadata: dict[str, Any],
    payload: dict[str, Any],
    target_context: CloudTargetContext,
) -> CloudBaselineState:
    """Load generic provider state from account metadata or scan payload snapshots."""

    target_metadata = {**target_context.metadata(), **metadata}
    server = (
        metadata.get("server_snapshot")
        or metadata.get("resource_snapshot")
        or payload.get("server")
        or payload.get("resource")
    )
    firewall = (
        metadata.get("firewall_snapshot")
        or metadata.get("firewall_policy_snapshot")
        or payload.get("firewall")
        or payload.get("firewall_policy")
    )
    if not isinstance(server, dict) or not isinstance(firewall, dict):
        raise RuntimeError(
            f"Cloud baseline state for provider {target_context.provider} requires resource and firewall snapshots"
        )

    return CloudBaselineState(
        cloud_account_id=str(account["id"]),
        account_metadata=metadata,
        target_metadata=target_metadata,
        server=server,
        firewall=firewall,
        scope_hash=metadata.get("scope_hash") or generic_cloud_scope_hash(target_context, server, firewall),
    )


def hetzner_cloud_baseline_state(
    account: Mapping[str, Any],
    metadata: dict[str, Any],
    payload: dict[str, Any],
    target_context: CloudTargetContext,
) -> CloudBaselineState:
    """Load Hetzner pilot state while preserving provider-specific scope hashing."""

    from sg_core.cloud.adapters.hetzner import pilot_target, scope_hash

    pilot_target(
        server_id=target_context.account_id,
        server_name=target_context.account_name,
        firewall_id=target_context.relationship_external_id("firewall_policy"),
    )
    target_metadata = {**target_context.metadata(), **metadata}
    server = metadata.get("server_snapshot") or fallback_hetzner_server(account, metadata, target_context)
    firewall = metadata.get("firewall_snapshot") or fallback_hetzner_firewall(metadata, payload, target_context)
    return CloudBaselineState(
        cloud_account_id=str(account["id"]),
        account_metadata=metadata,
        target_metadata=target_metadata,
        server=server,
        firewall=firewall,
        scope_hash=metadata.get("scope_hash") or scope_hash(server, firewall),
    )


CLOUD_BASELINE_STATE_LOADERS = {
    "hetzner": hetzner_cloud_baseline_state,
}


def generic_cloud_scope_hash(
    target_context: CloudTargetContext,
    server: dict[str, Any],
    firewall: dict[str, Any],
) -> str:
    payload = {
        "target": {
            "provider": target_context.provider,
            "target_id": target_context.target_id,
            "resource_type": target_context.resource_ref.resource_type,
            "resource_external_id": target_context.resource_ref.external_id,
            "firewall_id": target_context.relationship_external_id("firewall_policy"),
        },
        "server": server,
        "firewall": firewall,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def fallback_hetzner_server(
    account: Mapping[str, Any],
    metadata: dict[str, Any],
    target_context: CloudTargetContext,
) -> dict[str, Any]:
    firewall_id = metadata.get("firewall_id") or target_context.relationship_external_id("firewall_policy")
    return {
        "id": account["account_id"],
        "name": account["account_name"] or metadata.get("server_name") or target_context.account_name,
        "labels": dict(target_context.labels),
        "public_net": {
            "ipv4": {"ip": metadata.get("server_ipv4") or target_context.expected_ipv4},
            "firewalls": [{"id": maybe_int(firewall_id)}] if firewall_id else [],
        },
        "backups": bool(metadata.get("backups_enabled", False)),
    }


def fallback_hetzner_firewall(
    metadata: dict[str, Any],
    payload: dict[str, Any],
    target_context: CloudTargetContext,
) -> dict[str, Any]:
    health = as_dict(metadata.get("health"))
    health_firewall = as_dict(health.get("firewall"))
    firewall_id = metadata.get("firewall_id") or target_context.relationship_external_id("firewall_policy")
    firewall_name = metadata.get("firewall_name") or target_context.relationship_name("firewall_policy")
    return {
        "id": maybe_int(firewall_id),
        "name": firewall_name,
        "rules": payload.get("firewall_rules") or health_firewall.get("rules") or [],
        "applied_to": [{"type": "server", "server": {"id": maybe_int(target_context.account_id)}}],
    }


def as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def maybe_int(value: Any) -> int | Any:
    text_value = str(value)
    return int(text_value) if text_value.isdigit() else value
