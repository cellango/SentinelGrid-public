# Docker & Kubernetes Readiness Assessment

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-01-28  
**Status:** 📋 Assessment & Action Plan  
**Priority:** P1 (Production Deployment)

---

## Executive Summary

This document assesses Docker containerization status and Kubernetes readiness for all SentinelGrid components.

**Current Status:**
- ✅ **13/15 Core Services** - Dockerized
- 🔴 **2 Services Missing** - Dockerfiles needed
- 🔴 **3 External Services** - Need containerization strategy
- 🔴 **Kubernetes Manifests** - Need to be created

---

## Component Inventory

### ✅ Core Services (Dockerized)

| Service | Dockerfile | Status | Notes |
|---------|-----------|--------|-------|
| **Frontend** | ✅ `frontend/Dockerfile` | Ready | Next.js multi-stage build |
| **API Gateway** | ✅ `backend/services/api_gateway/Dockerfile` | Ready | FastAPI service |
| **Orchestrator** | ✅ `backend/services/orchestrator/Dockerfile` | Ready | FastAPI service |
| **Model Gateway** | ✅ `backend/services/model_gateway/Dockerfile` | Ready | FastAPI + data migrations |
| **Agent Runtime** | ✅ `backend/services/agent_runtime/Dockerfile` | Ready | Shared LLM/runtime agent service |
| **SIEM Agent** | ✅ `backend/agents/siem_agent/Dockerfile` | Ready | FastAPI service |
| **SOAR Agent** | ✅ `backend/agents/soar_agent/Dockerfile` | Ready | FastAPI + Flyway migrations |
| **IAM Agent** | ✅ `backend/agents/iam_agent/Dockerfile` | Ready | FastAPI service; owns entitlement/governance APIs |
| **Tenant Service** | ✅ `backend/services/tenant_service/Dockerfile` | Ready | FastAPI service |
| **Connector Service** | ✅ `backend/services/connector_service/Dockerfile` | Ready | FastAPI service |
| **Ingestion Service** | ✅ `backend/services/ingestion_service/Dockerfile` | Ready | FastAPI service |
| **Detection Service** | ✅ `backend/services/detection_service/Dockerfile` | Ready | FastAPI service |
| **Reporting Service** | ✅ `backend/services/reporting_service/Dockerfile` | Ready | FastAPI + WeasyPrint |

Legacy SIEM, entitlement, and AI-enrichment service trees have been removed. Build and deploy from the canonical `backend/agents/*` paths or the active `backend/services/agent_runtime` service.

### 🔴 Missing Dockerfiles

| Service | Status | Priority | Notes |
|---------|--------|----------|-------|
| **Posture Agent** | 🔴 Missing | P2 | Stub service, needs Dockerfile |
| **Ticketing Agent** | 🔴 Missing | P1 | New service from architecture docs |
| **Action Agent** | 🔴 Missing | P1 | New service from architecture docs |
| **Incident Service** | 🔴 Missing | P1 | May be part of orchestrator or separate |

### 🔴 External Services (Need Containerization)

| Service | Status | Priority | Notes |
|---------|--------|----------|-------|
| **TheHive** | 🔴 Not in docker-compose | P1 | Needs official TheHive image |
| **n8n** | 🔴 Not in docker-compose | P1 | Workflow engine for playbooks |
| **LLM Server** | 🔴 Not in docker-compose | P1 | vLLM/TGI for model inference |

### ✅ Infrastructure Services (Containerized)

| Service | Image | Status | Notes |
|---------|-------|--------|-------|
| **PostgreSQL** | `pgvector/pgvector:pg16` | ✅ Ready | Main database |
| **Keycloak DB** | `postgres:16-alpine` | ✅ Ready | Keycloak database |
| **Keycloak** | `quay.io/keycloak/keycloak:26.0.6` | ✅ Ready | IAM service |
| **OpenSearch** | `opensearchproject/opensearch:2.11.0` | ✅ Ready | SIEM data store |
| **OpenSearch Dashboards** | `opensearchproject/opensearch-dashboards:2.11.0` | ✅ Ready | SIEM UI |
| **Redis** | `redis:7-alpine` | ✅ Ready | Caching |

---

## Missing Dockerfiles - Implementation

### 1. Posture Agent Dockerfile

**Location:** `backend/services/posture_agent/Dockerfile`

```dockerfile
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY libs/requirements.txt ./libs-requirements.txt
COPY services/posture_agent/requirements.txt ./posture-requirements.txt
RUN pip install --no-cache-dir -r libs-requirements.txt && \
    pip install --no-cache-dir -r posture-requirements.txt && \
    rm libs-requirements.txt posture-requirements.txt

# Copy shared libs
COPY libs ./libs

# Copy app code
COPY services/posture_agent/app ./app

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Ticketing Agent Dockerfile

**Location:** `backend/services/ticketing_agent/Dockerfile`

```dockerfile
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY libs/requirements.txt ./libs-requirements.txt
COPY services/ticketing_agent/requirements.txt ./ticketing-requirements.txt
RUN pip install --no-cache-dir -r libs-requirements.txt && \
    pip install --no-cache-dir -r ticketing-requirements.txt && \
    rm libs-requirements.txt ticketing-requirements.txt

# Copy shared libs
COPY libs ./libs

# Copy app code
COPY services/ticketing_agent/app ./app

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. Action Agent Dockerfile

**Location:** `backend/services/action_agent/Dockerfile`

```dockerfile
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY libs/requirements.txt ./libs-requirements.txt
COPY services/action_agent/requirements.txt ./action-requirements.txt
RUN pip install --no-cache-dir -r libs-requirements.txt && \
    pip install --no-cache-dir -r action-requirements.txt && \
    rm libs-requirements.txt action-requirements.txt

# Copy shared libs
COPY libs ./libs

# Copy app code
COPY services/action_agent/app ./app

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## External Services - Containerization

### 1. TheHive

**Official Image:** `thehiveproject/thehive5:latest`

**Docker Compose Entry:**
```yaml
thehive:
  image: thehiveproject/thehive5:latest
  environment:
    - CASSANDRA_HOSTS=cassandra:9042
    - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    - SECRET_KEY=${THEHIVE_SECRET_KEY}
    - ADMIN_PASSWORD=${THEHIVE_ADMIN_PASSWORD}
  ports:
    - "9000:9000"
  depends_on:
    - cassandra
    - elasticsearch
  volumes:
    - thehive_data:/opt/thp/thehive/data

cassandra:
  image: cassandra:4.1
  environment:
    - CASSANDRA_CLUSTER_NAME=thehive
    - CASSANDRA_DC=dc1
  volumes:
    - cassandra_data:/var/lib/cassandra

elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=false
  volumes:
    - elasticsearch_data:/usr/share/elasticsearch/data
```

### 2. n8n (Workflow Engine)

**Official Image:** `n8nio/n8n:latest`

**Docker Compose Entry:**
```yaml
n8n:
  image: n8nio/n8n:latest
  environment:
    - N8N_BASIC_AUTH_ACTIVE=true
    - N8N_BASIC_AUTH_USER=${N8N_USER:-admin}
    - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
    - N8N_HOST=n8n
    - N8N_PORT=5678
    - N8N_PROTOCOL=http
    - DB_TYPE=postgresdb
    - DB_POSTGRESDB_HOST=postgres
    - DB_POSTGRESDB_PORT=5432
    - DB_POSTGRESDB_DATABASE=n8n
    - DB_POSTGRESDB_USER=n8n
    - DB_POSTGRESDB_PASSWORD=${N8N_DB_PASSWORD}
  ports:
    - "5678:5678"
  volumes:
    - n8n_data:/home/node/.n8n
  depends_on:
    - postgres
```

### 3. LLM Server (vLLM/TGI)

**Option 1: vLLM**
```yaml
llm_server:
  image: vllm/vllm-openai:latest
  environment:
    - MODEL_NAME=${LLM_MODEL_NAME:-mistralai/Mistral-7B-Instruct-v0.2}
    - HOST=0.0.0.0
    - PORT=8000
  ports:
    - "8001:8000"
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  volumes:
    - model_cache:/root/.cache/huggingface
```

**Option 2: Text Generation Inference (TGI)**
```yaml
llm_server:
  image: ghcr.io/huggingface/text-generation-inference:latest
  environment:
    - MODEL_ID=${LLM_MODEL_NAME:-mistralai/Mistral-7B-Instruct-v0.2}
    - HOSTNAME=0.0.0.0
    - PORT=8000
  ports:
    - "8001:8000"
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  volumes:
    - model_cache:/data
```

---

## Dockerfile Best Practices

### Standard Python Service Template

```dockerfile
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY libs/requirements.txt ./libs-requirements.txt
COPY services/{SERVICE_NAME}/requirements.txt ./service-requirements.txt
RUN pip install --no-cache-dir -r libs-requirements.txt && \
    pip install --no-cache-dir -r service-requirements.txt && \
    rm libs-requirements.txt service-requirements.txt

# Copy shared libraries
COPY libs ./libs

# Copy application code
COPY services/{SERVICE_NAME}/app ./app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Multi-Stage Build (Optional - for smaller images)

```dockerfile
# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY app ./app

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## .dockerignore Files

### Standard .dockerignore

**Location:** `backend/services/{SERVICE_NAME}/.dockerignore`

```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info
dist
build
.pytest_cache
.coverage
htmlcov
.env
.venv
venv/
*.log
.git
.gitignore
README.md
tests/
*.md
```

---

## Kubernetes Readiness

### Required Kubernetes Resources

For each service, we need:

1. **Deployment** - Pod specification
2. **Service** - ClusterIP/LoadBalancer
3. **ConfigMap** - Configuration (non-sensitive)
4. **Secret** - Sensitive data (passwords, tokens)
5. **Ingress** - External access (optional)
6. **HorizontalPodAutoscaler** - Auto-scaling (optional)

### Kubernetes Manifest Template

**Location:** `k8s/services/{SERVICE_NAME}/`

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {service-name}
  namespace: sentinelgrid
spec:
  replicas: 2
  selector:
    matchLabels:
      app: {service-name}
  template:
    metadata:
      labels:
        app: {service-name}
    spec:
      containers:
      - name: {service-name}
        image: sentinelgrid/{service-name}:latest
        ports:
        - containerPort: 8000
        env:
        - name: DB_URL
          valueFrom:
            secretKeyRef:
              name: sentinelgrid-secrets
              key: db-url
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: sentinelgrid-config
              key: log-level
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: {service-name}
  namespace: sentinelgrid
spec:
  selector:
    app: {service-name}
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sentinelgrid-config
  namespace: sentinelgrid
data:
  log-level: "INFO"
  debug-mode: "false"
---
# secret.yaml (example - use sealed-secrets or external secret manager)
apiVersion: v1
kind: Secret
metadata:
  name: sentinelgrid-secrets
  namespace: sentinelgrid
type: Opaque
stringData:
  db-url: "postgresql://user:pass@postgres:5432/sg"
  internal-service-token: "change-me"
```

---

## Docker Compose Updates Needed

### Add Missing Services

**File:** `docker-compose.dev.yml`

```yaml
# Add to existing docker-compose.dev.yml

  # New services
  ticketing_agent:
    build:
      context: ./backend
      dockerfile: services/ticketing_agent/Dockerfile
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=sg
      - DB_USER=sg
      - DB_PASSWORD=${DB_PASSWORD:-sg}
      - LOG_LEVEL=INFO
    ports:
      - "8011:8000"
    depends_on:
      - postgres

  action_agent:
    build:
      context: ./backend
      dockerfile: services/action_agent/Dockerfile
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=sg
      - DB_USER=sg
      - DB_PASSWORD=${DB_PASSWORD:-sg}
      - EDR_API_URL=${EDR_API_URL}
      - FIREWALL_API_URL=${FIREWALL_API_URL}
      - LOG_LEVEL=INFO
    ports:
      - "8013:8000"
    depends_on:
      - postgres

  posture_agent:
    build:
      context: ./backend
      dockerfile: services/posture_agent/Dockerfile
    environment:
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=sg
      - DB_USER=sg
      - DB_PASSWORD=${DB_PASSWORD:-sg}
      - LOG_LEVEL=INFO
    ports:
      - "8006:8000"
    depends_on:
      - postgres

  # External services
  thehive:
    image: thehiveproject/thehive5:latest
    environment:
      - CASSANDRA_HOSTS=cassandra:9042
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
      - SECRET_KEY=${THEHIVE_SECRET_KEY:-change-me}
      - ADMIN_PASSWORD=${THEHIVE_ADMIN_PASSWORD:-admin}
    ports:
    - "9000:9000"
    depends_on:
      - cassandra
      - elasticsearch
    volumes:
      - thehive_data:/opt/thp/thehive/data

  cassandra:
    image: cassandra:4.1
    environment:
      - CASSANDRA_CLUSTER_NAME=thehive
      - CASSANDRA_DC=dc1
    volumes:
      - cassandra_data:/var/lib/cassandra
    ports:
      - "9042:9042"

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    ports:
      - "9201:9200"

  n8n:
    image: n8nio/n8n:latest
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_USER:-admin}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD:-admin}
      - N8N_HOST=n8n
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=n8n
      - DB_POSTGRESDB_PASSWORD=${N8N_DB_PASSWORD:-n8n}
    ports:
      - "5678:5678"
    volumes:
      - n8n_data:/home/node/.n8n
    depends_on:
      - postgres

  llm_server:
    image: vllm/vllm-openai:latest
    environment:
      - MODEL_NAME=${LLM_MODEL_NAME:-mistralai/Mistral-7B-Instruct-v0.2}
      - HOST=0.0.0.0
      - PORT=8000
    ports:
      - "8001:8000"
    # Note: GPU support requires nvidia-docker or nvidia-container-toolkit
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]
    volumes:
      - model_cache:/root/.cache/huggingface
```

---

## Health Checks

### Standard Health Check Endpoint

All services should implement:

```python
# app/main.py

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes."""
    return {
        "status": "healthy",
        "service": "service-name",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health/ready")
async def readiness_check():
    """Readiness check - service is ready to accept traffic."""
    # Check database connection
    # Check external dependencies
    return {"status": "ready"}

@app.get("/health/live")
async def liveness_check():
    """Liveness check - service is alive."""
    return {"status": "alive"}
```

---

## Resource Requirements

### Recommended Resource Limits

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---------|-------------|-----------|----------------|--------------|
| Frontend | 100m | 500m | 128Mi | 512Mi |
| API Gateway | 250m | 1000m | 256Mi | 1Gi |
| Orchestrator | 250m | 1000m | 256Mi | 1Gi |
| Model Gateway | 500m | 2000m | 512Mi | 2Gi |
| SIEM Agent | 500m | 2000m | 512Mi | 2Gi |
| SOAR Agent | 250m | 1000m | 256Mi | 1Gi |
| IAM Agent | 250m | 1000m | 256Mi | 1Gi |
| Other Services | 250m | 500m | 256Mi | 512Mi |
| LLM Server | 2000m | 8000m | 8Gi | 32Gi (GPU) |

---

## Kubernetes Deployment Strategy

### Namespace Structure

```
sentinelgrid/
├── core/              # Core services
│   ├── api-gateway
│   ├── orchestrator
│   └── model-gateway
├── agents/            # Agent services
│   ├── siem-agent
│   ├── soar-agent
│   ├── iam-agent
│   └── ...
├── infrastructure/    # Infrastructure
│   ├── postgres
│   ├── opensearch
│   ├── redis
│   └── keycloak
└── external/          # External services
    ├── thehive
    ├── n8n
    └── llm-server
```

### Service Dependencies

```
Frontend → API Gateway
API Gateway → Orchestrator, IAM Agent
Orchestrator → Model Gateway, SIEM Agent, IAM Agent, SOAR Agent
SOAR Agent → TheHive, n8n
Model Gateway → LLM Server
All Services → PostgreSQL, Redis
```

---

## Action Items

### Immediate (P1)

1. ✅ **Create Missing Dockerfiles**
   - [ ] `backend/services/ticketing_agent/Dockerfile`
   - [ ] `backend/services/action_agent/Dockerfile`
   - [ ] `backend/services/posture_agent/Dockerfile`

2. ✅ **Add External Services to docker-compose**
   - [ ] TheHive + Cassandra + Elasticsearch
   - [ ] n8n
   - [ ] LLM Server (vLLM/TGI)

3. ✅ **Add Health Checks**
   - [ ] `/health` endpoint in all services
   - [ ] `/health/ready` for readiness
   - [ ] `/health/live` for liveness

4. ✅ **Create .dockerignore Files**
   - [ ] Standard .dockerignore for all services

### Short-term (P2)

5. ✅ **Kubernetes Manifests**
   - [ ] Deployment manifests for all services
   - [ ] Service manifests
   - [ ] ConfigMap manifests
   - [ ] Secret management strategy

6. ✅ **Resource Optimization**
   - [ ] Multi-stage builds where beneficial
   - [ ] Image size optimization
   - [ ] Layer caching optimization

### Long-term (P3)

7. ✅ **CI/CD Integration**
   - [ ] Docker image builds in CI
   - [ ] Image registry (Docker Hub/GCR/ECR)
   - [ ] Automated Kubernetes deployments

8. ✅ **Monitoring & Observability**
   - [ ] Prometheus metrics endpoints
   - [ ] Distributed tracing (Jaeger/Zipkin)
   - [ ] Log aggregation (Loki/Fluentd)

---

## Testing Docker Images

### Build Test Script

```bash
#!/bin/bash
# scripts/test-docker-builds.sh

SERVICES=(
  "api_gateway"
  "orchestrator"
  "siem_agent"
  "soar_agent"
  "iam_agent"
  "tenant_service"
  "connector_service"
  "ingestion_service"
  "detection_service"
  "reporting_service"
  "model_gateway"
  "entitlement_agent"
  "ticketing_agent"
  "action_agent"
  "posture_agent"
)

for service in "${SERVICES[@]}"; do
  echo "Building $service..."
  docker build -f backend/services/$service/Dockerfile -t sentinelgrid/$service:test ./backend
  if [ $? -eq 0 ]; then
    echo "✅ $service built successfully"
  else
    echo "❌ $service build failed"
    exit 1
  fi
done

echo "✅ All services built successfully"
```

---

## Summary

### Current Status

- ✅ **13/15 Core Services** - Dockerized and ready
- 🔴 **2 Services** - Need Dockerfiles (ticketing_agent, action_agent)
- 🔴 **1 Service** - Needs Dockerfile update (posture_agent)
- 🔴 **3 External Services** - Need containerization (TheHive, n8n, LLM Server)
- 🔴 **Kubernetes Manifests** - Need to be created

### Next Steps

1. Create missing Dockerfiles (3 files)
2. Add external services to docker-compose
3. Add health check endpoints to all services
4. Create Kubernetes manifests
5. Test all Docker builds
6. Set up CI/CD for image building

---

**Document Owner:** DevOps Team  
**Last Updated:** 2025-01-28  
**Status:** 📋 Ready for Implementation
