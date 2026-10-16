"""Deterministic SOC Agent read-only tools.

These tools deliberately call existing service APIs instead of reading data
directly. Tenant scope is injected from the agent task so model-supplied
arguments cannot switch tenants.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from .models import AgentTask, ToolDefinition
from .tool_registry import ToolRegistry


SOC_READ_TOOL_NAMES = [
    "get_incidents",
    "get_detections",
    "search_logs",
    "list_playbooks",
    "get_playbook",
    "get_user",
]


def _object_schema(
    properties: dict[str, Any],
    *,
    required: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required or [],
    }


def build_soc_tool_definitions() -> list[ToolDefinition]:
    """Return the read-only SOC tool definitions in runtime order."""
    return [
        ToolDefinition(
            name="get_incidents",
            description="List tenant-scoped incidents with optional filters.",
            parameters=_object_schema(
                {
                    "status": {"type": "string", "minLength": 1},
                    "severity": {"type": "string", "minLength": 1},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50},
                    "offset": {"type": "integer", "minimum": 0, "default": 0},
                }
            ),
            risk_level="low",
        ),
        ToolDefinition(
            name="get_detections",
            description="List tenant-scoped detection events with optional filters.",
            parameters=_object_schema(
                {
                    "severity": {"type": "string", "minLength": 1},
                    "status": {"type": "string", "minLength": 1},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50},
                }
            ),
            risk_level="low",
        ),
        ToolDefinition(
            name="search_logs",
            description="Search tenant-scoped SIEM logs using a keyword query.",
            parameters=_object_schema(
                {
                    "query": {"type": "string", "minLength": 1},
                    "event_type": {"type": "string", "minLength": 1},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50},
                    "offset": {"type": "integer", "minimum": 0, "default": 0},
                },
                required=["query"],
            ),
            risk_level="low",
        ),
        ToolDefinition(
            name="list_playbooks",
            description="List tenant-scoped and built-in playbooks.",
            parameters=_object_schema({}),
            risk_level="low",
        ),
        ToolDefinition(
            name="get_playbook",
            description="Get one playbook by id.",
            parameters=_object_schema(
                {"playbook_id": {"type": "string", "minLength": 1}},
                required=["playbook_id"],
            ),
            risk_level="low",
        ),
        ToolDefinition(
            name="get_user",
            description="Get one IAM user by id.",
            parameters=_object_schema(
                {"user_id": {"type": "string", "minLength": 1}},
                required=["user_id"],
            ),
            risk_level="low",
        ),
    ]


class SOCToolClient:
    """HTTP client wrapper for deterministic SOC Agent tools."""

    def __init__(
        self,
        *,
        api_gateway_url: str | None = None,
        siem_agent_url: str | None = None,
        iam_agent_url: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_gateway_url = _strip_trailing_slash(
            api_gateway_url or os.getenv("API_GATEWAY_URL") or "http://api_gateway:8000"
        )
        self.siem_agent_url = _strip_trailing_slash(
            siem_agent_url or os.getenv("SIEM_AGENT_URL") or "http://siem_agent:8000"
        )
        self.iam_agent_url = _strip_trailing_slash(
            iam_agent_url or os.getenv("IAM_AGENT_URL") or "http://iam_agent:8000"
        )
        self.timeout = timeout

    async def get_incidents(self, task: AgentTask, **filters: Any) -> dict[str, Any]:
        return await self._request(
            "api_gateway",
            self.api_gateway_url,
            "GET",
            "/api/v1/incidents/",
            task,
            params=_compact(
                {
                    "status": filters.get("status"),
                    "severity": filters.get("severity"),
                    "limit": filters.get("limit", 50),
                    "offset": filters.get("offset", 0),
                }
            ),
        )

    async def get_detections(self, task: AgentTask, **filters: Any) -> dict[str, Any]:
        return await self._request(
            "siem_agent",
            self.siem_agent_url,
            "GET",
            "/detection/events",
            task,
            params=_compact(
                {
                    "severity": filters.get("severity"),
                    "status": filters.get("status"),
                    "limit": filters.get("limit", 50),
                }
            ),
        )

    async def search_logs(
        self,
        task: AgentTask,
        *,
        query: str,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        return await self._request(
            "siem_agent",
            self.siem_agent_url,
            "GET",
            "/siem/logs/search/simple",
            task,
            params=_compact(
                {
                    "q": query,
                    "event_type": event_type,
                    "limit": limit,
                    "offset": offset,
                }
            ),
        )

    async def list_playbooks(self, task: AgentTask) -> dict[str, Any]:
        return await self._request(
            "api_gateway",
            self.api_gateway_url,
            "GET",
            "/api/v1/playbooks",
            task,
        )

    async def get_playbook(self, task: AgentTask, *, playbook_id: str) -> dict[str, Any]:
        return await self._request(
            "api_gateway",
            self.api_gateway_url,
            "GET",
            f"/api/v1/playbooks/{playbook_id}",
            task,
        )

    async def get_user(self, task: AgentTask, *, user_id: str) -> dict[str, Any]:
        return await self._request(
            "iam_agent",
            self.iam_agent_url,
            "GET",
            f"/api/iam-portal/users/{user_id}",
            task,
        )

    async def _request(
        self,
        service_name: str,
        base_url: str,
        method: str,
        path: str,
        task: AgentTask,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = _headers_from_task(task)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method,
                    f"{base_url}{path}",
                    headers=headers,
                    params=_compact(params or {}),
                    json=payload,
                )
        except httpx.RequestError as exc:
            return {
                "ok": False,
                "tenant_id": task.tenant_id,
                "service": service_name,
                "error": str(exc),
            }

        if response.status_code >= 400:
            return {
                "ok": False,
                "tenant_id": task.tenant_id,
                "service": service_name,
                "status_code": response.status_code,
                "error": _response_detail(response),
            }

        return {
            "ok": True,
            "tenant_id": task.tenant_id,
            "service": service_name,
            "data": _response_json(response),
        }


def register_soc_tools(
    registry: ToolRegistry,
    *,
    client: SOCToolClient | None = None,
) -> None:
    """Register read-only SOC tools on a runtime registry."""
    tool_client = client or SOCToolClient()

    async def get_incidents(_agent_task: AgentTask, **filters: Any) -> dict[str, Any]:
        return await tool_client.get_incidents(_agent_task, **filters)

    async def get_detections(_agent_task: AgentTask, **filters: Any) -> dict[str, Any]:
        return await tool_client.get_detections(_agent_task, **filters)

    async def search_logs(
        _agent_task: AgentTask,
        query: str,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        return await tool_client.search_logs(
            _agent_task,
            query=query,
            event_type=event_type,
            limit=limit,
            offset=offset,
        )

    async def list_playbooks(_agent_task: AgentTask) -> dict[str, Any]:
        return await tool_client.list_playbooks(_agent_task)

    async def get_playbook(_agent_task: AgentTask, playbook_id: str) -> dict[str, Any]:
        return await tool_client.get_playbook(_agent_task, playbook_id=playbook_id)

    async def get_user(_agent_task: AgentTask, user_id: str) -> dict[str, Any]:
        return await tool_client.get_user(_agent_task, user_id=user_id)

    handlers = {
        "get_incidents": get_incidents,
        "get_detections": get_detections,
        "search_logs": search_logs,
        "list_playbooks": list_playbooks,
        "get_playbook": get_playbook,
        "get_user": get_user,
    }
    for tool_def in build_soc_tool_definitions():
        registry.register(tool_def, handlers[tool_def.name])


def _strip_trailing_slash(value: str) -> str:
    return value.rstrip("/")


def _compact(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _headers_from_task(task: AgentTask) -> dict[str, str]:
    context = task.context or {}
    auth_context = context.get("auth") or context.get("auth_context") or {}
    authorization = (
        context.get("authorization")
        or context.get("Authorization")
        or auth_context.get("authorization")
        or auth_context.get("Authorization")
    )
    access_token = (
        context.get("access_token")
        or context.get("token")
        or auth_context.get("access_token")
        or auth_context.get("token")
    )
    internal_token = os.getenv("INTERNAL_SERVICE_TOKEN")

    headers = {
        "X-Tenant-ID": task.tenant_id,
        "X-Realm": str(context.get("realm") or context.get("realm_name") or "demo"),
        "Content-Type": "application/json",
    }
    if authorization:
        value = str(authorization).strip()
        headers["Authorization"] = value if value.lower().startswith("bearer ") else f"Bearer {value}"
    elif access_token:
        headers["Authorization"] = f"Bearer {str(access_token).strip()}"
    elif internal_token:
        headers["Authorization"] = f"Bearer {internal_token}"
    return headers


def _response_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"text": response.text}


def _response_detail(response: httpx.Response) -> Any:
    body = _response_json(response)
    if isinstance(body, dict):
        return body.get("detail") or body
    return body
