from types import SimpleNamespace

import httpx

from app.api import routes_siem
from app.main import app
from sg_core.opa import require_opa_allow
from sg_core.service_metrics import reset_service_metrics


def test_source_health_records_component_status_metrics(
    client,
    monkeypatch,
):
    reset_service_metrics("api-gateway")
    app.dependency_overrides[require_opa_allow] = lambda: None
    monkeypatch.setenv("INGESTION_SERVICE_URL", "http://health.test/ingestion")
    monkeypatch.setenv("SIEM_AGENT_URL", "http://health.test/siem")
    monkeypatch.setenv("OPENSEARCH_URL", "http://health.test/opensearch")
    monkeypatch.setenv("WAZUH_HEALTH_URL", "http://health.test/wazuh")
    monkeypatch.setenv("OPENEDR_HEALTH_URL", "http://health.test/openedr")
    monkeypatch.setenv("VELOCIRAPTOR_HEALTH_URL", "http://health.test/velociraptor")

    status_codes = {
        "http://health.test/ingestion": 200,
        "http://health.test/siem": 503,
        "http://health.test/opensearch/_cluster/health": 200,
        "http://health.test/wazuh": 200,
        "http://health.test/velociraptor": 200,
    }

    def fake_get(url, timeout, verify):
        if url == "http://health.test/openedr":
            raise httpx.ConnectError("openedr unavailable")
        return SimpleNamespace(status_code=status_codes[url])

    monkeypatch.setattr(routes_siem.httpx, "get", fake_get)

    try:
        response = client.get("/api/v1/siem/source-health")
        metrics_response = client.get("/metrics")
    finally:
        app.dependency_overrides.pop(require_opa_allow, None)

    assert response.status_code == 200
    assert response.json()["siem_agent"] == "degraded (503)"
    assert response.json()["openedr"] == "unreachable"
    assert metrics_response.status_code == 200

    payload = metrics_response.json()
    assert payload["counters"]["source_health_requests_total"]["total"] == 1
    assert payload["counters"]["source_health_probes_total"]["series"][
        "component=siem_agent,outcome=degraded"
    ] == 1
    assert payload["counters"]["source_health_probes_total"]["series"][
        "component=openedr,outcome=unreachable"
    ] == 1
    assert payload["gauges"]["source_health_components_last"]["status=healthy"] == 4.0
    assert payload["gauges"]["source_health_components_last"]["status=degraded"] == 1.0
    assert payload["gauges"]["source_health_components_last"]["status=unreachable"] == 1.0
    assert payload["gauges"]["source_health_component_up"]["component=siem_agent"] == 0
    assert payload["gauges"]["source_health_component_up"]["component=opensearch"] == 1
