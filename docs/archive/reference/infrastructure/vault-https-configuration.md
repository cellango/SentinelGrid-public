# Vault HTTPS Configuration

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-12-05  
**Status:** ✅ Implemented

---

## Overview

HashiCorp Vault is configured to use **HTTPS/TLS even in development mode**. This is a security best practice that ensures:

1. **Encryption in transit** - All Vault API calls are encrypted
2. **Production parity** - Development environment matches production security posture
3. **Security training** - Developers learn to work with TLS from the start

---

## Certificate Generation

### Self-Signed Certificates (Development)

Certificates are generated using the provided script:

```bash
bash backend/scripts/generate_vault_certs.sh
```

This creates:
- `infra/vault/certs/vault.key` - Private key (2048-bit RSA)
- `infra/vault/certs/vault.crt` - Self-signed certificate (valid for 10 years)

**Certificate Details:**
- **Subject:** `CN=localhost, O=SentinelGrid, OU=Dev`
- **SAN:** `localhost`, `vault`, `*.localhost`, `127.0.0.1`, `0.0.0.0`
- **Validity:** 10 years (3650 days)

### Production Certificates

For production, use proper CA-signed certificates:
1. Obtain certificates from your CA (Let's Encrypt, internal CA, etc.)
2. Replace `infra/vault/certs/vault.crt` and `vault.key`
3. Update `infra/vault/config/vault.hcl` if needed

---

## Configuration

### Docker Compose

Vault is configured in `docker-compose.dev.yml` to use dev mode with TLS:

```yaml
vault:
  image: hashicorp/vault:latest
  command: >
    server -dev
    -dev-root-token-id=${VAULT_ROOT_TOKEN:-sentinelgrid-dev-root-token}
    -dev-listen-address=0.0.0.0:8200
    -dev-tls-cert-file=/vault/certs/vault.crt
    -dev-tls-key-file=/vault/certs/vault.key
  volumes:
    - ./infra/vault/certs:/vault/certs:ro
```

### Vault Config File

The `infra/vault/config/vault.hcl` file is configured for production mode (not used in dev mode):

```hcl
listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/vault/certs/vault.crt"
  tls_key_file  = "/vault/certs/vault.key"
  tls_disable   = 0  # TLS enabled
}

api_addr = "https://0.0.0.0:8200"
```

---

## Usage

### Command Line (curl)

**With certificate verification skipped (dev):**
```bash
curl -k https://localhost:8200/v1/sys/health
```

**With certificate verification (production):**
```bash
curl --cacert infra/vault/certs/vault.crt https://localhost:8200/v1/sys/health
```

### Vault CLI

**Set environment variables:**
```bash
export VAULT_ADDR=https://localhost:8200
export VAULT_SKIP_VERIFY=true  # For self-signed certs in dev
export VAULT_TOKEN=sentinelgrid-dev-root-token
```

**Then use Vault CLI normally:**
```bash
vault status
vault kv list sentinelgrid/keycloak
vault kv get sentinelgrid/keycloak/master-admin-password
```

### Docker Exec

All scripts use `docker exec` to access Vault with proper TLS configuration:

```bash
docker exec \
  -e VAULT_ADDR="https://127.0.0.1:8200" \
  -e VAULT_SKIP_VERIFY="true" \
  -e VAULT_TOKEN="$VAULT_TOKEN" \
  vault vault status
```

### Python (hvac)

```python
import hvac

client = hvac.Client(
    url='https://localhost:8200',
    token='sentinelgrid-dev-root-token',
    verify=False  # Skip verification for self-signed certs
)

# Or use the sg_vault client library
from backend.libs.sg_vault.client import VaultClient

vault = VaultClient(
    url='https://localhost:8200',
    token='sentinelgrid-dev-root-token',
    verify=False  # Default for dev
)
```

---

## Scripts Updated

All scripts have been updated to use HTTPS:

1. **`backend/scripts/init_vault.sh`**
   - Uses `https://localhost:8200`
   - Sets `VAULT_SKIP_VERIFY=true` for docker exec commands
   - Uses `curl -k` for health checks

2. **`backend/scripts/init_complete_stack.sh`**
   - Uses `https://localhost:8200`
   - All vault commands use docker exec with TLS config

3. **`backend/scripts/generate_vault_certs.sh`**
   - Generates self-signed certificates
   - Sets proper permissions (600 for key, 644 for cert)

---

## Security Considerations

### Development

- ✅ **HTTPS enabled** - All traffic encrypted
- ⚠️ **Self-signed certificates** - Browser/curl warnings expected
- ⚠️ **Certificate verification skipped** - Use `-k` flag or `verify=False`
- ✅ **Certificates in .gitignore** - Private keys not committed

### Production

- ✅ **Use CA-signed certificates** - No browser warnings
- ✅ **Enable certificate verification** - Set `verify=True` in clients
- ✅ **Proper certificate management** - Rotate certificates regularly
- ✅ **Monitor certificate expiration** - Set up alerts

---

## Troubleshooting

### Certificate Errors

**Error:** `x509: certificate signed by unknown authority`

**Solution:** Use `-k` flag with curl or set `VAULT_SKIP_VERIFY=true`:
```bash
curl -k https://localhost:8200/v1/sys/health
```

### Connection Refused

**Error:** `connection refused` or `connection reset`

**Check:**
1. Vault is running: `docker-compose ps vault`
2. Port 8200 is not in use: `lsof -i :8200`
3. Certificates exist: `ls -la infra/vault/certs/`

### Certificate Not Found

**Error:** `open /vault/certs/vault.crt: no such file or directory`

**Solution:** Generate certificates:
```bash
bash backend/scripts/generate_vault_certs.sh
```

Then restart Vault:
```bash
docker-compose restart vault
```

---

## Files Modified

1. `docker-compose.dev.yml` - Updated Vault service to use TLS
2. `infra/vault/config/vault.hcl` - Configured for TLS
3. `backend/scripts/init_vault.sh` - Updated to use HTTPS
4. `backend/scripts/init_complete_stack.sh` - Updated to use HTTPS
5. `backend/scripts/generate_vault_certs.sh` - New script for certificate generation
6. `backend/libs/sg_vault/client.py` - Updated to support verify parameter
7. `docs/archive/reference/infrastructure/ports.md` - Updated to reflect HTTPS URLs
8. `.gitignore` - Added certificate files

---

## Next Steps

1. ✅ **Development:** HTTPS enabled with self-signed certs
2. ⏳ **Production:** Configure CA-signed certificates
3. ⏳ **Monitoring:** Set up certificate expiration alerts
4. ⏳ **Documentation:** Update customer-facing docs if needed

---

**Last Updated:** 2025-12-05  
**Maintained By:** SentinelGrid Team

