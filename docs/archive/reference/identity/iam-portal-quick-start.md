# IAM Portal Quick Start Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## 🚀 Quick Test (5 minutes)

### 1. Start Services

```bash
# Start database and Keycloak
docker-compose -f docker-compose.dev.yml up -d postgres keycloak redis

# Start IAM Agent (in one terminal)
cd backend/services/iam_agent
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Frontend (in another terminal)
cd frontend
npm run dev
```

### 2. Verify Services

```bash
# Run the test script
./scripts/test-iam-portal.sh
```

Or manually check:

```bash
# Check IAM Agent
curl http://localhost:8000/health

# Check Frontend
curl http://localhost:3000
```

### 3. Access the UI

1. Open browser: **http://localhost:3000**
2. Login with your Keycloak credentials
3. Navigate to: **http://localhost:3000/dashboard/iam/people**

### 4. Test Basic Flow

1. **People Page**: Click "Add User" → Fill form → Click "Invite User"
2. **My Access**: Click "My Access" → Click "Request Access" on an entitlement
3. **Policies**: Click "Policies" → Click "New Policy" → Create a simple policy

---

## 🔧 Troubleshooting

### "401 Unauthorized" Error

**Fix**: Ensure you're logged in and token is valid

```bash
# Check token in browser console
localStorage.getItem('access_token')
```

### "Tenant ID not found" Error

**Fix**: Ensure your Keycloak user has `tenant_id` attribute

1. Login to Keycloak Admin Console: http://localhost:8081
2. Go to Users → Select your user → Attributes
3. Add attribute: `tenant_id` = `your-tenant-uuid`

### Frontend can't connect to IAM Agent

**Fix**: Check environment variable

```bash
# In frontend/.env.local
NEXT_PUBLIC_IAM_AGENT_URL=http://localhost:8000
```

### No data showing

**Fix**: Seed some test data (see below)

---

## 📊 Seed Test Data

### Option 1: Use API (Recommended)

```bash
# Get your JWT token from browser localStorage
TOKEN="your-jwt-token-here"

# Create an app
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sentinelgrid",
    "display_name": "SentinelGrid Console",
    "app_type": "sentinelgrid",
    "is_active": true
  }' \
  http://localhost:8000/api/iam-portal/apps
```

### Option 2: Direct Database (Quick)

```sql
-- Connect to database
psql -U sg -d sg

-- Create a test app
INSERT INTO apps (tenant_id, name, display_name, app_type, is_active)
VALUES (
  'your-tenant-uuid'::uuid,
  'sentinelgrid',
  'SentinelGrid Console',
  'sentinelgrid',
  true
);
```

---

## 🎯 What to Test

### ✅ Basic Functionality

- [ ] Can access IAM Portal after login
- [ ] People page loads
- [ ] Can add a user
- [ ] My Access page loads
- [ ] Can request access
- [ ] Policies page loads
- [ ] Can create a policy

### ✅ Advanced Features

- [ ] Access profiles work
- [ ] Policy evaluation works
- [ ] Approval workflow works
- [ ] Templates work

---

## 📖 Full Documentation

- **Testing Guide**: `docs/archive/reference/identity/iam-portal-testing-guide.md`
- **Implementation**: `docs/archive/reference/identity/iam-portal-implementation.md`
- **Policy Editor**: `docs/archive/reference/identity/iam-policy-editor.md`

---

## 🆘 Need Help?

1. Check browser console (F12) for errors
2. Check IAM Agent logs: `docker-compose logs iam_agent`
3. Verify all migrations applied: Check database tables exist
4. Review the testing guide for detailed steps

