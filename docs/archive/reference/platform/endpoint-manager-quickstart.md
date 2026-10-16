# SentinelGrid Endpoint Manager - Quick Start Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Ready to use in 5 minutes!**

---

## Prerequisites

- ✅ Docker and Docker Compose installed
- ✅ Ports available: 1514, 1515, 55000, 8032
- ✅ ~2GB RAM available for Wazuh Manager

---

## Quick Start (5 Steps)

### Step 1: Start the Services (2 minutes)

```bash
cd /path/to/SentinelGrid

# Start Wazuh Manager and dependencies
docker-compose up -d postgres opensearch wazuh-manager

# Wait for services to be healthy (~30 seconds)
docker-compose ps

# Start the API service
docker-compose up -d wazuh_manager_service iam_agent

# Check all services are running
docker-compose ps | grep -E "wazuh|opensearch|postgres"
```

**Expected Output:**
```
wazuh-manager            running    1514/tcp, 1515/tcp, 55000/tcp
wazuh_manager_service    running    8032/tcp
opensearch               running    9200/tcp
postgres                 running    5432/tcp
```

### Step 2: Run Database Migration (30 seconds)

```bash
# Copy migration to postgres container
docker-compose exec -T postgres psql -U sg -d sg < backend/migrations/036_endpoint_agents.sql

# Verify tables were created
docker-compose exec postgres psql -U sg -d sg -c "\dt endpoint_*"
```

**Expected Output:**
```
              List of relations
 Schema |         Name          | Type  | Owner
--------+-----------------------+-------+-------
 public | endpoint_agent_events | table | sg
 public | endpoint_agents       | table | sg
```

### Step 3: Create OpenSearch Index Templates (30 seconds)

```bash
# Create index template
./scripts/wazuh/create-opensearch-templates.sh

# Verify template exists
curl -s http://localhost:9200/_index_template/wazuh-alerts-template | \
  jq '.index_templates[0].name'
```

**Expected Output:**
```
"wazuh-alerts-template"
```

### Step 4: Verify Service Health (30 seconds)

```bash
# Check wazuh_manager_service
curl -s http://localhost:8032/health | jq '.'

# Should show:
# {
#   "service": "wazuh-manager-service",
#   "status": "healthy",
#   "checks": {
#     "wazuh_manager": {
#       "status": "connected"
#     }
#   }
# }

# Check Wazuh Manager directly
curl -s -u wazuh-api:MyS3cr3tP455w0rd! \
  http://localhost:55000/ | jq '.data'
```

### Step 5: Test Agent Registration (1 minute)

```bash
# You need a JWT token with tenant_id claim
# For quick testing, you can create a test tenant first:

# 1. Create test tenant in database
docker-compose exec postgres psql -U sg -d sg -c "
  INSERT INTO tenants (id, name, slug, status) 
  VALUES (
    '12345678-1234-1234-1234-123456789012',
    'Test Tenant',
    'test-tenant',
    'active'
  ) ON CONFLICT DO NOTHING;
"

# 2. Now run the test script
export TENANT_TOKEN="<your-jwt-token>"
./scripts/wazuh/test-agent-registration.sh
```

---

## Verification Checklist

After quick start, verify:

- [ ] Docker services running
  ```bash
  docker-compose ps wazuh-manager wazuh_manager_service
  ```

- [ ] Database tables exist
  ```bash
  docker-compose exec postgres psql -U sg -d sg -c "\d endpoint_agents"
  ```

- [ ] OpenSearch template created
  ```bash
  curl -s http://localhost:9200/_index_template/wazuh-alerts-template | jq '.index_templates[0].name'
  ```

- [ ] Health check passes
  ```bash
  curl http://localhost:8032/health | jq '.status'
  # Should return: "healthy"
  ```

- [ ] Wazuh Manager API accessible
  ```bash
  curl -u wazuh-api:MyS3cr3tP455w0rd! http://localhost:55000/ | jq '.data.title'
  # Should return: "Wazuh API REST"
  ```

---

## Troubleshooting

### Wazuh Manager Won't Start

```bash
# Check logs
docker-compose logs wazuh-manager

# Common issues:
# 1. Port 1514 already in use
# 2. Insufficient memory
# 3. OpenSearch not healthy

# Solution: Check ports and memory
docker-compose down
docker system prune -f
docker-compose up -d
```

### wazuh_manager_service Can't Connect to Wazuh Manager

```bash
# Check if Wazuh Manager is accessible
docker-compose exec wazuh_manager_service curl -v http://wazuh-manager:55000/

# Check environment variables
docker-compose exec wazuh_manager_service env | grep WAZUH

# Restart service
docker-compose restart wazuh_manager_service
```

### Database Migration Fails

```bash
# Check if postgres is running
docker-compose ps postgres

# Check if tables already exist
docker-compose exec postgres psql -U sg -d sg -c "\dt endpoint_*"

# If tables exist, migration already ran - this is OK
```

---

## Next Steps

### A. Install an Agent (Real Test)

Download agent packages from `agents/wazuh/` and install on a test machine.

### B. Build Frontend UI

Create dashboard pages:
- `frontend/src/app/dashboard/endpoints/page.tsx` - List agents
- `frontend/src/app/dashboard/endpoints/install/page.tsx` - Installation wizard

### C. Production Deployment

Follow production checklist in [ENDPOINT_MANAGER_IMPLEMENTATION_COMPLETE.md](../../README.md#retired-references)

---

## Quick Reference

### Ports

| Port | Service | Purpose |
|------|---------|---------|
| 1514 | Wazuh Manager | Agent communication |
| 1515 | Wazuh Manager | Agent enrollment |
| 55000 | Wazuh Manager | API |
| 8032 | wazuh_manager_service | REST API |
| 9200 | OpenSearch | SIEM storage |

### URLs

| Component | URL |
|-----------|-----|
| Wazuh Manager API | http://localhost:55000 |
| Agent Management API | http://localhost:8032 |
| API Docs | http://localhost:8032/docs |
| OpenSearch | http://localhost:9200 |
| OpenSearch Dashboards | http://localhost:5601 |

### Environment Variables

```bash
# Wazuh Manager
WAZUH_MANAGER_URL=http://wazuh-manager:55000
WAZUH_API_USERNAME=wazuh-api
WAZUH_API_PASSWORD=MyS3cr3tP455w0rd!

# Database
DB_URL=postgresql://sg:sg@postgres:5432/sg

# OpenSearch  
OPENSEARCH_URL=http://opensearch:9200
```

---

## Support

- 📖 Documentation: See `ENDPOINT_MANAGER_IMPLEMENTATION_COMPLETE.md`
- 🐛 Issues: Check service logs with `docker-compose logs <service>`
- 💬 Questions: Review README files in `backend/services/wazuh_manager_service/` and `infra/wazuh/`

---

**Ready to Test!** 🚀

Start with Step 1 above and you'll have a working SentinelGrid Endpoint Manager in ~5 minutes!
