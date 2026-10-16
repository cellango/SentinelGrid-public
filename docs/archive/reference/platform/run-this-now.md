# 🚀 Run This NOW - Complete Realm Architecture Test

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## One Command to Rule Them All

```bash
bash run_realm_test.sh
```

This will:
1. ✅ Drop Keycloak database and volumes
2. ✅ Reset PostgreSQL realm tables
3. ✅ Restart Keycloak (fresh install)
4. ✅ Wait ~90 seconds for Keycloak to initialize
5. ✅ Run database migration (`002_realm_architecture.sql`)
6. ✅ Seed 3 realms in Keycloak:
   - `sg-admin` - Platform admin realm
   - `sg-mt-us-1` - US multi-tenant realm
   - `sg-mt-eu-1` - EU multi-tenant realm
7. ✅ Create platform admin user:
   - Email: `admin@sentinelgrid.ai`
   - Password: `admin123`
   - Role: `PLATFORM_ADMIN`
8. ✅ Restart IAM Agent to use new realm config
9. ✅ Test token generation
10. ✅ Run Selenium login test
11. ✅ Verify dashboard loads

**Time:** ~3-4 minutes total

---

## What Gets Created

### Keycloak Realms (3)

| Realm | Type | Purpose | Users |
|-------|------|---------|-------|
| `sg-admin` | Platform Admin | SentinelGrid staff | 1 (admin@sentinelgrid.ai) |
| `sg-mt-us-1` | Multi-Tenant | US customers | 1 (test@example.com) |
| `sg-mt-eu-1` | Multi-Tenant | EU customers | 0 |

### Database Tables (6)

- `realms` - Realm registry (3 records)
- `customers` - Company records (empty)
- `organizations` - Enterprise orgs (empty)
- `tenants` - Tenant records (empty)
- `realm_capacity_history` - Capacity tracking (empty)
- `tenant_provisioning_log` - Audit log (empty)

### Platform Admin User

- **Realm:** `sg-admin`
- **Email:** `admin@sentinelgrid.ai`
- **Password:** `admin123` ⚠️ **DEVELOPMENT ONLY**
- **Role:** `PLATFORM_ADMIN`
- **Purpose:** Login to SentinelGrid platform

### Service Accounts

- **`sentinelgrid-platform-api`** - Platform API service account (sg-admin)
- **`sentinelgrid-iam-agent`** - IAM Agent service account (all realms)

**Note:** Service account credentials are displayed during seeding and saved to:
  `backend/scripts/SEEDED_CREDENTIALS.txt`

### Test Customer User

- **Realm:** `sg-mt-us-1`
- **Email:** `test@example.com`
- **Password:** `test123`
- **Role:** `TENANT_ADMIN`
- **Purpose:** Testing customer flows

---

## What the Test Verifies

✅ Login form loads  
✅ Login with `admin@sentinelgrid.ai` / `admin123`  
✅ Token stored in localStorage  
✅ Redirect to dashboard  
✅ Dashboard content visible  

---

## If Test Fails

### Check Keycloak

```bash
# 1. Check if realms exist
curl -k https://localhost:8443/realms/sg-admin/.well-known/openid-configuration

# 2. Check Keycloak logs
docker-compose logs keycloak | tail -100

# 3. Login to Keycloak Admin
open http://localhost:8080/admin
# Login: admin/admin
# Select realm: sg-admin
# Check Users → admin@sentinelgrid.ai exists
```

### Check IAM Agent

```bash
# 1. Check environment
docker-compose exec iam_agent env | grep KEYCLOAK

# Should show:
#   KEYCLOAK_REALM=sg-admin

# 2. Check logs
docker-compose logs iam_agent | tail -100

# 3. Test login endpoint directly
curl -X POST http://localhost:8005/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@sentinelgrid.ai", "password": "admin123"}'
```

### Check Frontend

```bash
# 1. Check if running
docker-compose ps frontend

# 2. Check logs
docker-compose logs frontend | tail -100

# 3. Test access
curl -k https://localhost:3443
```

### Manual Test

```bash
# 1. Navigate to login page
open https://localhost:3443/login

# 2. Enter credentials:
#    Email: admin@sentinelgrid.ai
#    Password: admin123

# 3. Should redirect to dashboard
```

---

## After Successful Test

You can now:

### 1. Test Customer Signup

```bash
curl -X POST http://localhost:8008/api/v1/signup \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Acme Corp",
    "employee_count": 50,
    "admin_email": "admin@acme.com",
    "admin_password": "AcmePass123!",
    "admin_first_name": "John",
    "admin_last_name": "Doe",
    "terms_accepted": true,
    "privacy_accepted": true
  }'
```

### 2. Check Realm Assignment

```bash
psql postgresql://sg:sg@localhost:5432/sg -c "
  SELECT c.name, c.pricing_tier, t.realm_name, r.realm_type 
  FROM customers c
  JOIN tenants t ON t.customer_id = c.id
  JOIN realms r ON r.realm_name = t.realm_name
  ORDER BY c.created_at DESC;
"
```

### 3. Test Different Pricing Tiers

```bash
# Free tier (≤5 employees)
curl -X POST http://localhost:8008/api/v1/signup -d '{"employee_count": 5, ...}'

# Starter (≤100 employees) 
curl -X POST http://localhost:8008/api/v1/signup -d '{"employee_count": 50, ...}'

# Professional (≤1000 employees)
curl -X POST http://localhost:8008/api/v1/signup -d '{"employee_count": 200, ...}'

# Enterprise (>1000 employees)
curl -X POST http://localhost:8008/api/v1/signup -d '{"employee_count": 5000, ...}'
```

---

## Run Again Anytime

The script is safe to run multiple times:

```bash
# Quick reset and test
bash run_realm_test.sh
```

Perfect for iterative development! 🔄

---

## Next Steps

1. ✅ Run the test (you're here!)
2. Verify dashboard loads
3. Test customer signup flow
4. Integrate with frontend signup page
5. Add realm selection UI (for multi-org enterprise)
6. Deploy to staging environment

---

---

## ⚠️ SECURITY WARNING

**The seeded credentials are for DEVELOPMENT ONLY!**

Default passwords used:
- Keycloak master admin: `admin` / `admin`
- Platform admin: `admin@sentinelgrid.ai` / `admin123`
- Test customer: `test@example.com` / `test123`

**Before production:**
1. Change ALL default passwords
2. Rotate service account secrets
3. Use secure password generation
4. Store secrets in secrets manager
5. Review: [`docs/archive/reference/platform/production-security-checklist.md`](production-security-checklist.md)

### Generate Secure Passwords

```bash
# Generate secure password (32 bytes, base64 encoded)
openssl rand -base64 32

# Or use your password manager
```

### Update Keycloak Admin Password

```bash
# Change master admin password
python3 backend/scripts/seed_realms.py \
  --admin-user admin \
  --admin-password admin \
  --new-admin-password "YOUR_SECURE_PASSWORD"
```

**Credentials are saved to:** `backend/scripts/SEEDED_CREDENTIALS.txt`  
**This file is gitignored** - safe to store locally but never commit!

---

**Ready? Run this:**

```bash
bash run_realm_test.sh
```

🚀 Good luck!

