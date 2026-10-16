# Quick Vault Commands Reference

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Get Platform Admin Password

**Correct command (with HTTP address):**
```bash
docker exec -e VAULT_ADDR='http://127.0.0.1:8200' -e VAULT_TOKEN='sentinelgrid-dev-root-token' vault vault kv get -field=value sentinelgrid/keycloak/platform-admin-password
```

**Common mistake:** Forgetting `VAULT_ADDR` causes HTTPS error:
```
Error: http: server gave HTTP response to HTTPS client
```

## Fix: Always Include VAULT_ADDR

Since Vault runs on HTTP in dev mode, always set:
```bash
-e VAULT_ADDR='http://127.0.0.1:8200'
```

## Other Useful Commands

### Check Vault Status
```bash
docker exec -e VAULT_ADDR='http://127.0.0.1:8200' -e VAULT_TOKEN='sentinelgrid-dev-root-token' vault vault status
```

### List Secrets
```bash
docker exec -e VAULT_ADDR='http://127.0.0.1:8200' -e VAULT_TOKEN='sentinelgrid-dev-root-token' vault vault secrets list
```

### Re-initialize Vault (after restart)
```bash
backend/scripts/init_vault.sh
```

## After Vault Restart

If Vault restarts in dev mode, all secrets are lost. Run:
```bash
backend/scripts/init_vault.sh
```

This will recreate all mounts and secrets.

