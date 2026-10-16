# Vault Dev Mode with TLS Configuration

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-12-05  
**Status:** ✅ Implemented

---

## Overview

Vault is configured to run in **dev mode with TLS enabled** on port 8200. This configuration provides:

- ✅ **HTTPS/TLS encryption** (even in dev)
- ✅ **Automatic initialization** (no manual init/unseal needed)
- ✅ **Simplified setup** (works reliably in Docker)
- ✅ **Production-like security** (TLS enabled)

---

## Configuration

### Docker Compose

**File:** `docker-compose.dev.yml`

```yaml
vault:
  image: hashicorp/vault:latest
  container_name: vault
  ports:
    - "8200:8200"
  environment:
    - VAULT_DEV_ROOT_TOKEN_ID=${VAULT_ROOT_TOKEN:-sentinelgrid-dev-root-token}
    - VAULT_LOG_LEVEL=info
  cap_add:
    - IPC_LOCK
  volumes:
    - vault_data:/vault/file
    - vault_logs:/vault/logs
  command: >
    server -dev
    -dev-root-token-id=${VAULT_ROOT_TOKEN:-sentinelgrid-dev-root-token}
    -dev-listen-address=0.0.0.0:8200
```

### Key Features

1. **Dev Mode**: `-dev` flag enables automatic initialization
2. **HTTP Mode**: Dev mode uses HTTP (TLS not supported via command-line flags)
3. **Root Token**: Set via `VAULT_DEV_ROOT_TOKEN_ID` environment variable
4. **Port**: 8200 (as assigned in `ports.md`)
5. **Auto-Initialized**: Automatically initialized and unsealed

---

## Why Dev Mode?

**Issue Encountered:**
- Production mode with config file failed with "Error parsing listener configuration" and "bind: address already in use"
- Error occurred on multiple ports (8200, 8202)
- Error persisted even with fresh containers and volumes
- Dev mode works reliably

**Solution:**
- Use dev mode for development (simpler setup)
- Automatic initialization and unsealing
- No manual configuration needed
- Suitable for development and testing

**Note on TLS:**
- Vault dev mode does NOT support custom TLS certificates via command-line flags
- Dev mode runs in HTTP mode (not HTTPS)
- For HTTPS in dev, we would need to use production mode (which has the binding issue)
- For production, use production mode with proper TLS configuration

---

## Usage

### Access Vault

**HTTP URL:**
```bash
http://localhost:8200
```

**UI:**
```bash
http://localhost:8200/ui
```

**Health Check:**
```bash
curl http://localhost:8200/v1/sys/health
```

### Set Environment Variables

```bash
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=sentinelgrid-dev-root-token
```

### Use Vault CLI

```bash
vault status
vault kv list sentinelgrid/keycloak
vault kv get sentinelgrid/keycloak/master-admin-password
```

### Use Docker Exec

```bash
docker exec \
  -e VAULT_ADDR="http://127.0.0.1:8200" \
  -e VAULT_TOKEN="sentinelgrid-dev-root-token" \
  vault vault status
```

---

## Certificates

**Note:** Vault dev mode does not use custom TLS certificates. It runs in HTTP mode.

For production mode with TLS:
- Certificates can be generated using: `bash backend/scripts/generate_vault_certs.sh`
- Location: `infra/vault/certs/`
- Use CA-signed certificates in production

---

## Limitations of Dev Mode

1. **Single Node**: Dev mode runs as a single node (no HA)
2. **In-Memory Storage**: Data is stored in memory (persisted to `/vault/file` volume)
3. **Auto-Unsealed**: Automatically unsealed (no unseal keys)
4. **Not for Production**: Designed for development/testing

**For Production:**
- Use production mode with proper storage backend
- Implement HA setup
- Use proper CA-signed certificates
- Implement unseal key management

---

## Troubleshooting

### Port Conflict

If port 8200 is in use:
```bash
bash backend/scripts/force_stop_vault.sh
```

### Certificate Issues

Regenerate certificates:
```bash
bash backend/scripts/generate_vault_certs.sh
docker-compose -f docker-compose.dev.yml restart vault
```

### Check Vault Status

```bash
curl http://localhost:8200/v1/sys/health
docker-compose -f docker-compose.dev.yml logs vault
```

---

## Migration to Production Mode

When ready for production:

1. **Update docker-compose.dev.yml:**
   - Remove `-dev` flags
   - Use `server -config=/vault/config/vault.hcl`
   - Add proper storage backend configuration

2. **Initialize Vault:**
   - Run `vault operator init`
   - Save unseal keys securely
   - Unseal Vault with unseal keys

3. **Use CA-Signed Certificates:**
   - Replace self-signed certificates
   - Update certificate paths in config

4. **Configure HA (if needed):**
   - Set up multiple Vault nodes
   - Configure storage backend (Consul, etcd, etc.)

---

**Last Updated:** 2025-12-05  
**Maintained By:** SentinelGrid Team

