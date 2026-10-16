import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
LIBS = ROOT / "backend" / "libs"
if str(LIBS) not in sys.path:
    sys.path.insert(0, str(LIBS))

from sg_core.cloud.adapters.hetzner import (
    HETZNER_PILOT_FIREWALL_ID,
    HETZNER_PILOT_SERVER_ID,
    HetznerCloudAdapter,
    HetznerValidationError,
    build_firewall_plan,
    baseline_checks,
    failing_findings_from_checks,
    health_from_state,
    ssh_open_to_world,
)
from sg_core.cloud.baseline_state import load_cloud_baseline_state
from sg_core.cloud.types import CloudProviderAuth
from sg_core.cloud.targets import cloud_target_context


def _server():
    return {
        "id": int(HETZNER_PILOT_SERVER_ID),
        "name": "websites-prod",
        "labels": {"project": "websites", "role": "web"},
        "public_net": {
            "ipv4": {"ip": "203.0.113.42"},
            "firewalls": [{"id": int(HETZNER_PILOT_FIREWALL_ID)}],
        },
        "backups": False,
    }


def _firewall():
    return {
        "id": int(HETZNER_PILOT_FIREWALL_ID),
        "name": "websites-prod-firewall",
        "rules": [
            {"direction": "in", "protocol": "icmp", "source_ips": ["0.0.0.0/0", "::/0"]},
            {"direction": "in", "protocol": "tcp", "port": "22", "source_ips": ["0.0.0.0/0", "::/0"]},
            {"direction": "in", "protocol": "tcp", "port": "80", "source_ips": ["0.0.0.0/0", "::/0"]},
            {"direction": "in", "protocol": "tcp", "port": "443", "source_ips": ["0.0.0.0/0", "::/0"]},
        ],
        "applied_to": [{"type": "server", "server": {"id": int(HETZNER_PILOT_SERVER_ID)}}],
    }


def test_health_validates_single_server_scope():
    health = health_from_state(_server(), _firewall())

    assert health["success"] is True
    assert health["server"]["id"] == HETZNER_PILOT_SERVER_ID
    assert health["firewall"]["attached"] is True
    assert health["scope_hash"]


def test_baseline_detects_world_open_ssh_and_expected_public_web():
    firewall = _firewall()
    checks = {check["check_id"]: check for check in baseline_checks(_server(), firewall)}

    assert ssh_open_to_world(firewall["rules"]) is True
    assert checks["hetzner-ssh-world"]["status"] == "open"
    assert checks["hetzner-web-public-expected"]["status"] == "pass"
    assert checks["hetzner-backups-disabled"]["status"] == "recommendation"
    assert checks["hetzner-caddy-local-app-ports"]["status"] == "pass"


def test_baseline_resolves_ssh_after_sources_are_restricted():
    firewall = _firewall()
    for rule in firewall["rules"]:
        if rule.get("port") == "22":
            rule["source_ips"] = ["203.0.113.10/32"]

    checks = {check["check_id"]: check for check in baseline_checks(_server(), firewall)}

    assert ssh_open_to_world(firewall["rules"]) is False
    assert checks["hetzner-ssh-world"]["status"] == "resolved"
    assert checks["hetzner-web-public-expected"]["status"] == "pass"


def test_hetzner_compat_findings_keep_existing_resource_shape():
    checks = baseline_checks(_server(), _firewall())
    findings = failing_findings_from_checks(checks, _server(), _firewall(), scanner_id="cloud-resource-baseline")

    assert len(findings) == 1
    assert findings[0]["external_id"] == "hetzner:server:123456789:firewall:98765432"
    assert findings[0]["tags"]["server"] == "websites-prod"


def test_hetzner_baseline_state_loader_preserves_provider_scope_hash():
    target = cloud_target_context("websites-prod")
    account = {
        "id": "cloud-account-1",
        "account_id": HETZNER_PILOT_SERVER_ID,
        "account_name": "websites-prod",
        "metadata": {
            "server_snapshot": _server(),
            "firewall_snapshot": _firewall(),
        },
    }

    state = load_cloud_baseline_state("hetzner", account, {}, target)

    assert state.cloud_account_id == "cloud-account-1"
    assert state.server["id"] == int(HETZNER_PILOT_SERVER_ID)
    assert state.firewall["id"] == int(HETZNER_PILOT_FIREWALL_ID)
    assert state.scope_hash


def test_firewall_plan_replaces_only_ssh_sources_and_preserves_web():
    plan = build_firewall_plan(_firewall(), ["203.0.113.10/32"])

    ssh_rule = next(rule for rule in plan["proposed_rules"] if rule.get("port") == "22")
    http_rule = next(rule for rule in plan["proposed_rules"] if rule.get("port") == "80")
    https_rule = next(rule for rule in plan["proposed_rules"] if rule.get("port") == "443")

    assert ssh_rule["source_ips"] == ["203.0.113.10/32"]
    assert http_rule["source_ips"] == ["0.0.0.0/0", "::/0"]
    assert https_rule["source_ips"] == ["0.0.0.0/0", "::/0"]
    assert plan["diff"]["preserved"]["http_public"] is True
    assert plan["diff"]["preserved"]["https_public"] is True


def test_firewall_plan_requires_admin_cidrs():
    with pytest.raises(HetznerValidationError):
        build_firewall_plan(_firewall(), [])


class _FakeHetznerClient:
    def __init__(self):
        self.applied_rules = None

    def get_server(self, server_id):
        assert str(server_id) == HETZNER_PILOT_SERVER_ID
        return _server()

    def get_firewall(self, firewall_id):
        assert str(firewall_id) == HETZNER_PILOT_FIREWALL_ID
        return _firewall()

    def set_firewall_rules(self, firewall_id, rules):
        assert str(firewall_id) == HETZNER_PILOT_FIREWALL_ID
        self.applied_rules = rules
        return {"action": {"status": "running"}}


def test_hetzner_adapter_validates_auth_and_normalizes_firewall():
    adapter = HetznerCloudAdapter(client=_FakeHetznerClient())

    health = adapter.validate_auth(CloudProviderAuth(provider="hetzner", method="api_token", secret="token"))
    policy = adapter.normalize_firewall(_firewall())

    assert health.success is True
    assert policy.ref.resource_type == "firewall_policy"
    assert any(rule.port == "22" and "0.0.0.0/0" in rule.source_cidrs for rule in policy.rules)


def test_hetzner_adapter_plans_and_applies_direct_change():
    fake_client = _FakeHetznerClient()
    adapter = HetznerCloudAdapter(client=fake_client)

    plan = adapter.plan_change({}, {"firewall": _firewall(), "admin_ssh_cidrs": ["203.0.113.10/32"]})
    result = adapter.apply_change(plan)

    assert plan.provider == "hetzner"
    assert plan.resource_ref.external_id == HETZNER_PILOT_FIREWALL_ID
    assert plan.iac_patch["variable"] == "admin_ssh_cidrs"
    assert result.success is True
    assert fake_client.applied_rules == plan.raw_plan["proposed_rules"]
