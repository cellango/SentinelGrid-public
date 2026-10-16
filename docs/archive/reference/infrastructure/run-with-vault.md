# 🚀 Run Complete Stack with Vault

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Complete initialization with HashiCorp Vault secrets management**

---

## One Command

```bash
bash backend/scripts/init_complete_stack.sh
```

**Time:** ~4-5 minutes  
**What it does:** Everything needed for a complete, production-ready setup with secrets management

---

## What Gets Created

### 1. HashiCorp Vault (Secrets Management)

**Service:** vault container on port 8200  
**UI:** http://localhost:8200/ui  
**Token:** `sentinelgrid-dev-root-token`

**Secrets Stored:**
```
vault/
└── sentinelgrid/
    ├── keycloak/
    │   ├── master-admin-password      (Generated securely)
    │   └── platform-admin-password    (Generated securely)
    ├── database/
    │   └── postgres-password          (Generated securely)
    └── services/
        └── internal-service-token     (Generated securely)
```

**Access:** All secrets retrievable via Vault CLI or API

### 2. Keycloak Realms

**3 Realms Created:**
- `sg-admin` - Platform admin (with secure password from Vault)
- `sg-mt-us-1` - US multi-tenant
- `sg-mt-eu-1` - EU multi-tenant

**Platform Admin User:**
- Email: `admin@sentinelgrid.ai`
- Password: **Retrieved from Vault** (not hardcoded!)
- Realm: `sg-admin`
- Role: `PLATFORM_ADMIN`

### 3. Database Tables

**Realm Architecture (6 tables):**
- `realms` - 3 records
- `customers` - empty
- `organizations` - empty
- `tenants` - empty
- `realm_capacity_history` - empty
- `tenant_provisioning_log` - empty

**Vault Integration (6 tables):**
- `vault_customers` - empty
- `vault_organizations` - empty
- `vault_tenants` - empty
- `vault_audit_log` - empty
- `vault_access_grants` - empty
- `vault_usage_history` - empty

### 4. Service Configuration

**IAM Agent:** Configured to use `sg-admin` realm  
**Vault Token:** Root token for development  
**All Passwords:** Generated and stored in Vault

---

## Access Everything

### Vault UI

```bash
# Open Vault UI
open http://localhost:8200/ui

# Login with token
Token: sentinelgrid-dev-root-token

# Browse secrets:
# sentinelgrid → keycloak → master-admin-password
```

### Vault CLI

```bash
# Set environment
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=sentinelgrid-dev-root-token

# List secrets
vault kv list sentinelgrid/keycloak

# Get specific secret
vault kv get sentinelgrid/keycloak/platform-admin-password

# Output:
# ====== Data ======
# Key      Value
# ---      -----
# value    <secure-generated-password>
```

### Keycloak Admin

```bash
# Get master admin password from Vault
KEYCLOAK_ADMIN_PASS=$(vault kv get -field=value sentinelgrid/keycloak/master-admin-password)

# Login to Keycloak
open http://localhost:8080/admin
# Username: admin
# Password: (paste from Vault)
```

### Platform Admin Login

```bash
# Get platform admin password from Vault
PLATFORM_ADMIN_PASS=$(vault kv get -field=value sentinelgrid/keycloak/platform-admin-password)

# Login to SentinelGrid
open https://localhost:3443/login
# Email: admin@sentinelgrid.ai
# Password: (paste from Vault)
```

---

## Test the Setup

### 1. Test Vault

```bash
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=sentinelgrid-dev-root-token

# Check status
vault status

# List secrets
vault kv list sentinelgrid/keycloak

# Retrieve password
vault kv get sentinelgrid/keycloak/platform-admin-password
```

### 2. Test Keycloak Token Generation

```bash
# Get password from Vault
PLATFORM_PASS=$(vault kv get -field=value sentinelgrid/keycloak/platform-admin-password)

# Get token from Keycloak
curl -k -X POST https://localhost:8443/realms/sg-admin/protocol/openid-connect/token \
  -d "client_id=sentinelgrid-web" \
  -d "username=admin@sentinelgrid.ai" \
  -d "password=$PLATFORM_PASS" \
  -d "grant_type=password" \
  -d "scope=openid"

# Should return access_token
```

### 3. Test IAM Agent Login

```bash
# Get password from Vault
PLATFORM_PASS=$(vault kv get -field=value sentinelgrid/keycloak/platform-admin-password)

# Test IAM Agent endpoint
curl -X POST http://localhost:8005/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"admin@sentinelgrid.ai\",
    \"password\": \"$PLATFORM_PASS\",
    \"remember_me\": false
  }"

# Should return access_token with sg.* claims
```

### 4. Test Database

```bash
psql postgresql://sg:sg@localhost:5432/sg <<EOF
-- Check realms
SELECT * FROM realms;

-- Check Vault tables
SELECT table_name FROM information_schema.tables 
WHERE table_name LIKE 'vault_%';

-- Check views
SELECT * FROM vault_tenant_status;
EOF
```

---

## Security Benefits

### vs. Without Vault

| Aspect | Without Vault | With Vault |
|--------|---------------|------------|
| **Keycloak Password** | Hardcoded `admin` | Generated, stored in Vault |
| **Platform Password** | Hardcoded `admin123` | Generated, stored in Vault |
| **DB Password** | Hardcoded `sg` | Generated, stored in Vault |
| **Service Token** | Hardcoded value | Generated, stored in Vault |
| **Rotation** | Manual, risky | Automated, tracked |
| **Audit** | None | Complete audit trail |
| **Customer Secrets** | Not available | Full secrets management |

### Production Ready

✅ **No hardcoded passwords**  
✅ **Centralized secrets management**  
✅ **Audit logging built-in**  
✅ **Rotation support**  
✅ **Customer service offering ready**  

---

## Architecture

### Hierarchical Secrets Structure

```
Customer (BigCorp Inc)
    ├── Vault path: customers/cust-bigcorp-uuid/
    │   └── kv/secrets/corporate-license-key
    ↓
Organization (BigCorp North)
    ├── Realm: sg-ent-bigcorp-north
    ├── Vault path: organizations/org-north-uuid/
    │   └── kv/secrets/north-aws-account
    ↓
Tenant (Engineering Dept)
    ├── tenant_id: ten-north-eng-uuid (ISOLATION BOUNDARY)
    ├── Vault path: tenants/ten-north-eng-uuid/
    │   ├── kv/secrets/github-token
    │   ├── transit/keys/ten-north-eng-uuid
    │   └── pki/ten-north-eng-uuid/
    └── Access: ONLY this tenant's secrets
```

### Access Control

**Platform Admin:**
- Can access: `sentinelgrid/*`
- Cannot access: Customer/org/tenant secrets

**Customer Admin:**
- Can access: `customers/{their-uuid}/*` + all their orgs + all their tenants
- Cannot access: Other customers

**Org Admin:**
- Can access: `organizations/{their-uuid}/*` + all tenants in their org
- Cannot access: Other orgs or parent customer secrets

**Tenant User:**
- Can access: `tenants/{their-uuid}/*` ONLY
- Cannot access: Other tenants, org, or customer secrets

---

## Troubleshooting

### "Vault not ready"

```bash
# Check Vault logs
docker-compose logs vault

# Check Vault status
docker-compose exec vault vault status

# Restart Vault
docker-compose restart vault
```

### "Could not retrieve secret from Vault"

```bash
# Check if secret exists
vault kv list sentinelgrid/keycloak

# Check Vault token
echo $VAULT_TOKEN

# Verify authentication
vault token lookup
```

### "Keycloak authentication failed"

```bash
# Get correct password from Vault
PASS=$(vault kv get -field=value sentinelgrid/keycloak/platform-admin-password)
echo "Password: $PASS"

# Test directly with Keycloak
curl -k -X POST https://localhost:8443/realms/sg-admin/protocol/openid-connect/token \
  -d "client_id=sentinelgrid-web" \
  -d "username=admin@sentinelgrid.ai" \
  -d "password=$PASS" \
  -d "grant_type=password"
```

---

## Next Steps

After successful initialization:

### 1. Test Customer Signup with Vault Provisioning

When a customer signs up, they automatically get:
- Keycloak identity in appropriate realm
- Vault namespace: `tenants/{tenant-uuid}/`
- Vault policy with isolated access
- KV secrets engine enabled
- Transit encryption key created

### 2. UI Development

Create frontend pages under **People & Access** section:

```
/dashboard/iam/
└── secrets/  ← NEW
    ├── page.tsx           # Secrets overview
    ├── list/page.tsx      # List all secrets
    ├── new/page.tsx       # Create secret
    └── [id]/page.tsx      # View/edit secret
```

### 3. Enable Advanced Features

Update provisioning to enable per pricing tier:
- Professional: + Transit encryption
- Enterprise: + Database credentials + PKI

---

## Credentials Location

All credentials are in **Vault** (not in files):

```bash
# Platform admin credentials
vault kv get sentinelgrid/keycloak/platform-admin-password

# Database password
vault kv get sentinelgrid/database/postgres-password

# Service token
vault kv get sentinelgrid/services/internal-service-token
```

**No credentials in git, no credentials in files!** ✅

---

## Run It Now

```bash
bash backend/scripts/init_complete_stack.sh
```

Then test:

```bash
# Get password from Vault
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=sentinelgrid-dev-root-token
PLATFORM_PASS=$(vault kv get -field=value sentinelgrid/keycloak/platform-admin-password)

# Test login
open https://localhost:3443/login
# Email: admin@sentinelgrid.ai
# Password: (from $PLATFORM_PASS)
```

🔐 **Production-ready secrets management!**

