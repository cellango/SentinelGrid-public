# SentinelGrid MCP Server

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../RELEASE_SCOPE.md) first.


AI-first security operations via Model Context Protocol (MCP).

## Overview

The SentinelGrid MCP Server exposes security operations tools to AI agents (Claude, custom LLMs) through the standardized MCP protocol. This enables natural language security operations - talk to your SOC like talking to a colleague.

## Architecture

```
AI Agent (Claude/Custom) → MCP Protocol → MCP Server → SentinelGrid Microservices
```

## Available Tools

### SIEM Tools
- `search_logs` - Query OpenSearch for security logs
- `get_detections` - Fetch detection events/alerts  
- `get_incidents` - List security incidents
- `create_incident` - Create new incident

### SOAR Tools
- `list_playbooks` - List available response playbooks
- `get_playbook` - Get playbook details
- `run_playbook` - Execute automated response playbook
- `get_playbook_execution` - Check playbook execution status

### IAM Tools
- `get_user` - Fetch user details
- `lock_account` - Lock user account (HIGH RISK - requires approval)

### Observable Tools
- `get_observable` - Get enriched observable (IP, domain, hash, etc.)
- `search_observables` - Search observables by type/value

## Usage with Claude Desktop

1. Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sentinelgrid": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "-e",
        "MCP_TENANT_ID=your-tenant-id",
        "-e",
        "MCP_USER_ID=your-user-id",
        "sentinelgrid-mcp_server-1",
        "python",
        "-m",
        "app.main"
      ]
    }
  }
}
```

2. Restart Claude Desktop

3. Start talking to your SOC:
   - "Search logs for failed SSH attempts in the last hour"
   - "Show me all critical incidents"
   - "Run the phishing containment playbook for incident INC-123"
   - "Lock the account user@example.com due to suspicious activity"

## Example Workflows

### Incident Investigation
```
User: "Investigate the brute force alert for 192.168.1.100"

AI uses MCP to:
1. search_logs(query="src_ip:192.168.1.100", time_range="1h")
2. get_observable(value="192.168.1.100", type="ip")  
3. create_incident(title="Brute Force from 192.168.1.100", ...)
4. run_playbook(playbook_id="bruteforce-response", ...)
```

### Account Compromise Response
```
User: "User john@company.com clicked a phishing link, contain the threat"

AI uses MCP to:
1. get_user(user_id="john@company.com")
2. lock_account(user_id="john@company.com", reason="Phishing incident")
3. run_playbook(playbook_id="phishing-containment", params={...})
4. create_incident(...)
```

## Security Features

- **Authorization**: Every tool call checked against RBAC
- **Audit Logging**: All MCP calls logged to SIEM
- **Tenant Isolation**: Multi-tenant by design
- **High-Risk Controls**: Dangerous actions require approval
- **Prompt Injection Protection**: Tool outputs sanitized

## Development

```bash
# Build
docker-compose -f docker-compose.dev.yml build mcp_server

# Run
docker-compose -f docker-compose.dev.yml up mcp_server

# Test
docker exec -it sentinelgrid-mcp_server-1 python -m app.main
```

## Adding New Tools

1. Create tool function in `app/tools/`
2. Add authorization check via `security_manager`
3. Add audit logging
4. Register in `app/servers/core_server.py`
5. Update this README

## License

Part of SentinelGrid - AI-driven Security-as-a-Service platform.

