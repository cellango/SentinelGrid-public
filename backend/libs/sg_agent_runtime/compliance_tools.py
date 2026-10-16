"""Deterministic Compliance Agent tools.

These tools deliberately call existing service APIs instead of reading data
directly. The agent task tenant is injected into headers and request payloads
so the model cannot choose a tenant scope.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from .models import AgentTask, ToolDefinition
from .tool_registry import ToolRegistry


COMPLIANCE_TOOL_NAMES = [
    "list_frameworks",
    "get_selected_frameworks",
    "get_framework_coverage",
    "get_control_status",
    "list_evidence",
    "create_evidence_collection_task",
    "collect_evidence",
    "create_evidence_package",
    "generate_compliance_report",
    "list_control_gaps",
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


def build_compliance_tool_definitions() -> list[ToolDefinition]:
    """Return the Compliance Agent tool definitions in runtime order."""
    return [
        ToolDefinition(
            name="list_frameworks",
            description="List compliance frameworks available in SentinelGrid.",
            parameters=_object_schema({}),
            risk_level="low",
        ),
        ToolDefinition(
            name="get_selected_frameworks",
            description="List the current tenant's selected compliance frameworks.",
            parameters=_object_schema({}),
            risk_level="low",
        ),
        ToolDefinition(
            name="get_framework_coverage",
            description="Get coverage for one compliance framework for the current tenant.",
            parameters=_object_schema(
                {
                    "framework_id": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Framework id such as soc2, hipaa, pci_dss, or nist_800_171.",
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 100},
                    "offset": {"type": "integer", "minimum": 0, "default": 0},
                },
                required=["framework_id"],
            ),
            risk_level="low",
        ),
        ToolDefinition(
            name="get_control_status",
            description="Get tenant-scoped status for a compliance control.",
            parameters=_object_schema(
                {
                    "control_id": {"type": "string", "minLength": 1},
                    "framework_id": {"type": "string", "minLength": 1},
                },
                required=["control_id"],
            ),
            risk_level="low",
        ),
        ToolDefinition(
            name="list_evidence",
            description="List tenant-scoped evidence items with narrow filters.",
            parameters=_object_schema(
                {
                    "framework_id": {"type": "string", "minLength": 1},
                    "control_id": {"type": "string", "minLength": 1},
                    "source_system": {"type": "string", "minLength": 1},
                    "review_status": {"type": "string", "minLength": 1},
                    "package_id": {"type": "string", "minLength": 1},
                    "expires_before": {"type": "string", "format": "date-time"},
                    "expires_after": {"type": "string", "format": "date-time"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
                    "offset": {"type": "integer", "minimum": 0, "default": 0},
                },
            ),
            risk_level="low",
        ),
        ToolDefinition(
            name="create_evidence_collection_task",
            description="Create a supervised tenant-scoped evidence collection task.",
            parameters=_object_schema(
                {
                    "task_name": {"type": "string", "minLength": 1, "maxLength": 255},
                    "task_type": {"type": "string", "minLength": 1, "maxLength": 100},
                    "package_id": {"type": "string", "minLength": 1},
                    "source_system": {"type": "string", "minLength": 1, "maxLength": 120},
                    "source_resource_id": {"type": "string", "minLength": 1},
                    "collector": {"type": "string", "minLength": 1},
                    "collection_method": {"type": "string", "minLength": 1, "maxLength": 80},
                    "due_at": {"type": "string", "format": "date-time"},
                    "metadata": {"type": "object"},
                    "idempotency_key": {"type": "string", "maxLength": 255},
                },
                required=["task_name", "task_type"],
            ),
            requires_approval=True,
            risk_level="medium",
        ),
        ToolDefinition(
            name="collect_evidence",
            description="Collect evidence for one control through the IAM compliance collector.",
            parameters=_object_schema(
                {
                    "control_id": {"type": "string", "minLength": 1},
                    "evidence_types": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                        "minItems": 1,
                    },
                },
                required=["control_id", "evidence_types"],
            ),
            requires_approval=True,
            risk_level="medium",
        ),
        ToolDefinition(
            name="create_evidence_package",
            description="Create a tenant-scoped evidence package from selected evidence items.",
            parameters=_object_schema(
                {
                    "package_name": {"type": "string", "minLength": 1, "maxLength": 255},
                    "framework_id": {"type": "string", "minLength": 1},
                    "report_period_start": {"type": "string", "format": "date"},
                    "report_period_end": {"type": "string", "format": "date"},
                    "package_type": {"type": "string", "default": "audit_package"},
                    "summary": {"type": "string"},
                    "description": {"type": "string"},
                    "sensitivity": {
                        "type": "string",
                        "enum": ["public", "internal", "confidential", "restricted"],
                        "default": "internal",
                    },
                    "metadata": {"type": "object"},
                    "evidence_item_ids": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                },
                required=["package_name", "report_period_start", "report_period_end"],
            ),
            requires_approval=True,
            risk_level="medium",
        ),
        ToolDefinition(
            name="generate_compliance_report",
            description="Request a tenant-scoped compliance report from the reporting service.",
            parameters=_object_schema(
                {
                    "template_id": {"type": "string", "minLength": 1},
                    "format": {"type": "string", "enum": ["pdf", "csv"], "default": "pdf"},
                    "framework_ids": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "control_ids": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "evidence_package_ids": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "date_range": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "start": {"type": "string"},
                            "end": {"type": "string"},
                        },
                    },
                    "include_gaps": {"type": "boolean", "default": True},
                    "include_expired_evidence": {"type": "boolean", "default": False},
                    "parameters": {"type": "object"},
                },
                required=["template_id"],
            ),
            requires_approval=True,
            risk_level="medium",
        ),
        ToolDefinition(
            name="list_control_gaps",
            description="List tenant-scoped control gaps from compliance coverage.",
            parameters=_object_schema(
                {
                    "framework_id": {"type": "string", "minLength": 1},
                    "severity": {"type": "string", "minLength": 1},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
                    "offset": {"type": "integer", "minimum": 0, "default": 0},
                },
            ),
            risk_level="low",
        ),
    ]


class ComplianceToolClient:
    """HTTP client wrapper for Compliance Agent deterministic tools."""

    def __init__(
        self,
        *,
        compliance_service_url: str | None = None,
        reporting_service_url: str | None = None,
        iam_agent_url: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.compliance_service_url = _strip_trailing_slash(
            compliance_service_url
            or os.getenv("COMPLIANCE_SERVICE_URL")
            or "http://compliance_service:8000"
        )
        self.reporting_service_url = _strip_trailing_slash(
            reporting_service_url
            or os.getenv("REPORTING_SERVICE_URL")
            or "http://reporting_service:8000"
        )
        self.iam_agent_url = _strip_trailing_slash(
            iam_agent_url
            or os.getenv("IAM_AGENT_URL")
            or "http://iam_agent:8000"
        )
        self.timeout = timeout

    async def list_frameworks(self, task: AgentTask) -> dict[str, Any]:
        return await self._request(
            "compliance_service",
            self.compliance_service_url,
            "GET",
            "/api/v1/compliance/frameworks",
            task,
        )

    async def get_selected_frameworks(self, task: AgentTask) -> dict[str, Any]:
        return await self._request(
            "compliance_service",
            self.compliance_service_url,
            "GET",
            "/api/v1/compliance/framework-selections",
            task,
        )

    async def get_framework_coverage(
        self,
        task: AgentTask,
        *,
        framework_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        return await self._request(
            "compliance_service",
            self.compliance_service_url,
            "GET",
            f"/api/v1/compliance/frameworks/{framework_id}/coverage",
            task,
            params={"limit": limit, "offset": offset},
        )

    async def get_control_status(
        self,
        task: AgentTask,
        *,
        control_id: str,
        framework_id: str | None = None,
    ) -> dict[str, Any]:
        params = {"framework_id": framework_id} if framework_id else None
        return await self._request(
            "compliance_service",
            self.compliance_service_url,
            "GET",
            f"/api/v1/compliance/controls/{control_id}/status",
            task,
            params=params,
        )

    async def list_evidence(self, task: AgentTask, **filters: Any) -> dict[str, Any]:
        params = _compact(
            {
                "tenant_id": task.tenant_id,
                "framework_id": filters.get("framework_id"),
                "control_id": filters.get("control_id"),
                "source_system": filters.get("source_system"),
                "review_status": filters.get("review_status"),
                "package_id": filters.get("package_id"),
                "expires_before": filters.get("expires_before"),
                "expires_after": filters.get("expires_after"),
                "limit": filters.get("limit", 50),
                "offset": filters.get("offset", 0),
            }
        )
        return await self._request(
            "compliance_service",
            self.compliance_service_url,
            "GET",
            "/api/v1/compliance/evidence",
            task,
            params=params,
        )

    async def create_evidence_collection_task(
        self,
        task: AgentTask,
        **payload: Any,
    ) -> dict[str, Any]:
        body = _compact(
            {
                "tenant_id": task.tenant_id,
                "realm_name": payload.get("realm_name", "default"),
                "package_id": payload.get("package_id"),
                "task_name": payload.get("task_name"),
                "task_type": payload.get("task_type"),
                "status": payload.get("status", "pending"),
                "source_system": payload.get("source_system"),
                "source_resource_id": payload.get("source_resource_id"),
                "collector": payload.get("collector"),
                "collection_method": payload.get("collection_method"),
                "requested_by": _actor_id_from_task(task),
                "due_at": payload.get("due_at"),
                "metadata": payload.get("metadata", {}),
                "idempotency_key": payload.get("idempotency_key"),
            }
        )
        return await self._request(
            "compliance_service",
            self.compliance_service_url,
            "POST",
            "/api/v1/compliance/evidence/tasks",
            task,
            payload=body,
        )

    async def collect_evidence(
        self,
        task: AgentTask,
        *,
        control_id: str,
        evidence_types: list[str],
    ) -> dict[str, Any]:
        body = {
            "tenant_id": task.tenant_id,
            "control_id": control_id,
            "evidence_types": evidence_types,
        }
        return await self._request(
            "iam_agent",
            self.iam_agent_url,
            "POST",
            "/internal/iam/compliance/evidence/collect",
            task,
            payload=body,
        )

    async def create_evidence_package(self, task: AgentTask, **payload: Any) -> dict[str, Any]:
        body = _compact(
            {
                "tenant_id": task.tenant_id,
                "realm_name": payload.get("realm_name", "default"),
                "package_name": payload.get("package_name"),
                "framework_id": payload.get("framework_id"),
                "report_period_start": payload.get("report_period_start"),
                "report_period_end": payload.get("report_period_end"),
                "created_by": _actor_id_from_task(task),
                "package_type": payload.get("package_type", "audit_package"),
                "summary": payload.get("summary"),
                "description": payload.get("description"),
                "sensitivity": payload.get("sensitivity", "internal"),
                "metadata": payload.get("metadata", {}),
                "evidence_item_ids": payload.get("evidence_item_ids", []),
            }
        )
        return await self._request(
            "compliance_service",
            self.compliance_service_url,
            "POST",
            "/api/v1/compliance/evidence/packages",
            task,
            payload=body,
        )

    async def generate_compliance_report(self, task: AgentTask, **payload: Any) -> dict[str, Any]:
        body = _compact(
            {
                "template_id": payload.get("template_id"),
                "format": payload.get("format", "pdf"),
                "date_range": payload.get("date_range"),
                "framework_ids": payload.get("framework_ids"),
                "control_ids": payload.get("control_ids"),
                "evidence_package_ids": payload.get("evidence_package_ids"),
                "include_gaps": payload.get("include_gaps", True),
                "include_expired_evidence": payload.get("include_expired_evidence", False),
                "parameters": payload.get("parameters"),
            }
        )
        return await self._request(
            "reporting_service",
            self.reporting_service_url,
            "POST",
            "/api/v1/reports/generate",
            task,
            payload=body,
        )

    async def list_control_gaps(
        self,
        task: AgentTask,
        *,
        framework_id: str | None = None,
        severity: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        if framework_id:
            coverage = await self.get_framework_coverage(
                task,
                framework_id=framework_id,
                limit=min(max(limit, 1), 200),
                offset=offset,
            )
        else:
            coverage = await self._request(
                "compliance_service",
                self.compliance_service_url,
                "GET",
                "/api/v1/compliance/coverage",
                task,
                params={"limit": min(max(limit, 1), 200), "offset": offset},
            )
        if not coverage.get("ok"):
            return coverage
        gaps = _extract_gaps(coverage.get("data"), severity=severity)
        return {
            "ok": True,
            "tenant_id": task.tenant_id,
            "data": {
                "items": gaps[:limit],
                "total": len(gaps),
                "limit": limit,
                "offset": offset,
            },
        }

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
        try:
            headers = _auth_headers_from_task(task)
        except ValueError as exc:
            return {
                "ok": False,
                "tenant_id": task.tenant_id,
                "status_code": 401,
                "service": service_name,
                "error": str(exc),
            }

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


def register_compliance_tools(
    registry: ToolRegistry,
    *,
    client: ComplianceToolClient | None = None,
) -> None:
    """Register all Compliance Agent tools on a runtime registry."""
    tool_client = client or ComplianceToolClient()

    async def list_frameworks(_agent_task: AgentTask) -> dict[str, Any]:
        return await tool_client.list_frameworks(_agent_task)

    async def get_selected_frameworks(_agent_task: AgentTask) -> dict[str, Any]:
        return await tool_client.get_selected_frameworks(_agent_task)

    async def get_framework_coverage(
        _agent_task: AgentTask,
        framework_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        return await tool_client.get_framework_coverage(
            _agent_task,
            framework_id=framework_id,
            limit=limit,
            offset=offset,
        )

    async def get_control_status(
        _agent_task: AgentTask,
        control_id: str,
        framework_id: str | None = None,
    ) -> dict[str, Any]:
        return await tool_client.get_control_status(
            _agent_task,
            control_id=control_id,
            framework_id=framework_id,
        )

    async def list_evidence(_agent_task: AgentTask, **filters: Any) -> dict[str, Any]:
        return await tool_client.list_evidence(_agent_task, **filters)

    async def create_evidence_collection_task(
        _agent_task: AgentTask,
        **payload: Any,
    ) -> dict[str, Any]:
        return await tool_client.create_evidence_collection_task(_agent_task, **payload)

    async def collect_evidence(
        _agent_task: AgentTask,
        control_id: str,
        evidence_types: list[str],
    ) -> dict[str, Any]:
        return await tool_client.collect_evidence(
            _agent_task,
            control_id=control_id,
            evidence_types=evidence_types,
        )

    async def create_evidence_package(_agent_task: AgentTask, **payload: Any) -> dict[str, Any]:
        return await tool_client.create_evidence_package(_agent_task, **payload)

    async def generate_compliance_report(
        _agent_task: AgentTask,
        **payload: Any,
    ) -> dict[str, Any]:
        return await tool_client.generate_compliance_report(_agent_task, **payload)

    async def list_control_gaps(_agent_task: AgentTask, **params: Any) -> dict[str, Any]:
        return await tool_client.list_control_gaps(_agent_task, **params)

    handlers = {
        "list_frameworks": list_frameworks,
        "get_selected_frameworks": get_selected_frameworks,
        "get_framework_coverage": get_framework_coverage,
        "get_control_status": get_control_status,
        "list_evidence": list_evidence,
        "create_evidence_collection_task": create_evidence_collection_task,
        "collect_evidence": collect_evidence,
        "create_evidence_package": create_evidence_package,
        "generate_compliance_report": generate_compliance_report,
        "list_control_gaps": list_control_gaps,
    }
    for tool_def in build_compliance_tool_definitions():
        registry.register(tool_def, handlers[tool_def.name])


def _strip_trailing_slash(value: str) -> str:
    return value.rstrip("/")


def _compact(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def _auth_headers_from_task(task: AgentTask) -> dict[str, str]:
    authorization = _authorization_from_task(task)
    headers = {
        "Authorization": authorization,
        "X-Tenant-ID": task.tenant_id,
        "Content-Type": "application/json",
    }
    actor_id = _actor_id_from_task(task)
    if actor_id:
        headers["X-User-ID"] = actor_id
    return headers


def _authorization_from_task(task: AgentTask) -> str:
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
    if authorization:
        value = str(authorization).strip()
        return value if value.lower().startswith("bearer ") else f"Bearer {value}"
    if access_token:
        return f"Bearer {str(access_token).strip()}"
    raise ValueError("Compliance tools require task context authorization")


def _actor_id_from_task(task: AgentTask) -> str | None:
    context = task.context or {}
    auth_context = context.get("auth") or context.get("auth_context") or {}
    value = (
        context.get("user_id")
        or context.get("actor_id")
        or auth_context.get("user_id")
        or auth_context.get("actor_id")
    )
    return str(value) if value else None


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


def _extract_gaps(data: Any, *, severity: str | None = None) -> list[dict[str, Any]]:
    normalized_severity = str(severity).lower() if severity else None
    framework_items = []
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        framework_items = data["items"]
    elif isinstance(data, dict):
        framework_items = [data]

    gaps: list[dict[str, Any]] = []
    for framework in framework_items:
        if not isinstance(framework, dict):
            continue
        framework_id = framework.get("framework_id") or framework.get("id")
        controls = framework.get("controls") or []
        for control in controls:
            if not isinstance(control, dict):
                continue
            control_id = control.get("control_id") or control.get("id")
            for gap in control.get("gaps") or control.get("coverage_gaps") or []:
                if not isinstance(gap, dict):
                    continue
                gap_severity = str(gap.get("severity") or "").lower()
                if normalized_severity and gap_severity != normalized_severity:
                    continue
                gaps.append(
                    {
                        **gap,
                        "framework_id": framework_id,
                        "control_id": control_id,
                        "control_title": control.get("title") or control.get("name"),
                    }
                )
    return gaps
