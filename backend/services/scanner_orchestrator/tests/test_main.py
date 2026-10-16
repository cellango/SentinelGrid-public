import importlib
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[4]  # repo root
BACKEND = ROOT / "backend"
LIBS = ROOT / "backend" / "libs"
for p in (ROOT, BACKEND, LIBS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

scanner_main = importlib.import_module("backend.services.scanner_orchestrator.app.main")


def test_asset_ref_cloud():
    asset_type, external_id = scanner_main._asset_ref("cloud", {"cloud_connector_id": "acc-123"}, "")
    assert asset_type == "cloud_account"
    assert external_id == "acc-123"


def test_resolve_scan_request_maps_hetzner_alias_to_generic_cloud_baseline():
    scanner_id, target_ref, payload = scanner_main._resolve_scanner_request(
        "hetzner-single-server-baseline",
        payload={"admin_ssh_cidrs": ["203.0.113.10/32"]},
    )

    assert scanner_id == "cloud-resource-baseline"
    assert target_ref == "websites-prod"
    assert payload["requested_scanner_id"] == "hetzner-single-server-baseline"
    assert payload["scanner_id"] == "cloud-resource-baseline"


def test_rate_limit_blocks_after_max(monkeypatch):
    # Set small window/max and reset deque
    monkeypatch.setattr(scanner_main, "RATE_LIMIT_MAX", 1)
    monkeypatch.setattr(scanner_main, "RATE_LIMIT_WINDOW", 60)
    scanner_main._tenant_rates.clear()

    scanner_main._check_rate_limit("tenant-1")  # first allowed
    with pytest.raises(HTTPException) as excinfo:
        scanner_main._check_rate_limit("tenant-1")
    assert excinfo.value.status_code == 429

    # After window passes, should allow again
    # Manually age out the timestamp
    dq = scanner_main._tenant_rates["tenant-1"]
    dq[0] = dq[0] - 61
    scanner_main._check_rate_limit("tenant-1")  # no raise


def test_concurrency_limit(monkeypatch):
    monkeypatch.setattr(scanner_main, "MAX_TENANT_CONCURRENCY", 1)
    monkeypatch.setattr(scanner_main, "MAX_SCANNER_CONCURRENCY", 1)
    scanner_main._tenant_active.clear()
    scanner_main._scanner_active.clear()

    scanner_main._acquire_slots("tenant-1", "scan-a")
    with pytest.raises(HTTPException) as excinfo:
        scanner_main._acquire_slots("tenant-1", "scan-a")
    assert excinfo.value.status_code == 429

    scanner_main._release_slots("tenant-1", "scan-a")
    # should now succeed
    scanner_main._acquire_slots("tenant-1", "scan-a")
    scanner_main._release_slots("tenant-1", "scan-a")
