from pathlib import Path
import os
import sys

from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

os.environ.setdefault("DB_HOST", "localhost")

from app.main import app
from app.services.framework_catalog import framework_catalog, normalize_framework_id


def test_framework_catalog_loads_bundled_frameworks():
    payload = framework_catalog.list_frameworks()

    assert payload["source"] == "bundled_json"
    assert payload["count"] == 4
    assert "control_evidence_requirements" in payload["schema_tables"]
    assert "evidence_control_links" in payload["schema_tables"]
    assert "evidence_exports" in payload["schema_tables"]

    frameworks = {item["framework_id"]: item for item in payload["items"]}
    assert frameworks["soc2"]["runtime_support"] == "readiness"
    assert frameworks["soc2"]["control_count"] == 10
    assert frameworks["hipaa"]["control_count"] == 8
    assert frameworks["pci_dss"]["control_count"] == 10
    assert frameworks["nist_800_171"]["related_framework"] == "CMMC Level 2"


def test_framework_catalog_normalizes_aliases():
    assert normalize_framework_id("SOC 2") == "soc2"
    assert normalize_framework_id("pci") == "pci_dss"
    assert normalize_framework_id("NIST-800-171") == "nist_800_171"


def test_framework_endpoints_return_metadata_and_controls():
    with TestClient(app) as client:
        frameworks_response = client.get("/api/v1/compliance/frameworks")
        detail_response = client.get("/api/v1/compliance/frameworks/soc2")
        controls_response = client.get("/api/v1/compliance/frameworks/soc2/controls")

    assert frameworks_response.status_code == 200
    assert frameworks_response.json()["count"] == 4

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["framework_id"] == "soc2"
    assert detail["framework_code"] == "SOC2"
    assert detail["categories"][0]["code"] == "CC6"
    assert "controls" not in detail

    assert controls_response.status_code == 200
    controls = controls_response.json()
    assert controls["framework_id"] == "soc2"
    assert controls["count"] == 10
    cc61 = next(item for item in controls["items"] if item["control_id"] == "CC6.1")
    assert cc61["category"]["code"] == "CC6"
    assert "iam_agent" in cc61["sentinelgrid_features"]
    assert cc61["evidence_requirements"] == []


def test_framework_endpoint_rejects_unknown_framework():
    with TestClient(app) as client:
        response = client.get("/api/v1/compliance/frameworks/unknown-framework")

    assert response.status_code == 404
    assert response.json()["detail"] == "Compliance framework not found"
