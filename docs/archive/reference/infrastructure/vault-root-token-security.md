# 🔐 Vault Root Token Security - CRITICAL

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Status:** ⚠️ **CURRENTLY INSECURE - MUST BE FIXED FOR PRODUCTION**

---

## 🚨 Current Security Issue

### Where the Root Token is Currently Stored

**⚠️ HARDCODED IN MULTIPLE FILES (INSECURE):**

1. **`docker-compose.dev.yml` (Lines 766, 775)**
   ```yaml
   environment:
     - VAULT_DEV_ROOT_TOKEN_ID=${VAULT_ROOT_TOKEN:-sentinelgrid-dev-root-token}
   command: server -dev -dev-root-token-id=${VAULT_ROOT_TOKEN:-sentinelgrid-dev-root-token}
   ```
   - **Default:** `sentinelgrid-dev-root-token` (hardcoded)
   - **Override:** Can set `VAULT_ROOT_TOKEN` environment variable

2. **`backend/scripts/init_vault.sh` (Line 25)**
   ```bash
   VAULT_TOKEN="${VAULT_TOKEN:-sentinelgrid-dev-root-token}"
   ```
   - **Default:** `sentinelgrid-dev-root-token` (hardcoded)
   - **Override:** Can set `VAULT_TOKEN` environment variable

3. **`backend/scripts/init_complete_stack.sh` (Line 53)**
   ```bash
   VAULT_TOKEN="${VAULT_TOKEN:-sentinelgrid-dev-root-token}"
   ```
   - **Default:** `sentinelgrid-dev-root-token` (hardcoded)
   - **Override:** Can set `VAULT_TOKEN` environment variable

### Security Problems

❌ **Root token is hardcoded in source code**  
❌ **Root token is visible in git history**  
❌ **Root token is predictable (`sentinelgrid-dev-root-token`)**  
❌ **Root token has unlimited access to ALL secrets**  
❌ **No rotation mechanism**  
❌ **No access logging for root token usage**

---

## 🔒 Production Security Requirements

### 1. Root Token Must NOT Be in Code

**❌ NEVER DO THIS:**
```yaml
# docker-compose.yml
VAULT_DEV_ROOT_TOKEN_ID: "hardcoded-token-here"  # ❌ NEVER
```

**✅ DO THIS:**
```yaml
# docker-compose.yml
VAULT_DEV_ROOT_TOKEN_ID: ${VAULT_ROOT_TOKEN}  # ✅ From environment
```

**And set in secure location:**
```bash
# .env.production (NOT in git)
VAULT_ROOT_TOKEN=$(openssl rand -hex 32)  # Generated securely
```

---

### 2. Root Token Must Be Generated Securely

**Generate cryptographically secure token:**
```bash
# Generate 256-bit random token (64 hex characters)
VAULT_ROOT_TOKEN=$(openssl rand -hex 32)

# Or use Vault's built-in generation
vault operator generate-root -init
```

**Store securely:**
- ✅ Environment variable (`.env.production` - gitignored)
- ✅ Secret management system (AWS Secrets Manager, HashiCorp Vault, etc.)
- ✅ Encrypted file (GPG, age, etc.)
- ❌ NOT in source code
- ❌ NOT in git
- ❌ NOT in plain text files

---

### 3. Root Token Must Be Rotated

**Vault Root Token Rotation:**
```bash
# 1. Generate new root token
vault operator generate-root -init

# 2. Provide unseal keys (requires quorum)
vault operator generate-root

# 3. Revoke old root token
vault token revoke <old-root-token>

# 4. Update in secure storage
# Update VAULT_ROOT_TOKEN in .env.production
```

**Rotation Schedule:**
- ✅ **Quarterly** (every 3 months)
- ✅ **After security incident**
- ✅ **After employee departure** (if they had access)
- ✅ **After suspected compromise**

---

### 4. Root Token Access Must Be Logged

**Enable Vault Audit Logging:**
```hcl
# vault.hcl
audit_device "file" {
  path = "file"
  file_path = "/vault/logs/audit.log"
  log_raw = true
  log_requests = true
  log_response = true
}
```

**Monitor root token usage:**
```bash
# Check audit logs for root token usage
grep "root" /vault/logs/audit.log | jq '.request.path'

# Alert on root token usage (should be rare)
```

---

## 🛡️ Secure Implementation Plan

### Phase 1: Development (Current - Acceptable)

**Status:** ⚠️ Acceptable for development only

**Current Setup:**
- Hardcoded token: `sentinelgrid-dev-root-token`
- Dev mode Vault (auto-unsealed)
- No production data

**Why Acceptable:**
- Development environment only
- No real secrets
- Can be reset anytime
- Isolated from production

**Action Required:** None for development

---

### Phase 2: Production Setup (MUST IMPLEMENT)

**Status:** ❌ **NOT READY - MUST BE FIXED**

#### Step 1: Generate Secure Root Token

**Create secure token generation script:**

**File:** `backend/scripts/generate_vault_root_token.sh`
```bash
#!/bin/bash
# Generate secure Vault root token for production

set -e

# Generate 256-bit random token
ROOT_TOKEN=$(openssl rand -hex 32)

echo "🔐 Generated Vault Root Token:"
echo "$ROOT_TOKEN"
echo ""
echo "⚠️  SECURITY: Store this token securely:"
echo "  1. Add to .env.production (gitignored)"
echo "  2. Store in AWS Secrets Manager"
echo "  3. Store in encrypted password manager"
echo "  4. Share with authorized personnel only"
echo ""
echo "⚠️  DO NOT:"
echo "  ❌ Commit to git"
echo "  ❌ Share via email/Slack"
echo "  ❌ Store in plain text"
echo ""
echo "✅ Token generated. Store securely before proceeding."
```

**Usage:**
```bash
bash backend/scripts/generate_vault_root_token.sh > .env.production
```

#### Step 2: Store Token Securely

**Option A: Environment File (Gitignored)**

**File:** `.env.production` (NOT in git)
```bash
# Vault Configuration
VAULT_ADDR=https://vault.sentinelgrid.ai:8200
VAULT_ROOT_TOKEN=<generated-secure-token-here>
VAULT_TOKEN=$VAULT_ROOT_TOKEN

# Keycloak Configuration
KEYCLOAK_URL=https://keycloak.sentinelgrid.ai:8443
KEYCLOAK_ADMIN_PASSWORD=<from-vault>
```

**Verify gitignored:**
```bash
# Check .gitignore
grep -E "\.env\.production|\.env$" .gitignore

# Verify not tracked
git check-ignore .env.production
```

**Option B: AWS Secrets Manager**

```bash
# Store root token
aws secretsmanager create-secret \
  --name sentinelgrid/vault/root-token \
  --secret-string "$ROOT_TOKEN" \
  --description "Vault root token for SentinelGrid production"

# Retrieve in scripts
VAULT_ROOT_TOKEN=$(aws secretsmanager get-secret-value \
  --secret-id sentinelgrid/vault/root-token \
  --query SecretString --output text)
```

**Option C: HashiCorp Vault (Meta-Vault)**

```bash
# Store in separate Vault instance (meta-vault)
vault kv put secret/sentinelgrid/vault-root-token \
  value="$ROOT_TOKEN"
```

#### Step 3: Update Scripts to Use Environment Variable

**File:** `docker-compose.prod.yml`
```yaml
vault:
  environment:
    - VAULT_DEV_ROOT_TOKEN_ID=${VAULT_ROOT_TOKEN}  # ✅ From env, no default
  command: server -dev -dev-root-token-id=${VAULT_ROOT_TOKEN}
```

**File:** `backend/scripts/init_vault.sh`
```bash
# Require VAULT_TOKEN to be set (no default)
if [ -z "$VAULT_TOKEN" ]; then
    echo "❌ ERROR: VAULT_TOKEN must be set"
    echo "   Set in .env.production or export VAULT_TOKEN=<token>"
    exit 1
fi

export VAULT_TOKEN
```

**File:** `backend/scripts/init_complete_stack.sh`
```bash
# Require VAULT_TOKEN to be set (no default)
if [ -z "$VAULT_TOKEN" ]; then
    echo "❌ ERROR: VAULT_TOKEN must be set"
    echo "   This script requires a secure Vault root token"
    echo "   Set in .env.production or export VAULT_TOKEN=<token>"
    exit 1
fi

export VAULT_TOKEN
```

#### Step 4: Production Vault Configuration

**File:** `infra/vault/config/vault.hcl` (Production)
```hcl
storage "file" {
  path = "/vault/file"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_cert_file = "/vault/certs/vault.crt"
  tls_key_file = "/vault/certs/vault.key"
}

# Enable audit logging
audit_device "file" {
  path = "file"
  file_path = "/vault/logs/audit.log"
  log_raw = true
  log_requests = true
  log_response = true
}

# Disable dev mode (production)
# No VAULT_DEV_ROOT_TOKEN_ID in production
```

**Unsealing (Production):**
```bash
# Initialize Vault (first time only)
vault operator init -key-shares=5 -key-threshold=3

# Store unseal keys securely (Shamir's Secret Sharing)
# Distribute to 5 authorized personnel
# Require 3 to unseal

# Unseal Vault (requires 3 keys)
vault operator unseal <unseal-key-1>
vault operator unseal <unseal-key-2>
vault operator unseal <unseal-key-3>
```

---

## 📋 Security Checklist

### Development Environment

- [x] Hardcoded token acceptable (dev only)
- [x] Dev mode Vault (auto-unsealed)
- [x] No production data
- [x] Can be reset anytime

### Production Environment

- [ ] Root token generated securely (256-bit random)
- [ ] Root token stored in secure location (NOT in code)
- [ ] Root token NOT in git
- [ ] Root token shared only with authorized personnel
- [ ] Vault audit logging enabled
- [ ] Root token usage monitored
- [ ] Root token rotation schedule defined
- [ ] Unseal keys stored securely (Shamir's Secret Sharing)
- [ ] Unseal keys distributed to authorized personnel
- [ ] Production Vault uses TLS/HTTPS
- [ ] Production Vault NOT in dev mode
- [ ] Root token access requires approval workflow

---

## 🔐 Where to Store Root Token (Production)

### ✅ Secure Options (Ranked)

1. **AWS Secrets Manager** (Recommended)
   - Encrypted at rest
   - Access via IAM
   - Audit logging
   - Automatic rotation support

2. **HashiCorp Vault (Meta-Vault)**
   - Separate Vault instance
   - Encrypted storage
   - Access control
   - Audit logging

3. **Encrypted File (GPG/Age)**
   - GPG encrypted file
   - Age encrypted file
   - Stored in secure location
   - Requires key to decrypt

4. **Password Manager (1Password, Bitwarden)**
   - Encrypted storage
   - Access control
   - Audit logging
   - Easy sharing with team

### ❌ Insecure Options (NEVER USE)

1. **Source Code** ❌
   - Visible in git
   - Accessible to all developers
   - Cannot rotate easily

2. **Plain Text File** ❌
   - No encryption
   - Accessible to anyone with file access
   - No audit trail

3. **Environment Variable in CI/CD** ❌
   - May be logged
   - Accessible to CI/CD users
   - Hard to rotate

4. **Email/Slack** ❌
   - Not encrypted
   - Accessible to email admins
   - No audit trail

---

## 🚨 Emergency Procedures

### If Root Token is Compromised

1. **Immediately Revoke Token:**
   ```bash
   vault token revoke <compromised-token>
   ```

2. **Generate New Root Token:**
   ```bash
   vault operator generate-root -init
   # Provide unseal keys
   vault operator generate-root
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

---

## 📚 Related Documentation

- `PRODUCTION_SECURITY_CHECKLIST.md` - Complete security checklist
- `EXPLAIN_INIT_COMPLETE_STACK.md` - How initialization works
- `SAFETY_FEATURES_INIT_SCRIPT.md` - Safety mechanisms

---

## ✅ Summary

**Current Status:**
- ⚠️ Development: Acceptable (hardcoded token)
- ❌ Production: **NOT READY** (must implement secure storage)

**Action Required:**
1. Generate secure root token (256-bit random)
2. Store in secure location (AWS Secrets Manager, encrypted file, etc.)
3. Update scripts to require environment variable (no default)
4. Enable audit logging
5. Implement rotation schedule
6. Document access procedures

**Remember:** The root token is the **master key** to ALL secrets. Treat it with **extreme care**! 🔐

