"""SentinelGrid Core MCP Server - SIEM, SOAR, IAM, Posture tools."""

import logging
from mcp.server import Server
from mcp.shared.exceptions import McpError
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    CallToolRequest,
    ServerResult,
    ErrorData,
    INVALID_PARAMS,
)

from ..core.tool_admission import WIRE_TOOL_MAP, UNAVAILABLE_MESSAGE

logger = logging.getLogger(__name__)


def create_core_server(
    tenant_id: str = "", user_id: str = "", *, case_records=None
) -> Server:
    """
    Create legacy discovery/denial plus explicitly configured case-record tools.

    Legacy tenant_id/user_id arguments are retained for source compatibility only;
    they confer no identity or permissions. No legacy provider tool module is imported.

    Args:
        tenant_id: Tenant ID for multi-tenancy
        user_id: User ID for authorization

    Returns:
        Configured MCP Server
    """
    if case_records is not None:
        from ..core.case_records import CaseRecordTools

        if not isinstance(case_records, CaseRecordTools):
            raise TypeError("Owned case-record adapter required")
    server = Server("sentinelgrid-core")

    # SIEM Tools
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        tools = [
            # SIEM Tools
            Tool(
                name="search_logs",
                description="Search security logs in OpenSearch. Query using Lucene syntax. Time range examples: '1h', '24h', '7d'.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "OpenSearch/Lucene query string (e.g., 'failed_login AND user:admin')",
                        },
                        "time_range": {
                            "type": "string",
                            "description": "Time range to search (e.g., '1h', '24h', '7d')",
                            "default": "1h",
                        },
                        "source": {
                            "type": "string",
                            "description": "Optional source filter (e.g., 'windows', 'linux', 'firewall')",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 100,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_detections",
                description="Get detection events/alerts from the SIEM detection engine.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                            "description": "Filter by severity level",
                        },
                        "status": {
                            "type": "string",
                            "enum": [
                                "new",
                                "in_progress",
                                "resolved",
                                "false_positive",
                            ],
                            "description": "Filter by status",
                        },
                        "limit": {"type": "integer", "default": 50},
                    },
                },
            ),
            Tool(
                name="get_incidents",
                description="List security incidents from the ticketing system.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Filter by incident status",
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Filter by assigned user",
                        },
                        "limit": {"type": "integer", "default": 50},
                    },
                },
            ),
            Tool(
                name="create_incident",
                description="Create a new security incident.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Incident title"},
                        "description": {
                            "type": "string",
                            "description": "Detailed incident description",
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"],
                        },
                        "observables": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of observable IDs to attach",
                        },
                    },
                    "required": ["title", "description", "severity"],
                },
            ),
            # SOAR Tools
            Tool(
                name="list_playbooks",
                description="List available SOAR playbooks for automated response.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Filter by category (e.g., 'phishing', 'malware', 'bruteforce')",
                        }
                    },
                },
            ),
            Tool(
                name="get_playbook",
                description="Get detailed information about a specific playbook.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "playbook_id": {"type": "string", "description": "Playbook ID"}
                    },
                    "required": ["playbook_id"],
                },
            ),
            Tool(
                name="run_playbook",
                description="Execute a SOAR playbook. This will trigger automated response actions.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "playbook_id": {
                            "type": "string",
                            "description": "Playbook ID to execute",
                        },
                        "params": {
                            "type": "object",
                            "description": "Playbook parameters as key-value pairs",
                        },
                        "incident_id": {
                            "type": "string",
                            "description": "Optional incident ID to associate with execution",
                        },
                    },
                    "required": ["playbook_id", "params"],
                },
            ),
            Tool(
                name="get_playbook_execution",
                description="Check status of a playbook execution.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "Execution ID",
                        }
                    },
                    "required": ["execution_id"],
                },
            ),
            # IAM Tools
            Tool(
                name="get_user",
                description="Get user details from IAM system.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID or email"}
                    },
                    "required": ["user_id"],
                },
            ),
            Tool(
                name="lock_account",
                description="Lock a user account (HIGH RISK - requires approval). Use for security incidents.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID to lock"},
                        "reason": {
                            "type": "string",
                            "description": "Reason for locking account",
                        },
                    },
                    "required": ["user_id", "reason"],
                },
            ),
            # Observable Tools
            Tool(
                name="get_observable",
                description="Get enriched observable (IP, domain, hash, etc.) with threat intelligence.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "observable_id": {
                            "type": "string",
                            "description": "Observable ID",
                        }
                    },
                    "required": ["observable_id"],
                },
            ),
            Tool(
                name="search_observables",
                description="Search observables by type or value.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "observable_type": {
                            "type": "string",
                            "enum": [
                                "ip",
                                "domain",
                                "url",
                                "hash",
                                "email",
                                "user_id",
                                "cve",
                            ],
                            "description": "Type of observable",
                        },
                        "value": {
                            "type": "string",
                            "description": "Observable value (partial match)",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "enriching", "completed", "failed"],
                        },
                        "limit": {"type": "integer", "default": 50},
                    },
                },
            ),
        ]
        for tool in tools:
            tool.description = "Unavailable source-preview tool. " + (
                tool.description or ""
            )
        return tools + (case_records.tools() if case_records is not None else [])

    async def reject_unadmitted_call(request: CallToolRequest) -> ServerResult:
        """Reject before argument traversal, mutation or downstream imports.

        The source-preview transport has no verified caller/capabilities. Unknown
        wire names are protocol errors; declared but unavailable operations are
        explicit tool errors. Optional case-record tools use their authenticated
        request and receiving API; no provider dispatcher is installed.
        """
        if case_records is not None and request.params.name in {
            t.name for t in case_records.tools()
        }:
            try:
                context = server.request_context.request
            except LookupError:
                context = None
            if context is None:
                return ServerResult(case_records.unavailable())
            return ServerResult(
                await case_records.call(
                    context, request.params.name, request.params.arguments
                )
            )
        if request.params.name not in WIRE_TOOL_MAP:
            raise McpError(ErrorData(code=INVALID_PARAMS, message="Unknown MCP tool"))
        return ServerResult(
            CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=UNAVAILABLE_MESSAGE)],
            )
        )

    server.request_handlers[CallToolRequest] = reject_unadmitted_call
    return server
