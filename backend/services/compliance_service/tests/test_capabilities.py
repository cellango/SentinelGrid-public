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


def test_capabilities_endpoint_reports_phase_zero_defaults():
    with TestClient(app) as client:
        response = client.get("/api/v1/compliance/capabilities")

    assert response.status_code == 200
    payload = response.json()

    assert payload["runtime_mode"] == "soc2_readiness"
    assert payload["capabilities"]["soc2_readiness"] is True
    assert payload["capabilities"]["framework_starter_packs"] is True
    assert payload["capabilities"]["multi_framework_selection"] is False
    assert payload["capabilities"]["durable_evidence_repository"] is False
    assert payload["capabilities"]["compliance_agent_workflows"] is False
    assert "/api/v1/compliance/soc2/coverage" in payload["compatibility_endpoints"]
    assert payload["stub_endpoints"] == []
    assert payload["deprecated_endpoints"][0]["path"] == "/api/v1/compliance/report"
    assert payload["deprecated_endpoints"][0]["replacement"] == "/api/v1/reports"
    assert payload["truth_labels"]["dashboard_title"] == "SOC 2 Readiness Dashboard"
