# MCP Integration Guide

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


## Overview

The SentinelGrid Posture Agent includes an **MCP (Model Context Protocol) server** for AI agent integration. This allows AI agents (including Claude, GPT-4, or custom agents) to query posture data, trigger analyses, and reason about security posture.

## MCP Server

**Service**: `posture-mcp-server`  
**Port**: 8102  
**Protocol**: MCP (stdio-based)

## Available Tools

AI agents can call these tools:

### 1. get_posture_summary

Get overall security posture for a tenant.

**Input**:
```json
{
  "tenant_id": "tenant-uuid"
}
```

**Output**:
- Posture score (0-100)
- Grade (A-F)
- Finding counts by severity
- Total assets
- Findings by source

**Use Case**: "What's our overall security posture?"

### 2. list_findings

Query findings with filters.

**Input**:
```json
{
  "tenant_id": "tenant-uuid",
  "severity": "critical",  // optional
  "source": "cspm",       // optional
  "tool": "prowler",      // optional
  "status": "open",       // optional
  "limit": 100            // optional
}
```

**Output**: List of findings with details

**Use Case**: "Show me all critical CSPM findings"

### 3. get_finding_details

Get detailed information about a specific finding.

**Input**:
```json
{
  "finding_id": "finding-uuid"
}
```

**Output**:
- Full finding details
- Evidence
- Remediation steps
- Framework references

**Use Case**: "Explain this finding in detail"

### 4. analyze_observable

Trigger security analysis of an observable.

**Input**:
```json
{
  "tenant_id": "tenant-uuid",
  "observable_type": "web_application",
  "observable_value": "https://app.example.com",
  "analyzer_tags": ["critical"]  // optional
}
```

**Output**:
- Job ID
- Analyzers scheduled
- Status

**Use Case**: "Scan this web application for vulnerabilities"

### 5. get_top_risks

Get top N critical findings.

**Input**:
```json
{
  "tenant_id": "tenant-uuid",
  "limit": 10  // optional
}
```

**Output**: Top risk findings ordered by severity

**Use Case**: "What are our biggest security risks?"

### 6. list_analyzers

List available analyzers and their capabilities.

**Input**:
```json
{
  "observable_type": "web_application"  // optional
}
```

**Output**: List of analyzers with metadata

**Use Case**: "What tools can analyze web applications?"

### 7. update_finding_status

Update finding status (accept risk, mark fixed, etc.).

**Input**:
```json
{
  "finding_id": "finding-uuid",
  "status": "fixed",
  "resolved_by": "user-uuid"  // optional
}
```

**Output**: Updated finding status

**Use Case**: "Mark this finding as fixed"

### 8. list_assets

List infrastructure assets.

**Input**:
```json
{
  "tenant_id": "tenant-uuid",
  "asset_type": "aws_s3_bucket",  // optional
  "environment": "prod",          // optional
  "limit": 100                    // optional
}
```

**Output**: List of assets with risk scores

**Use Case**: "Show me all production assets"

## Available Resources

Resources AI agents can read directly:

### 1. posture://summary/{tenant_id}

JSON summary of security posture.

### 2. posture://findings/{tenant_id}

JSON list of all findings.

### 3. posture://assets/{tenant_id}

JSON list of all assets.

## Pre-defined Prompts

### analyze-posture

Comprehensive posture analysis prompt.

**Arguments**:
- `tenant_id` (required)

**What it does**:
- Gets posture summary
- Identifies top risks
- Provides recommendations

### prioritize-risks

Risk prioritization prompt with business context.

**Arguments**:
- `tenant_id` (required)
- `business_context` (optional)

**What it does**:
- Considers severity + business impact
- Prioritizes findings
- Provides remediation order

### remediation-plan

Create detailed remediation plan.

**Arguments**:
- `finding_ids` (required, comma-separated)

**What it does**:
- Analyzes each finding
- Creates step-by-step plan
- Estimates effort
- Identifies dependencies

## Using the MCP Server

### From Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sentinelgrid-posture": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--network", "host",
        "sentinelgrid-posture-mcp:latest"
      ]
    }
  }
}
```

### From Python

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def query_posture():
    server_params = StdioServerParameters(
        command="docker",
        args=["run", "-i", "--rm", "sentinelgrid-posture-mcp:latest"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            
            # Call tool
            result = await session.call_tool(
                "get_posture_summary",
                arguments={"tenant_id": "tenant-123"}
            )
            
            print(result)
```

### Example AI Conversations

#### Conversation 1: Posture Assessment

**User**: "What's our security posture?"

**AI** (uses `get_posture_summary`):
> Your security posture score is 78/100 (Grade: C).
> You have 15 findings: 2 critical, 5 high, 8 medium.
> Main issues are in CSPM (cloud misconfigurations).

**User**: "What are the critical issues?"

**AI** (uses `list_findings` with severity=critical):
> You have 2 critical findings:
> 1. Public S3 bucket with sensitive data
> 2. Exposed admin credentials in Git repository

#### Conversation 2: Trigger Analysis

**User**: "Scan our production web app at https://app.example.com"

**AI** (uses `analyze_observable`):
> I've triggered a security analysis (Job ID: abc-123).
> Running analyzers: ZAP (DAST), Nuclei (vulnerability scan).
> The scan is in progress. I'll notify you when complete.

#### Conversation 3: Remediation

**User**: "How do I fix finding XYZ?"

**AI** (uses `get_finding_details`):
> This finding is a public S3 bucket with sensitive tags.
> 
> Remediation steps:
> 1. Remove public access: `aws s3api put-public-access-block`
> 2. Enable default encryption
> 3. Add bucket policy denying public reads
> 
> Would you like me to create a SOAR playbook for this?

## MCP Tools → API Mapping

| MCP Tool | Backend API | Method |
|----------|-------------|--------|
| get_posture_summary | `/api/v1/posture/summary/{tenant_id}` | GET |
| list_findings | `/api/v1/findings/` | GET |
| get_finding_details | `/api/v1/findings/{id}` | GET |
| analyze_observable | `/api/v1/analyze` | POST |
| get_top_risks | `/api/v1/posture/top-risks/{tenant_id}` | GET |
| list_analyzers | `/api/v1/analyzers` | GET |
| update_finding_status | `/api/v1/findings/{id}` | PATCH |
| list_assets | `/api/v1/assets/` | GET |

## Multi-Tenancy

All MCP tools require `tenant_id` parameter to ensure data isolation. The MCP server enforces tenant-scoped queries.

## Security

- **Authentication**: MCP server validates internal service tokens
- **Authorization**: Tenant-scoped queries only
- **Audit**: All tool calls are logged
- **Rate Limiting**: Can be configured per tenant

## Testing MCP Server

### 1. Start MCP Server

```bash
docker-compose up -d posture-mcp-server
```

### 2. Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector docker run -i --rm sentinelgrid-posture-mcp:latest
```

### 3. Test Tool Call

Use the inspector to call:

```json
{
  "method": "tools/call",
  "params": {
    "name": "get_posture_summary",
    "arguments": {
      "tenant_id": "test-tenant"
    }
  }
}
```

## Integration with Main SentinelGrid

The MCP server can be registered with the main SentinelGrid MCP server to provide posture context to the main AI orchestrator.

**Add to main MCP config**:
```json
{
  "posture": {
    "server": "posture-mcp-server:8000",
    "tools": ["get_posture_summary", "analyze_observable", ...],
    "resources": ["posture://*"]
  }
}
```

## Future Enhancements

### LLM Integration
Once `posture-llm` service is built, add tools:
- `explain_finding` - LLM-powered explanation
- `suggest_remediation` - AI-generated remediation
- `analyze_risk_path` - Multi-hop risk analysis

### Graph Queries
Once GraphQL is implemented, add tools:
- `query_asset_graph` - Complex graph queries
- `find_risk_paths` - Attack path analysis

### Actions
Phase 4 features:
- `apply_remediation` - Execute fixes via SOAR
- `create_ticket` - Open tickets for findings
- `schedule_scan` - Schedule periodic scans

## Troubleshooting

### MCP Server Not Responding
- Check if posture-service and analyzer-orchestrator are running
- Verify network connectivity
- Check logs: `docker logs posture-mcp-server`

### Tool Calls Failing
- Verify tenant_id is valid
- Check backend service health
- Review MCP server logs

### Empty Results
- Ensure posture-service has data (run some analyses first)
- Check database contains findings
- Verify tenant_id matches

## Resources

- [MCP Specification](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- `SentinelGrid MCP Server` (historical reference unavailable)

---

**Status**: MCP server implemented and ready for AI integration

