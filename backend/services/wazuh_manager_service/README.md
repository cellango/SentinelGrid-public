# SentinelGrid Endpoint Manager Service

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../RELEASE_SCOPE.md) first.


**Service Name:** `wazuh_manager_service`  
**Port:** 8032  
**Purpose:** API layer for managing SentinelGrid Endpoint Protection agents

---

## Current source boundary

Only root metadata and a configured, authenticated stored inventory read at
`GET /api/v1/wazuh/agents` are admitted. The read requires owned user registration
and an exact `wazuh.read_owned_inventory` reader grant. Its stored status/version/
keepalive are not live Wazuh verification. Pagination defaults to100 and is bounded
to100 records per page; count describes that page. Arbitrary metadata and sensor
keys are excluded. Registration, live details, deletion, restart and health return
503 pending owned enrollment/provider/action contracts. Direct legacy helpers also
deny. No live manager, sensor, database/RLS or event pipeline has been qualified.

Read [the current identity boundary](../../../docs/architecture/gateway-identity.md#wazuh-stored-inventory-source-boundary)
for configuration, verification scope and restoration requirements. The reference
below describes retained legacy/proposed behavior; its commands and guarantees
are not an operational setup path for the current source boundary. Vendor Wazuh
Agent names and installed endpoint identities remain unchanged.

## Legacy capability reference

This service provides a REST API for managing endpoint security agents. It integrates with the SentinelGrid Endpoint Manager (Wazuh Manager 4.8.0) to handle:

- Agent registration with automatic tenant_id labeling
- Agent lifecycle management (list, get, delete, restart)
- Multi-tenant isolation via tenant_id labels
- Integration with IAM Agent for authentication

---

## Architecture

```
Frontend/API Gateway
    ↓ (JWT with tenant_id)
wazuh_manager_service
    ↓ (Wazuh REST API)
SentinelGrid Endpoint Manager (Wazuh Manager)
    ↓ (Events with tenant_id labels)
SentinelGrid SIEM (OpenSearch)
```

---

## API Endpoints

### Agent Management

**Register Agent**
```http
POST /api/v1/wazuh/agents/register
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "hostname": "web-server-01",
  "ip_address": "10.0.1.10",
  "os_platform": "linux",
  "os_version": "Ubuntu 22.04"
}

Response: {
  "success": true,
  "agent_id": "001",
  "agent_key": "${EXAMPLE_VALUE}",
  "manager_address": "manager.sentinelgrid.ai",
  "manager_port": 1514,
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "instructions": {
    "linux": "echo '<key>' | sudo /var/ossec/bin/manage_agents -i...",
    "windows": "...",
    "macos": "..."
  }
}
```

**List Agents**
```http
GET /api/v1/wazuh/agents
Authorization: Bearer <jwt_token>

Response: {
  "agents": [
    {
      "id": "uuid",
      "wazuh_agent_id": "001",
      "name": "web-server-01",
      "ip": "10.0.1.10",
      "os": "linux Ubuntu 22.04",
      "status": "active",
      "last_seen": "2025-12-03T10:30:00Z",
      "registered": "2025-12-01T09:15:00Z",
      "version": "4.8.0"
    }
  ],
  "count": 1
}
```

**Get Agent Details**
```http
GET /api/v1/wazuh/agents/{agent_id}
Authorization: Bearer <jwt_token>

Response: {
  "id": "uuid",
  "wazuh_agent_id": "001",
  "name": "web-server-01",
  "ip": "10.0.1.10",
  "os": {...},
  "version": "4.8.0",
  "status": "active",
  "last_keepalive": "2025-12-03T10:30:00Z",
  "labels": {
    "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
    "registered_via": "sentinelgrid_api",
    "platform": "linux"
  },
  "groups": []
}
```

**Delete Agent**
```http
DELETE /api/v1/wazuh/agents/{agent_id}
Authorization: Bearer <jwt_token>

Response: {
  "success": true,
  "agent_id": "001",
  "message": "Agent deleted successfully"
}
```

**Restart Agent**
```http
POST /api/v1/wazuh/agents/{agent_id}/restart
Authorization: Bearer <jwt_token>

Response: {
  "success": true,
  "agent_id": "001",
  "message": "Restart command sent to agent"
}
```

### Health Check

```http
GET /health

Response: {
  "service": "wazuh-manager-service",
  "version": "1.0.0",
  "status": "healthy",
  "checks": {
    "wazuh_manager": {
      "status": "connected",
      "url": "http://wazuh-manager:55000"
    }
  }
}
```

---

## Multi-Tenant Isolation

### How It Works

1. **JWT Token Contains tenant_id**
   - User authenticates → receives JWT with `tenant_id` claim
   - Every API request includes this JWT

2. **Service Extracts tenant_id**
   - Middleware validates JWT via IAM Agent
   - Extracts globally unique `tenant_id`

3. **Agent Registration Sets Label**
   - When agent registers, service calls Wazuh API
   - Sets `agent.labels.tenant_id` on the agent
   - **Labels stored server-side in Wazuh Manager**

4. **Events Include tenant_id**
   - Agent sends events to Wazuh Manager
   - Manager injects labels into events
   - Filebeat routes to tenant-specific index: `wazuh-alerts-{tenant_id}-YYYY.MM.DD`

5. **Queries Are Tenant-Isolated**
   - Service only queries indices matching tenant's ID
   - Cannot access other tenants' data

### Isolation requirements awaiting qualification

The following require evidence before deployment: authoritative sensor-to-tenant
ownership, tamper-resistant event routing, cross-tenant index access denials,
least-privilege database RLS, exact API/action authorization, and durable audit.
Stored manager labels, index names and source test doubles alone do not establish
these properties. Enrollment, lifecycle and provider operations remain unavailable.

---

## Configuration

### Environment Variables

```bash
# Database
DB_URL=postgresql://sg:sg@postgres:5432/sg

# Wazuh Manager
WAZUH_MANAGER_URL=http://wazuh-manager:55000
WAZUH_API_USERNAME=wazuh-api
WAZUH_API_PASSWORD=MyS3cr3tP455w0rd!

# IAM Agent (for token validation)
IAM_AGENT_URL=http://iam_agent:8000

# Keycloak (optional, for direct validation)
KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=sentinelgrid

# Security
INTERNAL_SERVICE_TOKEN=internal-service-token-change-in-production

# Logging
LOG_LEVEL=INFO
```

---

## Development

### Running Locally

```bash
cd backend/services/wazuh_manager_service

# Install dependencies
pip install -r requirements.txt

# Run service
uvicorn app.main:app --reload --port 8032
```

### Running in Docker

```bash
# Build and start all services
docker-compose up wazuh_manager_service

# View logs
docker-compose logs -f wazuh_manager_service

# Restart service
docker-compose restart wazuh_manager_service
```

---

## Testing

### Test Agent Registration

```bash
# Get JWT token (replace with real token)
export TOKEN="eyJhbGc..."

# Register an agent
curl -X POST http://localhost:8032/api/v1/wazuh/agents/register \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "test-server-01",
    "ip_address": "10.0.1.50",
    "os_platform": "linux",
    "os_version": "Ubuntu 22.04"
  }'

# List agents
curl -X GET http://localhost:8032/api/v1/wazuh/agents \
  -H "Authorization: Bearer $TOKEN"
```

### Verify Tenant Isolation

```bash
# Script: scripts/wazuh/test-tenant-isolation.sh
./scripts/wazuh/test-tenant-isolation.sh
```

---

## Dependencies

- **Wazuh Manager 4.8.0** - Must be running and accessible
- **PostgreSQL** - For agent metadata storage
- **IAM Agent** - For JWT token validation
- **OpenSearch** - For event storage (indirect dependency)

---

## Database Schema

### endpoint_agents

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| tenant_id | UUID | Globally unique tenant ID (references tenants.id) |
| wazuh_agent_id | VARCHAR(10) | Wazuh internal ID (e.g., "001") |
| agent_name | VARCHAR(255) | Agent hostname |
| ip_address | INET | Agent IP address |
| os_platform | VARCHAR(100) | Operating system type |
| os_version | VARCHAR(100) | OS version string |
| agent_version | VARCHAR(50) | Wazuh agent version |
| registration_date | TIMESTAMPTZ | When agent was registered |
| last_keepalive | TIMESTAMPTZ | Last time agent checked in |
| status | VARCHAR(20) | pending, active, disconnected, removed |
| metadata | JSONB | Custom metadata |

---

## Troubleshooting

### Agent Registration Fails

**Check:**
1. Wazuh Manager is running: `docker-compose ps wazuh-manager`
2. API credentials are correct
3. Database is accessible
4. IAM Agent can validate token

**Logs:**
```bash
docker-compose logs wazuh_manager_service
docker-compose logs wazuh-manager
```

### Agent Not Showing in List

**Check:**
1. Token contains correct tenant_id
2. Agent was registered with same tenant_id
3. Database query successful

### Events Not in OpenSearch

**Check:**
1. Agent is connected (status = "active")
2. Filebeat is running
3. Agent labels include tenant_id
4. Index pattern exists: `wazuh-alerts-{tenant_id}-*`

---

## Related Documentation

- [Implementation Plan](../../../docs/archive/README.md#retired-references)
- `Branding Guide` (historical reference unavailable)
- [Agent Download](../../../agents/wazuh/README.md)
- [Wazuh Official Docs](https://documentation.wazuh.com/)

---

**Created:** December 3, 2025  
**Last Updated:** December 3, 2025  
**Status:** Production Ready
