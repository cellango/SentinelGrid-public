"""Adapter-backed cloud onboarding helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from sg_core.cloud.adapters import create_cloud_adapter
from sg_core.cloud.registry import canonical_provider_id, default_cloud_target_id
from sg_core.cloud.remediation import CloudRemediationError, normalize_cidrs
from sg_core.cloud.targets import CloudTargetContext, cloud_target_context


AdapterFactory = Callable[..., Any]


class CloudConnectionValidationError(ValueError):
    """Raised when a cloud connection cannot be validated."""

    def __init__(self, detail: Any):
        super().__init__(str(detail))
        self.detail = detail


@dataclass(frozen=True)
class CloudConnectionProbe:
    """Validated cloud connection state ready for persistence."""

    provider: str
    account_id: str
    account_name: str | None
    service_principal_id: str
    secret: str
    metadata: dict[str, Any]
    health: dict[str, Any]
    state: dict[str, Any]
    target_context: CloudTargetContext


def validate_cloud_connection(
    provider_id: str,
    *,
    config: dict[str, Any] | None = None,
    account_id: str | None = None,
    account_name: str | None = None,
    secret: str | None = None,
    adapter_factory: AdapterFactory = create_cloud_adapter,
) -> CloudConnectionProbe:
    """Validate an adapter-backed cloud connection.

    This path is intentionally implemented for the first adapter-backed provider
    only. Legacy AWS/Azure/GCP onboarding still uses their existing service
    testers until those providers get full adapters.
    """

    provider = canonical_provider_id(provider_id)
    if provider == "hetzner":
        return _validate_hetzner_connection(
            config=config or {},
            account_id=account_id,
            account_name=account_name,
            secret=secret,
            adapter_factory=adapter_factory,
        )
    raise CloudConnectionValidationError(f"Cloud provider {provider} does not have adapter-backed onboarding")


def refresh_cloud_connection_state(
    provider_id: str,
    *,
    account_id: str,
    account_name: str | None,
    secret: str,
    metadata: dict[str, Any] | None = None,
    adapter_factory: AdapterFactory = create_cloud_adapter,
) -> CloudConnectionProbe:
    """Refresh health/state for a previously connected adapter-backed target."""

    cfg = dict(metadata or {})
    cfg["api_token"] = secret
    cfg.setdefault("server_id", account_id)
    if account_name:
        cfg.setdefault("server_name", account_name)
    return validate_cloud_connection(
        provider_id,
        config=cfg,
        account_id=account_id,
        account_name=account_name,
        secret=secret,
        adapter_factory=adapter_factory,
    )


def _validate_hetzner_connection(
    *,
    config: dict[str, Any],
    account_id: str | None,
    account_name: str | None,
    secret: str | None,
    adapter_factory: AdapterFactory,
) -> CloudConnectionProbe:
    from sg_core.cloud.adapters.hetzner import (
        HETZNER_PILOT_FIREWALL_ID,
        HETZNER_PILOT_SERVER_ID,
        HETZNER_PILOT_SERVER_NAME,
        HetznerValidationError,
        pilot_target,
    )

    token = (
        secret
        or config.get("api_token")
        or config.get("hetzner_api_token")
        or config.get("token")
    )
    if not token:
        raise CloudConnectionValidationError("Hetzner API token is required")

    target_id = config.get("target_ref") or config.get("target_id") or default_cloud_target_id("hetzner")
    target_context = cloud_target_context(str(target_id) if target_id else None, provider_id="hetzner")
    server_id = str(account_id or config.get("server_id") or target_context.account_id or HETZNER_PILOT_SERVER_ID)
    server_name = str(account_name or config.get("server_name") or target_context.account_name or HETZNER_PILOT_SERVER_NAME)
    firewall_id = str(
        config.get("firewall_id")
        or target_context.relationship_external_id("firewall_policy")
        or HETZNER_PILOT_FIREWALL_ID
    )

    try:
        target = pilot_target(server_id=server_id, server_name=server_name, firewall_id=firewall_id)
        normalized_admin_cidrs = normalize_cidrs(config.get("admin_ssh_cidrs") or config.get("admin_cidrs"))
        adapter = adapter_factory("hetzner", api_token=token, target=target)
        state = adapter.read_target_state()
    except (HetznerValidationError, CloudRemediationError) as exc:
        raise CloudConnectionValidationError(str(exc)) from exc

    health = dict(state.get("health") or {})
    if not health.get("success"):
        raise CloudConnectionValidationError(
            {
                "message": "Hetzner connection did not match the configured target scope",
                "health": health,
            }
        )

    metadata = {
        **target.metadata(),
        "target_id": target_context.target_id,
        "target_manifest": target_context.metadata(),
        "admin_ssh_cidrs": normalized_admin_cidrs,
        "health": health,
        "server_snapshot": state.get("server") or {},
        "firewall_snapshot": state.get("firewall") or {},
        "scope_hash": health.get("scope_hash"),
        "connection_tested_at": _utc_now_iso(),
    }
    return CloudConnectionProbe(
        provider="hetzner",
        account_id=target.server_id,
        account_name=target.server_name,
        service_principal_id=f"hetzner-server:{target.server_id}",
        secret=token,
        metadata=metadata,
        health=health,
        state=state,
        target_context=target_context,
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

