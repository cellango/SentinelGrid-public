# Safety Features: `init_complete_stack.sh`

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Purpose:** Document all safety mechanisms to prevent accidental data deletion

---

## 🛡️ Multi-Layer Safety Protection

This script has **5 layers of protection** to prevent accidental data deletion:

### Layer 1: Header Documentation ✅

**Location:** Top of script file

**What it does:**
- Clear warning in script header comments
- Explains when to use (first-time production setup only)
- Explains what will be deleted
- Visible to anyone reading the script

**Example:**
```bash
# ⚠️  CRITICAL WARNING: THIS SCRIPT PERMANENTLY DELETES ALL DATA ⚠️
#
# WHEN TO USE:
#   ✅ FIRST-TIME PRODUCTION SETUP - Use ONCE when setting up production
#   ❌ NEVER USE IN PRODUCTION AFTER INITIAL SETUP
```

---

### Layer 2: Production Environment Detection ✅

**Location:** Lines 58-95 (after configuration)

**What it does:**
- Automatically detects production environment indicators:
  - `ENVIRONMENT=production`
  - `NODE_ENV=production`
  - `DB_URL` containing "prod", "production", or "live"
  - `KEYCLOAK_URL` containing "prod", "production", "live", or "sentinelgrid.ai"

**If production detected:**
- Shows **RED WARNING BANNER**
- Lists all production indicators found
- Requires **EXTRA confirmation**: `"I UNDERSTAND THIS WILL DELETE ALL PRODUCTION DATA"`
- If not typed exactly, script exits safely

**Example Output:**
```
🚨  PRODUCTION ENVIRONMENT DETECTED  🚨

⚠️  PRODUCTION ENVIRONMENT INDICATORS FOUND:
  • ENVIRONMENT=production
  • KEYCLOAK_URL contains production indicators

🔴  THIS SCRIPT WILL DELETE ALL PRODUCTION DATA  🔴

To proceed in production, you must type:
I UNDERSTAND THIS WILL DELETE ALL PRODUCTION DATA
```

---

### Layer 3: Detailed Warning Banner ✅

**Location:** Lines 97-130

**What it does:**
- Shows **large red warning banner**
- Lists **exactly what will be deleted**:
  - All Keycloak realms, users, clients
  - All Vault secrets, policies, audit logs
  - All database tables, views, functions
- Explains **when to use** (first-time production setup)
- Explains **when NOT to use** (after initial setup)

**Example Output:**
```
🚨  DESTRUCTIVE OPERATION - COMPLETE DATA DELETION  🚨

⚠️  CRITICAL WARNING: THIS SCRIPT WILL PERMANENTLY DELETE ALL DATA ⚠️

📋 WHAT THIS SCRIPT DOES:

  Phase 1: DESTROYS ALL EXISTING DATA
    • DELETES all Keycloak Docker volumes (all realms, users, clients)
    • DELETES all Vault Docker volumes (all secrets, policies)
    • DROPS all database tables (realms, customers, organizations, tenants)
    • THIS IS IRREVERSIBLE - ALL DATA WILL BE LOST FOREVER

🎯 WHEN TO USE THIS SCRIPT:

  ✅ FIRST-TIME PRODUCTION SETUP
     Use this ONCE when setting up production for the very first time
     After that, NEVER RUN THIS AGAIN

  ❌ NEVER USE IN PRODUCTION AFTER INITIAL SETUP
     This will DELETE ALL CUSTOMER DATA
```

---

### Layer 4: Explicit Confirmation Required ✅

**Location:** Lines 131-145

**What it does:**
- Requires user to type **exact phrase**: `"DELETE ALL DATA"`
- Case-sensitive and must match exactly
- If not typed correctly, script exits safely
- No default "yes" - user must actively confirm

**Example:**
```bash
🔴 THIS OPERATION CANNOT BE UNDONE 🔴

To proceed, you must type: DELETE ALL DATA
This confirms you understand the consequences.

Type "DELETE ALL DATA" to continue: 
```

**If user types anything else:**
```
✅ Operation cancelled. No data was deleted.
```

---

### Layer 5: Final Countdown Warning ✅

**Location:** Lines 147-160

**What it does:**
- After confirmation, shows **10-second countdown**
- Displays: `"Press Ctrl+C NOW to cancel"`
- Updates every second: `"Starting deletion in X seconds..."`
- Gives user final chance to cancel

**Example:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚠️  FINAL WARNING: DELETION WILL BEGIN IN 10 SECONDS  ⚠️
  Press Ctrl+C NOW to cancel
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Starting deletion in 10 seconds...
  Starting deletion in 9 seconds...
  ...
  Starting deletion in 1 seconds...
  Starting deletion now...
```

---

## 📊 Safety Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Script Starts                                          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Header Documentation                          │
│  (Visible in script file)                               │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Production Detection                           │
│  Checks: ENVIRONMENT, NODE_ENV, DB_URL, KEYCLOAK_URL    │
└──────────────────┬──────────────────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
    Production?          Development?
         │                   │
         ▼                   ▼
┌─────────────────┐  ┌─────────────────┐
│ Extra Confirmation│  │ Standard Flow   │
│ "I UNDERSTAND..."│  │                 │
└────────┬─────────┘  └────────┬─────────┘
         │                    │
         └─────────┬──────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Detailed Warning Banner                       │
│  Shows what will be deleted, when to use                │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 4: Explicit Confirmation                         │
│  Must type: "DELETE ALL DATA"                           │
└──────────────────┬──────────────────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
    Correct?            Wrong?
         │                   │
         ▼                   ▼
┌─────────────────┐  ┌─────────────────┐
│ Continue        │  │ Exit Safely     │
│                 │  │ "Cancelled"     │
└────────┬────────┘  └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 5: Final Countdown                               │
│  10-second countdown with Ctrl+C option                 │
└──────────────────┬──────────────────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
    Interrupted?         Not Interrupted?
         │                   │
         ▼                   ▼
┌─────────────────┐  ┌─────────────────┐
│ Exit Safely     │  │ Begin Deletion  │
│ "Cancelled"     │  │                 │
└─────────────────┘  └─────────────────┘
```

---

## 🎯 When Each Layer Activates

| Layer | Always Active | Production Only | Development Only |
|-------|--------------|-----------------|-------------------|
| 1. Header Docs | ✅ | ✅ | ✅ |
| 2. Prod Detection | ✅ | ✅ (Extra confirm) | ✅ (Skip extra) |
| 3. Warning Banner | ✅ | ✅ | ✅ |
| 4. Explicit Confirm | ✅ | ✅ | ✅ |
| 5. Countdown | ✅ | ✅ | ✅ |

**Result:** Production gets **5 layers**, Development gets **4 layers** (Layer 2 skips extra confirmation but still shows warning)

---

## 🔒 Production Safety Guarantees

### Guarantee 1: Cannot Run Accidentally
- Must type exact phrase: `"DELETE ALL DATA"`
- No default "yes" option
- No `-y` or `--yes` flag to skip

### Guarantee 2: Production Detection
- Automatically detects production environment
- Requires **extra confirmation** in production
- Shows all production indicators found

### Guarantee 3: Multiple Warnings
- Warning at script start
- Warning before confirmation
- Warning during countdown
- Clear explanation of consequences

### Guarantee 4: Easy Cancellation
- Can cancel at any point before countdown ends
- Ctrl+C works during countdown
- Safe exit (no partial deletion)

---

## 📝 Usage Guidelines

### ✅ Safe to Use

**First-Time Production Setup:**
```bash
# Setting up production for the very first time
ENVIRONMENT=production bash backend/scripts/init_complete_stack.sh
# Will require extra confirmation
```

**Development/Testing:**
```bash
# Resetting dev environment
bash backend/scripts/init_complete_stack.sh
# Standard confirmation only
```

### ❌ Never Use

**Production After Initial Setup:**
```bash
# ❌ DO NOT RUN - Will delete all customer data
# Production is already running with customers
```

**Without Understanding:**
```bash
# ❌ DO NOT RUN - If you don't understand what will be deleted
# Read EXPLAIN_INIT_COMPLETE_STACK.md first
```

---

## 🚨 Emergency Stop

**If you accidentally start the script:**

1. **During confirmation prompt:**
   - Type anything other than `"DELETE ALL DATA"`
   - Script exits safely

2. **During countdown:**
   - Press `Ctrl+C`
   - Script exits safely

3. **After countdown starts:**
   - Press `Ctrl+C` immediately
   - Script exits safely (no deletion started yet)

**Note:** Once Phase 1 begins (volume deletion), it's too late. But you have **10 seconds** to cancel.

---

## 📚 Related Documentation

- `EXPLAIN_INIT_COMPLETE_STACK.md` - Detailed explanation of what the script does
- `RUN_WITH_VAULT.md` - How to use the initialized stack
- `PRODUCTION_SECURITY_CHECKLIST.md` - Production security guidelines

---

## ✅ Summary

**5 Layers of Protection:**
1. ✅ Header documentation (always visible)
2. ✅ Production environment detection (extra confirmation)
3. ✅ Detailed warning banner (explains everything)
4. ✅ Explicit confirmation required (`"DELETE ALL DATA"`)
5. ✅ Final countdown (10 seconds to cancel)

**Result:** **Impossible to run accidentally** - requires multiple deliberate confirmations

**Use Case:** **First-time production setup ONLY** - never run again after initial setup

---

**Safety First! 🛡️**

