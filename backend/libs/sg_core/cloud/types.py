"""Provider-neutral cloud adapter types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class CloudProviderAuth:
    provider: str
    method: str
    secret: str | None = None
    secret_ref: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CloudTargetSelector:
    provider: str
    resource_type: str
    external_id: str | None = None
    name: str | None = None
    labels: dict[str, str] = field(default_factory=dict)
    relationships: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CloudResourceRef:
    provider: str
    resource_type: str
    external_id: str
    name: str | None = None


@dataclass(frozen=True)
class CloudResource:
    ref: CloudResourceRef
    raw: dict[str, Any] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CloudResourceRelationship:
    source: CloudResourceRef
    relationship_type: str
    target: CloudResourceRef
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FirewallRule:
    direction: str
    protocol: str
    port: str | None = None
    source_cidrs: list[str] = field(default_factory=list)
    destination_cidrs: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FirewallPolicy:
    ref: CloudResourceRef
    rules: list[FirewallRule] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderHealth:
    success: bool
    status: str
    provider: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CloudControlResult:
    control_id: str
    provider: str
    resource_ref: CloudResourceRef
    status: str
    severity: str
    title: str
    description: str
    remediation: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CloudFinding:
    control_result: CloudControlResult
    fingerprint: str
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CloudRemediationPlan:
    provider: str
    apply_mode: str
    resource_ref: CloudResourceRef
    action: str
    desired_state: dict[str, Any] = field(default_factory=dict)
    diff: dict[str, Any] = field(default_factory=dict)
    iac_patch: dict[str, Any] | None = None
    raw_plan: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ApplyResult:
    success: bool
    provider: str
    resource_ref: CloudResourceRef | None = None
    status: str = "unknown"
    raw: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@runtime_checkable
class CloudProviderAdapter(Protocol):
    provider: str

    def validate_auth(self, auth: CloudProviderAuth | dict[str, Any]) -> ProviderHealth:
        ...

    def discover(self, selector: CloudTargetSelector) -> list[CloudResource]:
        ...

    def read_resource(self, resource_ref: CloudResourceRef) -> CloudResource:
        ...

    def read_relationships(self, resource_ref: CloudResourceRef) -> list[CloudResourceRelationship]:
        ...

    def normalize_firewall(self, raw: dict[str, Any]) -> FirewallPolicy:
        ...

    def plan_change(
        self,
        control_result: CloudControlResult | dict[str, Any],
        desired_state: dict[str, Any],
    ) -> CloudRemediationPlan:
        ...

    def apply_change(self, change_request: CloudRemediationPlan | dict[str, Any]) -> ApplyResult:
        ...
