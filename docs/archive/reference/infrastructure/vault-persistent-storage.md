# Vault Persistent Storage Setup

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Current Status

Vault is currently running in **dev mode** which uses in-memory storage. Passwords are lost when Docker/Vault restarts.

## Quick Answer

**Yes, we can mount a volume to Vault** - we already have `vault_data:/vault/file` mounted, but dev mode ignores it.

To enable persistent storage, we need to:
1. Switch from dev mode to file storage mode
2. Initialize Vault (one-time)
3. Unseal Vault (can be automated)

## Option 1: Keep Dev Mode (Current - Simple)

**Pros:**
- Fast and simple
- No initialization needed
- Auto-unsealed

**Cons:**
- Passwords lost on restart
- Volume exists but not used

**After restart:** Run `backend/scripts/init_vault.sh` to re-seed passwords.

## Option 2: Enable Persistent Storage

I've created the configuration files. To enable:

1. **Config file created:** `infra/vault/config/vault-dev-persistent.hcl`
2. **Volume already mounted:** `vault_data:/vault/file`

To switch:
1. Update docker-compose to use file storage (config exists)
2. Initialize Vault on first run
3. Passwords will persist in the volume

Would you like me to complete the setup for persistent storage?

## Files Created

- ✅ `infra/vault/config/vault-dev-persistent.hcl` - Config for persistent file storage
- ✅ `infra/vault/scripts/vault-entrypoint.sh` - Auto-initialization script (optional)
- ✅ `docs/VAULT_STORAGE_OPTIONS.md` - Detailed comparison

## Quick Fix After Restart

If you restart Docker and passwords are lost, run:

```bash
backend/scripts/init_vault.sh
```

This will re-seed all passwords in Vault.

