"""Provider-neutral infrastructure change request helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from sg_core.cloud.adapters import create_cloud_adapter
from sg_core.cloud.registry import canonical_provider_id
from sg_core.cloud.targets import cloud_target_context


AdapterFactory = Callable[..., Any]


class CloudChangeRequestError(ValueError):
    """Raised when a cloud infrastructure change cannot be approved or applied."""

    def __init__(self, detail: Any, status_code: int = 400):
        super().__init__(str(detail))
        self.detail = detail
        self.status_code = status_code


class UnsupportedCloudChangeProviderError(CloudChangeRequestError):
    """Raised when a provider does not yet implement change-request handling."""

    def __init__(self, provider: str, operation: str):
        super().__init__(
            f"Infrastructure change {operation} is not implemented for provider {provider}",
            status_code=501,
        )


@dataclass(frozen=True)
class CloudChangeApproval:
    """Provider-normalized approval output ready for persistence."""

    provider: str
    proposed_diff: dict[str, Any]


@dataclass(frozen=True)
class PreparedCloudChangeApply:
    """Live-validated cloud change ready for the caller's apply gate."""

    provider: str
    server_id: str
    firewall_id: str
    scope_hash: str | None
    proposed_rules: list[dict[str, Any]]
    current_server: dict[str, Any]
    current_firewall: dict[str, Any]
    current_health: dict[str, Any]
    account_metadata: dict[str, Any]
    adapter: Any = field(repr=False)
    provider_context: Any = field(repr=False)


@dataclass(frozen=True)
class CloudChangeApplyResult:
    """Applied cloud change output ready for persistence."""

    provider: str
    result_payload: dict[str, Any]
    account_metadata: dict[str, Any]


def change_request_approval_inputs(payload: Any) -> dict[str, Any]:
    """Normalize direct and nested approval inputs from API payloads."""

    nested = _value(payload, "inputs") or {}
    merged: dict[str, Any] = dict(nested) if isinstance(nested, Mapping) else {}

    direct_admin_cidrs = _value(payload, "admin_ssh_cidrs")
    if direct_admin_cidrs is not None:
        merged["admin_ssh_cidrs"] = direct_admin_cidrs

    return merged


def approval_admin_cidrs(inputs: Mapping[str, Any] | None) -> Any:
    """Return the provider-neutral admin source CIDR input, if present."""

    for key in ("admin_ssh_cidrs", "admin_cidrs", "source_cidrs", "source_ips"):
        if inputs and key in inputs:
            return inputs[key]
    return None


def prepare_cloud_change_approval(
    provider_id: str,
    *,
    pre_state: Mapping[str, Any] | None,
    proposed_diff: Mapping[str, Any] | None,
    inputs: Mapping[str, Any] | None,
    adapter_factory: AdapterFactory = create_cloud_adapter,
) -> CloudChangeApproval:
    """Prepare an approved provider change without mutating cloud state."""

    provider = canonical_provider_id(provider_id)
    if provider == "hetzner":
        return _prepare_hetzner_change_approval(
            pre_state=dict(pre_state or {}),
            proposed_diff=dict(proposed_diff or {}),
            inputs=inputs or {},
            adapter_factory=adapter_factory,
        )
    raise UnsupportedCloudChangeProviderError(provider, "approval")


def prepare_cloud_change_apply(
    provider_id: str,
    *,
    account_id: str | None,
    account_name: str | None,
    secret: str | None,
    metadata: Mapping[str, Any] | None,
    change_request: Mapping[str, Any],
    adapter_factory: AdapterFactory = create_cloud_adapter,
) -> PreparedCloudChangeApply:
    """Validate live cloud scope before the caller flips the apply gate."""

    provider = canonical_provider_id(provider_id)
    if provider == "hetzner":
        return _prepare_hetzner_change_apply(
            account_id=account_id,
            account_name=account_name,
            secret=secret,
            metadata=dict(metadata or {}),
            change_request=dict(change_request),
            adapter_factory=adapter_factory,
        )
    raise UnsupportedCloudChangeProviderError(provider, "apply")


def apply_prepared_cloud_change(prepared: PreparedCloudChangeApply) -> CloudChangeApplyResult:
    """Apply a previously live-validated cloud change."""

    provider = canonical_provider_id(prepared.provider)
    if provider == "hetzner":
        return _apply_prepared_hetzner_change(prepared)
    raise UnsupportedCloudChangeProviderError(provider, "apply")


def _prepare_hetzner_change_approval(
    *,
    pre_state: dict[str, Any],
    proposed_diff: dict[str, Any],
    inputs: Mapping[str, Any],
    adapter_factory: AdapterFactory,
) -> CloudChangeApproval:
    from sg_core.cloud.adapters.hetzner import HetznerValidationError

    admin_cidrs = approval_admin_cidrs(inputs)
    if admin_cidrs is not None:
        try:
            plan = adapter_factory("hetzner").plan_change(
                {},
                {
                    "firewall": pre_state.get("firewall") or {},
                    "admin_ssh_cidrs": admin_cidrs,
                },
            )
            proposed_diff = dict(plan.raw_plan)
        except HetznerValidationError as exc:
            raise CloudChangeRequestError(str(exc), status_code=400) from exc

    if not proposed_diff.get("proposed_rules"):
        raise CloudChangeRequestError("Admin SSH CIDRs are required before approval", status_code=400)

    return CloudChangeApproval(provider="hetzner", proposed_diff=proposed_diff)


def _prepare_hetzner_change_apply(
    *,
    account_id: str | None,
    account_name: str | None,
    secret: str | None,
    metadata: dict[str, Any],
    change_request: dict[str, Any],
    adapter_factory: AdapterFactory,
) -> PreparedCloudChangeApply:
    from sg_core.cloud.adapters.hetzner import HetznerValidationError

    if not secret:
        raise CloudChangeRequestError("Missing Hetzner API token reference", status_code=400)

    proposed_diff = change_request.get("proposed_diff") or {}
    proposed_rules = proposed_diff.get("proposed_rules") or []
    if not proposed_rules:
        raise CloudChangeRequestError(
            "Approved change request is missing proposed firewall rules",
            status_code=400,
        )

    try:
        target = _hetzner_target_from_account(account_id, account_name, metadata)
    except (HetznerValidationError, ValueError) as exc:
        raise CloudChangeRequestError(str(exc), status_code=409) from exc

    request_server_id = str(change_request.get("server_id"))
    request_firewall_id = str(change_request.get("firewall_id"))
    if request_server_id != target.server_id or request_firewall_id != target.firewall_id:
        raise CloudChangeRequestError(
            "Hetzner change request is outside the single-server pilot scope",
            status_code=409,
        )

    try:
        adapter = adapter_factory("hetzner", api_token=secret, target=target)
        state = adapter.read_target_state()
    except HetznerValidationError as exc:
        raise CloudChangeRequestError(str(exc), status_code=400) from exc

    current_server = state.get("server") or {}
    current_firewall = state.get("firewall") or {}
    current_health = state.get("health") or {}
    current_scope_hash = current_health.get("scope_hash")
    if not current_health.get("success"):
        raise CloudChangeRequestError(
            {"message": "Hetzner scope validation failed", "health": current_health},
            status_code=409,
        )
    if current_scope_hash != change_request.get("scope_hash"):
        raise CloudChangeRequestError(
            {
                "message": "Hetzner scope changed after the plan was created",
                "expected_scope_hash": change_request.get("scope_hash"),
                "current_scope_hash": current_scope_hash,
            },
            status_code=409,
        )

    return PreparedCloudChangeApply(
        provider="hetzner",
        server_id=target.server_id,
        firewall_id=target.firewall_id,
        scope_hash=current_scope_hash,
        proposed_rules=list(proposed_rules),
        current_server=current_server,
        current_firewall=current_firewall,
        current_health=current_health,
        account_metadata=metadata,
        adapter=adapter,
        provider_context=target,
    )


def _apply_prepared_hetzner_change(prepared: PreparedCloudChangeApply) -> CloudChangeApplyResult:
    from sg_core.cloud.adapters.hetzner import HetznerValidationError, health_from_state

    try:
        adapter_result = prepared.adapter.apply_change(
            {"firewall_id": prepared.firewall_id, "proposed_rules": prepared.proposed_rules}
        )
        if not adapter_result.success:
            raise HetznerValidationError(adapter_result.error or "Hetzner firewall apply failed")
    except HetznerValidationError as exc:
        raise CloudChangeRequestError(str(exc), status_code=400) from exc

    updated_firewall = {**prepared.current_firewall, "rules": prepared.proposed_rules}
    updated_health = health_from_state(prepared.current_server, updated_firewall, prepared.provider_context)
    result_payload = {
        "success": True,
        "provider": "hetzner",
        "server_id": prepared.server_id,
        "firewall_id": prepared.firewall_id,
        "scope_hash_before_apply": prepared.scope_hash,
        "scope_hash_after_apply": updated_health.get("scope_hash"),
        "hetzner_response": adapter_result.raw,
        "applied_rules": prepared.proposed_rules,
        "applied_at": _utc_now_iso(),
    }
    merged_metadata = {
        **prepared.account_metadata,
        "health": updated_health,
        "server_snapshot": prepared.current_server,
        "firewall_snapshot": updated_firewall,
        "scope_hash": updated_health.get("scope_hash"),
        "last_apply_result": result_payload,
        "last_proposed_firewall_rules": prepared.proposed_rules,
    }
    return CloudChangeApplyResult(
        provider="hetzner",
        result_payload=result_payload,
        account_metadata=merged_metadata,
    )


def _hetzner_target_from_account(account_id: str | None, account_name: str | None, metadata: dict[str, Any]) -> Any:
    from sg_core.cloud.adapters.hetzner import (
        HETZNER_PILOT_FIREWALL_ID,
        HETZNER_PILOT_SERVER_ID,
        HETZNER_PILOT_SERVER_NAME,
        pilot_target,
    )

    target_id = metadata.get("target_id") or metadata.get("target_ref")
    manifest_account_id = HETZNER_PILOT_SERVER_ID
    manifest_account_name = HETZNER_PILOT_SERVER_NAME
    manifest_firewall_id = HETZNER_PILOT_FIREWALL_ID
    if target_id:
        context = cloud_target_context(str(target_id), provider_id="hetzner")
        manifest_account_id = context.account_id
        manifest_account_name = context.account_name or manifest_account_name
        manifest_firewall_id = context.relationship_external_id("firewall_policy") or manifest_firewall_id

    return pilot_target(
        server_id=str(account_id or metadata.get("server_id") or manifest_account_id),
        server_name=str(account_name or metadata.get("server_name") or manifest_account_name),
        firewall_id=str(metadata.get("firewall_id") or manifest_firewall_id),
    )


def _value(payload: Any, key: str) -> Any:
    if isinstance(payload, Mapping):
        return payload.get(key)
    return getattr(payload, key, None)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
