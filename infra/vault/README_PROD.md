# Vault Production Setup with Persistent Storage

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This document describes the production Vault configuration that persists secrets across container restarts, unlike the dev mode setup.

## Overview

The production Vault setup uses:
- **File storage backend** - Secrets are stored in a Docker volume (`vault_prod_data`)
- **Auto-initialization** - Vault automatically initializes on first run
- **Auto-unsealing** - Unseal keys are stored securely in the volume
- **Persistent tokens** - Root token is stored in the volume for automatic authentication

## Architecture

```
docker-compose.vault.yml
├── vault service (port 8210)
├── vault_prod_data volume (persistent storage)
└── vault_prod_logs volume (logs)

Configuration Files:
├── infra/vault/config/vault.hcl (production config)
└── infra/vault/scripts/vault-entrypoint.sh (init/unseal logic)
```

## Key Differences from Dev Mode

| Feature | Dev Mode | Production Mode |
|---------|----------|-----------------|
| Storage | In-memory (lost on restart) | File-based (persists) |
| Port | 8200 | 8210 |
| Container | `vault` | `vault` |
| Auto-init | N/A (dev mode handles it) | Yes (via entrypoint script) |
| Unsealing | Automatic (dev mode) | Automatic (stored unseal key) |
| Compose file | `docker-compose.dev.yml` | `docker-compose.vault.yml` |

## Quick Start

### 1. Start Production Vault

```bash
docker-compose -f docker-compose.vault.yml up -d vault
```

### 2. Wait for Initialization

The entrypoint script will:
- Start Vault server
- Initialize if first run
- Store unseal key and root token in volume
- Auto-unseal Vault

Check logs:
```bash
docker-compose -f docker-compose.vault.yml logs -f vault
```

### 3. Initialize Secrets Engines

```bash
# The script will auto-detect the root token from the volume
./backend/scripts/init_vault_prod.sh
```

Or manually:
```bash
export VAULT_ADDR=http://localhost:8210
export VAULT_TOKEN=$(docker exec vault cat /vault/file/.vault_root_token)

vault secrets enable -path=sentinelgrid -version=2 kv
vault secrets enable transit
vault secrets enable database
```

### 4. Test Persistence

Run the persistence test:
```bash
./scripts/test_vault_prod_persistence.sh
```

This script will:
1. Store a test secret
2. Restart the container
3. Verify the secret still exists

## Configuration

### Environment Variables

Set in `docker-compose.vault.yml` or `.env`:

```bash
VAULT_ROOT_TOKEN=<explicit-root-token-if-you-are-overriding-the-generated-one>
```

After first initialization, the actual root token is stored at:
- Container: `/vault/file/.vault_root_token`
- Host: `.vault-root-token` (created by scripts)

### Vault Configuration

Edit `infra/vault/config/vault.hcl` to customize:
- Storage path
- Listeners (enable TLS for production)
- Lease TTLs
- Logging

### Enable TLS (Production)

1. Generate certificates:
```bash
./backend/scripts/generate_vault_certs.sh
```

2. Update `vault.hcl`:
```hcl
listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/vault/certs/vault.crt"
  tls_key_file  = "/vault/certs/vault.key"
  tls_disable   = 0
}

api_addr = "https://0.0.0.0:8200"
```

3. Update `VAULT_ADDR` in applications:
```bash
VAULT_ADDR=https://localhost:8210
```

## Usage in Application

### Environment Variables

For applications connecting to production Vault:

```bash
VAULT_ADDR=http://localhost:8210
VAULT_TOKEN=<token-from-vault>
```

Or use the root token:
```bash
VAULT_TOKEN=$(cat .vault-root-token)
```

### Python Client

```python
from backend.libs.sg_vault import VaultClient

client = VaultClient(
    url="http://localhost:8210",
    token=os.getenv("VAULT_TOKEN"),
    tenant_id="your-tenant-id"
)

# Secrets persist across restarts!
secret = client.get_secret("my-secret-key")
```

## Testing

### Run Persistence Test

```bash
./scripts/test_vault_prod_persistence.sh
```

### Manual Testing

1. Store a secret:
```bash
export VAULT_ADDR=http://localhost:8210
export VAULT_TOKEN=$(docker exec vault cat /vault/file/.vault_root_token)
vault kv put sentinelgrid/test/my-secret value="test-data"
```

2. Restart container:
```bash
docker-compose -f docker-compose.vault.yml restart vault
```

3. Verify secret still exists:
```bash
vault kv get sentinelgrid/test/my-secret
```

## Troubleshooting

### Vault is Sealed

If Vault is sealed after restart:

```bash
# Get unseal key from volume
UNSEAL_KEY=$(docker exec vault cat /vault/file/.vault_unseal_key)

# Unseal
export VAULT_ADDR=http://localhost:8210
vault operator unseal "$UNSEAL_KEY"
```

### Cannot Authenticate

1. Get root token from volume:
```bash
docker exec vault cat /vault/file/.vault_root_token
```

2. Use it:
```bash
export VAULT_TOKEN=<token-from-above>
vault token lookup
```

### Container Won't Start

Check logs:
```bash
docker-compose -f docker-compose.vault.yml logs vault
```

Common issues:
- Port 8210 already in use
- Volume permissions issue
- Config file syntax error

### Reset Vault (Start Fresh)

⚠️ **Warning: This deletes all secrets!**

```bash
# Stop and remove container
docker-compose -f docker-compose.vault.yml down

# Remove volumes
docker volume rm sentinelgrid_vault_prod_data sentinelgrid_vault_prod_logs

# Remove local token file
rm -f .vault-root-token

# Start fresh
docker-compose -f docker-compose.vault.yml up -d vault
```

## Integration with Application

Once tested and verified, update your application docker-compose files:

### Option 1: Replace Dev Vault

In `docker-compose.dev.yml`, change:
```yaml
vault:
  # Remove dev mode
  # Add reference to vault service or use same setup
```

### Option 2: Use Separate Vault Service

Keep both dev and prod:
- Dev Vault: Port 8200 (for development)
- Prod Vault: Port 8210 (for production/staging)

Applications can choose which to use via `VAULT_ADDR` environment variable.

## Security Considerations

1. **Root Token**: Change default root token in production
2. **Unseal Keys**: Store unseal keys securely (not in volumes for production)
3. **TLS**: Enable TLS for production deployments
4. **Access Control**: Use policies and tokens, not root token
5. **Backup**: Backup the `vault_prod_data` volume regularly

## Backup and Restore

### Backup

```bash
# Backup volume
docker run --rm \
  -v sentinelgrid_vault_prod_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/vault-backup-$(date +%Y%m%d).tar.gz /data
```

### Restore

```bash
# Restore volume
docker run --rm \
  -v sentinelgrid_vault_prod_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/vault-backup-YYYYMMDD.tar.gz -C /
```

## Next Steps

1. ✅ Test persistence with `test_vault_prod_persistence.sh`
2. ✅ Verify secrets engines work correctly
3. ✅ Update application docker-compose to use production Vault
4. ✅ Enable TLS for production
5. ✅ Set up automated backups
6. ✅ Implement proper unseal key management (e.g., AWS KMS, HashiCorp Cloud)
