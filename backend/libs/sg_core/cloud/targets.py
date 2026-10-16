"""Cloud target manifest normalization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sg_core.cloud.registry import canonical_provider_id, default_cloud_target_id, get_cloud_target
from sg_core.cloud.types import CloudResourceRef


@dataclass(frozen=True)
class CloudTargetContext:
    """Normalized view of a provider target manifest."""

    target_id: str
    provider: str
    environment: str | None
    mode: str | None
    resource_ref: CloudResourceRef
    expected_ipv4: str | None = None
    labels: dict[str, str] = field(default_factory=dict)
    relationships: dict[str, dict[str, Any]] = field(default_factory=dict)
    expected_exposure: dict[str, Any] = field(default_factory=dict)
    edge: dict[str, Any] = field(default_factory=dict)
    iac: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def account_id(self) -> str:
        return self.resource_ref.external_id

    @property
    def account_name(self) -> str | None:
        return self.resource_ref.name

    @property
    def asset_type(self) -> str:
        if self.resource_ref.resource_type == "compute_instance":
            return "cloud_server"
        return "cloud_resource"

    @property
    def asset_external_id(self) -> str:
        return f"{self.provider}:{_asset_ref_kind(self.resource_ref.resource_type)}:{self.resource_ref.external_id}"

    def relationship_external_id(self, relationship_type: str) -> str | None:
        relationship = self.relationships.get(relationship_type) or {}
        external_id = relationship.get("external_id")
        return str(external_id) if external_id is not None else None

    def relationship_name(self, relationship_type: str) -> str | None:
        relationship = self.relationships.get(relationship_type) or {}
        name = relationship.get("name")
        return str(name) if name is not None else None

    def metadata(self) -> dict[str, Any]:
        """Return target metadata suitable for asset/account records."""

        firewall_id = self.relationship_external_id("firewall_policy")
        firewall_name = self.relationship_name("firewall_policy")
        tls_proxy = self.edge.get("tls_proxy") if isinstance(self.edge, dict) else None
        metadata = {
            "target_id": self.target_id,
            "target_mode": self.mode,
            "provider": self.provider,
            "environment": self.environment,
            "resource": {
                "type": self.resource_ref.resource_type,
                "external_id": self.resource_ref.external_id,
                "name": self.resource_ref.name,
                "expected_ipv4": self.expected_ipv4,
                "labels": dict(self.labels),
            },
            "relationships": self.relationships,
            "expected_exposure": self.expected_exposure,
            "edge": self.edge,
            "iac": self.iac,
            "asset_type": self.asset_type,
            "asset_external_id": self.asset_external_id,
        }
        if self.resource_ref.resource_type == "compute_instance":
            metadata.update(
                {
                    "server_id": self.resource_ref.external_id,
                    "server_name": self.resource_ref.name,
                    "server_ipv4": self.expected_ipv4,
                }
            )
        if firewall_id:
            metadata["firewall_id"] = firewall_id
        if firewall_name:
            metadata["firewall_name"] = firewall_name
        if tls_proxy:
            metadata["public_tls_edge"] = tls_proxy
        if "project" in self.labels:
            metadata["project_label"] = self.labels["project"]
        if "role" in self.labels:
            metadata["role_label"] = self.labels["role"]
        return metadata


def _asset_ref_kind(resource_type: str) -> str:
    # Preserve the existing external ID shape for compute assets while the UI
    # and findings still refer to cloud servers.
    if resource_type == "compute_instance":
        return "server"
    return resource_type


def cloud_target_context(
    target_id: str | None = None,
    *,
    provider_id: str | None = None,
    target_config: dict[str, Any] | None = None,
) -> CloudTargetContext:
    """Resolve and normalize a target manifest."""

    resolved_target_id = target_id
    config = target_config
    if config is None:
        if not resolved_target_id:
            resolved_target_id = default_cloud_target_id(provider_id)
        config = get_cloud_target(resolved_target_id)
    if not config:
        raise ValueError(f"Cloud target manifest not found: {resolved_target_id or provider_id or 'default'}")

    provider = canonical_provider_id(config.get("provider") or provider_id or "")
    resource = config.get("resource") or {}
    external_id = resource.get("external_id")
    if external_id is None:
        raise ValueError(f"Cloud target {resolved_target_id or '<inline>'} is missing resource.external_id")

    resource_type = str(resource.get("type") or "cloud_resource")
    labels = {str(k): str(v) for k, v in (resource.get("labels") or {}).items()}
    return CloudTargetContext(
        target_id=str(resolved_target_id or config.get("id") or resource.get("name") or external_id),
        provider=provider,
        environment=config.get("environment"),
        mode=config.get("mode"),
        resource_ref=CloudResourceRef(
            provider=provider,
            resource_type=resource_type,
            external_id=str(external_id),
            name=resource.get("name"),
        ),
        expected_ipv4=resource.get("expected_ipv4"),
        labels=labels,
        relationships=config.get("relationships") or {},
        expected_exposure=config.get("expected_exposure") or {},
        edge=config.get("edge") or {},
        iac=config.get("iac") or {},
        raw=config,
    )

