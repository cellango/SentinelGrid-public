"""MCP Server for AI agent integration with SentinelGrid Posture Agent."""

from mcp.server import Server
from mcp.types import Tool, Resource, TextContent, Prompt
import httpx
import os
import logging
from typing import Any, Dict, List

# Configuration
POSTURE_SERVICE_URL = os.getenv("POSTURE_SERVICE_URL", "http://posture-service:8000")
ANALYZER_ORCHESTRATOR_URL = os.getenv("ANALYZER_ORCHESTRATOR_URL", "http://analyzer-orchestrator:8000")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Create MCP server
server = Server("sentinelgrid-posture")


# =============================================================================
# TOOLS - Operations AI agents can perform
# =============================================================================

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="get_posture_summary",
            description="Get overall cloud security posture summary for a tenant including score, grade, and finding counts",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant identifier"
                    }
                },
                "required": ["tenant_id"]
            }
        ),
        Tool(
            name="list_findings",
            description="List security findings with optional filters for severity, source, tool, and status",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant identifier"
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low", "info"],
                        "description": "Filter by severity level"
                    },
                    "source": {
                        "type": "string",
                        "enum": ["cspm", "iac", "dast", "sast", "sca", "secret_scan"],
                        "description": "Filter by finding source"
                    },
                    "tool": {
                        "type": "string",
                        "description": "Filter by tool name (prowler, zap, trivy, etc.)"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["open", "in_progress", "accepted", "fixed", "false_positive"],
                        "description": "Filter by finding status"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of findings to return",
                        "default": 100
                    }
                },
                "required": ["tenant_id"]
            }
        ),
        Tool(
            name="get_finding_details",
            description="Get detailed information about a specific security finding including evidence and remediation",
            inputSchema={
                "type": "object",
                "properties": {
                    "finding_id": {
                        "type": "string",
                        "description": "Finding identifier (UUID)"
                    }
                },
                "required": ["finding_id"]
            }
        ),
        Tool(
            name="analyze_observable",
            description="Trigger security analysis of an observable (asset, repo, image, etc.) using applicable analyzers",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant identifier"
                    },
                    "observable_type": {
                        "type": "string",
                        "enum": [
                            "web_application", "aws_account", "aws_s3_bucket",
                            "docker_image", "git_repository", "k8s_cluster"
                        ],
                        "description": "Type of observable to analyze"
                    },
                    "observable_value": {
                        "type": "string",
                        "description": "Observable value (URL, ARN, image name, etc.)"
                    },
                    "analyzer_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags to filter analyzers (e.g., ['critical'])"
                    }
                },
                "required": ["tenant_id", "observable_type", "observable_value"]
            }
        ),
        Tool(
            name="get_top_risks",
            description="Get top N critical and high severity findings for a tenant",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant identifier"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of top risks to return",
                        "default": 10
                    }
                },
                "required": ["tenant_id"]
            }
        ),
        Tool(
            name="list_analyzers",
            description="List available security analyzers and their capabilities",
            inputSchema={
                "type": "object",
                "properties": {
                    "observable_type": {
                        "type": "string",
                        "description": "Optional: filter by observable type"
                    }
                }
            }
        ),
        Tool(
            name="update_finding_status",
            description="Update the status of a security finding (accept risk, mark as fixed, false positive, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "finding_id": {
                        "type": "string",
                        "description": "Finding identifier (UUID)"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["open", "in_progress", "accepted", "fixed", "false_positive"],
                        "description": "New status"
                    },
                    "resolved_by": {
                        "type": "string",
                        "description": "User ID who resolved the finding"
                    }
                },
                "required": ["finding_id", "status"]
            }
        ),
        Tool(
            name="list_assets",
            description="List infrastructure assets with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "Tenant identifier"
                    },
                    "asset_type": {
                        "type": "string",
                        "description": "Filter by asset type"
                    },
                    "environment": {
                        "type": "string",
                        "enum": ["prod", "staging", "dev"],
                        "description": "Filter by environment"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of assets to return",
                        "default": 100
                    }
                },
                "required": ["tenant_id"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls from AI agents."""
    
    logger.info(f"Tool called: {name} with arguments: {arguments}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        if name == "get_posture_summary":
            tenant_id = arguments["tenant_id"]
            response = await client.get(
                f"{POSTURE_SERVICE_URL}/api/v1/posture/summary/{tenant_id}"
            )
            data = response.json()
            
            summary_text = f"""Posture Summary for Tenant {tenant_id}:
- Score: {data['posture_score']}/100 (Grade: {data['grade']})
- Total Findings: {data['total_findings']}
- Critical: {data['critical_findings']}
- High: {data['high_findings']}
- Medium: {data['medium_findings']}
- Low: {data['low_findings']}
- Total Assets: {data['total_assets']}
- Findings by Source: {data['findings_by_source']}
"""
            
            return [TextContent(
                type="text",
                text=summary_text
            )]
        
        elif name == "list_findings":
            tenant_id = arguments["tenant_id"]
            params = {"tenant_id": tenant_id}
            
            # Add optional filters
            for key in ["severity", "source", "tool", "status", "limit"]:
                if key in arguments:
                    params[key] = arguments[key]
            
            response = await client.get(
                f"{POSTURE_SERVICE_URL}/api/v1/findings/",
                params=params
            )
            data = response.json()
            
            findings_text = f"Found {data['total_count']} findings (showing {len(data['findings'])}):\n\n"
            for finding in data['findings']:
                findings_text += f"- [{finding['severity'].upper()}] {finding['title']}\n"
                findings_text += f"  Tool: {finding['tool']}, Status: {finding['status']}\n"
                findings_text += f"  ID: {finding['id']}\n\n"
            
            return [TextContent(type="text", text=findings_text)]
        
        elif name == "get_finding_details":
            finding_id = arguments["finding_id"]
            response = await client.get(
                f"{POSTURE_SERVICE_URL}/api/v1/findings/{finding_id}"
            )
            data = response.json()
            
            details_text = f"""Finding Details:
ID: {data['id']}
Title: {data['title']}
Severity: {data['severity']}
Status: {data['status']}
Source: {data['source']}
Tool: {data['tool']}

Description:
{data['description']}

Remediation:
{data.get('remediation', 'No remediation guidance available')}

Evidence:
{data.get('evidence', {})}

Framework References:
{data.get('framework_refs', {})}
"""
            
            return [TextContent(type="text", text=details_text)]
        
        elif name == "analyze_observable":
            tenant_id = arguments["tenant_id"]
            observable_type = arguments["observable_type"]
            observable_value = arguments["observable_value"]
            analyzer_tags = arguments.get("analyzer_tags")
            
            payload = {
                "tenant_id": tenant_id,
                "observable_type": observable_type,
                "observable_value": observable_value
            }
            if analyzer_tags:
                payload["analyzer_tags"] = analyzer_tags
            
            response = await client.post(
                f"{ANALYZER_ORCHESTRATOR_URL}/api/v1/analyze",
                json=payload
            )
            data = response.json()
            
            result_text = f"""Analysis Job Started:
Job ID: {data['job_id']}
Observable: {observable_type} = {observable_value}
Analyzers Scheduled: {', '.join(data['analyzers_scheduled'])}
Status: {data['status']}

The analysis is running in the background. Use the job ID to check status.
"""
            
            return [TextContent(type="text", text=result_text)]
        
        elif name == "get_top_risks":
            tenant_id = arguments["tenant_id"]
            limit = arguments.get("limit", 10)
            
            response = await client.get(
                f"{POSTURE_SERVICE_URL}/api/v1/posture/top-risks/{tenant_id}",
                params={"limit": limit}
            )
            data = response.json()
            
            risks_text = f"Top {limit} Risks for Tenant {tenant_id}:\n\n"
            for i, risk in enumerate(data['top_risks'], 1):
                risks_text += f"{i}. [{risk['severity'].upper()}] {risk['title']}\n"
                risks_text += f"   Source: {risk['source']}, Tool: {risk['tool']}\n"
                risks_text += f"   First seen: {risk['first_seen']}\n\n"
            
            return [TextContent(type="text", text=risks_text)]
        
        elif name == "list_analyzers":
            params = {}
            if "observable_type" in arguments:
                params["observable_type"] = arguments["observable_type"]
            
            response = await client.get(
                f"{ANALYZER_ORCHESTRATOR_URL}/api/v1/analyzers",
                params=params
            )
            data = response.json()
            
            analyzers_text = "Available Analyzers:\n\n"
            for analyzer in data.get('analyzers', []):
                analyzers_text += f"- {analyzer['name']} (v{analyzer['version']})\n"
                analyzers_text += f"  {analyzer['description']}\n"
                analyzers_text += f"  Types: {analyzer['supported_types']}\n"
                analyzers_text += f"  Tags: {analyzer['tags']}\n\n"
            
            return [TextContent(type="text", text=analyzers_text)]
        
        elif name == "update_finding_status":
            finding_id = arguments["finding_id"]
            payload = {"status": arguments["status"]}
            if "resolved_by" in arguments:
                payload["resolved_by"] = arguments["resolved_by"]
            
            response = await client.patch(
                f"{POSTURE_SERVICE_URL}/api/v1/findings/{finding_id}",
                json=payload
            )
            data = response.json()
            
            return [TextContent(
                type="text",
                text=f"Finding {finding_id} updated to status: {data['status']}"
            )]
        
        elif name == "list_assets":
            tenant_id = arguments["tenant_id"]
            params = {"tenant_id": tenant_id}
            
            for key in ["asset_type", "environment", "limit"]:
                if key in arguments:
                    params[key] = arguments[key]
            
            response = await client.get(
                f"{POSTURE_SERVICE_URL}/api/v1/assets/",
                params=params
            )
            data = response.json()
            
            assets_text = f"Found {data['total_count']} assets (showing {len(data['assets'])}):\n\n"
            for asset in data['assets']:
                assets_text += f"- {asset['name']} ({asset['asset_type']})\n"
                assets_text += f"  Risk Score: {asset['risk_score']}/100\n"
                assets_text += f"  Findings: {asset['critical_findings_count']} critical, {asset['high_findings_count']} high\n"
                assets_text += f"  Environment: {asset['environment']}, Region: {asset['region']}\n\n"
            
            return [TextContent(type="text", text=assets_text)]
        
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]


# =============================================================================
# RESOURCES - Data AI agents can read
# =============================================================================

@server.list_resources()
async def list_resources() -> List[Resource]:
    """List available MCP resources."""
    return [
        Resource(
            uri="posture://summary/{tenant_id}",
            name="Posture Summary",
            description="Overall security posture summary for a tenant",
            mimeType="application/json"
        ),
        Resource(
            uri="posture://findings/{tenant_id}",
            name="Security Findings",
            description="List of security findings for a tenant",
            mimeType="application/json"
        ),
        Resource(
            uri="posture://assets/{tenant_id}",
            name="Infrastructure Assets",
            description="List of infrastructure assets for a tenant",
            mimeType="application/json"
        )
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource."""
    logger.info(f"Reading resource: {uri}")
    
    # Parse URI
    parts = uri.split("/")
    if len(parts) < 3:
        return json.dumps({"error": "Invalid URI format"})
    
    resource_type = parts[1]  # summary, findings, assets
    tenant_id = parts[2] if len(parts) > 2 else None
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        if resource_type == "summary" and tenant_id:
            response = await client.get(
                f"{POSTURE_SERVICE_URL}/api/v1/posture/summary/{tenant_id}"
            )
            return response.text
        
        elif resource_type == "findings" and tenant_id:
            response = await client.get(
                f"{POSTURE_SERVICE_URL}/api/v1/findings/",
                params={"tenant_id": tenant_id, "limit": 100}
            )
            return response.text
        
        elif resource_type == "assets" and tenant_id:
            response = await client.get(
                f"{POSTURE_SERVICE_URL}/api/v1/assets/",
                params={"tenant_id": tenant_id, "limit": 100}
            )
            return response.text
        
        else:
            return json.dumps({"error": "Unknown resource type"})


# =============================================================================
# PROMPTS - Pre-defined prompts for AI agents
# =============================================================================

@server.list_prompts()
async def list_prompts() -> List[Prompt]:
    """List available prompts."""
    return [
        Prompt(
            name="analyze-posture",
            description="Analyze security posture and provide recommendations",
            arguments=[
                {"name": "tenant_id", "description": "Tenant to analyze", "required": True}
            ]
        ),
        Prompt(
            name="prioritize-risks",
            description="Prioritize security risks based on severity and business impact",
            arguments=[
                {"name": "tenant_id", "description": "Tenant identifier", "required": True},
                {"name": "business_context", "description": "Business context for prioritization", "required": False}
            ]
        ),
        Prompt(
            name="remediation-plan",
            description="Create a remediation plan for security findings",
            arguments=[
                {"name": "finding_ids", "description": "Comma-separated finding IDs", "required": True}
            ]
        )
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: Dict[str, str]) -> str:
    """Get a prompt with filled arguments."""
    
    if name == "analyze-posture":
        tenant_id = arguments.get("tenant_id")
        return f"""Analyze the security posture for tenant {tenant_id}.

Use the following tools:
1. get_posture_summary - Get overall posture score and metrics
2. get_top_risks - Get the most critical findings
3. list_findings - Get detailed finding information

Provide:
1. Overall assessment of security posture
2. Top 3-5 most critical risks
3. Recommendations for improvement
4. Priority order for remediation
"""
    
    elif name == "prioritize-risks":
        tenant_id = arguments.get("tenant_id")
        business_context = arguments.get("business_context", "")
        
        return f"""Prioritize security risks for tenant {tenant_id}.

Business Context: {business_context}

Use these tools:
1. get_top_risks - Get critical and high findings
2. list_findings - Get all findings
3. list_assets - Understand asset landscape

Consider:
1. Severity level
2. Business impact (based on asset environment and type)
3. Exploitability
4. Compliance requirements

Provide a prioritized list with reasoning.
"""
    
    elif name == "remediation-plan":
        finding_ids = arguments.get("finding_ids", "")
        
        return f"""Create a remediation plan for these findings: {finding_ids}

Use these tools:
1. get_finding_details - Get details for each finding
2. list_assets - Understand affected assets

For each finding, provide:
1. What the issue is
2. Why it's important
3. Step-by-step remediation
4. Estimated effort
5. Dependencies

Create a consolidated remediation plan with timeline.
"""
    
    else:
        return f"Unknown prompt: {name}"


# =============================================================================
# RUN SERVER
# =============================================================================

async def main():
    """Run the MCP server."""
    import mcp.server.stdio
    
    logger.info("Starting SentinelGrid Posture MCP Server...")
    logger.info(f"Posture Service: {POSTURE_SERVICE_URL}")
    logger.info(f"Analyzer Orchestrator: {ANALYZER_ORCHESTRATOR_URL}")
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    import json
    asyncio.run(main())

