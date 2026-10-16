"""Tests for registry-driven cloud onboarding normalization."""

import asyncio

from app.api import onboarding
from sg_core.cloud.adapters import (
    HetznerCloudAdapter,
    UnsupportedCloudProviderError,
    create_cloud_adapter,
    provider_has_adapter,
)
from sg_core.cloud.change_requests import (
    CloudChangeRequestError,
    apply_prepared_cloud_change,
    approval_admin_cidrs,
    change_request_approval_inputs,
    prepare_cloud_change_apply,
    prepare_cloud_change_approval,
)
from sg_core.cloud.registry import (
    CLOUD_RESOURCE_BASELINE_SCANNER_ID,
    canonical_provider_id,
    default_cloud_target_id,
    provider_registry_payload,
    resolve_scanner_alias,
)
from sg_core.cloud.onboarding import (
    CloudConnectionValidationError,
    refresh_cloud_connection_state,
    validate_cloud_connection,
)
from sg_core.cloud.targets import cloud_target_context
from sg_core.cloud.types import ApplyResult


def test_provider_registry_payload_contains_hetzner_pilot_defaults():
    payload = provider_registry_payload()
    hetzner = next(provider for provider in payload["providers"] if provider["id"] == "hetzner")

    assert hetzner["onboarding"]["default"] is True
    assert hetzner["onboarding"]["target_mode"] == "single_server"
    field_defaults = {field["name"]: field.get("default") for field in hetzner["onboarding_fields"]}
    assert field_defaults["server_id"] == "123456789"
    assert field_defaults["server_name"] == "websites-prod"
    assert field_defaults["firewall_id"] == "98765432"


def test_provider_registry_canonicalizes_google_alias_to_gcp():
    assert canonical_provider_id("google") == "gcp"
    assert canonical_provider_id("google-cloud") == "gcp"


def test_scanner_alias_resolves_hetzner_pilot_to_cloud_resource_baseline():
    resolution = resolve_scanner_alias("hetzner-single-server-baseline")

    assert resolution["alias"] is True
    assert resolution["scanner"] == CLOUD_RESOURCE_BASELINE_SCANNER_ID
    assert resolution["target"] == "websites-prod"


def test_cloud_target_context_normalizes_websites_prod_manifest():
    assert default_cloud_target_id() == "websites-prod"

    target = cloud_target_context("websites-prod")

    assert target.provider == "hetzner"
    assert target.account_id == "123456789"
    assert target.account_name == "websites-prod"
    assert target.relationship_external_id("firewall_policy") == "98765432"
    assert target.asset_type == "cloud_server"
    assert target.asset_external_id == "hetzner:server:123456789"
    assert target.metadata()["public_tls_edge"]["service"] == "caddy"


class _FakeHetznerOnboardingAdapter:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def read_target_state(self):
        return {
            "server": {"id": 123456789, "name": "websites-prod"},
            "firewall": {"id": 98765432, "rules": []},
            "health": {"success": True, "status": "healthy", "scope_hash": "scope-123"},
        }


def _fake_adapter_factory(provider, **kwargs):
    assert provider == "hetzner"
    return _FakeHetznerOnboardingAdapter(**kwargs)


def _hetzner_server():
    return {
        "id": 123456789,
        "name": "websites-prod",
        "labels": {"project": "websites", "role": "web"},
        "public_net": {
            "ipv4": {"ip": "203.0.113.42"},
            "firewalls": [{"id": 98765432}],
        },
        "backups": False,
    }


def _hetzner_firewall():
    return {
        "id": 98765432,
        "name": "websites-prod-firewall",
        "rules": [
            {"direction": "in", "protocol": "icmp", "source_ips": ["0.0.0.0/0", "::/0"]},
            {"direction": "in", "protocol": "tcp", "port": "22", "source_ips": ["0.0.0.0/0", "::/0"]},
            {"direction": "in", "protocol": "tcp", "port": "80", "source_ips": ["0.0.0.0/0", "::/0"]},
            {"direction": "in", "protocol": "tcp", "port": "443", "source_ips": ["0.0.0.0/0", "::/0"]},
        ],
        "applied_to": [{"type": "server", "server": {"id": 123456789}}],
    }


class _FakePlan:
    def __init__(self, raw_plan):
        self.raw_plan = raw_plan


class _FakeHetznerChangeAdapter:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def plan_change(self, control_result, desired_state):
        firewall = desired_state["firewall"]
        proposed_rules = []
        for rule in firewall.get("rules") or []:
            next_rule = dict(rule)
            if next_rule.get("protocol") == "tcp" and str(next_rule.get("port")) == "22":
                next_rule["source_ips"] = list(desired_state["admin_ssh_cidrs"])
            proposed_rules.append(next_rule)
        return _FakePlan(
            {
                "provider": "hetzner",
                "action": "replace_firewall_rules",
                "proposed_rules": proposed_rules,
                "admin_ssh_cidrs": list(desired_state["admin_ssh_cidrs"]),
            }
        )

    def read_target_state(self):
        return {
            "server": _hetzner_server(),
            "firewall": _hetzner_firewall(),
            "health": {"success": True, "status": "healthy", "scope_hash": "scope-123"},
        }

    def apply_change(self, change_request):
        return ApplyResult(
            success=True,
            provider="hetzner",
            status="applied",
            raw={"action": {"status": "running"}},
        )


def _fake_change_adapter_factory(provider, **kwargs):
    assert provider == "hetzner"
    return _FakeHetznerChangeAdapter(**kwargs)


def test_adapter_backed_cloud_connection_builds_persistable_metadata():
    connection = validate_cloud_connection(
        "hcloud",
        config={
            "api_token": "hcloud-token",
            "server_id": "123456789",
            "server_name": "websites-prod",
            "firewall_id": "98765432",
            "admin_ssh_cidrs": "203.0.113.10/32",
        },
        adapter_factory=_fake_adapter_factory,
    )

    assert connection.provider == "hetzner"
    assert connection.account_id == "123456789"
    assert connection.account_name == "websites-prod"
    assert connection.service_principal_id == "hetzner-server:123456789"
    assert connection.health["status"] == "healthy"
    assert connection.metadata["target_id"] == "websites-prod"
    assert connection.metadata["admin_ssh_cidrs"] == ["203.0.113.10/32"]
    assert connection.metadata["target_manifest"]["asset_external_id"] == "hetzner:server:123456789"


def test_adapter_backed_cloud_connection_requires_secret():
    try:
        validate_cloud_connection("hetzner", config={}, adapter_factory=_fake_adapter_factory)
    except CloudConnectionValidationError as exc:
        assert "API token is required" in str(exc)
    else:
        raise AssertionError("Expected missing Hetzner token to fail")


def test_cloud_connection_health_refresh_reuses_stored_target_metadata():
    connection = refresh_cloud_connection_state(
        "hetzner",
        account_id="123456789",
        account_name="websites-prod",
        secret="hcloud-token",
        metadata={"firewall_id": "98765432", "admin_ssh_cidrs": ["203.0.113.10/32"]},
        adapter_factory=_fake_adapter_factory,
    )

    assert connection.health["scope_hash"] == "scope-123"
    assert connection.metadata["firewall_id"] == "98765432"


def test_cloud_adapter_factory_resolves_hetzner_aliases():
    assert provider_has_adapter("hetzner") is True
    assert provider_has_adapter("hcloud") is True
    assert isinstance(create_cloud_adapter("hcloud"), HetznerCloudAdapter)


def test_cloud_adapter_factory_reports_unimplemented_registry_providers():
    assert provider_has_adapter("aws") is False
    try:
        create_cloud_adapter("aws")
    except UnsupportedCloudProviderError as exc:
        assert "aws" in str(exc)
    else:
        raise AssertionError("Expected AWS to be unimplemented in the adapter factory")


def test_generic_cloud_connection_normalizes_gcp_registry_fields():
    request = onboarding.CloudConnectionRequest(
        cloud_provider="google",
        config={
            "project_id": "web-prod-123",
            "service_account_email": "sentinelgrid-monitor@web-prod-123.iam.gserviceaccount.com",
            "service_account_key": {"type": "service_account"},
        },
    )

    normalized = onboarding._normalize_cloud_connection_request(request)

    assert normalized.cloud_provider == "gcp"
    assert normalized.account_id == "web-prod-123"
    assert normalized.service_principal_id == "sentinelgrid-monitor@web-prod-123.iam.gserviceaccount.com"
    assert normalized.service_principal_secret == '{"type": "service_account"}'
    assert normalized.metadata["project_id"] == "web-prod-123"


def test_connect_cloud_dispatches_adapter_backed_provider(monkeypatch):
    calls = {}

    async def fake_connect(request_data, request, customer_id, db):
        calls["provider"] = request_data.cloud_provider
        calls["customer_id"] = customer_id
        calls["db"] = db
        return onboarding.CloudConnectionResponse(
            success=True,
            cloud_account_id="cloud-account-123",
            status="connected",
            message="adapter target connected",
        )

    monkeypatch.setattr(onboarding, "_connect_adapter_backed_cloud", fake_connect)

    response = asyncio.run(
        onboarding.connect_cloud(
            onboarding.CloudConnectionRequest(cloud_provider="hcloud"),
            request=object(),
            customer_id="tenant-123",
            db=object(),
        )
    )

    assert response.cloud_account_id == "cloud-account-123"
    assert calls["provider"] == "hetzner"
    assert calls["customer_id"] == "tenant-123"


def test_infrastructure_change_approval_accepts_generic_inputs():
    request = onboarding.InfrastructureChangeApprovalRequest(
        provider="hetzner",
        inputs={"admin_ssh_cidrs": ["203.0.113.10/32"]},
    )

    assert approval_admin_cidrs(change_request_approval_inputs(request)) == ["203.0.113.10/32"]


def test_infrastructure_change_approval_direct_cidrs_take_precedence():
    request = onboarding.InfrastructureChangeApprovalRequest(
        provider="hetzner",
        admin_ssh_cidrs=["203.0.113.10/32"],
        inputs={"admin_ssh_cidrs": ["198.51.100.10/32"]},
    )

    assert approval_admin_cidrs(change_request_approval_inputs(request)) == ["203.0.113.10/32"]


def test_cloud_change_approval_regenerates_provider_plan():
    approval = prepare_cloud_change_approval(
        "hetzner",
        pre_state={"firewall": _hetzner_firewall()},
        proposed_diff={},
        inputs={"admin_ssh_cidrs": ["203.0.113.10/32"]},
        adapter_factory=_fake_change_adapter_factory,
    )

    ssh_rule = next(rule for rule in approval.proposed_diff["proposed_rules"] if rule.get("port") == "22")

    assert approval.provider == "hetzner"
    assert ssh_rule["source_ips"] == ["203.0.113.10/32"]


def test_cloud_change_apply_validates_scope_before_apply():
    change_request = {
        "server_id": "123456789",
        "firewall_id": "98765432",
        "scope_hash": "scope-123",
        "proposed_diff": {
            "proposed_rules": [
                {"direction": "in", "protocol": "tcp", "port": "22", "source_ips": ["203.0.113.10/32"]},
                {"direction": "in", "protocol": "tcp", "port": "80", "source_ips": ["0.0.0.0/0", "::/0"]},
                {"direction": "in", "protocol": "tcp", "port": "443", "source_ips": ["0.0.0.0/0", "::/0"]},
            ]
        },
    }

    prepared = prepare_cloud_change_apply(
        "hetzner",
        account_id="123456789",
        account_name="websites-prod",
        secret="hcloud-token",
        metadata={"target_id": "websites-prod", "firewall_id": "98765432"},
        change_request=change_request,
        adapter_factory=_fake_change_adapter_factory,
    )
    result = apply_prepared_cloud_change(prepared)

    assert prepared.scope_hash == "scope-123"
    assert result.result_payload["provider"] == "hetzner"
    assert result.account_metadata["last_apply_result"]["success"] is True


def test_cloud_change_apply_rejects_stale_scope_hash():
    change_request = {
        "server_id": "123456789",
        "firewall_id": "98765432",
        "scope_hash": "stale-scope",
        "proposed_diff": {"proposed_rules": [{"direction": "in", "protocol": "tcp", "port": "22"}]},
    }

    try:
        prepare_cloud_change_apply(
            "hetzner",
            account_id="123456789",
            account_name="websites-prod",
            secret="hcloud-token",
            metadata={"target_id": "websites-prod", "firewall_id": "98765432"},
            change_request=change_request,
            adapter_factory=_fake_change_adapter_factory,
        )
    except CloudChangeRequestError as exc:
        assert exc.status_code == 409
        assert exc.detail["message"] == "Hetzner scope changed after the plan was created"
    else:
        raise AssertionError("Expected stale scope hash to fail")
