# Platform Administrator Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**SentinelGrid Platform Administration - Complete Reference**

---

## Table of Contents

1. [Overview](#overview)
2. [Initial Setup](#initial-setup)
3. [Vault Secrets Management](#vault-secrets-management)
4. [Keycloak Realm Management](#keycloak-realm-management)
5. [Database Management](#database-management)
6. [Security & Access Control](#security--access-control)
7. [Troubleshooting](#troubleshooting)
8. [Emergency Procedures](#emergency-procedures)

---

## Overview

### What is a Platform Administrator?

Platform Administrators have **full access** to the SentinelGrid infrastructure:

- ✅ Vault secrets management
- ✅ Keycloak realm configuration
- ✅ Database schema and data
- ✅ Service configuration
- ✅ User and tenant management
- ✅ Security policies

### Platform Admin Account

**Default Account:**
- **Email:** `admin@sentinelgrid.ai`
- **Realm:** `sg-admin`
- **Role:** `PLATFORM_ADMIN`
- **Password:** Stored in Vault (see [Vault Secrets Management](#vault-secrets-management))

**Access:**
- Dashboard: `https://localhost:3443/login`
- Keycloak Admin: `http://localhost:8080/admin`
- Vault UI: `http://localhost:8200/ui`

---

## Initial Setup

### Complete Stack Initialization

**Purpose:** First-time production setup or complete reset of development environment

**⚠️ DESTRUCTIVE OPERATION - DELETES ALL DATA**

#### What It Does

The `init_complete_stack.sh` script performs a complete reset and initialization:

1. **Optional Backup (Before Deletion):**
   - Prompts user to create backup
   - Backs up Keycloak realms, Vault secrets, database, volumes
   - **Note:** Backup functionality is currently stubbed (see Backup Implementation)

2. **Destroys all existing data:**
   - All Keycloak realms, users, clients
   - All Vault secrets, policies
   - All database tables (customers, organizations, tenants, vault_*)

3. **Creates fresh infrastructure:**
   - Initializes Vault with secure secrets
   - Creates Keycloak realms (sg-admin, sg-mt-us-1, sg-mt-eu-1)
   - Runs database migrations
   - Seeds platform admin user
   - Configures service accounts

#### When to Use

**✅ Safe to Use:**
- First-time production setup (ONCE)
- Development environment reset
- Testing infrastructure changes

**❌ Never Use:**
- Production after initial setup (will delete all customer data)
- Without understanding consequences

#### Safety Features

**5 Layers of Protection:**

1. **Header Documentation** - Clear warnings in script
2. **Production Detection** - Extra confirmation in production
3. **Detailed Warning Banner** - Explains what will be deleted
4. **Explicit Confirmation** - Must type "DELETE ALL DATA"
5. **Final Countdown** - 10 seconds to cancel

#### Running the Script

**Development:**
```bash
bash backend/scripts/init_complete_stack.sh
```

**Production (First-Time Only):**
```bash
ENVIRONMENT=production bash backend/scripts/init_complete_stack.sh
```

**Confirmation Prompts:**
1. **Production Detection** (if production): Type `"I UNDERSTAND THIS WILL DELETE ALL PRODUCTION DATA"`
2. **Main Confirmation**: Type `"DELETE ALL DATA"`
3. **Backup Prompt**: Answer `y` to create backup, or `N` to skip
4. **Final Countdown**: 10-second countdown (Ctrl+C to cancel)

**Backup Option:**
- Script will ask: `Create backup before deletion? [y/N]:`
- If `y`: Creates backup in `backups/YYYYMMDD_HHMMSS/`
- **Note:** Backup functionality is currently stubbed (structure only)
- See `backend/scripts/BACKUP_IMPLEMENTATION.md` for implementation details

**See:** [Complete Stack Initialization Details](#complete-stack-initialization-details)

---

## Vault Secrets Management

### Overview

HashiCorp Vault stores all sensitive credentials and secrets:

- Keycloak master admin password
- Platform admin password
- Database passwords
- Service account tokens
- Customer secrets (future)

### Vault Root Token Security

**⚠️ CRITICAL: Root Token is Company Top Secret**

#### Current Location (Development)

**Hardcoded in 3 files (DEVELOPMENT ONLY):**
- `docker-compose.dev.yml` - Default: `sentinelgrid-dev-root-token`
- `backend/scripts/init_vault.sh` - Default: `sentinelgrid-dev-root-token`
- `backend/scripts/init_complete_stack.sh` - Default: `sentinelgrid-dev-root-token`

**⚠️ This is INSECURE for production!**

#### Generating Secure Root Token

**For Production:**
```bash
bash backend/scripts/generate_vault_root_token.sh
```

**This generates:**
- 256-bit cryptographically secure token
- 64 hex characters
- Suitable for production use

#### Storing Root Token Securely

**✅ Secure Options (Ranked):**

1. **AWS Secrets Manager** (Recommended)
   ```bash
   aws secretsmanager create-secret \
     --name sentinelgrid/vault/root-token \
     --secret-string "<generated-token>" \
     --description "Vault root token for SentinelGrid production"
   ```

2. **Password Manager** (1Password, Bitwarden)
   - Create item: "Vault Root Token"
   - Share with authorized personnel only

3. **Encrypted File** (GPG/Age)
   ```bash
   echo "<token>" | gpg --encrypt --recipient security@sentinelgrid.ai > vault-root-token.gpg
   ```

4. **Environment File** (`.env.production` - gitignored)
   ```bash
   echo "VAULT_ROOT_TOKEN=<token>" >> .env.production
   ```

**❌ NEVER:**
- Commit to git
- Share via email/Slack
- Store in plain text
- Hardcode in source code

#### Accessing Vault

**Vault UI:**
```bash
open http://localhost:8200/ui
# Token: <root-token>
```

**Vault CLI:**
```bash
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=<root-token>
vault status
```

**See:** [Vault Root Token Security Details](#vault-root-token-security-details)

### Retrieving Secrets

**Keycloak Master Admin Password:**
```bash
vault kv get sentinelgrid/keycloak/master-admin-password
```

**Platform Admin Password:**
```bash
vault kv get sentinelgrid/keycloak/platform-admin-password
```

**Database Password:**
```bash
vault kv get sentinelgrid/database/postgres-password
```

**Service Token:**
```bash
vault kv get sentinelgrid/services/internal-service-token
```

### Secret Structure

```
vault/
└── sentinelgrid/
    ├── keycloak/
    │   ├── master-admin-password
    │   └── platform-admin-password
    ├── database/
    │   └── postgres-password
    └── services/
        └── internal-service-token
```

### Production Vault Credentials Management

**⚠️ CRITICAL: Production Vault Credentials Must Be Stored Securely**

Production Vault uses persistent storage and TLS encryption. The root token and unseal key must be stored in a **physical vault or safe** for disaster recovery.

#### Exporting Credentials for Physical Storage

**Export Script:**
```bash
./scripts/export_vault_credentials.sh
```

This script:
- Extracts root token and unseal key from the production Vault container
- Creates a formatted credentials document (`vault-credentials-secure.txt`)
- Includes usage instructions and security notes
- Sets secure file permissions (600 - owner read/write only)

**Output File:**
- Location: `vault-credentials-secure.txt` (project root)
- **⚠️ NEVER commit to git** (already in `.gitignore`)
- Contains:
  - Root Token (full administrative access)
  - Unseal Key (required after container restarts)
  - Vault access information
  - Usage instructions
  - Security best practices

#### Physical Storage Procedure

**1. Export Credentials:**
```bash
./scripts/export_vault_credentials.sh
```

**2. Print the Document:**
```bash
# Print to default printer
cat vault-credentials-secure.txt | lpr

# Or open and print manually
open vault-credentials-secure.txt
```

**3. Store Securely:**
- Place printed document in company physical safe/vault
- Consider splitting root token and unseal key into separate documents
- Store in multiple secure locations (primary + backup)
- Limit access to authorized personnel only

**4. Delete Digital File:**
```bash
# After printing and verifying storage
rm vault-credentials-secure.txt
```

#### Accessing Production Vault

**From Host Machine:**
```bash
export VAULT_ADDR=https://localhost:8210
export VAULT_SKIP_VERIFY=true  # For self-signed certificates
export VAULT_TOKEN=$(docker exec vault-prod cat /vault/file/.vault_root_token)
vault status
```

**If Vault is Sealed (after restart):**
```bash
# Get unseal key from physical storage, then:
UNSEAL_KEY="<from-physical-vault>"
docker exec vault-prod sh -c "export VAULT_ADDR=https://127.0.0.1:8200 && export VAULT_SKIP_VERIFY=true && vault operator unseal $UNSEAL_KEY"
```

#### Production Vault Details

**Access Information:**
- **Address:** `https://localhost:8210`
- **TLS:** Enabled (self-signed certificates)
- **Container:** `vault-prod` (separate from dev Vault on port 8200)
- **Storage:** Persistent Docker volume (`vault_prod_data`)
- **Auto-unseal:** Configured (unseals on container restart)

**Secrets Engines Enabled:**
- `sentinelgrid/` - KV v2 (application secrets)
- `transit/` - Encryption service
- `database/` - Dynamic database credentials

**See:** `infra/vault/README_PROD.md` for complete production Vault documentation

---

## Keycloak Realm Management

### Realm Architecture

**3 Realms Created:**

1. **`sg-admin`** - Platform administration
   - Purpose: Platform admin users
   - Strategy: Dedicated
   - Capacity: N/A

2. **`sg-mt-us-1`** - US multi-tenant
   - Purpose: US customer tenants
   - Strategy: Multi-tenant
   - Capacity: 1000 tenants
   - Region: US

3. **`sg-mt-eu-1`** - EU multi-tenant
   - Purpose: EU customer tenants
   - Strategy: Multi-tenant
   - Capacity: 1000 tenants
   - Region: EU

### Platform Admin User

**Account Details:**
- **Email:** `admin@sentinelgrid.ai`
- **Realm:** `sg-admin`
- **Role:** `PLATFORM_ADMIN`
- **Password:** Retrieved from Vault

**Access:**
- Dashboard: `https://localhost:3443/login`
- Keycloak Admin: `http://localhost:8080/admin`

**Login:**
```bash
# Get password from Vault
PLATFORM_PASS=$(vault kv get -field=value sentinelgrid/keycloak/platform-admin-password)

# Login at https://localhost:3443/login
# Email: admin@sentinelgrid.ai
# Password: <from Vault>
```

### Service Accounts

**`sentinelgrid-platform-api`:**
- Realm: `sg-admin`
- Purpose: Platform API operations
- Secret: Retrieve from Keycloak Admin Console

**`sentinelgrid-iam-agent`:**
- Realms: `sg-admin`, `sg-mt-us-1`, `sg-mt-eu-1`
- Purpose: IAM Agent operations
- Secret: Retrieve from Keycloak Admin Console

### Token Structure

**JWT Claims (sg.* namespace):**
- `sg.tenant_id` - Tenant UUID
- `sg.tenant_slug` - Tenant slug
- `sg.org_id` - Organization UUID
- `sg.customer_id` - Customer UUID
- `sg.realm_name` - Realm name
- `sg.pricing_tier` - Pricing tier

**Client Scope:** `sentinelgrid-tenant` (attached to all clients)

---

## Database Management

### Schema Overview

**Realm Architecture Tables (6):**
- `realms` - Realm metadata
- `customers` - Customer billing entities
- `organizations` - Organizations (realm assignment level)
- `tenants` - Tenants (isolation boundary)
- `realm_capacity_history` - Capacity audit trail
- `tenant_provisioning_log` - Provisioning audit trail

**Vault Integration Tables (6):**
- `vault_customers` - Customer Vault namespaces
- `vault_organizations` - Organization Vault namespaces
- `vault_tenants` - Tenant Vault namespaces
- `vault_access_grants` - Vault access permissions
- `vault_audit_log` - Vault operation logs
- `vault_usage_history` - Vault usage tracking

### Migrations

**Migration Files:**
- `002_realm_architecture.sql` - Realm architecture schema
- `003_vault_integration.sql` - Vault integration schema

**Running Migrations:**
```bash
psql postgresql://sg:sg@localhost:5432/sg -f backend/migrations/002_realm_architecture.sql
psql postgresql://sg:sg@localhost:5432/sg -f backend/migrations/003_vault_integration.sql
```

### Database Access

**Connection String:**
```bash
postgresql://sg:sg@localhost:5432/sg
```

**Password:** Retrieved from Vault
```bash
vault kv get sentinelgrid/database/postgres-password
```

---

## Security & Access Control

### Production Security Checklist

**Before Production Deployment:**

- [ ] Vault root token generated securely (256-bit random)
- [ ] Vault root token stored in secure location (NOT in code)
- [ ] Vault root token NOT in git
- [ ] Vault root token shared only with authorized personnel
- [ ] Vault audit logging enabled
- [ ] Root token usage monitored
- [ ] Root token rotation schedule defined (quarterly)
- [ ] Keycloak master admin password changed from default
- [ ] Platform admin password from Vault (not hardcoded)
- [ ] All service accounts configured
- [ ] Database passwords from Vault
- [ ] HTTPS enabled for all services
- [ ] Production Vault NOT in dev mode
- [ ] Unseal keys stored securely (Shamir's Secret Sharing)
- [ ] Access control policies configured
- [ ] Audit logging enabled for all systems

**See:** [Production Security Checklist Details](#production-security-checklist-details)

### Access Control

**Who Should Have Root Token Access:**

- CTO / Head of Engineering
- Security Lead
- DevOps Lead
- On-call Engineer (temporary, for emergencies)

**Access Requirements:**
- Background check completed
- Security training completed
- Signed NDA
- Access logged and audited

### Token Rotation

**When to Rotate:**
- Quarterly (every 3 months)
- After security incident
- After employee departure (if they had access)
- After suspected compromise

**How to Rotate:**
```bash
# 1. Generate new token
bash backend/scripts/generate_vault_root_token.sh

# 2. Update in secure storage
# (AWS Secrets Manager, password manager, etc.)

# 3. Update all systems
# (Restart services, update CI/CD, etc.)

# 4. Revoke old token
vault token revoke <old-token>
```

---

## Troubleshooting

### Vault Issues

**"Vault not ready":**
```bash
# Check Vault logs
docker-compose logs vault

# Check Vault status
docker-compose exec vault vault status

# Restart Vault
docker-compose restart vault
```

**"Could not retrieve secret from Vault":**
```bash
# Check if secret exists
vault kv list sentinelgrid/keycloak

# Check Vault token
echo $VAULT_TOKEN

# Verify authentication
vault token lookup
```

### Keycloak Issues

**"Keycloak authentication failed":**
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

**"Keycloak failed to start":**
```bash
# Check Keycloak logs
docker-compose logs keycloak

# Check database connection
docker-compose exec keycloak_db psql -U keycloak -d keycloak -c "SELECT 1"

# Increase wait time in init script
# (Edit MAX_RETRIES in init_complete_stack.sh)
```

### Database Issues

**"Migration failed":**
```bash
# Check database connection
psql postgresql://sg:sg@localhost:5432/sg -c "SELECT 1"

# Manually run migrations
psql postgresql://sg:sg@localhost:5432/sg -f backend/migrations/002_realm_architecture.sql
psql postgresql://sg:sg@localhost:5432/sg -f backend/migrations/003_vault_integration.sql

# Check tables
psql postgresql://sg:sg@localhost:5432/sg -c "\dt"
```

---

## Emergency Procedures

### If Root Token is Compromised

1. **Immediately Revoke Token:**
   ```bash
   vault token revoke <compromised-token>
   ```

2. **Generate New Root Token:**
   ```bash
   bash backend/scripts/generate_vault_root_token.sh
   ```

3. **Update All Systems:**
   - Update `.env.production`
   - Update AWS Secrets Manager
   - Update all scripts/services using token

4. **Audit All Access:**
   ```bash
   # Check audit logs for unauthorized access
   grep <compromised-token> /vault/logs/audit.log
   ```

5. **Notify Security Team:**
   - Document incident
   - Review access logs
   - Update security procedures

### If Platform Admin Account is Compromised

1. **Reset Password:**
   ```bash
   # Generate new password
   NEW_PASS=$(openssl rand -base64 24)
   
   # Store in Vault
   vault kv put sentinelgrid/keycloak/platform-admin-password value="$NEW_PASS"
   
   # Update in Keycloak
   # (Use Keycloak Admin Console or API)
   ```

2. **Review Access Logs:**
   ```bash
   # Check Keycloak audit logs
   # Check Vault audit logs
   # Check application logs
   ```

3. **Notify Security Team:**
   - Document incident
   - Review all changes made
   - Update access controls

---

## Detailed Sections

### Complete Stack Initialization Details

**Script:** `backend/scripts/init_complete_stack.sh`

**8 Phases:**

1. **Reset Infrastructure** - Stops services, deletes volumes, drops tables
2. **Start Services** - Starts Vault and Keycloak containers
3. **Initialize Vault** - Enables engines, creates policies, generates secrets
4. **Wait for Keycloak** - Polls health endpoint (60-90 seconds)
5. **Run Database Migrations** - Creates schema (realms + vault)
6. **Seed Keycloak Realms** - Creates realms, users, clients, roles
7. **Restart IAM Agent** - Refreshes Keycloak connection
8. **Verification** - Checks Vault, database, Keycloak

**See:** `EXPLAIN_INIT_COMPLETE_STACK.md` for complete details

### Vault Root Token Security Details

**Current Status:**
- Development: Hardcoded `sentinelgrid-dev-root-token` (acceptable)
- Production: **MUST be generated and stored securely**

**Security Requirements:**
- 256-bit random token (64 hex characters)
- Stored in secure location (AWS Secrets Manager, encrypted file, etc.)
- NOT in source code or git
- Shared only with authorized personnel
- Rotated quarterly
- Access logged and monitored

**See:** `VAULT_ROOT_TOKEN_SECURITY.md` for complete details

### Production Security Checklist Details

**Pre-Production Checklist:**

**Vault:**
- [ ] Root token generated securely
- [ ] Root token stored securely
- [ ] Root token and unseal key exported for physical storage
- [ ] Credentials document printed and stored in physical safe
- [ ] Digital credentials file deleted after printing
- [ ] Audit logging enabled
- [ ] Production mode (not dev mode)
- [ ] TLS/HTTPS enabled
- [ ] Unseal keys stored securely in physical vault

**Keycloak:**
- [ ] Master admin password changed
- [ ] Platform admin password from Vault
- [ ] Service accounts configured
- [ ] HTTPS enabled
- [ ] Audit logging enabled

**Database:**
- [ ] Passwords from Vault
- [ ] Encrypted connections
- [ ] Backup configured
- [ ] Access restricted

**See:** `docs/archive/reference/platform/production-security-checklist.md` for complete checklist

---

## Quick Reference

### Common Commands

**Vault:**
```bash
# Get platform admin password
vault kv get sentinelgrid/keycloak/platform-admin-password

# List all secrets
vault kv list sentinelgrid/keycloak

# Check status
vault status
```

**Keycloak:**
```bash
# Get token
curl -k -X POST https://localhost:8443/realms/sg-admin/protocol/openid-connect/token \
  -d "client_id=sentinelgrid-web" \
  -d "username=admin@sentinelgrid.ai" \
  -d "password=<from-vault>" \
  -d "grant_type=password"
```

**Database:**
```bash
# Check realms
psql postgresql://sg:sg@localhost:5432/sg -c "SELECT * FROM realms"

# Check Vault tables
psql postgresql://sg:sg@localhost:5432/sg -c "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'vault_%'"
```

### File Locations

**Scripts:**
- `backend/scripts/init_complete_stack.sh` - Complete stack initialization
- `backend/scripts/init_vault.sh` - Vault initialization (dev)
- `backend/scripts/init_vault_prod.sh` - Production Vault initialization
- `backend/scripts/generate_vault_root_token.sh` - Token generation
- `scripts/export_vault_credentials.sh` - Export credentials for physical storage
- `backend/scripts/seed_realms.py` - Realm seeding

**Configuration:**
- `docker-compose.dev.yml` - Docker Compose configuration
- `infra/vault/config/vault.hcl` - Vault configuration
- `infra/vault/policies/*.hcl` - Vault policies

**Migrations:**
- `backend/migrations/002_realm_architecture.sql` - Realm schema
- `backend/migrations/003_vault_integration.sql` - Vault schema

---

## Detailed Reference Sections

### Complete Stack Initialization

**Location:** `../EXPLAIN_INIT_COMPLETE_STACK.md`

**Contents:**
- Detailed step-by-step explanation of `init_complete_stack.sh`
- What each phase does
- What gets created
- Troubleshooting guide

### Vault Root Token Security

**Location:** `../VAULT_ROOT_TOKEN_SECURITY.md`

**Contents:**
- Current security issues
- Production security requirements
- Secure implementation plan
- Token rotation procedures
- Emergency procedures

### Vault Password Location

**Location:** `../WHERE_IS_THE_VAULT_PASSWORD.md`

**Contents:**
- Where root token is currently stored
- How to generate secure token
- Secure storage options
- Quick reference

### Safety Features

**Location:** `../SAFETY_FEATURES_INIT_SCRIPT.md`

**Contents:**
- 5 layers of protection
- Production environment detection
- Confirmation mechanisms
- Emergency stop procedures

### Production Security Checklist

**Location:** `docs/archive/reference/platform/production-security-checklist.md`

**Contents:**
- Pre-production security checklist
- Keycloak security
- Vault security
- Database security
- Network security

### Realm Architecture

**Location:** `docs/archive/reference/identity/realm-architecture-implementation.md`

**Contents:**
- Realm architecture design
- Multi-tenant strategy
- Token structure
- Provisioning flow

---

## Related Documentation

**Quick References:**
- `../QUICK_REFERENCE_INIT_SCRIPT.md` - Quick command reference
- `../RUN_WITH_VAULT.md` - How to run with Vault
- `../RUN_THIS_NOW.md` - Quick start guide

**Architecture:**
- `docs/realms.md` - Original realm design
- `docs/archive/reference/identity/realm-architecture-implementation.md` - Implementation details
- `../UNIFIED_HIERARCHY_ARCHITECTURE.md` - Hierarchy model

---

**Last Updated:** December 6, 2025  
**Maintained By:** Platform Engineering Team  
**Version:** 1.1

