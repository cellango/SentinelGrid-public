# SentinelGrid Docker Management Scripts

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../RELEASE_SCOPE.md) first.


## Quick Reference

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `docker-health-check.sh` | Show Docker system status | Anytime (read-only) |
| `docker-safe-prune.sh` | Clean up safely | Weekly maintenance |
| `docker-force-repull.sh` | Repull 3rd-party images | Rarely (only if needed) |
| `embedding-fanout-smoke.sh` | Verify ingestion → embeddings fan-out works | After changes to ingestion/model_gateway |
| `embedding-search-smoke.sh` | Verify embeddings search endpoint returns results | After changes to model_gateway search |

## Installation

```bash
# Make scripts executable
chmod +x scripts/docker-*.sh

# Verify
./scripts/docker-health-check.sh
```

## Usage Examples

### Daily: Check Status

```bash
./scripts/docker-health-check.sh
```

**Output shows:**
- Disk usage
- Missing images
- Volume status
- Running services
- Cleanup recommendations

### Weekly: Clean Up

```bash
./scripts/docker-safe-prune.sh
```

**Interactive prompts for:**
- Removing custom images (safe - can rebuild)
- Removing unused volumes (careful - checks protection)

**Automatically removes:**
- Stopped containers
- Dangling images
- Old build cache (>24h)

### Rarely: Force Update

```bash
./scripts/docker-force-repull.sh
```

**Interactive menu:**
1. LLM Server only (8.3GB)
2. OpenSearch (1.2GB)
3. Keycloak (600MB)
4. Wazuh (2GB)
5. Databases (300MB)
6. Automation tools (2GB)
7. ALL images (14GB+)

## Protected Resources

### Images (Never Auto-Deleted)
- `vllm/vllm-openai:*` - 8.3GB LLM
- `opensearchproject/*` - 1.2GB SIEM
- `quay.io/keycloak/*` - 600MB Auth
- `quay.io/wazuh/*` - 2GB Security
- `postgres:*` - 238MB Database
- `redis:*` - 42MB Cache

### Volumes (Never Auto-Deleted)
- `*model_cache` - LLM weights
- `*postgres_data` - Database
- `*opensearch_data` - Logs
- `*keycloak_db_data` - Users
- `*redis_data` - Cache

## Safety Features

✅ All scripts use color-coded output
✅ Confirmation prompts before destructive actions
✅ Protected resources are never touched
✅ Detailed logging of actions taken
✅ Rollback information provided

## Common Workflows

### Before Starting Work

```bash
./scripts/docker-health-check.sh
docker-compose -f docker-compose.dev.yml up -d
```

### After Major Development

```bash
# Check what's accumulated
./scripts/docker-health-check.sh

# Clean up if needed
./scripts/docker-safe-prune.sh

# Verify cleanup
./scripts/docker-health-check.sh
```

### Troubleshooting Image Issues

```bash
# Check status
./scripts/docker-health-check.sh

# If image is corrupted, repull specific one
./scripts/docker-force-repull.sh
# Select the problematic image group

# Restart services
docker-compose -f docker-compose.dev.yml restart
```

## Exit Codes

All scripts use standard exit codes:
- `0` - Success
- `1` - Error or user cancelled

## Logging

Scripts output to stdout with color coding:
- 🔵 **Blue** - Informational
- 🟢 **Green** - Success
- 🟡 **Yellow** - Warning
- 🔴 **Red** - Error or critical

## See Also

- [Docker Resource Management Guide](../docs/archive/reference/infrastructure/docker-resource-management.md) - Complete documentation
- [Build Notes](../docs/archive/reference/infrastructure/build-notes-dec-3-2025.md) - Build system overview
- [Docker Audit Report](../docs/archive/reference/infrastructure/docker-audit-report.md) - Architecture details
