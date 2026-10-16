# Detailed Next Steps - AgribotsAI Onboarding

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-01-28  
**Priority:** Execute in order

---

## Phase 1: Keycloak Configuration (30 minutes)

### Step 1.1: Apply Terraform Configuration ⏳

**Action:**
```bash
cd infra/customers/agribotsai/keycloak/terraform

# Ensure Keycloak is accessible
curl http://localhost:8081/health

# Review what will be created
terraform plan

# Apply configuration
terraform apply
```

**Expected Output:**
- Realm `agribotsai` created
- 3 clients created
- 4 roles created
- Protocol mappers configured
- 3 users created

**Verification:**
- Visit http://localhost:8081/admin
- Login with admin/admin
- Select realm `agribotsai` from dropdown
- Verify clients, roles, users exist

**Time:** 10 minutes

---

### Step 1.2: Create Tenant in Database ⏳

**Action:**
```sql
-- Connect to PostgreSQL
docker-compose -f docker-compose.dev.yml exec postgres psql -U sg -d sg

-- Create tenant
INSERT INTO tenants (id, name, slug, status) 
VALUES (
  gen_random_uuid(),
  'AgribotsAI',
  'agribotsai',
  'active'
) RETURNING id;
```

**Copy the UUID** that's returned - you'll need it for the next step.

**Time:** 5 minutes

---

### Step 1.3: Update Tenant ID in User Attributes ⏳

**Action:**
```bash
# Update users.tf with actual tenant UUID
# Or update via Keycloak admin console:
# Users → Select user → Attributes → tenant_id → Update value
```

**Alternative:** Use Terraform variable or update manually in Keycloak admin console.

**Time:** 5 minutes

---

### Step 1.4: Verify Configuration ⏳

**Action:**
1. Check realm exists
2. Check clients are configured
3. Check users have tenant_id attribute
4. Check roles are assigned

**Time:** 10 minutes

---

## Phase 2: Token Generation & Testing (30 minutes)

### Step 2.1: Generate JWT Token ⏳

**Action:**
```bash
cd infra/shared/scripts
./get-token.sh agribotsai agribotsai-web admin@agribotsai.com ChangeMe123!
```

**Expected:**
- Access token returned
- Token decoded shows tenant_id claim
- Token shows roles in realm_access

**Time:** 5 minutes

---

### Step 2.2: Test Token Validation ⏳

**Action:**
```bash
# Use token from 2.1
TOKEN="<token-from-step-2.1>"

curl -X POST http://localhost:8005/internal/iam/auth/validate-token \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$TOKEN\"}" | jq
```

**Expected Response:**
```json
{
  "valid": true,
  "tenant_id": "agribotsai-tenant-uuid",
  "user_id": "...",
  "username": "admin@agribotsai.com",
  "roles": ["TENANT_ADMIN"],
  ...
}
```

**Verify:**
- ✅ `valid: true`
- ✅ `tenant_id` matches database UUID
- ✅ `roles` array contains TENANT_ADMIN

**Time:** 10 minutes

---

### Step 2.3: Test Token Introspection ⏳

**Action:**
```bash
curl -X POST http://localhost:8005/internal/iam/auth/introspect \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$TOKEN\"}" | jq
```

**Expected:** Similar response with `active: true`

**Time:** 5 minutes

---

## Phase 3: API Gateway Integration (20 minutes)

### Step 3.1: Test API Gateway with Token ⏳

**Action:**
```bash
# Ensure API Gateway is running
curl http://localhost:8080/health

# Test with token
curl http://localhost:8080/api/v1/alerts \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Expected:**
- HTTP 200 (or appropriate status)
- Response shows alerts (or empty list)
- Tenant isolation enforced

**Time:** 10 minutes

---

### Step 3.2: Test Unauthorized Access ⏳

**Action:**
```bash
# Test without token
curl http://localhost:8080/api/v1/alerts
# Should return 401

# Test with invalid token
curl http://localhost:8080/api/v1/alerts \
  -H "Authorization: Bearer ${ACCESS_TOKEN}"
# Should return 401
```

**Expected:** Proper 401 Unauthorized responses

**Time:** 5 minutes

---

### Step 3.3: Test Tenant Isolation ⏳

**Action:**
1. Create second tenant (if needed)
2. Get token for Tenant A
3. Try to access Tenant B data
4. Verify access is denied

**Expected:** Tenant isolation works correctly

**Time:** 10 minutes

---

## Phase 4: End-to-End Testing (20 minutes)

### Step 4.1: Run E2E Test Script ⏳

**Action:**
```bash
cd infra/shared/scripts
./test-auth-flow.sh http://localhost:8081 agribotsai admin@agribotsai.com ChangeMe123!
```

**Expected:** All test steps pass

**Time:** 10 minutes

---

### Step 4.2: Test Different User Roles ⏳

**Action:**
1. Get token for analyst user
2. Test access permissions
3. Get token for viewer user
4. Test read-only restrictions

**Expected:** Role-based access control works

**Time:** 10 minutes

---

## Phase 5: Role-Based Access Testing (30 minutes)

### Step 5.1: Test TENANT_ADMIN ⏳

**User:** `admin@agribotsai.com`  
**Expected:** Full access to all endpoints

**Time:** 5 minutes

---

### Step 5.2: Test SOC_ANALYST ⏳

**User:** `analyst@agribotsai.com`  
**Expected:** Can view/triage alerts, manage incidents, cannot manage users

**Time:** 10 minutes

---

### Step 5.3: Test VIEW_ONLY ⏳

**User:** `viewer@agribotsai.com`  
**Expected:** Read-only access, cannot modify anything

**Time:** 10 minutes

---

## Testing Checklist

### Configuration ✅
- [ ] Realm created
- [ ] Clients created
- [ ] Roles created
- [ ] Protocol mappers working
- [ ] Users created with tenant_id

### Token Generation ⏳
- [ ] Can get token from Keycloak
- [ ] Token contains tenant_id
- [ ] Token contains roles
- [ ] Token expiration works

### Token Validation ⏳
- [ ] IAM Agent validates tokens
- [ ] Tenant ID extracted
- [ ] Roles extracted
- [ ] Invalid tokens rejected

### API Gateway ⏳
- [ ] Accepts valid tokens
- [ ] Rejects invalid tokens
- [ ] Enforces tenant isolation
- [ ] Role-based access works

### End-to-End ⏳
- [ ] Full auth flow works
- [ ] Multi-tenant isolation
- [ ] Role-based permissions
- [ ] Error handling works

---

## Total Time Estimate

- **Phase 1:** 30 minutes
- **Phase 2:** 30 minutes
- **Phase 3:** 20 minutes
- **Phase 4:** 20 minutes
- **Phase 5:** 30 minutes

**Total:** ~2 hours for complete setup and testing

---

## Success Criteria

✅ AgribotsAI realm fully configured  
✅ Users can login and get tokens  
✅ Tokens contain tenant_id and roles  
✅ IAM Agent validates tokens correctly  
✅ API Gateway enforces authentication  
✅ Multi-tenant isolation verified  
✅ Role-based access control working  

---

**Ready to execute!** 🚀

