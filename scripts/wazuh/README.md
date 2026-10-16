# SentinelGrid Endpoint Manager Scripts

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


Scripts for managing and testing the SentinelGrid Endpoint Manager (Wazuh Manager integration).

---

## Scripts Overview

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `create-opensearch-templates.sh` | Create OpenSearch index templates | First-time setup |
| `test-agent-registration.sh` | Test agent registration API flow | After setup, before deploying agents |
| `verify-tenant-isolation.sh` | Verify multi-tenant isolation | After registering multiple tenants' agents |

---

## Script Details

### 1. create-opensearch-templates.sh

**Purpose:** Creates index templates in OpenSearch for Wazuh alert data

**Usage:**
```bash
# Default (uses localhost:9200)
./create-opensearch-templates.sh

# Custom OpenSearch URL
OPENSEARCH_URL=http://opensearch:9200 ./create-opensearch-templates.sh
```

**What It Does:**
1. Checks OpenSearch connectivity
2. Creates `wazuh-alerts-template` index template
3. Configures mappings for Wazuh fields
4. Sets up tenant_id as keyword field

**When to Run:**
- ✅ Once during initial setup
- ✅ After changing index template JSON
- ✅ After OpenSearch version upgrade

**Expected Output:**
```
==========================================
Creating OpenSearch Index Templates
==========================================
OpenSearch URL: http://localhost:9200

✅ OpenSearch is available

Creating wazuh-alerts index template...
HTTP Status: 200

==========================================
✅ Index template created successfully!
==========================================
```

---

### 2. test-agent-registration.sh

**Purpose:** End-to-end test of agent registration flow

**Usage:**
```bash
# Interactive mode (prompts for JWT token)
./test-agent-registration.sh

# With token environment variable
export TENANT_TOKEN="eyJhbGc..."
./test-agent-registration.sh

# Custom API URL
API_BASE=http://localhost:8032 ./test-agent-registration.sh
```

**What It Tests:**
1. ✅ Service health check
2. ✅ Agent registration via API
3. ✅ tenant_id label verification in Wazuh Manager
4. ✅ Agent appears in tenant's agent list
5. ✅ Agent details retrieval
6. ✅ Returns installation instructions

**Prerequisites:**
- wazuh_manager_service running
- Wazuh Manager running
- Valid JWT token with tenant_id claim

**Expected Output:**
```
==========================================
SentinelGrid Endpoint Manager
Agent Registration Test
==========================================

Step 1: JWT Token
-------------------
Enter JWT token: eyJhbGc...
✅ Token provided

Step 2: Service Health Check
-------------------
{
  "service": "wazuh-manager-service",
  "status": "healthy",
  ...
}
✅ Service is healthy

Step 3: Register Agent
-------------------
{
  "success": true,
  "agent_id": "001",
  "agent_key": "${EXAMPLE_VALUE}",
  ...
}
✅ Agent registered successfully
   Agent ID: 001
   Tenant ID: 123e4567-e89b-12d3-a456-426614174000

Step 4: Verify Agent Labels in Wazuh Manager
-------------------
{
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "registered_via": "sentinelgrid_api",
  ...
}
✅ tenant_id label verified in Wazuh Manager

... (more steps)

==========================================
✅ All Tests Passed!
==========================================
```

---

### 3. verify-tenant-isolation.sh

**Purpose:** Verify multi-tenant isolation is working correctly

**Usage:**
```bash
# Default (uses localhost)
./verify-tenant-isolation.sh

# Custom URLs
OPENSEARCH_URL=http://opensearch:9200 \
WAZUH_API=http://wazuh-manager:55000 \
./verify-tenant-isolation.sh
```

**What It Verifies:**
1. ✅ All agents have tenant_id labels
2. ✅ Each tenant has unique tenant_id
3. ✅ OpenSearch indices are tenant-specific
4. ✅ Events in indices have matching tenant_id
5. ✅ Cross-tenant queries return zero results

**Prerequisites:**
- Wazuh Manager running
- At least one agent registered
- Ideally 2+ tenants for full isolation test

**Expected Output:**
```
==========================================
Tenant Isolation Verification
==========================================

Step 1: Authenticating with Wazuh Manager...
✅ Authenticated with Wazuh Manager

Step 2: Listing All Agents and Labels...
{
  "id": "001",
  "name": "web-server-01",
  "labels": {
    "tenant_id": "123e4567-e89b-12d3-a456-426614174000"
  }
}

Step 3: Unique tenant_ids Found...
123e4567-e89b-12d3-a456-426614174000
abcdef12-3456-7890-abcd-ef1234567890
Found 2 unique tenant(s)

Step 4: Checking OpenSearch Indices...
wazuh-alerts-123e4567-e89b-12d3-a456-426614174000-2025.12.03  25
wazuh-alerts-abcdef12-3456-7890-abcd-ef1234567890-2025.12.03  10

Step 5: Verifying Tenant-Specific Indices...
...

Step 6: Testing Cross-Tenant Access Prevention...
Tenant 1: 123e4567-e89b-12d3-a456-426614174000
Tenant 2: abcdef12-3456-7890-abcd-ef1234567890

Tenant 1 has 25 alerts
Tenant 2 has 10 alerts
✅ Tenant isolation verified - no cross-tenant data leak

==========================================
✅ Isolation Verification Complete
==========================================
```

---

## Common Workflows

### Initial Setup

```bash
# 1. Start services
docker-compose up -d wazuh-manager wazuh_manager_service

# 2. Apply database migration
docker-compose exec -T postgres psql -U sg -d sg < backend/migrations/036_endpoint_agents.sql

# 3. Create OpenSearch templates
./create-opensearch-templates.sh

# 4. Test registration (need JWT token)
export TENANT_TOKEN="..."
./test-agent-registration.sh
```

### After Registering Agents

```bash
# Verify isolation
./verify-tenant-isolation.sh

# Check OpenSearch indices
curl http://localhost:9200/_cat/indices/wazuh-alerts-*
```

### Debugging Agent Issues

```bash
# Check Wazuh Manager logs
docker-compose logs wazuh-manager | grep "agent"

# Check specific agent
TOKEN=$(curl -s -u wazuh-api:MyS3cr3tP455w0rd! \
  -X POST http://localhost:55000/security/user/authenticate | jq -r '.data.token')

curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:55000/agents/001 | jq '.'
```

---

## Environment Variables

All scripts support these environment variables:

```bash
# OpenSearch
export OPENSEARCH_URL=http://localhost:9200

# Wazuh Manager API
export WAZUH_API=http://localhost:55000

# Agent Management API
export API_BASE=http://localhost:8032

# IAM Agent (for tokens)
export IAM_BASE=http://localhost:8000
```

---

## Next Scripts to Create

### Planned (Future)

- `bulk-register-agents.sh` - Register multiple agents from CSV
- `agent-health-report.sh` - Generate health report for all agents
- `rotate-wazuh-api-password.sh` - Rotate API credentials
- `backup-wazuh-config.sh` - Backup agent configs and labels
- `upgrade-agents.sh` - Bulk agent upgrade

---

## Tips

### Getting a JWT Token

```bash
# Using IAM Agent
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@test.com",
    "password": "password"
  }' | jq -r '.access_token'
```

### Monitoring OpenSearch Indices

```bash
# Watch indices being created
watch -n 5 'curl -s http://localhost:9200/_cat/indices/wazuh-alerts-* | sort'

# Count documents per index
for index in $(curl -s http://localhost:9200/_cat/indices/wazuh-alerts-*?h=index); do
  count=$(curl -s http://localhost:9200/${index}/_count | jq '.count')
  echo "${index}: ${count}"
done
```

---

## Troubleshooting

### Script Permission Denied

```bash
# Make scripts executable
chmod +x scripts/wazuh/*.sh

# Or run with bash
bash scripts/wazuh/create-opensearch-templates.sh
```

### Connection Refused

**Check services are running:**
```bash
docker-compose ps

# Start services if needed
docker-compose up -d wazuh-manager opensearch wazuh_manager_service
```

### Wazuh API Authentication Fails

**Check credentials:**
```bash
# Default credentials
Username: wazuh-api
Password: MyS3cr3tP455w0rd!

# Change in docker-compose.yml if needed
```

---

**All scripts are ready to use!** 🚀

Start with [`ENDPOINT_MANAGER_QUICKSTART.md`](../../docs/archive/reference/platform/endpoint-manager-quickstart.md) for step-by-step setup.
