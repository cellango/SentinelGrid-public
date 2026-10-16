"""Focused tests for Agent Runtime status and readiness contracts."""

from __future__ import annotations

import json
import os
import sys

import pytest
from fastapi.testclient import TestClient


LIBS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "libs"))
if LIBS_PATH not in sys.path:
    sys.path.insert(0, LIBS_PATH)

from sg_agent_runtime import service as agent_service  # noqa: E402
from sg_agent_runtime.agents import build_builtin_agents  # noqa: E402
from sg_agent_runtime.compliance_tools import COMPLIANCE_TOOL_NAMES, register_compliance_tools  # noqa: E402
from sg_agent_runtime.soc_tools import register_soc_tools  # noqa: E402
from sg_agent_runtime.tool_registry import ToolRegistry  # noqa: E402


class _ReadyRedis:
    async def ping(self) -> bool:
        return True


class _BrokenRedis:
    async def ping(self) -> bool:
        raise RuntimeError("redis unavailable")


class _FakeQueue:
    def __init__(self, redis):
        self.redis = redis


@pytest.fixture(autouse=True)
def reset_agent_runtime_state(monkeypatch):
    monkeypatch.setattr(agent_service, "_task_queue", None)
    monkeypatch.setattr(agent_service, "_tool_registry", None)
    monkeypatch.setattr(agent_service, "_memory", None)
    monkeypatch.setattr(agent_service, "_llm_client", None)
    monkeypatch.setattr(agent_service, "_agent_loops", {})
    monkeypatch.setattr(agent_service, "_active_agents", build_builtin_agents())
    monkeypatch.setattr(agent_service, "_feature_flags", {})
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "internal-test-token")


def _soc_registry() -> ToolRegistry:
    registry = ToolRegistry()
    register_soc_tools(registry)
    return registry


def _soc_and_compliance_registry() -> ToolRegistry:
    registry = _soc_registry()
    register_compliance_tools(registry)
    return registry


@pytest.mark.asyncio
async def test_agent_status_reports_active_declared_and_disabled_agents(monkeypatch):
    monkeypatch.setenv("COMPLIANCE_AGENT_ENABLED", "false")
    monkeypatch.setattr(
        agent_service,
        "_active_agents",
        build_builtin_agents(compliance_agent_enabled=False),
    )
    monkeypatch.setattr(agent_service, "_tool_registry", _soc_registry())
    monkeypatch.setattr(agent_service, "_feature_flags", {"compliance_agent_enabled": False})

    statuses = {status.agent_id: status for status in await agent_service.agent_status()}

    soc_case = statuses["soc_case_agent"]
    assert soc_case.available is True
    assert soc_case.runtime_status == "active"
    assert soc_case.status_reason == "runtime_loop_enabled"
    assert soc_case.runtime_configured is True
    assert soc_case.model_required is False
    assert soc_case.missing_tools == []
    assert soc_case.tool_count == len(soc_case.tools)

    soc_triage = statuses["soc_triage_agent"]
    assert soc_triage.available is False
    assert soc_triage.runtime_status == "declared_only"
    assert soc_triage.status_reason == "runtime_flow_not_enabled"
    assert soc_triage.missing_tools == []

    investigation = statuses["investigation_agent"]
    assert investigation.available is False
    assert investigation.runtime_status == "declared_only"
    assert investigation.status_reason == "missing_or_disabled_tools"
    assert investigation.missing_tools == ["create_incident"]

    response = statuses["response_agent"]
    assert response.available is False
    assert response.runtime_status == "declared_only"
    assert response.status_reason == "missing_or_disabled_tools"
    assert set(response.missing_tools) == {"lock_account", "run_playbook"}

    compliance = statuses["compliance_agent"]
    assert compliance.available is False
    assert compliance.runtime_status == "disabled"
    assert compliance.status_reason == "feature_flag_disabled"
    assert compliance.tools == []
    assert compliance.feature_flags == {"compliance_agent_enabled": False}


@pytest.mark.asyncio
async def test_agent_status_reports_compliance_agent_when_feature_enabled(monkeypatch):
    monkeypatch.setenv("COMPLIANCE_AGENT_ENABLED", "true")
    monkeypatch.setattr(
        agent_service,
        "_active_agents",
        build_builtin_agents(compliance_agent_enabled=True),
    )
    monkeypatch.setattr(agent_service, "_tool_registry", _soc_and_compliance_registry())
    monkeypatch.setattr(agent_service, "_feature_flags", {"compliance_agent_enabled": True})

    statuses = {status.agent_id: status for status in await agent_service.agent_status()}
    compliance = statuses["compliance_agent"]

    assert compliance.available is True
    assert compliance.runtime_status == "active"
    assert compliance.status_reason == "runtime_loop_enabled"
    assert compliance.tools == COMPLIANCE_TOOL_NAMES
    assert compliance.missing_tools == []
    assert compliance.tool_count == len(COMPLIANCE_TOOL_NAMES)
    assert compliance.feature_flags == {"compliance_agent_enabled": True}


def test_agent_status_endpoint_requires_internal_token(monkeypatch):
    monkeypatch.setattr(
        agent_service,
        "_active_agents",
        build_builtin_agents(compliance_agent_enabled=False),
    )
    monkeypatch.setattr(agent_service, "_tool_registry", _soc_registry())
    monkeypatch.setattr(agent_service, "_feature_flags", {"compliance_agent_enabled": False})

    client = TestClient(agent_service.app)

    missing_token = client.get("/agents/status")
    assert missing_token.status_code == 403

    valid_token = client.get(
        "/agents/status",
        headers={"Authorization": "Bearer internal-test-token"},
    )
    assert valid_token.status_code == 200
    assert any(agent["agent_id"] == "soc_case_agent" for agent in valid_token.json())


@pytest.mark.asyncio
async def test_ready_returns_ready_when_redis_and_available_agents_exist(monkeypatch):
    monkeypatch.setattr(agent_service, "_task_queue", _FakeQueue(_ReadyRedis()))
    monkeypatch.setattr(
        agent_service,
        "_active_agents",
        build_builtin_agents(compliance_agent_enabled=False),
    )
    monkeypatch.setattr(agent_service, "_tool_registry", _soc_registry())
    monkeypatch.setattr(agent_service, "_feature_flags", {"compliance_agent_enabled": False})
    monkeypatch.setattr(agent_service, "_agent_loops", {"soc_case_agent": object()})

    response = await agent_service.ready()
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert payload["ready"] is True
    assert payload["redis"]["ready"] is True
    assert payload["active_agent_loops"] == ["soc_case_agent"]
    assert payload["feature_flags"] == {"compliance_agent_enabled": False}


@pytest.mark.asyncio
async def test_ready_returns_not_ready_when_redis_ping_fails(monkeypatch):
    monkeypatch.setattr(agent_service, "_task_queue", _FakeQueue(_BrokenRedis()))
    monkeypatch.setattr(
        agent_service,
        "_active_agents",
        build_builtin_agents(compliance_agent_enabled=False),
    )
    monkeypatch.setattr(agent_service, "_tool_registry", _soc_registry())
    monkeypatch.setattr(agent_service, "_feature_flags", {"compliance_agent_enabled": False})

    response = await agent_service.ready()
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["ready"] is False
    assert payload["redis"]["ready"] is False
    assert "redis unavailable" in payload["redis"]["error"]
