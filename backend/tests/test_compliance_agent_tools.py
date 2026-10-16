"""Focused tests for Compliance Agent tool registration."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException


LIBS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "libs"))
if LIBS_PATH not in sys.path:
    sys.path.insert(0, LIBS_PATH)

from sg_agent_runtime.agent_loop import AgentLoop  # noqa: E402
from sg_agent_runtime.agents import build_builtin_agents  # noqa: E402
from sg_agent_runtime.compliance_tools import (  # noqa: E402
    COMPLIANCE_TOOL_NAMES,
    ComplianceToolClient,
    _auth_headers_from_task,
    build_compliance_tool_definitions,
    register_compliance_tools,
)
from sg_agent_runtime.models import AgentTask  # noqa: E402
from sg_agent_runtime.tool_registry import ToolRegistry  # noqa: E402
from sg_agent_runtime import service as agent_service  # noqa: E402


class RecordingComplianceClient(ComplianceToolClient):
    def __init__(self):
        super().__init__(
            compliance_service_url="http://compliance",
            reporting_service_url="http://reporting",
            iam_agent_url="http://iam",
        )
        self.calls: list[dict[str, Any]] = []

    async def _request(
        self,
        service_name,
        base_url,
        method,
        path,
        task,
        *,
        payload=None,
        params=None,
    ):
        self.calls.append(
            {
                "service_name": service_name,
                "base_url": base_url,
                "method": method,
                "path": path,
                "tenant_id": task.tenant_id,
                "headers": _auth_headers_from_task(task),
                "payload": payload,
                "params": params,
            }
        )
        return {"ok": True, "tenant_id": task.tenant_id, "data": {"path": path}}


def test_compliance_agent_tools_are_feature_flagged():
    disabled_agents = build_builtin_agents(compliance_agent_enabled=False)
    enabled_agents = build_builtin_agents(compliance_agent_enabled=True)

    assert disabled_agents["compliance_agent"].tools == []
    assert enabled_agents["compliance_agent"].tools == COMPLIANCE_TOOL_NAMES


def test_agent_service_status_uses_compliance_agent_env_flag(monkeypatch):
    monkeypatch.setenv("COMPLIANCE_AGENT_ENABLED", "false")
    assert agent_service._agents()["compliance_agent"].tools == []

    monkeypatch.setenv("COMPLIANCE_AGENT_ENABLED", "true")
    assert agent_service._agents()["compliance_agent"].tools == COMPLIANCE_TOOL_NAMES


def test_agent_runtime_internal_auth_guard_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "expected-token")

    with pytest.raises(HTTPException) as exc:
        agent_service._require_internal_token(None)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_agent_runtime_rejects_compliance_write_task_without_user_auth(monkeypatch):
    monkeypatch.setenv("COMPLIANCE_AGENT_ENABLED", "true")
    monkeypatch.setattr(
        agent_service,
        "_active_agents",
        build_builtin_agents(compliance_agent_enabled=True),
    )
    monkeypatch.setattr(agent_service, "_task_queue", SimpleNamespace(submit=lambda task: None))
    monkeypatch.setattr(agent_service, "_tool_registry", None)
    monkeypatch.setattr(agent_service, "_feature_flags", {"compliance_agent_enabled": True})

    request = agent_service.SubmitTaskRequest(
        tenant_id="tenant-a",
        agent_id="compliance_agent",
        task_type="high_priority_control_gap_detected",
        payload={
            "proposed_actions": [
                {"action": "create_evidence_collection_task", "requires_approval": True}
            ]
        },
        context={},
    )

    with pytest.raises(HTTPException) as exc:
        await agent_service.submit_task(request)

    assert exc.value.status_code == 400
    assert "user auth context" in exc.value.detail


def test_compliance_tool_schemas_are_narrow_and_tenantless():
    definitions = build_compliance_tool_definitions()

    assert [tool.name for tool in definitions] == COMPLIANCE_TOOL_NAMES
    for tool in definitions:
        assert tool.parameters["type"] == "object"
        assert tool.parameters["additionalProperties"] is False
        assert "tenant_id" not in tool.parameters.get("properties", {})

    write_tools = {
        tool.name
        for tool in definitions
        if tool.requires_approval
    }
    assert write_tools == {
        "create_evidence_collection_task",
        "collect_evidence",
        "create_evidence_package",
        "generate_compliance_report",
    }


@pytest.mark.asyncio
async def test_registered_compliance_tools_inject_task_tenant_and_auth_context():
    registry = ToolRegistry()
    client = RecordingComplianceClient()
    register_compliance_tools(registry, client=client)
    agent_def = build_builtin_agents(compliance_agent_enabled=True)["compliance_agent"]
    loop = AgentLoop(
        agent_def=agent_def,
        task_queue=SimpleNamespace(),
        tool_registry=registry,
        memory=SimpleNamespace(),
        llm_client=SimpleNamespace(),
    )
    task = AgentTask(
        tenant_id="tenant-a",
        agent_id="compliance_agent",
        task_type="inspect_evidence",
        context={
            "authorization": "Bearer user-token",
            "user_id": "user-123",
        },
    )

    result = await loop._call_tool(
        "list_evidence",
        {
            "tenant_id": "tenant-b",
            "control_id": "CC6.1",
            "_agent_task": "model-supplied-value",
        },
        task,
    )

    assert result["ok"] is True
    assert client.calls[0]["params"]["tenant_id"] == "tenant-a"
    assert client.calls[0]["params"]["control_id"] == "CC6.1"
    assert client.calls[0]["headers"]["Authorization"] == "Bearer user-token"
    assert client.calls[0]["headers"]["X-Tenant-ID"] == "tenant-a"
    assert client.calls[0]["headers"]["X-User-ID"] == "user-123"


def test_agent_prompt_redacts_auth_context():
    agent_def = build_builtin_agents(compliance_agent_enabled=True)["compliance_agent"]
    loop = AgentLoop(
        agent_def=agent_def,
        task_queue=SimpleNamespace(),
        tool_registry=SimpleNamespace(),
        memory=SimpleNamespace(),
        llm_client=SimpleNamespace(),
    )
    task = AgentTask(
        tenant_id="tenant-a",
        agent_id="compliance_agent",
        task_type="inspect_evidence",
        context={
            "authorization": "Bearer secret-token",
            "auth": {"access_token": "nested-secret"},
            "safe_context": "visible",
        },
    )

    messages = loop._build_messages(task)
    rendered = "\n".join(message["content"] for message in messages)

    assert "secret-token" not in rendered
    assert "nested-secret" not in rendered
    assert "[redacted]" in rendered
    assert "visible" in rendered
