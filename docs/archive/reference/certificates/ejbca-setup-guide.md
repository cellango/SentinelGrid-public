# EJBCA Setup Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-01-28  
**Purpose:** Guide for setting up EJBCA in development and production

---

## Quick Start (Development)

### 1. Start EJBCA

```bash
docker-compose up -d ejbca ejbca_db
```

Wait for EJBCA to fully start (2-3 minutes). Check logs:
```bash
docker-compose logs -f ejbca
```

### 2. Access EJBCA Admin UI

**URL:** `https://localhost:8443/ejbca/adminweb/`

**Default Credentials:**
- Username: `admin`
- Password: `admin` (change in production!)

**Note:** Browser will warn about self-signed certificate - accept it for development.

### 3. Initial EJBCA Configuration

#### Step 1: Create Root CA

1. Navigate to: **CA Functions → Create CA**
2. **CA Name:** `SentinelGrid-Root-CA`
3. **CA Type:** Root CA
4. **Key Algorithm:** RSA 4096 (or ECDSA P-384)
5. **Validity:** 20 years
6. **Subject DN:** `CN=SentinelGrid Root CA, O=SentinelGrid, C=US`
7. Click **Create**

**⚠️ IMPORTANT:** Export Root CA certificate and private key for secure storage (production).

#### Step 2: Create Subordinate CA

1. Navigate to: **CA Functions → Create CA**
2. **CA Name:** `SentinelGrid-Issuing-CA`
3. **CA Type:** Sub CA
4. **Signed by:** `SentinelGrid-Root-CA`
5. **Key Algorithm:** RSA 2048 (or ECDSA P-256)
6. **Validity:** 10 years
7. **Subject DN:** `CN=SentinelGrid Issuing CA, O=SentinelGrid, C=US`
8. Click **Create**

#### Step 3: Create Certificate Profile

1. Navigate to: **Certificate Profiles → Add**
2. **Profile Name:** `service-tls`
3. **CA:** `SentinelGrid-Issuing-CA`
4. **Key Algorithm:** RSA 2048 or ECDSA P-256
5. **Validity:** 90 days (auto-renewal)
6. **Key Usage:** Digital Signature, Key Encipherment
7. **Extended Key Usage:** Server Authentication, Client Authentication
8. Click **Save**

#### Step 4: Enable REST API

1. Navigate to: **System Configuration → External RA**
2. Enable **REST API**
3. Configure authentication (Basic Auth with admin credentials)
4. Save configuration

### 4. Verify Setup

Test EJBCA REST API:
```bash
curl -k -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} https://localhost:8443/ejbca/ejbca-rest-api/v1/certificate/ca
```

Should return list of CAs.

---

## Configuration for SentinelGrid

### Environment Variables

Update `.env` or `docker-compose.dev.yml`:

```bash
# EJBCA Configuration
EJBCA_URL=https://ejbca:8443
EJBCA_USERNAME=admin
EJBCA_PASSWORD=admin  # Change in production!
EJBCA_CA_NAME=SentinelGrid-Issuing-CA
EJBCA_CERTIFICATE_PROFILE=service-tls
EJBCA_VERIFY_SSL=false  # true in production

# Certificate Service
CA_BACKEND_TYPE=ejbca  # Use EJBCA instead of step-ca
```

### Database Configuration

The `cert_service` will automatically create a default EJBCA CA authority in the database on first run.

---

## Production Setup

### 1. Secure Root CA Storage

**⚠️ CRITICAL:** Root CA private key must be stored securely:

1. **Export Root CA:**
   - Navigate to: **CA Functions → Manage CAs**
   - Select `SentinelGrid-Root-CA`
   - Export certificate and private key
   - Store in HSM or encrypted file

2. **Store in Vault:**
   ```bash
   vault kv put sentinelgrid/ejbca/root-ca \
     certificate=@root-ca.crt \
     private_key=@root-ca.key
   ```

3. **Take Root CA Offline:**
   - After creating Subordinate CA, remove Root CA from EJBCA
   - Store offline (air-gapped system)
   - Use only for CA signing ceremonies

### 2. Change Default Passwords

1. Change EJBCA admin password
2. Update in Vault: `vault kv put sentinelgrid/ejbca/admin-password value="<new-password>"`
3. Update environment variables

### 3. Enable HTTPS with Valid Certificate

1. Obtain SSL certificate for EJBCA hostname
2. Configure in EJBCA: **System Configuration → Network Configuration**
3. Set `EJBCA_VERIFY_SSL=true` in production

### 4. Configure Multi-Tenant CAs

For per-tenant CA isolation:

1. Create Subordinate CA per tenant: `SentinelGrid-Tenant-{tenant_id}-CA`
2. Store CA configuration in database with `tenant_id`
3. Certificate Service will select appropriate CA per tenant

---

## Troubleshooting

### EJBCA Won't Start

**Check logs:**
```bash
docker-compose logs ejbca
```

**Common issues:**
- Database not ready: Wait for `ejbca_db` to be healthy
- Port conflict: Check if 8443/8080 are in use
- Memory: Increase `JAVA_OPTS` if needed

### Cannot Authenticate

**Check credentials:**
```bash
curl -k -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} https://localhost:8443/ejbca/ejbca-rest-api/v1/certificate/ca
```

**Reset admin password:**
1. Access EJBCA Admin UI
2. Navigate to: **Administrators → Edit**
3. Change password
4. Update environment variables

### Certificate Issuance Fails

**Check EJBCA logs:**
```bash
docker-compose logs ejbca | grep -i error
```

**Common issues:**
- CA not found: Verify `EJBCA_CA_NAME` matches CA name in EJBCA
- Profile not found: Verify `EJBCA_CERTIFICATE_PROFILE` exists
- Invalid CSR: Check CSR format

### REST API Not Working

**Verify REST API is enabled:**
1. Navigate to: **System Configuration → External RA**
2. Ensure REST API is enabled
3. Check authentication settings

**Test API:**
```bash
curl -k -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} https://localhost:8443/ejbca/ejbca-rest-api/v1/certificate/ca
```

---

## Next Steps

After EJBCA is configured:

1. ✅ Test certificate issuance via API
2. ✅ Configure certificate profiles
3. ✅ Set up ACME endpoint (Phase 3)
4. ✅ Set up SCEP endpoint (Phase 3)
5. ✅ Configure multi-tenant CAs (Phase 2)

---

## References

- [EJBCA Documentation](https://doc.primekey.com/ejbca)
- [EJBCA REST API](https://doc.primekey.com/ejbca/ejbca-operations/ejbca-rest-api)
- [EJBCA Certificate Profiles](https://doc.primekey.com/ejbca/ejbca-operations/certificate-profiles)

---

**Last Updated:** 2025-01-28

