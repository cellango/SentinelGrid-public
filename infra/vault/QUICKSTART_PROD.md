# Vault Production Quick Start

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This is a standalone production Vault setup that persists secrets across container restarts.

## 🚀 Quick Start

### 1. Start Vault

```bash
docker-compose -f docker-compose.vault.yml up -d vault
```

### 2. Initialize (First Time)

```bash
./backend/scripts/init_vault_prod.sh
```

### 3. Test Persistence

```bash
./scripts/test_vault_prod_persistence.sh
```

## 📋 What Gets Created

- **Container**: `vault` (port 8210)
- **Volumes**: 
  - `vault_prod_data` - Persistent secrets storage
  - `vault_prod_logs` - Log files
- **Config**: `infra/vault/config/vault.hcl`
- **Auto-init**: Runs automatically on first start

## 🔑 Access Vault

```bash
# Get root token (auto-saved by scripts)
export VAULT_ADDR=http://localhost:8210
export VAULT_TOKEN=$(cat .vault-root-token)

# Or get from container
export VAULT_TOKEN=$(docker exec vault cat /vault/file/.vault_root_token)

# Verify
vault status
```

## 🧪 Test Persistence

The test script will:
1. Store a test secret
2. Restart the container
3. Verify the secret still exists

```bash
./scripts/test_vault_prod_persistence.sh
```

## 🛠️ Common Commands

```bash
# View logs
docker-compose -f docker-compose.vault.yml logs -f vault

# Restart
docker-compose -f docker-compose.vault.yml restart vault

# Stop
docker-compose -f docker-compose.vault.yml down

# Remove everything (including volumes)
docker-compose -f docker-compose.vault.yml down -v
```

## 📚 Full Documentation

See `infra/vault/README_PROD.md` for complete documentation.

