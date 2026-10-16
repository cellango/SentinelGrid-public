import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
LIBS = ROOT / "backend" / "libs"
if str(LIBS) not in sys.path:
    sys.path.insert(0, str(LIBS))

from sg_core.cloud.controls import admin_port_open_to_world, expected_public_tcp_ports
from sg_core.cloud.baseline import (
    active_cloud_findings_from_checks,
    admin_port_cidrs_required_plan,
    admin_port_open_from_checks,
    cloud_resource_baseline_checks,
    expected_public_tcp_ports_for_target,
    fixed_target_ref,
    posture_framework,
    posture_remediation_plan,
    posture_remediation_status,
    posture_status,
    summarize_cloud_baseline,
)
from sg_core.cloud.baseline_state import load_cloud_baseline_state
from sg_core.cloud.remediation import CloudRemediationError, plan_firewall_source_restriction
from sg_core.cloud.targets import cloud_target_context
from sg_core.cloud.types import CloudResourceRef, FirewallPolicy, FirewallRule


def _policy():
    return FirewallPolicy(
        ref=CloudResourceRef(provider="testcloud", resource_type="firewall_policy", external_id="fw-1"),
        rules=[
            FirewallRule(
                direction="in",
                protocol="icmp",
                source_cidrs=["0.0.0.0/0"],
                raw={"direction": "in", "protocol": "icmp", "source_ips": ["0.0.0.0/0"]},
            ),
            FirewallRule(
                direction="in",
                protocol="tcp",
                port="22",
                source_cidrs=["0.0.0.0/0", "::/0"],
                raw={"direction": "in", "protocol": "tcp", "port": "22", "source_ips": ["0.0.0.0/0", "::/0"]},
            ),
            FirewallRule(
                direction="in",
                protocol="tcp",
                port="80",
                source_cidrs=["0.0.0.0/0", "::/0"],
                raw={"direction": "in", "protocol": "tcp", "port": "80", "source_ips": ["0.0.0.0/0", "::/0"]},
            ),
            FirewallRule(
                direction="in",
                protocol="tcp",
                port="443",
                source_cidrs=["0.0.0.0/0", "::/0"],
                raw={"direction": "in", "protocol": "tcp", "port": "443", "source_ips": ["0.0.0.0/0", "::/0"]},
            ),
        ],
    )


def test_admin_port_open_to_world_is_provider_neutral():
    result = admin_port_open_to_world(_policy(), port=22)

    assert result.control_id == "network.admin_port_open_to_world"
    assert result.provider == "testcloud"
    assert result.status == "open"
    assert result.evidence["matching_rules"]


def test_expected_public_ports_passes_when_declared_public_ports_are_world_open():
    result = expected_public_tcp_ports(_policy(), (80, 443))

    assert result.control_id == "network.expected_public_ports"
    assert result.status == "pass"
    assert result.evidence["missing_ports"] == []


def test_firewall_source_restriction_preserves_unrelated_rules():
    plan = plan_firewall_source_restriction(
        _policy(),
        port=22,
        allowed_source_cidrs=["203.0.113.10/32"],
        iac_variable="admin_ssh_cidrs",
    )

    ssh_rule = next(rule for rule in plan.raw_plan["proposed_rules"] if rule.get("port") == "22")
    http_rule = next(rule for rule in plan.raw_plan["proposed_rules"] if rule.get("port") == "80")

    assert plan.provider == "testcloud"
    assert plan.apply_mode == "iac_patch"
    assert plan.iac_patch["variable"] == "admin_ssh_cidrs"
    assert ssh_rule["source_ips"] == ["203.0.113.10/32"]
    assert http_rule["source_ips"] == ["0.0.0.0/0", "::/0"]
    assert plan.diff["preserved"]["unchanged_rule_count"] == 3


def test_firewall_source_restriction_requires_cidrs():
    with pytest.raises(CloudRemediationError):
        plan_firewall_source_restriction(_policy(), port=22, allowed_source_cidrs=[])


def _target_context():
    return cloud_target_context(
        target_config={
            "provider": "testcloud",
            "environment": "prod",
            "mode": "single_resource",
            "resource": {
                "type": "compute_instance",
                "external_id": "i-1",
                "name": "web-1",
                "labels": {"project": "web"},
            },
            "relationships": {
                "firewall_policy": {"external_id": "fw-1", "name": "web-firewall"},
            },
            "expected_exposure": {
                "public": [
                    {"protocol": "tcp", "port": 80},
                    {"protocol": "tcp", "port": 443},
                ],
                "admin": [{"protocol": "tcp", "port": 22}],
            },
            "edge": {
                "tls_proxy": {
                    "service": "caddy",
                    "public_ports": [80, 443],
                    "expected_local_app_ports": [3000],
                },
            },
        }
    )


class _FakeBaselineAdapter:
    provider = "testcloud"

    def normalize_firewall(self, raw):
        return _policy()


def test_posture_payload_helpers_are_provider_neutral():
    target = _target_context()
    check = {"status": "recommendation"}

    assert posture_status(check) == "open"
    assert posture_remediation_status(check) == "recommendation"
    assert posture_framework(target) == "SentinelGrid Testcloud Baseline"
    assert fixed_target_ref(target) == "firewall_policy:fw-1"

    plan = posture_remediation_plan(check, target)
    assert plan["provider"] == "testcloud"
    assert plan["target_id"] == "web-1"
    assert plan["resource_ref"]["external_id"] == "i-1"


def test_admin_port_required_plan_uses_normalized_firewall_policy():
    target = _target_context()

    plan = admin_port_cidrs_required_plan(_FakeBaselineAdapter(), {}, target, port=22)

    assert plan["provider"] == "testcloud"
    assert plan["resource_ref"]["external_id"] == "fw-1"
    assert plan["firewall_id"] == "fw-1"
    assert plan["proposed_rules"] is None
    assert plan["admin_cidrs_required"] is True
    assert plan["diff"]["changed"][0]["before_source_cidrs"] == ["0.0.0.0/0", "::/0"]


def test_cloud_resource_baseline_checks_are_provider_neutral():
    target = _target_context()
    checks = {
        check["check_id"]: check
        for check in cloud_resource_baseline_checks(
            _FakeBaselineAdapter(),
            {"id": "i-1", "name": "web-1", "backups": False},
            {"id": "fw-1", "rules": []},
            target,
            target.metadata(),
        )
    }

    assert expected_public_tcp_ports_for_target(target) == (80, 443)
    assert checks["testcloud-ssh-world"]["control_id"] == "network.admin_port_open_to_world"
    assert checks["testcloud-ssh-world"]["status"] == "open"
    assert checks["testcloud-web-public-expected"]["status"] == "pass"
    assert checks["testcloud-backups-disabled"]["status"] == "recommendation"
    assert checks["testcloud-caddy-local-app-ports"]["status"] == "pass"
    assert admin_port_open_from_checks(list(checks.values()), port=22) is True


def test_cloud_baseline_findings_skip_recommendation_only_checks():
    target = _target_context()
    checks = cloud_resource_baseline_checks(
        _FakeBaselineAdapter(),
        {"id": "i-1", "name": "web-1", "backups": False},
        {"id": "fw-1", "rules": []},
        target,
        target.metadata(),
    )

    findings = active_cloud_findings_from_checks(
        checks,
        target,
        scanner_id="cloud-resource-baseline",
        server={"id": "i-1", "name": "web-1"},
        firewall={"id": "fw-1"},
        firewall_policy=_policy(),
    )
    summary = summarize_cloud_baseline(
        checks,
        target,
        change_request_id="cr-1",
        scope="scope-1",
        scanner_id="cloud-resource-baseline",
    )

    assert [finding["fingerprint"] for finding in findings] == [
        "testcloud-ssh-world:testcloud:server:i-1:firewall:fw-1"
    ]
    assert summary["findings"] == 1
    assert summary["recommendations"] == 1
    assert summary["change_request_id"] == "cr-1"


def test_metadata_baseline_state_loader_supports_generic_provider_snapshots():
    target = _target_context()
    account = {
        "id": "cloud-account-1",
        "metadata": {
            "resource_snapshot": {"id": "i-1", "name": "web-1"},
            "firewall_policy_snapshot": {"id": "fw-1", "rules": []},
            "scope_hash": "scope-1",
        },
    }

    state = load_cloud_baseline_state("testcloud", account, {}, target)

    assert state.cloud_account_id == "cloud-account-1"
    assert state.server["id"] == "i-1"
    assert state.firewall["id"] == "fw-1"
    assert state.scope_hash == "scope-1"
    assert state.target_metadata["asset_external_id"] == "testcloud:server:i-1"
