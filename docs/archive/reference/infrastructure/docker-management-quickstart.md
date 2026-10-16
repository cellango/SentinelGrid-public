# Docker Management Quick Start

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## 🎯 The Problem We Solved

SentinelGrid has 44 services with **14GB+ of 3rd-party images**. The LLM server alone is **8.3GB** and takes 15-30 minutes to download. We need to:
- ✅ Pull these expensive images **once**
- ✅ Never accidentally delete them
- ✅ Clean up development artifacts safely
- ✅ Repull only when absolutely necessary

## 🚀 Quick Commands

### Daily: Check What You Have

```bash
./scripts/docker-health-check.sh
```

Shows: disk usage, missing images, volume status, running services

### Weekly: Clean Up Safely

```bash
./scripts/docker-safe-prune.sh
```

Removes: stopped containers, dangling images, old build cache
**Protects:** LLM (8.3GB), OpenSearch (1.2GB), Keycloak (600MB), all volumes

### Rarely: Force Repull

```bash
./scripts/docker-force-repull.sh
```

Interactive menu to repull specific image groups (only use if corrupted or need updates)

## 🛡️ Protected Resources

### Never Auto-Deleted:

**Images (14GB total):**
- `vllm/vllm-openai` - 8.3GB LLM server
- `opensearchproject/opensearch` - 824MB SIEM
- `quay.io/keycloak/keycloak` - 600MB auth
- `quay.io/wazuh/wazuh-manager` - 2GB security
- Plus postgres, redis, n8n, stackstorm, cortex

**Volumes:**
- `model_cache` - Downloaded LLM weights (7GB+)
- `postgres_data` - All database data
- `opensearch_data` - Security events
- `keycloak_db_data` - User accounts
- Plus redis, n8n, step-ca data

## ⚠️ NEVER Run These

```bash
docker system prune -a --volumes  # ❌ Deletes EVERYTHING
docker volume prune               # ❌ Deletes volumes including LLM
docker rmi $(docker images -q)   # ❌ Removes ALL images
```

## ✅ Safe Alternatives

```bash
./scripts/docker-safe-prune.sh    # ✅ Protected cleanup
docker container prune            # ✅ Only containers
docker image prune                # ✅ Only dangling images
```

## 📊 Expected Sizes

| State | Total Disk Usage |
|-------|------------------|
| Fresh install | ~15 GB |
| After first run | ~26 GB |
| After 1 week dev | ~38 GB |
| After cleanup | ~30 GB |

**Reserve 40-50 GB for SentinelGrid development.**

## 🔄 Typical Workflows

### Starting Development

```bash
# 1. Check system
./scripts/docker-health-check.sh

# 2. Start services
docker-compose -f docker-compose.dev.yml up -d

# 3. Work on your feature
# Rebuild only what you changed
docker-compose -f docker-compose.dev.yml build api_gateway
docker-compose -f docker-compose.dev.yml restart api_gateway
```

### Weekly Maintenance

```bash
# 1. Check status
./scripts/docker-health-check.sh

# 2. Clean up
./scripts/docker-safe-prune.sh

# 3. Verify
./scripts/docker-health-check.sh
```

### Troubleshooting

```bash
# Image corrupted or won't start?
./scripts/docker-force-repull.sh
# Select the specific image group

# Out of disk space?
./scripts/docker-safe-prune.sh

# Want to see what's running?
docker-compose -f docker-compose.dev.yml ps
```

## 📚 Full Documentation

- **[Docker Resource Management Guide](docker-resource-management.md)** - Complete documentation
- **[Scripts README](../../../../scripts/README.md)** - Detailed script usage
- **[Docker Audit Report](docker-audit-report.md)** - Architecture details

## 🎓 Key Principles

1. **Pull once** - Let large images download completely the first time
2. **Protect volumes** - Never prune volumes without checking
3. **Rebuild selectively** - Only rebuild the service you changed
4. **Use health checks** - Know what you have before cleaning
5. **Keep services running** - No resource waste with Docker

## 🆘 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Out of disk space | `./scripts/docker-safe-prune.sh` |
| Image won't pull | Retry or use `./scripts/docker-force-repull.sh` |
| Service won't start | Check logs: `docker-compose logs service_name` |
| Volume not found | Service will recreate on next start |
| Slow build | Check build cache with health script |

## 💡 Pro Tips

- Keep services running between sessions (no need to stop)
- Tag important images: `docker tag vllm/vllm-openai:latest vllm/vllm-openai:keep`
- Run health check before every cleanup
- Start only services you need with selective startup
- Commit container config changes to docker-compose, not manual tweaks

---

**Remember:** The LLM server is **8.3GB** - pull it once, protect it always! 🛡️

