# Quick Reference: `init_complete_stack.sh`

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## 🎯 Purpose

**First-time production setup ONLY** - Creates fresh infrastructure with Vault secrets management

**⚠️ NEVER RUN AGAIN AFTER INITIAL PRODUCTION SETUP**

---

## 🛡️ Safety Features

**5 Layers of Protection:**
1. ✅ Header documentation (always visible)
2. ✅ Production environment detection (extra confirmation)
3. ✅ Detailed warning banner (explains everything)
4. ✅ Explicit confirmation required (`"DELETE ALL DATA"`)
5. ✅ Final countdown (10 seconds to cancel)

---

## 📋 What Gets Deleted

**Everything:**
- All Keycloak realms, users, clients, organizations
- All Vault secrets, policies, audit logs
- All database tables (customers, organizations, tenants, vault_*)
- All Docker volumes (Keycloak, Vault)

**This is IRREVERSIBLE!**

---

## ✅ When to Use

### ✅ Safe to Use

1. **First-Time Production Setup**
   ```bash
   ENVIRONMENT=production bash backend/scripts/init_complete_stack.sh
   ```
   - Will require extra confirmation
   - Use ONCE when setting up production for the very first time

2. **Development/Testing**
   ```bash
   bash backend/scripts/init_complete_stack.sh
   ```
   - Standard confirmation only
   - Safe for dev environments

### ❌ Never Use

1. **Production After Initial Setup**
   - Will delete all customer data
   - Will delete all secrets
   - Will delete all users

2. **Without Understanding**
   - Read `EXPLAIN_INIT_COMPLETE_STACK.md` first
   - Understand what will be deleted

---

## 🚨 Confirmation Prompts

### Development
```
Type "DELETE ALL DATA" to continue: 
```

### Production (Extra Confirmation)
```
Type "I UNDERSTAND THIS WILL DELETE ALL PRODUCTION DATA": 
```

Then:
```
Type "DELETE ALL DATA" to continue: 
```

Then:
```
⚠️  FINAL WARNING: DELETION WILL BEGIN IN 10 SECONDS  ⚠️
Press Ctrl+C NOW to cancel

Starting deletion in 10 seconds...
```

---

## 🛑 How to Cancel

**At any point before deletion starts:**
- Type anything other than exact confirmation phrase
- Press `Ctrl+C` during countdown
- Script exits safely with: `✅ Operation cancelled. No data was deleted.`

---

## 📚 Full Documentation

- `EXPLAIN_INIT_COMPLETE_STACK.md` - Detailed step-by-step explanation
- `SAFETY_FEATURES_INIT_SCRIPT.md` - All safety mechanisms explained
- `RUN_WITH_VAULT.md` - How to use the initialized stack

---

## ⚡ Quick Commands

```bash
# Check script syntax
bash -n backend/scripts/init_complete_stack.sh

# View script (see warnings)
cat backend/scripts/init_complete_stack.sh | head -50

# Run in development
bash backend/scripts/init_complete_stack.sh

# Run in production (first-time only!)
ENVIRONMENT=production bash backend/scripts/init_complete_stack.sh
```

---

**Remember: First-time production setup ONLY! 🚨**

