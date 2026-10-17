import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.request_identity import require_gateway_identity
from sg_core.opa import require_opa_allow


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):  # noqa: A003
        return  # silence server logs in tests


def start_health_server() -> tuple[str, HTTPServer]:
    server = HTTPServer(("127.0.0.1", 0), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return f"http://{host}:{port}", server


@pytest.mark.integration
def test_source_health_reads_sidecar_endpoints(monkeypatch, mock_get_db, mock_get_current_tenant):
    # Start lightweight health endpoints
    ingest_url, ingest_srv = start_health_server()
    siem_url, siem_srv = start_health_server()
    os_url, os_srv = start_health_server()
    wazuh_url, wazuh_srv = start_health_server()
    openedr_url, openedr_srv = start_health_server()
    velo_url, velo_srv = start_health_server()

    # Configure env to point to test servers
    monkeypatch.setenv("INGESTION_SERVICE_URL", ingest_url)
    monkeypatch.setenv("SIEM_AGENT_URL", siem_url)
    monkeypatch.setenv("OPENSEARCH_URL", os_url)
    monkeypatch.setenv("WAZUH_HEALTH_URL", wazuh_url)
    monkeypatch.setenv("OPENEDR_HEALTH_URL", openedr_url)
    monkeypatch.setenv("VELOCIRAPTOR_HEALTH_URL", velo_url)

    from sg_core.db import get_db
    from sg_core.security import get_current_tenant

    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_current_tenant] = mock_get_current_tenant
    # Route-unit fixture; real gateway admission has its own no-override suite.
    app.dependency_overrides[require_gateway_identity] = lambda: None
    app.dependency_overrides[require_opa_allow] = lambda: None

    client = TestClient(app)
    try:
        resp = client.get("/api/v1/siem/source-health")
        assert resp.status_code == 200
        data = resp.json()
        for key in ("ingestion_service", "siem_agent", "opensearch", "wazuh", "openedr", "velociraptor"):
            assert data.get(key) == "healthy"
    finally:
        for srv in (ingest_srv, siem_srv, os_srv, wazuh_srv, openedr_srv, velo_srv):
            srv.shutdown()
        app.dependency_overrides.clear()
