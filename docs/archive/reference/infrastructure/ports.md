# Port Assignments - SentinelGrid Platform

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This document tracks all port assignments for SentinelGrid services and infrastructure, including the **SentinelGridPostureAgent** (CSPM platform).

**Last Updated:** 2025-12-02  
**Version:** 2.0

---

## Overview

### Main SentinelGrid Platform
- **Port Range:** 8000-8099 (services), 3443 (frontend HTTPS), 3444 (website HTTPS dev), 5432 (database)
- **Services:** API Gateway, IAM, SIEM, SOAR, Model Gateway, etc.

### SentinelGridPostureAgent (NEW)
- **Port Range:** 8100-8103 (services), 5433 (database)
- **Services:** Analyzer Orchestrator, Posture Service, MCP Server
- **Architecture:** Observable-Analyzer pattern (Cortex-style)
- **Status:** ✅ Production Ready
- **Can Spin Off:** Yes - separate ports, database, services

---

## Service Ports

### API Gateway
- **Internal Port:** 8000
- **External Port:** 8082 (changed from 8080 due to Traefik conflict)
- **URL:** http://localhost:8082
- **Purpose:** Main REST API for frontend
- **Health Check:** http://localhost:8082/health

### IAM Agent
- **Internal Port:** 8000
- **External Port:** 8005
- **URL:** http://localhost:8005
- **Purpose:** Identity and Access Management service for Keycloak integration
- **Health Check:** http://localhost:8005/health
- **Internal API:** http://iam_agent:8000 (Docker network)

### IAM Governance And Entitlements
- **Runtime Owner:** IAM Agent
- **Internal API:** http://iam_agent:8000 (Docker network)
- **Purpose:** Fine-grained access control and governance APIs now live in the canonical IAM Agent.
- **Legacy Port:** 8007 is reserved for historical entitlement deployments and is not active in the current dev stack.

### Keycloak
- **Internal Port:** 8080
- **External Port:** 8081
- **URL:** http://localhost:8081
- **Admin Console:** http://localhost:8081/admin
- **Purpose:** Identity Provider (IdP) for authentication and authorization
- **Health Check:** http://localhost:8081/health

### EJBCA (PKI)
- **Internal Ports:** 8080 (HTTP redirect), 8443 (HTTPS admin/UI)
- **External Ports:** 9080 (HTTP), 9443 (HTTPS)
- **URLs:** http://localhost:9080 (redirects), https://localhost:9443/ejbca/adminweb/
- **Purpose:** Certificate Authority (when `CA_BACKEND_TYPE=ejbca`)
- **Notes:** Ports moved off 8080/8443 to avoid conflicts; `docker-compose.dev.yml` exposes 9080/9443. Image pinned to `linux/amd64` on arm hosts.

### Vault
- **Prod Vault (`vault`)**
  - **Host Port:** 8210 ➜ Container 8200
  - **Protocol:** HTTPS (TLS enabled in `infra/vault/config/vault.hcl`)
  - **Compose:** `docker-compose.vault.yml` (also defined in `docker-compose.dev.yml`)
  - **Entrypoint:** `infra/vault/scripts/vault-entrypoint.sh` (auto-init/unseal, persists data)
- **Legacy Dev Vault (`vault`)**
  - **Status:** Removed from `docker-compose.dev.yml` (was dev mode on host 8200 HTTP)
  - **Port History:** Host 8200 ➜ Container 8200 (host 8200 now available)
  - **Note:** Use `vault` for all environments; re-add dev Vault only if explicitly needed for testing

### Model Gateway
- **Internal Port:** 8000
- **External Port:** 8002
- **URL:** http://localhost:8002
- **Purpose:** AI/LLM model gateway service

### OPA (dev)
- **Internal Port:** 8181
- **External Port:** 8181
- **URL:** http://localhost:8181
- **Purpose:** Open Policy Agent server (dev sandbox)
- **Notes:** Pulls bundles from API Gateway bundle endpoint; not part of runtime app containers.

### SIEM Agent
- **Internal Port:** 8000
- **External Port:** 8003
- **URL:** http://localhost:8003
- **Purpose:** SIEM integration agent
- **Canonical path:** `backend/agents/siem_agent`

### SOAR Agent
- **Internal Port:** 8000
- **External Port:** 8004
- **URL:** http://localhost:8004
- **Purpose:** SOAR (Security Orchestration, Automation, and Response) agent
- **Canonical path:** `backend/agents/soar_agent`

### Agent Runtime
- **Internal Port:** 8000
- **External Port:** 8029
- **URL:** http://localhost:8029
- **Purpose:** Shared runtime for supervised SOC and Compliance agents
- **Canonical path:** `backend/services/agent_runtime`

### Tenant Service
- **Internal Port:** 8000
- **External Port:** 8008
- **URL:** http://localhost:8008
- **Purpose:** Tenant provisioning and management service

### Ingestion Service
- **Internal Port:** 8000
- **External Port:** 8009
- **URL:** http://localhost:8009
- **Purpose:** Event ingestion and normalization service

### Compliance Service
- **Internal Port:** 8000
- **External Port:** 8017
- **URL:** http://localhost:8017
- **Purpose:** Compliance findings/remediation service

### Connector Service
- **Internal Port:** 8000
- **External Port:** 8027  _(moved off 8005 to avoid IAM conflict)_
- **URL:** http://localhost:8027
- **Purpose:** Identity and Cloud connector service (Google Workspace, AWS, etc.)

### Detection Service
- **Internal Port:** 8000
- **External Port:** 8010
- **URL:** http://localhost:8010
- **Purpose:** Detection rules engine for security alerts

### Automated Response Service
- **Internal Port:** 8000
- **External Port:** 8013
- **URL:** http://localhost:8013
- **Purpose:** Automated playbook execution and response actions

### Action Service
- **Internal Port:** 8000
- **External Port:** 8028
- **URL:** http://localhost:8028
- **Purpose:** Approval-gated and manual action execution service

### Reporting Service
- **Internal Port:** 8000
- **External Port:** 8014
- **URL:** http://localhost:8014
- **Purpose:** Scheduled reports and exports
- **DB search_path:** reporting,public

### Audit Service
- **Internal Port:** 8000
- **External Port:** 8016
- **URL:** http://localhost:8016
- **Purpose:** Audit log queries/exports (platform_audit_logs)
- **DB search_path:** audit,public

### CMDB Service
- **Internal Port:** 8000
- **External Port:** 8026
- **URL:** http://localhost:8026
- **Purpose:** Asset and configuration inventory (CloudQuery integration ready)

### Website (Next.js marketing/app)
- **External Port (Dev):** 3444
- **Protocol:** HTTPS (self-signed in dev)
- **Purpose:** Primary marketing/product site (canonical source; replaces legacy marketing content)

### SentinelGridPostureAgent Services

#### Analyzer Orchestrator
- **Internal Port:** 8000
- **External Port:** 8103
- **URL:** http://localhost:8103
- **Purpose:** Observable-analyzer orchestration service (Cortex-style)
- **Health Check:** http://localhost:8103/health
- **Key APIs:**
  - POST /api/v1/analyze - Trigger security analysis
  - GET /api/v1/analyzers - List available analyzers
  - GET /api/v1/jobs/{id} - Check job status

#### Posture Service
- **Internal Port:** 8000
- **External Port:** 8100
- **URL:** http://localhost:8100
- **Purpose:** Core CSPM REST + GraphQL API
- **Health Check:** http://localhost:8100/health
- **Key APIs:**
  - GET /api/v1/posture/summary/{tenant_id} - Posture summary
  - GET /api/v1/findings/ - List findings
  - GET /api/v1/assets/ - List assets

#### Posture MCP Server
- **Internal Port:** 8000
- **External Port:** 8102
- **URL:** http://localhost:8102
- **Purpose:** Model Context Protocol server for AI agent integration
- **Protocol:** MCP (stdio-based)
- **Tools:** 8 MCP tools (get_posture_summary, list_findings, analyze_observable, etc.)

#### Posture PostgreSQL
- **Internal Port:** 5432
- **External Port:** 5433
- **Connection String:** `postgresql://posture_user:posture_pass@localhost:5433/posture_db`
- **Purpose:** Separate database for SentinelGridPostureAgent
- **Internal URL:** `postgresql://posture_user:posture_pass@posture-postgres:5432/posture_db` (Docker network)

### Orchestrator
- **Internal Port:** 8000
- **External Port:** Not exposed (internal only)
- **Internal URL:** http://orchestrator:8000 (Docker network)
- **Purpose:** Orchestration service for coordinating agents

### Frontend (Next.js)
- **Internal Port:** 3001 (Next.js), 3443 (nginx HTTPS)
- **External Port:** 3443 (HTTPS)
- **HTTPS URL:** https://localhost:3443 (main frontend with SSL)
- **Purpose:** Main web application frontend (HTTPS only)
- **API Base:** http://localhost:8082 (API Gateway)
- **Note:** nginx is bundled in the frontend container and handles:
  - Port 3443: HTTPS listener with SSL certificates that proxies to Next.js on internal port 3001

---

## SentinelGridPostureAgent Ports

**Location:** `SentinelGridPostureAgent/` directory (can be spun off independently)

**Port Range:** 8100-8103, 5433

### Analyzer Orchestrator
- **Internal Port:** 8000
- **External Port:** 8103
- **URL:** http://localhost:8103
- **Purpose:** Cortex-style analyzer orchestration service
- **Architecture:** Observable-Analyzer pattern
- **Health Check:** http://localhost:8103/health
- **Docs:** http://localhost:8103/docs
- **Key Features:**
  - Dynamic analyzer selection based on observable type
  - Parallel execution of security tools
  - Supports: Prowler, ZAP, Trivy, Checkov, Gitleaks

### Posture Service
- **Internal Port:** 8000
- **External Port:** 8100
- **URL:** http://localhost:8100
- **Purpose:** Core CSPM REST + GraphQL API service
- **Health Check:** http://localhost:8100/health
- **Docs:** http://localhost:8100/docs
- **Key Features:**
  - Posture score calculation
  - Finding management
  - Asset tracking
  - GraphQL for complex queries (planned)

### Posture MCP Server
- **Internal Port:** 8000 (stdio protocol)
- **External Port:** 8102
- **URL:** http://localhost:8102
- **Purpose:** Model Context Protocol server for AI agent integration
- **Protocol:** MCP
- **Tools Available:** 8 tools (get_posture_summary, list_findings, analyze_observable, etc.)
- **Use Case:** Integrate with Claude, GPT-4, or custom AI agents

### Posture PostgreSQL
- **Internal Port:** 5432
- **External Port:** 5433
- **Connection String:** `postgresql://posture_user:posture_pass@localhost:5433/posture_db`
- **Purpose:** Dedicated database for posture platform (isolated from main SentinelGrid DB)
- **Internal URL:** `postgresql://posture_user:posture_pass@posture-postgres:5432/posture_db` (Docker network)
- **Tables:** observables, assets, findings, analyzer_jobs, posture_scores, cloud_accounts, repositories
- **Note:** Separate database for clean isolation and future spin-off capability

---

## Infrastructure Ports

### HashiCorp Vault
- **Container Port:** 8200 (TLS)
- **External Port:** 8210
- **URL:** https://localhost:8210 (self-signed; use `-k`)
- **UI:** https://localhost:8210/ui
- **Purpose:** Secrets management for Keycloak passwords, database credentials, service tokens
- **Mode:** Production config (persistent file storage, TLS)
- **Location:** `docker-compose.vault.yml` (also defined in `docker-compose.dev.yml`)
- **Health Check:** `curl -k https://localhost:8210/v1/sys/health`
- **Note:** Legacy dev Vault on host 8200 has been removed from compose; host port 8200 is now free.

### PostgreSQL (Application Database)
- **Internal Port:** 5432
- **External Port:** 5432
- **Connection String:** `postgresql://sg:sg@localhost:5432/sg`
- **Purpose:** Primary database for SentinelGrid application data
- **Internal URL:** `postgresql://sg:sg@postgres:5432/sg` (Docker network)

### PostgreSQL (Keycloak Database)
- **Internal Port:** 5432
- **External Port:** Not exposed (internal only)
- **Connection String:** `postgresql://keycloak:keycloak@keycloak_db:${EXAMPLE_VALUE}` (Docker network)
- **Purpose:** Database for Keycloak instance

### PostgreSQL (SentinelGridIAM Database)
- **Internal Port:** 5432
- **External Port:** Not exposed (internal only)
- **Connection String:** `postgresql://sg:sg@postgres:5432/SentinelGridIAM` (Docker network)
- **Purpose:** Database for IAM-related features (entitlements, governance, audit)

### PostgreSQL (SentinelGridPostureAgent Database)
- **Internal Port:** 5432
- **External Port:** 5433
- **Connection String:** `postgresql://posture_user:posture_pass@localhost:5433/posture_db`
- **Purpose:** Separate database for SentinelGridPostureAgent (CSPM platform)
- **Internal URL:** `postgresql://posture_user:posture_pass@posture-postgres:5432/posture_db` (Docker network)
- **Note:** Isolated from main SentinelGrid database for future spin-off capability

### Redis
- **Internal Port:** 6379
- **External Port:** 6379
- **Connection String:** `redis://localhost:6379/0`
- **Purpose:** Caching (JWKS, session data), Job queues for analyzers
- **Internal URL:** `redis://redis:6379/0` (Docker network)

### Grafana (Observability)
- **Internal Port:** 3000
- **External Port:** 3000
- **URL:** https://localhost:3000
- **Protocol:** HTTPS (self-signed dev cert from `website/certificates/localhost.pem`)
- **Purpose:** Observability dashboards (Prometheus/Loki/Tempo)
- **Note:** Runs in `docker-compose.observability.yml` under project `sentinelgrid-observability`

---

## Frontend

### Next.js Frontend (HTTPS only)
- **HTTPS Port:** 3443 (nginx serves with SSL)
- **Internal Next.js Port:** 3001 (proxied by nginx)
- **HTTPS URL:** https://localhost:3443 (main frontend URL)
- **Purpose:** Main web application frontend (HTTPS only - direct access)
- **API Base:** http://localhost:8082 (API Gateway)
- **Configuration:** nginx bundled in frontend container (see `frontend/nginx.conf`)
- **Note:** Frontend runs only on 3443. Port 3000 is now used by Grafana (observability stack, HTTPS).

---

## Port Conflicts & Notes

### Known Conflicts

#### Port 8080
- **Used by:** Traefik (reverse proxy for other services)
- **Solution:** API Gateway moved to port 8082
- **Note:** Consider stopping Traefik or moving it if 8080 is needed for API Gateway

#### Port 8200 ✅ **RESOLVED** (Legacy dev Vault removed)
- **Previously used by:** **HashiCorp Vault** dev mode (`docker-compose.dev.yml`, service `vault`)
  - Purpose: Secrets management for Keycloak, database, service accounts
  - Previous URL: http://localhost:8200 (HTTP)
  - Previous UI: http://localhost:8200/ui
  - **Resolution:** Dev Vault removed; host 8200 now free. `vault` runs on host 8210 ➜ container 8200 (TLS).

#### Port 8201 ✅ **RESOLVED** (December 5, 2025)
- **Used by:** **Pentest Service** (SentinelGridPenTestAgent)
  - Location: `SentinelGridPenTestAgent/docker-compose.yml`
  - Service: `pentest-service`
  - Purpose: Penetration testing REST API
  - URL: http://localhost:8201
  - Docs: http://localhost:8201/docs
  - **Changed from:** 8200 (December 5, 2025)
  - **Reason:** Resolve conflict with HashiCorp Vault
  - **Note:** Internal Docker network port remains 8200 (pentest-service:8200)

### Reserved Ports
- **Port 8000:** Used internally by multiple services (FastAPI default)
  - Services use external ports to avoid conflicts
- **Port 8080:** Traefik (not part of SentinelGrid core services)

### Available Ports
- **Port 3000:** ✅ **AVAILABLE** (December 5, 2025)
  - Previously used by Frontend HTTP redirect (removed)
  - Frontend now accessed directly on HTTPS port 3443
  - Available for other services

---

## Port Assignment Strategy

1. **External Ports:** Start from 8000+ for services
   - 8001: LLM Server
   - 8002: Model Gateway
   - 8003: SIEM Agent
   - 8004: SOAR Agent
   - 8005: IAM Agent
   - 8007: Entitlement Agent
   - 8008: Tenant Service
   - 8009: Ingestion Service
   - 8010: Detection Service
   - 8011: Ticketing Service
   - 8012: Orchestrator
   - 8013: Automated Response Service
   - 8014: Reporting Service
   - 8015: Certificate Service
   - 8016: Audit Service
   - 8017: Compliance Service
   - 8018: Framework Service
   - 8019: Incident Service
   - 8020: Email Ingestion Service
   - 8021: Observables Service
   - 8022: MCP Server
   - 8023: SentinelGrid AI Shield Gateway
   - 8024: SentinelGrid AI Shield Services
   - 8025: Scanner Orchestrator
   - 8026: CMDB Service
   - 8027: Connector Service
   - 8028: Action Service
   - 8030: Vulnerability Service
   - 8082: API Gateway
   - **8100: Posture Service (SentinelGridPostureAgent)**
   - **8102: Posture MCP Server (SentinelGridPostureAgent)**
   - **8103: Analyzer Orchestrator (SentinelGridPostureAgent)**

2. **Infrastructure Ports:** Standard ports
   - 5432: PostgreSQL (Main)
   - **5433: PostgreSQL (Posture)** - Separate database
   - 6379: Redis
   - 8081: Keycloak
   - **8210: HashiCorp Vault (prod)**
   - **8201: Pentest Service** (SentinelGridPenTestAgent)

3. **Internal Ports:** All services use 8000 internally (Docker network communication)

4. **SentinelGridPostureAgent Ports:** 8100-8103 range
   - Grouped together for easy identification
   - Can be spun off independently

---

## Docker Network Communication

All services communicate via Docker internal network:
- Service name is the hostname (e.g., `api_gateway`, `iam_agent`, `keycloak`)
- Internal ports are used for inter-service communication
- Example: `http://iam_agent:8000/internal/iam/auth/validate-token`

---

## Environment Variables

Services use these environment variables for service discovery:

```bash
IAM_AGENT_URL=http://iam_agent:8000
ORCHESTRATOR_URL=http://orchestrator:8000
KEYCLOAK_URL=http://keycloak:8080
DB_URL=postgresql://sg:sg@postgres:5432/sg
REDIS_URL=redis://redis:6379/0
```

---

## Quick Reference

| Service | External Port | Internal Port | URL |
|---------|--------------|---------------|-----|
| API Gateway | 8082 | 8000 | http://localhost:8082 |
| IAM Agent | 8005 | 8000 | http://localhost:8005 |
| Connector Service | 8027 | 8000 | http://localhost:8027 |
| Entitlement Agent | 8007 | 8000 | http://localhost:8007 |
| Keycloak | 8081 | 8080 | http://localhost:8081 |
| Model Gateway | 8002 | 8000 | http://localhost:8002 |
| SIEM Agent | 8003 | 8000 | http://localhost:8003 |
| SOAR Agent | 8004 | 8000 | http://localhost:8004 |
| **Analyzer Orchestrator** | **8103** | **8000** | **http://localhost:8103** |
| **Posture Service** | **8100** | **8000** | **http://localhost:8100** |
| **Posture MCP Server** | **8102** | **8000** | **http://localhost:8102** |
| Frontend (HTTPS) | 3443 | - | https://localhost:3443 (main URL) |
| PostgreSQL (Main) | 5432 | 5432 | localhost:5432 |
| **PostgreSQL (Posture)** | **5433** | **5432** | **localhost:5433** |
| Redis | 6379 | 6379 | localhost:6379 |
| **HashiCorp Vault (prod)** | **8210** | **8200** | **https://localhost:8210** |
| **Pentest Service** | **8201** | **8200** | **http://localhost:8201** |

---

## Testing URLs

### Main SentinelGrid Services
- **API Gateway Health:** http://localhost:8082/health
- **IAM Agent Health:** http://localhost:8005/health
- **Entitlement Agent Health:** http://localhost:8007/health
- **Keycloak Admin:** http://localhost:8081/admin
- **Keycloak Health:** http://localhost:8081/health
- **Vault UI:** https://localhost:8210/ui
- **Vault Health:** `curl -k https://localhost:8210/v1/sys/health`
- **Frontend (HTTPS):** https://localhost:3443 (main URL)

### SentinelGridPostureAgent Services
- **Analyzer Orchestrator Health:** http://localhost:8103/health
- **Analyzer Orchestrator API Docs:** http://localhost:8103/docs
- **Analyzer Orchestrator - List Analyzers:** http://localhost:8103/api/v1/analyzers
- **Posture Service Health:** http://localhost:8100/health
- **Posture Service API Docs:** http://localhost:8100/docs
- **Posture Database:** `psql postgresql://posture_user:posture_pass@localhost:5433/posture_db`

### SentinelGridPenTestAgent Services
- **Pentest Service API:** http://localhost:8201
- **Pentest Service Docs:** http://localhost:8201/docs
- **Pentest Service Health:** http://localhost:8201/health

---

## SentinelGridPostureAgent Port Allocation

The SentinelGridPostureAgent uses a dedicated port range to facilitate:
- Independent operation
- Easy identification
- Future spin-off capability
- Clean separation from main SentinelGrid

### Port Range: 8100-8103 + 5433

| Port | Service | Purpose |
|------|---------|---------|
| **8100** | Posture Service | Core REST + GraphQL API |
| **8102** | MCP Server | AI agent integration |
| **8103** | Analyzer Orchestrator | Security tool orchestration |
| **5433** | PostgreSQL | Separate database |

### Why Separate Ports?

1. **Isolation**: Can run alongside main SentinelGrid without conflicts
2. **Spin-off Ready**: All services use dedicated ports
3. **Clear Boundaries**: Easy to identify posture-related services
4. **Development**: Can develop/test independently

---

## Complete Port Map (All Services)

### Application Services (8000-8099)
- 8001: LLM Server
- 8002: Model Gateway
- 8003: SIEM Agent
- 8004: SOAR Agent
- 8005: IAM Agent
- 8007: Entitlement Agent
- 8008: Tenant Service
- 8009: Ingestion Service
- 8010: Detection Service
- 8011: Ticketing Service
- 8012: Orchestrator
- 8013: Automated Response Service
- 8014: Reporting Service
- 8015: Certificate Service
- 8016: Audit Service
- 8017: Compliance Service
- 8018: Framework Service
- 8019: Incident Service
- 8020: Email Ingestion Service
- 8021: Observables Service
- 8022: MCP Server
- 8023: SentinelGrid AI Shield Gateway (proxy on 8080 internally)
- 8024: SentinelGrid AI Shield Services
- 8025: Scanner Orchestrator
- 8026: CMDB Service
- 8027: Connector Service
- 8028: Action Service
- 8030: Vulnerability Service
- 8082: API Gateway

### SentinelGridPostureAgent (8100-8103)
- 8100: Posture Service (REST + GraphQL)
- 8102: MCP Server (AI integration)
- 8103: Analyzer Orchestrator (Cortex-style)

### Infrastructure
- 3443: Frontend HTTPS (nginx with SSL - main URL)
- 3000: ✅ **AVAILABLE** (previously Frontend HTTP redirect - removed)
- 5432: PostgreSQL (Main - sg database)
- 5433: PostgreSQL (Posture - posture_db)
- 6379: Redis
- 8081: Keycloak
- **8210: HashiCorp Vault (prod, TLS)**
- **8201: Pentest Service** (SentinelGridPenTestAgent)
- 8200: Available (legacy dev Vault removed)

### Internal Only (Not Exposed)
- orchestrator:8000 - Main orchestrator service
- keycloak_db:5432 - Keycloak database
- posture-postgres:5432 - Posture database (internal)

---

## Observable-Analyzer Flow (Ports Perspective)

```
User Request
    ↓
:8082 (API Gateway)
    ↓
:8103 (Analyzer Orchestrator)
    ↓
Multiple Analyzers (internal)
    ├─ Prowler
    ├─ ZAP  
    ├─ Trivy
    ├─ Checkov
    └─ Gitleaks
    ↓
:8100 (Posture Service)
    ↓
:5433 (Posture Database)
```

---

## MCP Integration Flow

```
AI Agent (Claude/GPT)
    ↓
:8102 (MCP Server)
    ↓
    ├─→ :8100 (Posture Service) for queries
    └─→ :8103 (Analyzer Orchestrator) for analysis
```

---

## Environment-Specific Port Conventions

### Development (Current)
- Ports as documented above
- All services exposed for debugging

### Production (Recommended)
- External ports behind reverse proxy/load balancer
- Internal services not exposed to internet
- Use environment-specific prefixes:
  - Dev: 8000-8999
  - Staging: 9000-9999
  - Prod: 10000-10999

---

## Future Considerations

- Consider using Traefik or another reverse proxy for unified routing
- May need to expose Orchestrator externally for debugging
- Consider port ranges for multiple environments (dev, staging, prod)
- SentinelGridPostureAgent may expand to 8104-8110 range for additional services:
  - 8104: Posture LLM Service (planned)
  - 8105-8110: Reserved for future analyzers/workers

---

## Port Conflict Resolution

### If Port 8103 is Taken
Update in multiple files:
1. `SentinelGridPostureAgent/docker-compose.yml`
2. `docker-compose.dev.yml`
3. `backend/services/api_gateway/app/api/routes_posture.py`
4. Update `ANALYZER_ORCHESTRATOR_URL` environment variable

### If Port 5433 is Taken
Update database connection strings:
1. `SentinelGridPostureAgent/docker-compose.yml`
2. `SentinelGridPostureAgent/database/alembic.ini`
3. Database connection in services

---

## Quick Reference Commands

```bash
# Check which ports are in use
lsof -i :8100
lsof -i :8103
lsof -i :5433

# Test service availability
curl http://localhost:8103/health  # Analyzer Orchestrator
curl http://localhost:8100/health  # Posture Service
curl http://localhost:8082/health  # API Gateway

# Connect to databases
psql postgresql://sg:sg@localhost:5432/sg                           # Main DB
psql postgresql://posture_user:posture_pass@localhost:5433/posture_db  # Posture DB

# View all SentinelGrid ports
docker-compose ps
cd SentinelGridPostureAgent && docker-compose ps
```

---

**Last Updated:** 2025-12-05  
**Maintained By:** SentinelGrid Team  
**Version:** 2.3 (removed HTTP redirect - frontend now HTTPS only on port 3443, port 3000 available)
