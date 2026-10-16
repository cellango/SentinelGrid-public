# Docker Resource Management for SentinelGrid

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## 🎯 Overview

SentinelGrid uses a mix of custom-built services and heavy 3rd-party images. This guide ensures you never waste time or bandwidth re-downloading large images.

## 📦 Resource Categories

### Critical 3rd-Party Images (Protected - NEVER auto-delete)

| Image | Size | Purpose | Pull Time* |
|-------|------|---------|------------|
| `vllm/vllm-openai:latest` | 8.3 GB | LLM Server | ~15-30 min |
| `opensearchproject/opensearch:2.11.0` | 824 MB | SIEM Backend | ~3-5 min |
| `opensearchproject/opensearch-dashboards:2.11.0` | 444 MB | SIEM UI | ~2-3 min |
| `quay.io/keycloak/keycloak:latest` | 600 MB | IAM | ~2-4 min |
| `quay.io/wazuh/wazuh-manager:latest` | 2.0 GB | Endpoint Protection | ~5-10 min |
| `docker.n8n.io/n8nio/n8n:latest` | 272 MB | Automation | ~1-2 min |
| `stackstorm/stackstorm:latest` | 345 MB | SOAR | ~2-3 min |
| `cortexproject/cortex:latest` | 836 MB | Observability | ~3-5 min |
| `postgres:15-alpine` | 238 MB | Database | ~1-2 min |
| `redis:7-alpine` | 42 MB | Cache | ~30 sec |

**Total: ~14 GB** | **Est. Pull Time: 40-70 minutes on typical connection**

*Pull times vary based on network speed and CDN location

### Custom SentinelGrid Images (Ephemeral - safe to rebuild)

| Image Pattern | Build Time | Can Rebuild |
|---------------|------------|-------------|
| `sentinelgrid-*:latest` | ~1-2 min | ✅ Yes |
| `sentinelgrid/api-base:latest` | ~30 sec | ✅ Yes |
| `sentinelgrid/*-agent:latest` | ~30 sec | ✅ Yes |

### Protected Volumes (NEVER delete without backup)

| Volume | Contains | Recovery |
|--------|----------|----------|
| `model_cache` | Downloaded LLM weights (7GB+) | Re-download |
| `postgres_data` | All database data | ❌ Lost |
| `opensearch_data` | Security events/logs | ❌ Lost |
| `keycloak_db_data` | User accounts/auth | ❌ Lost |
| `redis_data` | Session cache | ⚠️ Sessions lost |
| `n8n_data` | Workflows | ❌ Lost |
| `step_ca_data` | SSL certificates | ⚠️ Regenerate |

## 🛠️ Management Scripts

### 1. Health Check (Run Anytime)

```bash
./scripts/docker-health-check.sh
```

**Shows:**
- Current disk usage
- Missing critical images
- Volume status
- Running services
- Recommendations

**Run this:**
- Before starting work
- After failed pulls
- To check what can be cleaned

### 2. Safe Prune (Weekly Maintenance)

```bash
./scripts/docker-safe-prune.sh
```

**What it does:**
- ✅ Removes stopped containers
- ✅ Removes dangling images
- ✅ Clears old build cache
- ✅ Offers to remove custom SentinelGrid images
- ❌ NEVER touches protected volumes
- ❌ NEVER touches 3rd-party images

**When to run:**
- Weekly as maintenance
- After rebuilding services multiple times
- When disk space is low
- Before major updates

### 3. Force Repull (Rarely Needed)

```bash
./scripts/docker-force-repull.sh
```

**Only use when:**
- Image is corrupted
- Need latest version (security update)
- Troubleshooting image issues

**Interactive menu lets you choose:**
- Specific image groups
- Individual components
- All images

## 📋 Daily Workflow

### Starting Work

```bash
# 1. Check system health
./scripts/docker-health-check.sh

# 2. Start services
docker-compose -f docker-compose.dev.yml up -d
```

### During Development

```bash
# Rebuild only your service
docker-compose -f docker-compose.dev.yml build api_gateway

# Restart single service
docker-compose -f docker-compose.dev.yml restart api_gateway
```

### End of Day (Optional)

```bash
# Stop services (volumes remain)
docker-compose -f docker-compose.dev.yml down

# Keep services running overnight (recommended)
# - No need to repull images tomorrow
# - Faster startup
```

### Weekly Maintenance

```bash
# 1. Health check
./scripts/docker-health-check.sh

# 2. Safe cleanup
./scripts/docker-safe-prune.sh

# 3. Verify
./scripts/docker-health-check.sh
```

## ⚠️ What NOT to Do

### ❌ NEVER Run These Commands

```bash
# These will delete your LLM and data!
docker system prune -a --volumes  # ❌ Deletes EVERYTHING including volumes
docker volume prune               # ❌ Deletes unused volumes (including LLM cache)
docker rmi $(docker images -q)   # ❌ Removes ALL images
```

### ✅ Safe Alternatives

```bash
# Remove only stopped containers
docker container prune

# Remove only dangling images
docker image prune

# Remove only dangling volumes (our script checks protection)
./scripts/docker-safe-prune.sh
```

## 🚀 Advanced: Selective Startup

### Start Only Core Services

```bash
docker-compose -f docker-compose.dev.yml up -d \
  postgres \
  redis \
  keycloak \
  keycloak_db \
  api_gateway \
  iam_agent
```

### Start Without LLM (Save Resources)

```bash
docker-compose -f docker-compose.dev.yml up -d \
  --scale llm_server=0 \
  --scale ai_shield_services=0
```

### Start Only AI Shield

```bash
docker-compose -f docker-compose.dev.yml up -d \
  postgres \
  redis \
  llm_server \
  ai_shield_services \
  sentinelgrid_ai_shield_gateway
```

## 📊 Monitoring Disk Usage

### Check Total Usage

```bash
docker system df
```

### Detailed Volume Usage

```bash
docker system df -v
```

### Find Largest Volumes

```bash
docker system df -v | sort -k3 -h
```

## 🔄 Recovery Procedures

### If LLM Image is Corrupted

```bash
# 1. Stop services
docker-compose -f docker-compose.dev.yml stop llm_server

# 2. Remove corrupted image
docker rmi vllm/vllm-openai:latest

# 3. Repull
./scripts/docker-force-repull.sh
# Select option 1

# 4. Restart
docker-compose -f docker-compose.dev.yml up -d llm_server
```

### If Volume is Corrupted

```bash
# 1. Stop all services
docker-compose -f docker-compose.dev.yml down

# 2. Backup if possible
docker run --rm -v sentinelgrid_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup.tar.gz /data

# 3. Remove volume
docker volume rm sentinelgrid_postgres_data

# 4. Restart (will recreate)
docker-compose -f docker-compose.dev.yml up -d
```

## 💡 Best Practices

1. **Let initial pull complete** - Don't interrupt the first pull of large images
2. **Use health check before cleanup** - Know what you have before removing
3. **Never prune volumes blindly** - Always use the safe script
4. **Keep services running** - Stopping/starting wastes no resources with Docker
5. **Rebuild selectively** - Only rebuild the service you changed
6. **Tag before experimenting** - `docker tag vllm/vllm-openai:latest vllm/vllm-openai:backup`
7. **Check disk space regularly** - Run health check weekly

## 🆘 Troubleshooting

### "No space left on device"

```bash
./scripts/docker-health-check.sh
./scripts/docker-safe-prune.sh
```

### "Image pull timeout"

```bash
# Retry with increased timeout
DOCKER_CLIENT_TIMEOUT=600 docker-compose -f docker-compose.dev.yml pull llm_server
```

### "Volume not found"

```bash
# Recreate volume
docker volume create sentinelgrid_model_cache

# Restart service
docker-compose -f docker-compose.dev.yml up -d llm_server
```

## 📈 Expected Disk Usage

| State | Images | Volumes | Build Cache | Total |
|-------|--------|---------|-------------|-------|
| Fresh install | ~14 GB | ~100 MB | ~1 GB | ~15 GB |
| After first run | ~14 GB | ~10 GB | ~2 GB | ~26 GB |
| After 1 week dev | ~18 GB | ~15 GB | ~5 GB | ~38 GB |
| After cleanup | ~14 GB | ~15 GB | ~500 MB | ~30 GB |

**Recommendation:** Reserve 40-50 GB for SentinelGrid development environment.

