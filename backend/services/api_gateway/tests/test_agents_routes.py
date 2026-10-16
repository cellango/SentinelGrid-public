from app.main import agents_legacy_root, agents_legacy_versions
from app.api import routes_agents


def test_legacy_agents_root_returns_benign_stub(client):
    response = client.get("/api/agents")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_legacy_agents_versions_returns_stubbed_versions(client):
    response = client.get("/api/agents/versions")

    assert response.status_code == 200
    assert response.json()["latest_version"] == "4.8.0"
    assert len(response.json()["versions"]) == 2


def test_legacy_agents_handlers_do_not_require_db_parameters():
    assert agents_legacy_root() == {"items": [], "total": 0}
    assert agents_legacy_versions()["latest_version"] == "4.8.0"


def test_agent_inventory_merges_runtime_and_endpoint_agents(monkeypatch):
    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return [
                {
                    "agent_id": "soc_case_agent",
                    "name": "SOC AI Agent",
                    "available": True,
                    "tools": ["get_incidents"],
                    "autonomy_level": "supervised",
                    "model_required": False,
                    "tool_count": 1,
                    "missing_tools": [],
                    "feature_flags": {"compliance_agent_enabled": False},
                }
            ]

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, *args, **kwargs):
            return _Response()

    monkeypatch.setattr(routes_agents.httpx, "Client", lambda *args, **kwargs: _Client())

    response = routes_agents.list_agents(tenant_id="tenant-1")

    assert response["diagnostics"]["agent_runtime_status"] == "reachable"
    assert any(item["id"] == "soc_case_agent" for item in response["items"])
    assert any(item["id"] == "sentinelguard_endpoint" for item in response["items"])


def test_agent_inventory_preserves_runtime_statuses(monkeypatch):
    class _Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, *args, **kwargs):
            if url.endswith("/agents/status"):
                return _Response(
                    [
                        {
                            "agent_id": "soc_case_agent",
                            "name": "SOC AI Agent",
                            "available": True,
                            "runtime_status": "active",
                            "status_reason": "runtime_loop_enabled",
                            "runtime_configured": True,
                            "tools": ["get_incidents"],
                            "autonomy_level": "supervised",
                            "model_required": False,
                            "tool_count": 1,
                            "missing_tools": [],
                            "feature_flags": {"compliance_agent_enabled": False},
                        },
                        {
                            "agent_id": "soc_triage_agent",
                            "name": "SOC Triage Agent",
                            "available": False,
                            "runtime_status": "declared_only",
                            "status_reason": "runtime_flow_not_enabled",
                            "runtime_configured": True,
                            "tools": ["search_logs"],
                            "autonomy_level": "supervised",
                            "model_required": True,
                            "tool_count": 1,
                            "missing_tools": [],
                            "feature_flags": {"compliance_agent_enabled": False},
                        },
                        {
                            "agent_id": "compliance_agent",
                            "name": "Compliance Agent",
                            "available": False,
                            "runtime_status": "disabled",
                            "status_reason": "feature_flag_disabled",
                            "runtime_configured": True,
                            "tools": [],
                            "autonomy_level": "supervised",
                            "model_required": True,
                            "tool_count": 0,
                            "missing_tools": [],
                            "feature_flags": {"compliance_agent_enabled": False},
                        },
                    ]
                )
            return _Response({"versions": [], "latest_versions": {}})

    monkeypatch.setattr(routes_agents.httpx, "Client", lambda *args, **kwargs: _Client())

    response = routes_agents.list_agents(tenant_id="tenant-1")
    items = {item["id"]: item for item in response["items"]}

    assert items["soc_case_agent"]["runtime_status"] == "active"
    assert items["soc_case_agent"]["enabled"] is True
    assert items["soc_triage_agent"]["runtime_status"] == "declared_only"
    assert items["soc_triage_agent"]["enabled"] is False
    assert items["soc_triage_agent"]["status_reason"] == "runtime_flow_not_enabled"
    assert items["compliance_agent"]["runtime_status"] == "disabled"
    assert items["compliance_agent"]["enabled"] is False
    assert items["compliance_agent"]["requires_approval"] is True
    assert response["diagnostics"]["runtime_agent_counts"] == {
        "active": 1,
        "declared_only": 1,
        "disabled": 1,
        "unknown": 0,
    }


def test_agent_inventory_uses_iam_agent_package_versions(monkeypatch):
    class _Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, *args, **kwargs):
            if url.endswith("/agents/status"):
                return _Response([])
            return _Response(
                {
                    "versions": [
                        {
                            "agent_type": "endpoint_protection",
                            "upstream_tool": "wazuh",
                            "upstream_version": "4.9.2",
                            "sentinelgrid_version": "1.4.0",
                            "release_date": "2026-04-28",
                            "download_urls": {"linux_deb": "https://agents.example/sentinelgrid.deb"},
                            "checksums": {"linux_deb": "sha256:abc"},
                            "is_latest": True,
                            "is_deprecated": False,
                        }
                    ],
                    "latest_versions": {},
                }
            )

    monkeypatch.setattr(routes_agents.httpx, "Client", lambda *args, **kwargs: _Client())

    response = routes_agents.list_agents(tenant_id="tenant-1")
    sentinelguard = next(item for item in response["items"] if item["id"] == "sentinelguard_endpoint")
    wazuh = next(item for item in response["items"] if item["id"] == "wazuh_endpoint")

    assert response["diagnostics"]["endpoint_package_inventory_status"] == "reachable"
    assert sentinelguard["version"] == "1.4.0"
    assert sentinelguard["upstream_version"] == "4.9.2"
    assert sentinelguard["download_urls"]["linux_deb"].endswith("sentinelgrid.deb")
    assert wazuh["version"] == "4.9.2"
    assert sentinelguard["source"] == "iam_agent_versions_api"


def test_agent_diagnostics_reports_runtime_ready_and_package_source(monkeypatch):
    class _Response:
        def __init__(self, payload, status_code=200):
            self.payload = payload
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

        def json(self):
            return self.payload

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, *args, **kwargs):
            if url.endswith("/agents/status"):
                return _Response(
                    [
                        {
                            "agent_id": "soc_case_agent",
                            "name": "SOC AI Agent",
                            "available": True,
                            "runtime_status": "active",
                            "status_reason": "runtime_loop_enabled",
                            "tools": [],
                            "feature_flags": {"compliance_agent_enabled": False},
                        }
                    ]
                )
            if url.endswith("/ready"):
                return _Response(
                    {
                        "ready": True,
                        "status": "ready",
                        "redis": {"ready": True, "error": None},
                        "active_agent_loops": ["soc_case_agent"],
                        "feature_flags": {"compliance_agent_enabled": False},
                    }
                )
            return _Response({"versions": [], "latest_versions": {}})

    monkeypatch.setattr(routes_agents.httpx, "Client", lambda *args, **kwargs: _Client())

    response = routes_agents.get_agent_diagnostics(tenant_id="tenant-1")

    assert response["agent_runtime"]["agent_runtime_status"] == "reachable"
    assert response["agent_runtime"]["ready"]["ready"] is True
    assert response["agent_runtime"]["ready"]["active_agent_loops"] == ["soc_case_agent"]
    assert response["agent_runtime"]["runtime_agent_counts"]["active"] == 1
    assert response["endpoint_packages"]["endpoint_package_inventory_status"] == "reachable"


def test_agent_versions_proxy_uses_iam_agent_payload(monkeypatch):
    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "versions": [
                    {
                        "agent_type": "endpoint_protection",
                        "upstream_version": "4.9.2",
                        "sentinelgrid_version": "1.4.0",
                        "is_latest": True,
                    }
                ],
                "latest_versions": {
                    "endpoint_protection": {
                        "upstream_version": "4.9.2",
                        "sentinelgrid_version": "1.4.0",
                    }
                },
            }

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, *args, **kwargs):
            return _Response()

    monkeypatch.setattr(routes_agents.httpx, "Client", lambda *args, **kwargs: _Client())

    response = routes_agents.get_agent_versions(tenant_id="tenant-1")

    assert response["source"] == "iam_agent_versions_api"
    assert response["latest_version"] == "4.9.2"
    assert response["versions"][0]["sentinelgrid_version"] == "1.4.0"
