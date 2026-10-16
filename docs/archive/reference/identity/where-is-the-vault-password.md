# 🔐 Where is the Vault Root Token? (Company Top Secret)

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Status:** ⚠️ **CURRENTLY INSECURE - MUST BE SECURED FOR PRODUCTION**

---

## 🚨 Current Location (Development Only)

### Where It's Stored Now

**⚠️ HARDCODED IN 3 FILES (DEVELOPMENT ONLY - NOT SECURE):**

1. **`docker-compose.dev.yml`** (Line 766, 775)
   - Default: `sentinelgrid-dev-root-token`
   - Can override with `VAULT_ROOT_TOKEN` environment variable

2. **`backend/scripts/init_vault.sh`** (Line 25)
   - Default: `sentinelgrid-dev-root-token`
   - Can override with `VAULT_TOKEN` environment variable

3. **`backend/scripts/init_complete_stack.sh`** (Line 53)
   - Default: `sentinelgrid-dev-root-token`
   - Can override with `VAULT_TOKEN` environment variable

### Why This is a Problem

❌ **Hardcoded in source code** - visible to anyone with code access  
❌ **Predictable** - `sentinelgrid-dev-root-token` is easy to guess  
❌ **In git history** - even if removed, it's in commit history  
❌ **Unlimited access** - root token can access ALL secrets  
❌ **No rotation** - cannot change without code changes  

**⚠️ This is ACCEPTABLE for development, but MUST BE FIXED for production!**

---

## 🔒 How to Secure It (Production)

### Step 1: Generate Secure Token

**Run the secure generation script:**
```bash
bash backend/scripts/generate_vault_root_token.sh
```

**This will:**
- Generate a 256-bit cryptographically secure token
- Display the token (copy it immediately)
- Optionally write to `.env.production` (gitignored)

**Example output:**
```
✅ Generated secure Vault root token

Root Token:
${EXAMPLE_VALUE}

🚨 CRITICAL SECURITY WARNINGS 🚨
...
```

### Step 2: Store Securely (Choose One)

#### Option A: Environment File (Recommended for Small Teams)

**File:** `.env.production` (NOT in git - already gitignored)

```bash
# Add to .env.production
VAULT_ROOT_TOKEN=${EXAMPLE_VALUE}
```

**Verify it's gitignored:**
```bash
git check-ignore .env.production
# Should output: .env.production
```

**Access:**
```bash
# Load environment
source .env.production

# Or use in scripts
export VAULT_ROOT_TOKEN=$(grep VAULT_ROOT_TOKEN .env.production | cut -d'=' -f2)
```

#### Option B: AWS Secrets Manager (Recommended for Production)

**Store:**
```bash
aws secretsmanager create-secret \
  --name sentinelgrid/vault/root-token \
  --secret-string "${EXAMPLE_VALUE}" \
  --description "Vault root token for SentinelGrid production"
```

**Retrieve:**
```bash
VAULT_ROOT_TOKEN=$(aws secretsmanager get-secret-value \
  --secret-id sentinelgrid/vault/root-token \
  --query SecretString --output text)
```

**Benefits:**
- ✅ Encrypted at rest
- ✅ Access via IAM
- ✅ Audit logging
- ✅ Automatic rotation support

#### Option C: Password Manager (1Password, Bitwarden)

**Store:**
- Create new item: "Vault Root Token"
- Field: `VAULT_ROOT_TOKEN`
- Value: `${EXAMPLE_VALUE}`
- Share with authorized team members only

**Benefits:**
- ✅ Encrypted storage
- ✅ Access control
- ✅ Audit logging
- ✅ Easy team sharing

#### Option D: Encrypted File (GPG/Age)

**GPG Encrypted:**
```bash
# Encrypt
echo "${EXAMPLE_VALUE}" | \
  gpg --encrypt --recipient security@sentinelgrid.ai > vault-root-token.gpg

# Decrypt
gpg --decrypt vault-root-token.gpg
```

**Age Encrypted:**
```bash
# Encrypt
echo "${EXAMPLE_VALUE}" | \
  age -r age1... > vault-root-token.age

# Decrypt
age --decrypt -i ~/.age/key.txt vault-root-token.age
```

### Step 3: Use Token in Scripts

**Set environment variable:**
```bash
export VAULT_ROOT_TOKEN="${EXAMPLE_VALUE}"
```

**Run scripts:**
```bash
# Token will be used automatically
bash backend/scripts/init_complete_stack.sh
```

---

## 📋 Security Checklist

### Development (Current)
- [x] Hardcoded token acceptable (dev only)
- [x] No production data
- [x] Can be reset anytime

### Production (MUST DO)
- [ ] Generate secure token (256-bit random)
- [ ] Store in secure location (AWS Secrets Manager, encrypted file, etc.)
- [ ] NOT in source code
- [ ] NOT in git
- [ ] Shared only with authorized personnel
- [ ] Enable audit logging
- [ ] Set up rotation schedule (quarterly)
- [ ] Document access procedures

---

## 🚨 Who Should Have Access?

### Authorized Personnel Only

**Minimum Access:**
- CTO / Head of Engineering
- Security Lead
- DevOps Lead
- On-call Engineer (temporary, for emergencies)

**Access Requirements:**
- ✅ Background check completed
- ✅ Security training completed
- ✅ Signed NDA
- ✅ Access logged and audited

**Access Method:**
- ✅ Via secure password manager (shared vault)
- ✅ Via AWS Secrets Manager (IAM access)
- ✅ Via encrypted file (GPG key required)

**❌ NEVER:**
- Share via email
- Share via Slack/unencrypted chat
- Store in shared drive
- Write on paper (unless in secure safe)

---

## 🔄 Token Rotation

### When to Rotate

- ✅ **Quarterly** (every 3 months)
- ✅ **After security incident**
- ✅ **After employee departure** (if they had access)
- ✅ **After suspected compromise**

### How to Rotate

1. **Generate new token:**
   ```bash
   bash backend/scripts/generate_vault_root_token.sh
   ```

2. **Update in secure storage:**
   - Update AWS Secrets Manager
   - Update password manager
   - Update `.env.production`

3. **Update all systems:**
   - Restart services using token
   - Update CI/CD pipelines
   - Update documentation

4. **Revoke old token:**
   ```bash
   vault token revoke <old-token>
   ```

---

## 📚 Full Documentation

- **`VAULT_ROOT_TOKEN_SECURITY.md`** - Complete security guide
- **`PRODUCTION_SECURITY_CHECKLIST.md`** - Production security checklist
- **`backend/scripts/generate_vault_root_token.sh`** - Token generation script

---

## ✅ Quick Answer

**Q: Where is the Vault root token?**

**A: Currently hardcoded as `sentinelgrid-dev-root-token` in 3 files (development only).**

**For production:**
1. Generate secure token: `bash backend/scripts/generate_vault_root_token.sh`
2. Store in AWS Secrets Manager or encrypted password manager
3. Set `VAULT_ROOT_TOKEN` environment variable
4. Never commit to git

**This is company top secret - handle with extreme care!** 🔐

