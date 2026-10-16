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
from sg_core.service_metrics import get_service_metrics, reset_service_metrics


def test_compliance_metrics_endpoints_render_runtime_snapshot_and_prometheus():
    reset_service_metrics("compliance-service")
    runtime_metrics = get_service_metrics("compliance-service")
    runtime_metrics.increment_counter(
        "compliance_evidence_collection_total",
        outcome="success",
        source_system="iam_agent",
        collection_method="api",
    )
    runtime_metrics.set_gauge("compliance_stale_evidence_items", 2, tenant_id="tenant-a")

    with TestClient(app) as client:
        snapshot_response = client.get("/metrics")
        prometheus_response = client.get("/metrics/prometheus")

    assert snapshot_response.status_code == 200
    snapshot = snapshot_response.json()
    assert snapshot["service"] == "compliance-service"
    assert (
        snapshot["counters"]["compliance_evidence_collection_total"]["series"][
            "collection_method=api,outcome=success,source_system=iam_agent"
        ]
        == 1
    )
    assert snapshot["gauges"]["compliance_stale_evidence_items"]["tenant_id=tenant-a"] == 2

    assert prometheus_response.status_code == 200
    assert prometheus_response.headers["content-type"].startswith("text/plain")
    assert (
        'compliance_evidence_collection_total{collection_method="api",outcome="success",'
        'service="compliance-service",source_system="iam_agent"} 1.0'
    ) in prometheus_response.text
    assert 'compliance_stale_evidence_items{service="compliance-service",tenant_id="tenant-a"} 2' in prometheus_response.text
