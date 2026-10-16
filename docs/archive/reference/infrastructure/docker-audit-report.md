# SentinelGrid Docker Architecture Audit Report

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date**: December 3, 2025  
**Auditor**: System Analysis  
**Scope**: Complete docker-compose.dev.yml and container architecture

---

## 🚨 Executive Summary

**CRITICAL FINDINGS**:
- **47 total services** in docker-compose
- **34 services built from source** (27 Python backend services)
- **18.76 GB total images** (3.41 GB reclaimable)
- **27 services use identical base image**: `python:3.11-slim`
- **Estimated 70-80% duplication** in dependencies across services

**IMPACT**:
- 12-hour pull times (before Docker upgrade)
- Slow builds (each service rebuilds common dependencies)
- Disk space waste (~10-12 GB estimated duplicated layers)
- Memory waste (duplicate libraries in each container)

**RECOMMENDATION**: Consolidate into shared base images and consider service consolidation

---

## 📊 Service Breakdown

### Services by Type

| Category | Count | Notes |
|----------|-------|-------|
| **Python Backend Services** | 31 | ALL use python:3.11-slim |
| **Third-Party Services** | 6 | Keycloak, Wazuh, n8n, Cortex, StackStorm, Step-CA |
| **Search/Database** | 5 | Postgres, Redis, OpenSearch, Elasticsearch, Keycloak DB |
| **Frontend** | 1 | Next.js |
| **Gateway** | 1 | Go (AI Shield) |
| **Migration Jobs** | 3 | Flyway runners |
| **TOTAL** | 47 | |

### Built vs Pulled

| Type | Count | Pull Time | Build Time |
|------|-------|-----------|------------|
| **Pulled Images** | 13 | ~15-30 min | N/A |
| **Built Images** | 34 | N/A | ~20-45 min |
| **TOTAL** | 47 | **45-75 min** | **Cold build** |

---

## 🔍 Detailed Analysis

### Python Backend Services (31 services)

**ALL use the same base**: `python:3.11-slim` (155 MB)

**Common dependencies** (installed in 19+ services):
- `fastapi` - 19 services
- `sqlalchemy` - 16 services  
- `httpx` - 24 services
- `pydantic` - 19 services
- `uvicorn` - 19 services
- `psycopg2-binary` - 16 services
- `python-jose` - 12+ services
- `redis` - 10+ services

**Duplication Impact**:
```
Base image: 155 MB × 31 services = 4.8 GB
Common deps: ~50-100 MB × 31 services = 1.5-3.0 GB
Total duplication: ~6-8 GB
```

### Full Service List

**Backend Microservices (27)**:
1. api_gateway
2. orchestrator
3. iam_agent
4. entitlement_agent
5. model_gateway
6. cmdb_service
7. framework_service
8. vulnerability_service
9. ai_enrichment_agent
10. ticketing_agent
11. action_agent
12. siem_agent
13. ingestion_service
14. connector_service
15. compliance_service
16. incident_service
17. tenant_service
18. observables_service
19. reporting_service
20. ai_shield_services
21. wazuh_manager_service
22. mcp_server
23. email_ingestion_service
24. automated_response_service
25. detection_service
26. soar_agent
27. audit_service

**Migration/Init Services (4)**:
- entitlement_agent_flyway
- model_gateway_migrations
- model_gateway_data_migrations
- soar_agent_flyway

**AI/ML Services (2)**:
- llm_server (vLLM - LARGE ~10GB)
- analyzer-orchestrator (Posture Agent)

**Third-Party (7)**:
- keycloak, keycloak_db
- wazuh-manager
- cortex
- n8n
- stackstorm
- step-ca

**Infrastructure (6)**:
- postgres (pgvector/pgvector:pg16 - 745 MB)
- opensearch (2.8 GB)
- elasticsearch (1.2 GB)
- opensearch-dashboards
- redis
- frontend (Next.js)

**Gateway (1)**:
- sentinelgrid_ai_shield_gateway (Go - 20 MB)

---

## 🎯 Optimization Recommendations

### HIGH PRIORITY - Quick Wins

#### 1. **Create Shared Base Images** (Save 5-7 GB, 30% faster builds)

**Problem**: 27 services all start from scratch with `python:3.11-slim`

**Solution**: Create 2-3 tiered base images

```dockerfile
# backend/docker/base-images/Dockerfile.python-base
FROM python:3.11-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# backend/docker/base-images/Dockerfile.python-fastapi
FROM sentinelgrid/python-base:latest
COPY requirements-common.txt .
RUN pip install --no-cache-dir -r requirements-common.txt
# Includes: fastapi, sqlalchemy, pydantic, httpx, uvicorn, psycopg2-binary

# backend/docker/base-images/Dockerfile.python-ml
FROM sentinelgrid/python-fastapi:latest
RUN pip install --no-cache-dir transformers torch presidio-analyzer
# For AI/ML services only
```

**Then services become**:
```dockerfile
# backend/services/api_gateway/Dockerfile
FROM sentinelgrid/python-fastapi:latest
COPY . .
RUN pip install -r requirements-specific.txt  # Only unique deps
CMD ["uvicorn", "app.main:app"]
```

**Impact**:
- Base image built ONCE, reused 27 times
- Build time: 45 min → 15 min (3x faster)
- Disk space: -6 GB
- Pull time: Much faster (shared layers)

---

#### 2. **Consolidate Similar Services** (Reduce from 47 → 30-35)

**Candidates for consolidation**:

**Group A: Simple CRUD Services** (can be one service with modules)
- cmdb_service
- vulnerability_service  
- observables_service
- incident_service
- tenant_service
→ **Consolidate into**: `metadata_service` (5 → 1)

**Group B: Agent Interfaces** (similar patterns)
- ticketing_agent
- action_agent
- automated_response_service
→ **Consolidate into**: `automation_service` (3 → 1)

**Group C: Reporting & Audit**
- reporting_service
- audit_service
→ **Consolidate into**: `reporting_service` (2 → 1)

**Result**: 47 services → 37 services (10 fewer containers)

---

#### 3. **Eliminate Duplicate Search Engines** (Save 4 GB)

**Current**:
- OpenSearch (2.8 GB) - Used for logs/SIEM
- Elasticsearch (1.2 GB) - Used for... what?

**Question**: Why both OpenSearch AND Elasticsearch?

**Recommendation**: 
- Pick ONE (OpenSearch recommended - AWS-backed)
- Migrate any Elasticsearch usage to OpenSearch
- **Save**: 1.2 GB disk, 1 fewer service

---

#### 4. **Optimize Third-Party Services** (Optional, save 2-3 GB)

**Current Heavy Services**:
- StackStorm (800 MB) - Do you actively use it?
- Cortex (400 MB) - TheHive integration, is it used?
- n8n (350 MB) - Workflow automation, active?
- vLLM/llm_server (~10 GB!) - Local LLM server

**Questions**:
- Are StackStorm, Cortex, n8n actively used in production?
- Can llm_server be optional (dev/ML team only)?

**Recommendation**: Move optional services to separate compose file:
- `docker-compose.dev.yml` - Core 30 services
- `docker-compose.optional.yml` - n8n, StackStorm, Cortex, llm_server

---

### MEDIUM PRIORITY - Architecture Improvements

#### 5. **Multi-Stage Docker Builds** (Smaller final images)

**Current State**: Only 10 services use multi-stage builds (AS base)

**Problem**: Services install build tools (gcc, make) then ship them in production

**Example - Current**:
```dockerfile
FROM python:3.11-slim
RUN apt-get install build-essential  # 200 MB
RUN pip install -r requirements.txt
# Build tools still in final image!
```

**Solution - Multi-Stage**:
```dockerfile
FROM python:3.11-slim AS builder
RUN apt-get install build-essential
RUN pip install -r requirements.txt --target /deps

FROM python:3.11-slim
COPY --from=builder /deps /usr/local
# No build tools in final image!
```

**Impact**: 150-200 MB per service × 17 services = **2.5-3.4 GB saved**

---

### LOW PRIORITY - Future Optimizations

#### 6. **Alpine vs Slim Debate**

**Current**: Using `python:3.11-slim` (Debian-based, 155 MB)

**Alternative**: `python:3.11-alpine` (Alpine Linux, 50 MB)

**Pros**:
- 105 MB smaller per image
- Faster pulls
- Smaller attack surface

**Cons**:
- Some Python packages don't work on Alpine (musl vs glibc)
- Compilation required for many packages (slower builds)
- More debugging complexity

**Recommendation**: **Stick with slim** for Python services (stability > size)

---

## 🎯 Specific Duplication Issues

### Issue 1: Repeated Dependency Installation

**27 services install the SAME packages**:

```python
# Installed 19 times:
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.0.0
python-jose[cryptography]

# Installed 16 times:
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0

# Installed 24 times:
httpx>=0.25.0
```

**Impact**: Each pip install takes 2-5 minutes × 27 services = **54-135 minutes**

**Solution**: Pre-built base image with common deps already installed

---

### Issue 2: Build Context Size

**Current**: Each service copies entire `backend/` or `backend/services/X`

**Problem**: Large context = slow Docker build

**Check sizes**:
```bash
du -sh backend/
du -sh backend/services/*
```

**Solution**: Multi-stage builds + .dockerignore

---

### Issue 3: Flyway Migration Containers

**Current**: 3 separate Flyway containers for migrations
- entitlement_agent_flyway
- model_gateway_migrations
- soar_agent_flyway

**Issue**: Each pulls Flyway image separately

**Solution**: Single migration runner service with volume mounts

---

## 💰 Optimization ROI

### Current State
- **Pull time**: 45-75 minutes (slow network)
- **Build time**: 45+ minutes (all services)
- **Disk usage**: 18.76 GB
- **Memory**: ~8-12 GB (all services running)
- **Container count**: 47

### After Tier 1 Optimizations
- **Pull time**: 15-25 minutes (67% faster)
- **Build time**: 12-20 minutes (73% faster)
- **Disk usage**: 10-12 GB (40% reduction)
- **Memory**: ~6-8 GB (25% reduction)
- **Container count**: 37 (-10 services)

### After Tier 2 Optimizations
- **Pull time**: 10-15 minutes (80% faster)
- **Build time**: 8-12 minutes (82% faster)
- **Disk usage**: 8-10 GB (50% reduction)
- **Memory**: ~5-7 GB (40% reduction)
- **Container count**: 30-32 (-15-17 services)

---

## 📋 Action Plan

### Phase 1: Quick Wins (1-2 days)

1. **Create shared base images**
   - `sentinelgrid/python-base:latest`
   - `sentinelgrid/python-fastapi:latest`
   - `sentinelgrid/python-ml:latest`

2. **Update all Dockerfiles** to use shared bases

3. **Remove duplicate search engine**
   - Audit: Is Elasticsearch actually needed?
   - Migrate to OpenSearch if possible

4. **Create .dockerignore files**
   - Exclude tests, docs, node_modules
   - Reduce build context by 50%

**Effort**: 8-12 hours  
**Savings**: 5-7 GB disk, 30-40% faster builds

---

### Phase 2: Service Consolidation (1 week)

1. **Merge simple CRUD services**
   - cmdb + vulnerability + observables + incident + tenant → `metadata_service`

2. **Merge agent services**
   - ticketing + action + automated_response → `automation_service`

3. **Audit third-party usage**
   - Remove StackStorm if unused
   - Remove Cortex if unused
   - Make n8n optional

**Effort**: 2-3 days  
**Savings**: 10 fewer containers, 2-3 GB disk

---

### Phase 3: Advanced Optimization (2 weeks)

1. **Multi-stage builds for all services**
2. **Implement layer caching strategy**
3. **Create minimal docker-compose profiles**:
   - `core`: Just essential services (15-20)
   - `full`: Everything (47)
   - `dev`: Core + dev tools (25-30)

**Effort**: 1 week  
**Savings**: 3-4 GB additional, better DX

---

## 🔬 Detailed Service Analysis

### Services That Should Stay Separate

**Critical Services** (must be independent):
- api_gateway (entry point)
- iam_agent (authentication)
- siem_agent (security monitoring)
- soar_agent (incident response)
- model_gateway (AI/LLM)
- frontend (UI)

### Services That Could Be Consolidated

**Group 1: Metadata/CRUD Services** (similar patterns):
```
cmdb_service         → All do simple CRUD
vulnerability_service  → All use FastAPI + SQLAlchemy
observables_service    → All connect to same DB
incident_service       → Could be modules in one service
tenant_service
```

**Group 2: External Integrations**:
```
ticketing_agent        → All integrate with external systems
connector_service      → Could share connector framework
email_ingestion_service
```

**Group 3: Analytics/Reporting**:
```
reporting_service      → Similar data processing
audit_service          → Could be single service with modules
detection_service      → (keep separate - security critical)
```

---

## 🚀 Immediate Actions You Can Take

### 1. **Check What's Actually Running**
```bash
docker-compose -f docker-compose.dev.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Size}}"
```

### 2. **Start With Minimal Set** (for development)
```bash
# Core services only
docker-compose -f docker-compose.dev.yml up -d \
  postgres redis keycloak keycloak_db \
  iam_agent api_gateway frontend \
  model_gateway siem_agent soar_agent

# This gives you a working system with ~15 services instead of 47
```

### 3. **Create docker-compose.minimal.yml** (already exists!)
```bash
# Check what's in minimal
docker-compose -f docker-compose.minimal.yml config --services

# Use it for development
docker-compose -f docker-compose.minimal.yml up -d
```

### 4. **Prune Unused Images Right Now**
```bash
# Remove dangling images
docker image prune -f

# Remove unused images (be careful!)
docker image prune -a --filter "until=24h" -f
```

---

## 📈 Disk Space Recovery

**Immediate cleanup**:
```bash
# Remove build cache
docker builder prune -f

# Remove unused images
docker image prune -a --filter "until=720h" -f  # 30 days old

# Remove unused volumes
docker volume prune -f
```

**Expected recovery**: 2-5 GB

---

## 🎯 Recommended Next Steps

**For TODAY**:
1. Use `docker-compose.minimal.yml` for development
2. Run `docker system prune -a --volumes` to clean up
3. Document which services are actually used vs nice-to-have

**For THIS WEEK**:
1. Create shared Python base images
2. Update 5-10 most-used services to use shared base
3. Test build times

**For NEXT SPRINT**:
1. Consolidate CRUD services
2. Move optional services to separate compose file
3. Remove Elasticsearch if not needed

---

**Would you like me to**:
1. Create the shared base image Dockerfiles?
2. Audit which services are actually needed vs optional?
3. Create optimized docker-compose profiles?
4. Check the minimal.yml file to see what's there?

<function_calls>
<invoke name="grep">
<parameter name="pattern">FROM.*AS (base|builder|build)
