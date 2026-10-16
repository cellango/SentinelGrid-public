"""SentinelGrid Core MCP Server - SIEM, SOAR, IAM, Posture tools."""

import logging
from mcp.server import Server
from mcp.types import Tool, TextContent

from app.tools import siem_tools, soar_tools, iam_tools, observable_tools

logger = logging.getLogger(__name__)


def create_core_server(tenant_id: str = "", user_id: str = "") -> Server:
    """
    Create the SentinelGrid Core MCP server.
    
    Args:
        tenant_id: Tenant ID for multi-tenancy
        user_id: User ID for authorization
    
    Returns:
        Configured MCP Server
    """
    server = Server("sentinelgrid-core")
    
    # SIEM Tools
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            # SIEM Tools
            Tool(
                name="search_logs",
                description="Search security logs in OpenSearch. Query using Lucene syntax. Time range examples: '1h', '24h', '7d'.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "OpenSearch/Lucene query string (e.g., 'failed_login AND user:admin')"
                        },
                        "time_range": {
                            "type": "string",
                            "description": "Time range to search (e.g., '1h', '24h', '7d')",
                            "default": "1h"
                        },
                        "source": {
                            "type": "string",
                            "description": "Optional source filter (e.g., 'windows', 'linux', 'firewall')"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 100
                        }
                    },
                    "required": ["query"]
                }
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
                            "description": "Filter by severity level"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["new", "in_progress", "resolved", "false_positive"],
                            "description": "Filter by status"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 50
                        }
                    }
                }
            ),
            Tool(
                name="get_incidents",
                description="List security incidents from the ticketing system.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Filter by incident status"
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"]
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Filter by assigned user"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 50
                        }
                    }
                }
            ),
            Tool(
                name="create_incident",
                description="Create a new security incident.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Incident title"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed incident description"
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low"]
                        },
                        "observables": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of observable IDs to attach"
                        }
                    },
                    "required": ["title", "description", "severity"]
                }
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
                            "description": "Filter by category (e.g., 'phishing', 'malware', 'bruteforce')"
                        }
                    }
                }
            ),
            Tool(
                name="get_playbook",
                description="Get detailed information about a specific playbook.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "playbook_id": {
                            "type": "string",
                            "description": "Playbook ID"
                        }
                    },
                    "required": ["playbook_id"]
                }
            ),
            Tool(
                name="run_playbook",
                description="Execute a SOAR playbook. This will trigger automated response actions.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "playbook_id": {
                            "type": "string",
                            "description": "Playbook ID to execute"
                        },
                        "params": {
                            "type": "object",
                            "description": "Playbook parameters as key-value pairs"
                        },
                        "incident_id": {
                            "type": "string",
                            "description": "Optional incident ID to associate with execution"
                        }
                    },
                    "required": ["playbook_id", "params"]
                }
            ),
            Tool(
                name="get_playbook_execution",
                description="Check status of a playbook execution.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "execution_id": {
                            "type": "string",
                            "description": "Execution ID"
                        }
                    },
                    "required": ["execution_id"]
                }
            ),
            # IAM Tools
            Tool(
                name="get_user",
                description="Get user details from IAM system.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID or email"
                        }
                    },
                    "required": ["user_id"]
                }
            ),
            Tool(
                name="lock_account",
                description="Lock a user account (HIGH RISK - requires approval). Use for security incidents.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID to lock"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for locking account"
                        }
                    },
                    "required": ["user_id", "reason"]
                }
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
                            "description": "Observable ID"
                        }
                    },
                    "required": ["observable_id"]
                }
            ),
            Tool(
                name="search_observables",
                description="Search observables by type or value.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "observable_type": {
                            "type": "string",
                            "enum": ["ip", "domain", "url", "hash", "email", "user_id", "cve"],
                            "description": "Type of observable"
                        },
                        "value": {
                            "type": "string",
                            "description": "Observable value (partial match)"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "enriching", "completed", "failed"]
                        },
                        "limit": {
                            "type": "integer",
                            "default": 50
                        }
                    }
                }
            ),
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Handle tool calls."""
        try:
            # Add tenant_id and user_id to all tool calls
            arguments["tenant_id"] = tenant_id
            arguments["user_id"] = user_id
            
            # Route to appropriate tool
            if name == "search_logs":
                result = await siem_tools.search_logs(**arguments)
            elif name == "get_detections":
                result = await siem_tools.get_detections(**arguments)
            elif name == "get_incidents":
                result = await siem_tools.get_incidents(**arguments)
            elif name == "create_incident":
                result = await siem_tools.create_incident(**arguments)
            elif name == "list_playbooks":
                result = await soar_tools.list_playbooks(**arguments)
            elif name == "get_playbook":
                result = await soar_tools.get_playbook(**arguments)
            elif name == "run_playbook":
                result = await soar_tools.run_playbook(**arguments)
            elif name == "get_playbook_execution":
                result = await soar_tools.get_playbook_execution(**arguments)
            elif name == "get_user":
                result = await iam_tools.get_user(**arguments)
            elif name == "lock_account":
                result = await iam_tools.lock_account(**arguments)
            elif name == "get_observable":
                result = await observable_tools.get_observable(**arguments)
            elif name == "search_observables":
                result = await observable_tools.search_observables(**arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
            
            # Return result
            import json
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        except Exception as e:
            logger.error(f"Tool call failed: {name} - {e}")
            return [TextContent(
                type="text",
                text=f"Error executing {name}: {str(e)}"
            )]
    
    return server

