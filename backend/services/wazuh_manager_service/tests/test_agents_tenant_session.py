"""Focused tenant-session coverage for Wazuh manager agent routes."""

from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api import agents as agents_api
from app.main import app
from app.services.agent_service import AgentService


TENANT_ID = UUID("00000000-0000-0000-0000-000000000111")


class FakeDB:
    """Minimal DB stub for route dependency overrides."""


@pytest.fixture
def tenant_scoped_client(monkeypatch):
    """Force the Wazuh manager routes to use get_tenant_session."""
    fake_db = FakeDB()
    fake_wazuh_client = SimpleNamespace(name="fake-wazuh")
    observed = {}

    def override_current_tenant():
        return TENANT_ID

    def unexpected_get_db():
        raise AssertionError("Wazuh manager route used get_db instead of get_tenant_session")
        yield  # pragma: no cover

    def override_get_tenant_session():
        yield fake_db

    def override_get_wazuh_client():
        return fake_wazuh_client

    async def register_agent(self, tenant_id, hostname, ip_address=None, os_platform=None, os_version=None):
        assert self.db is fake_db
        assert self.wazuh is fake_wazuh_client
        observed["register"] = {
            "tenant_id": str(tenant_id),
            "hostname": hostname,
            "ip_address": ip_address,
            "os_platform": os_platform,
            "os_version": os_version,
        }
        return {
            "success": True,
            "agent_id": "001",
            "agent_key": "agent-key",
            "manager_address": "manager.sentinelgrid.ai",
            "manager_port": 1514,
            "tenant_id": str(tenant_id),
            "instructions": {"linux": "install"},
        }

    async def list_agents(self, tenant_id):
        assert self.db is fake_db
        assert self.wazuh is fake_wazuh_client
        observed["list"] = str(tenant_id)
        return [
            {
                "id": "agent-record-1",
                "wazuh_agent_id": "001",
                "name": "endpoint-1",
                "ip": "10.0.0.5",
                "os": "Ubuntu 22.04",
                "status": "active",
                "last_seen": "2026-03-29T11:00:00Z",
                "registered": "2026-03-29T10:00:00Z",
                "version": "4.8.0",
            }
        ]

    async def get_agent_details(self, tenant_id, agent_id):
        assert self.db is fake_db
        assert self.wazuh is fake_wazuh_client
        observed["details"] = {"tenant_id": str(tenant_id), "agent_id": agent_id}
        return {
            "id": "agent-record-1",
            "wazuh_agent_id": agent_id,
            "name": "endpoint-1",
            "ip": "10.0.0.5",
            "os": {"name": "Ubuntu", "version": "22.04"},
            "version": "4.8.0",
            "status": "active",
            "last_keepalive": "2026-03-29T11:00:00Z",
            "registration_date": "2026-03-29T10:00:00Z",
            "labels": {"tenant_id": str(tenant_id)},
            "groups": ["default"],
        }

    async def delete_agent(self, tenant_id, agent_id):
        assert self.db is fake_db
        assert self.wazuh is fake_wazuh_client
        observed["delete"] = {"tenant_id": str(tenant_id), "agent_id": agent_id}
        return True

    async def restart_agent(self, tenant_id, agent_id):
        assert self.db is fake_db
        assert self.wazuh is fake_wazuh_client
        observed["restart"] = {"tenant_id": str(tenant_id), "agent_id": agent_id}
        return {
            "success": True,
            "agent_id": agent_id,
            "message": "Agent restart initiated",
        }

    app.dependency_overrides[agents_api.get_current_tenant] = override_current_tenant
    app.dependency_overrides[agents_api.get_db] = unexpected_get_db
    app.dependency_overrides[agents_api.get_tenant_session] = override_get_tenant_session
    app.dependency_overrides[agents_api.get_wazuh_client] = override_get_wazuh_client

    monkeypatch.setattr(AgentService, "register_agent", register_agent)
    monkeypatch.setattr(AgentService, "list_agents", list_agents)
    monkeypatch.setattr(AgentService, "get_agent_details", get_agent_details)
    monkeypatch.setattr(AgentService, "delete_agent", delete_agent)
    monkeypatch.setattr(AgentService, "restart_agent", restart_agent)

    try:
        with TestClient(app) as test_client:
            yield test_client, observed
    finally:
        app.dependency_overrides.clear()


def test_agent_routes_use_tenant_session(tenant_scoped_client):
    """Agent routes should not fall back to plain get_db."""
    test_client, observed = tenant_scoped_client

    register_response = test_client.post(
        "/api/v1/wazuh/agents/register",
        json={
            "hostname": "endpoint-1",
            "ip_address": "10.0.0.5",
            "os_platform": "linux",
            "os_version": "Ubuntu 22.04",
        },
    )
    assert register_response.status_code == 201
    assert register_response.json()["tenant_id"] == str(TENANT_ID)
    assert observed["register"]["hostname"] == "endpoint-1"

    list_response = test_client.get("/api/v1/wazuh/agents")
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 1
    assert observed["list"] == str(TENANT_ID)

    get_response = test_client.get("/api/v1/wazuh/agents/001")
    assert get_response.status_code == 200
    assert get_response.json()["wazuh_agent_id"] == "001"
    assert observed["details"] == {"tenant_id": str(TENANT_ID), "agent_id": "001"}

    delete_response = test_client.delete("/api/v1/wazuh/agents/001")
    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True
    assert observed["delete"] == {"tenant_id": str(TENANT_ID), "agent_id": "001"}

    restart_response = test_client.post("/api/v1/wazuh/agents/001/restart")
    assert restart_response.status_code == 200
    assert restart_response.json()["message"] == "Agent restart initiated"
    assert observed["restart"] == {"tenant_id": str(TENANT_ID), "agent_id": "001"}
