# How to Get Platform Admin Password from Vault

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Correct Command (with HTTP address)

Since Vault is running in dev mode on HTTP, you need to specify the address:

```bash
docker exec -e VAULT_ADDR='http://127.0.0.1:8200' -e VAULT_TOKEN='sentinelgrid-dev-root-token' vault vault kv get -field=value sentinelgrid/keycloak/platform-admin-password
```

## Common Issue: Secret Doesn't Exist

If you get a 403 error, it means:
1. Vault was restarted (dev mode loses all data)
2. The `sentinelgrid/` mount doesn't exist
3. Secrets need to be re-seeded

## Solution: Re-initialize Vault

Run the initialization script to recreate mounts and secrets:

```bash
backend/scripts/init_vault.sh
```

This will:
- Enable the `sentinelgrid/` KV mount
- Generate and store platform admin password
- Store other required secrets

## After Re-initialization

Then you can retrieve the password:

```bash
docker exec -e VAULT_ADDR='http://127.0.0.1:8200' -e VAULT_TOKEN='sentinelgrid-dev-root-token' vault vault kv get -field=value sentinelgrid/keycloak/platform-admin-password
```

