# IAM Portal Testing Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## CI/CD Integration

The IAM Portal smoke tests are automatically run in CI/CD via GitHub Actions:

- **Workflow**: `.github/workflows/iam-portal-tests.yml`
- **Triggers**: 
  - Push to `main` or `develop` branches (when IAM Portal files change)
  - Pull requests to `main` or `develop` branches
  - Manual workflow dispatch
- **What it tests**:
  - IAM Portal API endpoints (user creation, listing)
  - Keycloak integration
  - Database connectivity

To run the same tests locally:
```bash
# Using the smoke test script
./scripts/iam-portal-smoke-test.sh

# Or using Make
make test-iam-portal
```

See the `GitHub Actions workflow` (historical reference unavailable) for details.

## Prerequisites

Before testing the IAM Portal UI, ensure you have:

1. **Database migrations applied**
   ```bash
   # Apply IAM portal schema
   psql -U sg -d sg -f backend/migrations/015_iam_portal_schema.sql
   
   # Apply policies schema
   psql -U sg -d sg -f backend/migrations/016_iam_policies_schema.sql
   ```

2. **Keycloak running** with a tenant realm configured
   ```bash
   # Check if Keycloak is running
   curl http://localhost:8081/health
   ```

3. **IAM Agent service running**
   ```bash
   # Check IAM Agent health
   curl http://localhost:8000/health
   ```

4. **Frontend dependencies installed**
   ```bash
   cd frontend
   npm install
   ```

## Quick Start

### 1. Start Backend Services

```bash
# From project root
docker-compose -f docker-compose.dev.yml up -d postgres keycloak redis

# Start IAM Agent (if not using docker-compose)
cd backend/services/iam_agent
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start Frontend

```bash
# From project root
cd frontend
npm run dev
```

The frontend should start on `http://localhost:3000`

### 3. Login

1. Navigate to `http://localhost:3000/login`
2. Login with your Keycloak credentials
3. Ensure your JWT token includes `tenant_id` claim

## Testing the IAM Portal

### Access the IAM Portal

After logging in, navigate to:
- **Main Navigation**: Click "IAM" in the sidebar
- **Direct URL**: `http://localhost:3000/dashboard/iam/people`

You should see the IAM sub-navigation with:
- People
- My Access
- Apps & Profiles
- Policies
- Chat

---

## Testing Flow 1: People Page (Add User)

### Step 1: Access People Page

1. Click **"People"** in IAM sub-navigation
2. URL: `http://localhost:3000/dashboard/iam/people`
3. You should see:
   - Header with "People" title
   - "Add User" button
   - Search bar
   - List of users (if any exist)

### Step 2: Add a New User

1. Click **"Add User"** button
2. Fill in the form:
   - **Work Email**: `test.user@example.com`
   - **First Name**: `Test`
   - **Last Name**: `User`
   - **Department**: `Engineering`
   - **Access Profile**: Select a profile (if available)
   - **Make them an admin?**: Unchecked
3. Click **"Invite User"**

### Expected Behavior

- Modal closes
- User appears in the list
- User is created in Keycloak
- Access profile entitlements are granted (if profile selected)

### Troubleshooting

**Error: "Failed to create user"**
- Check IAM Agent logs: `docker-compose logs iam_agent`
- Verify Keycloak connection
- Check tenant_id in JWT token

**User not appearing in list**
- Refresh the page
- Check browser console for errors
- Verify API response in Network tab

---

## Testing Flow 2: My Access Page (Self-Service)

### Step 1: Access My Access Page

1. Click **"My Access"** in IAM sub-navigation
2. URL: `http://localhost:3000/dashboard/iam/my-access`
3. You should see:
   - Current Access section
   - Pending Requests section (if any)
   - Available Access section

### Step 2: Request Access

1. Scroll to **"Available Access"** section
2. Find an entitlement you don't have
3. Click **"Request Access"** button
4. Fill in the request form:
   - **Reason**: "Need access for project work"
   - **Temporary access**: Check if needed
   - **Duration**: 30 days (if temporary)
5. Click **"Submit Request"**

### Expected Behavior

- Request appears in "Pending Requests"
- Request is created in database
- Approval workflow is triggered (if privileged)

### Step 3: Approve Request (as Admin)

1. Navigate to **People** page
2. Find the user who requested access
3. Or check pending requests (if approval UI exists)
4. Approve the request

### Troubleshooting

**No available entitlements shown**
- Create apps and entitlements first (see Apps & Profiles testing)
- Check API response: `GET /api/iam-portal/my-access`

**Request not appearing**
- Check browser console
- Verify API call succeeded in Network tab
- Check IAM Agent logs

---

## Testing Flow 3: Apps & Access Profiles

### Step 1: Access Apps Page

1. Click **"Apps & Profiles"** in IAM sub-navigation
2. URL: `http://localhost:3000/dashboard/iam/apps`
3. You should see tabs:
   - **Apps** tab (default)
   - **Access Profiles** tab

### Step 2: View Apps

1. On **Apps** tab, you should see:
   - List of apps (if any exist)
   - Each app shows:
     - App name and description
     - Available roles
     - Active/Inactive status

### Step 3: View Access Profiles

1. Click **"Access Profiles"** tab
2. You should see:
   - List of access profiles
   - Each profile shows:
     - Profile name
     - Description
     - Entitlements included
     - Default/System flags

### Troubleshooting

**No apps shown**
- Apps need to be created via API or seeded
- Check database: `SELECT * FROM apps WHERE tenant_id = 'your-tenant-id'`

**No access profiles shown**
- Profiles need to be created
- Check database: `SELECT * FROM access_profiles WHERE tenant_id = 'your-tenant-id'`

---

## Testing Flow 4: Policies Page

### Step 1: Access Policies Page

1. Click **"Policies"** in IAM sub-navigation
2. URL: `http://localhost:3000/dashboard/iam/policies`
3. You should see:
   - Header with "Policies" title
   - Tabs: Sign-on, Access, Approval & Workflow, SoD & Risk
   - "Use Template" and "New Policy" buttons

### Step 2: Create a Policy

1. Click **"New Policy"** button
2. Policy editor opens
3. Fill in:
   - **Policy Name**: "Test Sign-on Policy"
   - **Description**: "Test policy for sign-on"
4. Add a rule:
   - Click **"+ Add Rule"**
   - Rule appears with conditions and actions
5. Click **"Save Policy"**

### Expected Behavior

- Policy is saved
- Policy appears in the list
- Policy can be edited/deleted

### Step 3: Use a Template

1. Click **"Use Template"** button
2. Template modal opens
3. Select a template
4. Policy is created from template

### Troubleshooting

**Policy editor not opening**
- Check browser console for errors
- Verify API endpoint: `POST /api/iam-portal/policies`

**Policy not saving**
- Check IAM Agent logs
- Verify policy_data structure is valid
- Check database constraints

---

## API Testing (Using curl)

### Test IAM Portal API Directly

```bash
# Get auth token first (from Keycloak)
TOKEN="your-jwt-token"

# List users
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/iam-portal/users

# List apps
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/iam-portal/apps

# List access profiles
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/iam-portal/access-profiles

# Get my access
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/iam-portal/my-access

# List policies
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/iam-portal/policies?policy_type=signon
```

---

## Browser Developer Tools

### Check Network Requests

1. Open browser DevTools (F12)
2. Go to **Network** tab
3. Filter by "iam-portal" or "policies"
4. Check:
   - Request URLs
   - Request payloads
   - Response status codes
   - Response data

### Check Console Errors

1. Open browser DevTools (F12)
2. Go to **Console** tab
3. Look for:
   - API errors
   - React errors
   - TypeScript errors

### Check Application State

1. Open browser DevTools (F12)
2. Go to **Application** tab
3. Check:
   - Local Storage: `access_token`, `tenant_id`
   - Session Storage
   - Cookies

---

## Common Issues & Solutions

### Issue: "401 Unauthorized"

**Cause**: Missing or invalid JWT token

**Solution**:
1. Check if token exists in localStorage: `localStorage.getItem('access_token')`
2. Verify token is included in API requests
3. Check token expiration
4. Re-login if needed

### Issue: "Tenant ID not found"

**Cause**: JWT token doesn't include `tenant_id` claim

**Solution**:
1. Check Keycloak protocol mapper for `tenant_id`
2. Verify user has `tenant_id` attribute in Keycloak
3. Check token payload: decode JWT at jwt.io

### Issue: "Failed to fetch"

**Cause**: IAM Agent service not running or wrong URL

**Solution**:
1. Check IAM Agent is running: `curl http://localhost:8000/health`
2. Verify `NEXT_PUBLIC_IAM_AGENT_URL` in frontend `.env`
3. Check CORS settings in IAM Agent

### Issue: Empty lists (no users, apps, etc.)

**Cause**: No data seeded for tenant

**Solution**:
1. Create test data via API
2. Or seed initial data (see Seeding section below)

---

## Seeding Test Data

### Create Test App

```bash
TOKEN="your-jwt-token"

curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sentinelgrid",
    "display_name": "SentinelGrid Console",
    "description": "Main SentinelGrid application",
    "app_type": "sentinelgrid",
    "is_active": true
  }' \
  http://localhost:8000/api/iam-portal/apps
```

### Create Test Entitlement

```bash
# First, get app ID from previous response
APP_ID="app-uuid-here"

curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "'$APP_ID'",
    "name": "analyst",
    "display_name": "Analyst",
    "description": "Standard analyst role",
    "entitlement_type": "role",
    "is_privileged": false,
    "risk_level": "low"
  }' \
  http://localhost:8000/api/iam-portal/entitlements
```

### Create Test Access Profile

```bash
# Get entitlement ID from previous response
ENTITLEMENT_ID="entitlement-uuid-here"

curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "standard_employee",
    "display_name": "Standard Employee",
    "description": "Default profile for employees",
    "is_default": true,
    "entitlement_ids": ["'$ENTITLEMENT_ID'"]
  }' \
  http://localhost:8000/api/iam-portal/access-profiles
```

---

## Testing Checklist

- [ ] IAM Portal accessible after login
- [ ] People page loads and shows users
- [ ] Can add new user via form
- [ ] User appears in list after creation
- [ ] My Access page shows current entitlements
- [ ] Can request new access
- [ ] Request appears in pending requests
- [ ] Apps page shows apps (if any)
- [ ] Access Profiles page shows profiles (if any)
- [ ] Policies page loads
- [ ] Can create new policy
- [ ] Can edit existing policy
- [ ] Can delete policy
- [ ] Templates modal opens
- [ ] Can create policy from template
- [ ] All API calls succeed (check Network tab)
- [ ] No console errors
- [ ] Responsive design works on mobile

---

## Next Steps

After basic testing:

1. **Test approval workflow** - Request access and approve it
2. **Test policy evaluation** - Create sign-on policy and test login
3. **Test access policies** - Create access policy and test entitlement grant
4. **Test templates** - Create policies from different templates
5. **Test error handling** - Try invalid inputs, missing data, etc.

---

## Debugging Tips

1. **Enable verbose logging** in IAM Agent:
   ```python
   # In app/core/config.py
   LOG_LEVEL = "DEBUG"
   ```

2. **Check database directly**:
   ```bash
   psql -U sg -d sg
   SELECT * FROM apps WHERE tenant_id = 'your-tenant-id';
   SELECT * FROM policies WHERE tenant_id = 'your-tenant-id';
   ```

3. **Use React Query DevTools** (if installed):
   - Shows query cache
   - Shows mutation states
   - Helps debug data fetching

4. **Check Keycloak Admin Console**:
   - Verify users exist
   - Check user attributes (tenant_id)
   - Verify roles/groups

---

## Support

If you encounter issues:

1. Check logs: `docker-compose logs iam_agent`
2. Check browser console for errors
3. Verify all services are running
4. Check database migrations are applied
5. Review the implementation docs:
   - `docs/archive/reference/identity/iam-portal-implementation.md`
   - `docs/archive/reference/identity/iam-policy-editor.md`

