# Certificate Management Feature - UI Location & Test Status

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-01-28

---

## UI Location

### Navigation Path

The certificate management feature is located in the **IAM section** of the dashboard:

**Main Navigation:**
```
Dashboard → People & Access → Certificates
```

**Direct URL:**
```
/dashboard/iam/certificates
```

### Navigation Structure

The "Certificates" link is already present in the IAM sub-navigation menu:

```24:24:frontend/src/app/(dashboard)/dashboard/iam/layout.tsx
  { name: 'Certificates', href: '/dashboard/iam/certificates', icon: DocumentTextIcon },
```

**Full IAM Navigation Menu:**
1. People
2. My Account
3. My Access
4. Apps & Profiles
5. Devices
6. Security Events
7. Reports
8. Privileged Access
9. Secrets
10. API Keys
11. **Certificates** ← Certificate Management Feature
12. Access Reviews
13. Policies
14. Chat

### Pages Available

1. **Certificate List Page**
   - Route: `/dashboard/iam/certificates`
   - File: `frontend/src/app/(dashboard)/dashboard/iam/certificates/page.tsx`
   - Features: List, filter, request, renew, revoke certificates

2. **Certificate Detail Page**
   - Route: `/dashboard/iam/certificates/[id]`
   - File: `frontend/src/app/(dashboard)/dashboard/iam/certificates/[id]/page.tsx`
   - Features: View certificate details, download PEM, download private key

3. **Enrollment Protocols Page**
   - Route: `/dashboard/iam/certificates/enroll`
   - File: `frontend/src/app/(dashboard)/dashboard/iam/certificates/enroll/page.tsx`
   - Features: ACME, SCEP, EST endpoint information and examples

---

## Test Status

### ✅ Backend Tests (EXIST)

**Location:** `backend/tests/cert_service/test_tenant_isolation.py`

**Test Coverage:**
- ✅ Tenant isolation in certificate service
- ✅ Tenant A cannot see Tenant B's certificates
- ✅ Tenant A cannot get Tenant B's certificate by ID
- ✅ Tenant A cannot revoke Tenant B's certificate
- ✅ Tenant A cannot renew Tenant B's certificate
- ✅ Tenant A can access own certificates
- ✅ List certificates filters by tenant_id
- ✅ Internal service (no tenant_id) can see all certificates

**Run Tests:**
```bash
cd backend/tests/cert_service
pytest test_tenant_isolation.py -v
```

**Test Structure:**
```python
class TestTenantIsolation:
    def test_tenant_a_cannot_see_tenant_b_certificates(...)
    def test_tenant_a_cannot_get_tenant_b_certificate(...)
    def test_tenant_a_cannot_revoke_tenant_b_certificate(...)
    def test_tenant_a_cannot_renew_tenant_b_certificate(...)
    def test_tenant_a_can_access_own_certificates(...)
    def test_list_certificates_filters_by_tenant(...)
    def test_service_without_tenant_id_can_see_all(...)
```

### ❌ Frontend/UI Tests (MISSING)

**Status:** No UI tests exist for certificate management pages

**Missing Test Coverage:**
- ❌ Certificate list page rendering
- ❌ Certificate filtering functionality
- ❌ Certificate request modal
- ❌ Certificate detail page
- ❌ Certificate renewal flow
- ❌ Certificate revocation flow
- ❌ Certificate download functionality
- ❌ Enrollment protocols page
- ❌ ACME/SCEP/EST endpoint display
- ❌ Copy-to-clipboard functionality
- ❌ Error handling in UI
- ❌ Loading states
- ❌ Empty states

**Reference:** Other IAM pages have Selenium tests:
- `backend/tests/test_iam_ui_selenium.py` - Tests for People, My Access, Policies, Access Reviews
- No equivalent tests for Certificates page

---

## Recommended Test Implementation

### 1. Selenium UI Tests (Similar to test_iam_ui_selenium.py)

**File to Create:** `backend/tests/test_certificates_ui_selenium.py`

**Test Cases to Implement:**

```python
class TestCertificatesPage:
    def test_certificates_page_loads(self):
        """Test that certificates page loads and displays correctly."""
        
    def test_certificate_list_displays(self):
        """Test that certificate list is displayed."""
        
    def test_filter_certificates_by_status(self):
        """Test filtering certificates by status."""
        
    def test_filter_certificates_by_ca(self):
        """Test filtering certificates by CA authority."""
        
    def test_request_certificate_modal(self):
        """Test opening and closing request certificate modal."""
        
    def test_request_private_certificate(self):
        """Test requesting a private certificate."""
        
    def test_request_public_certificate(self):
        """Test requesting a public certificate."""
        
    def test_certificate_detail_page(self):
        """Test navigating to certificate detail page."""
        
    def test_renew_certificate(self):
        """Test renewing a certificate."""
        
    def test_revoke_certificate(self):
        """Test revoking a certificate."""
        
    def test_download_certificate_pem(self):
        """Test downloading certificate PEM."""
        
    def test_enrollment_protocols_page(self):
        """Test enrollment protocols page loads."""
        
    def test_acme_directory_display(self):
        """Test ACME directory URL is displayed."""
        
    def test_scep_endpoint_display(self):
        """Test SCEP endpoint URL is displayed."""
        
    def test_est_endpoints_display(self):
        """Test EST endpoints are displayed."""
        
    def test_copy_to_clipboard(self):
        """Test copy-to-clipboard functionality."""
```

### 2. API Integration Tests

**File to Create:** `backend/tests/test_certificates_api.py`

**Test Cases:**
- Certificate API endpoints
- Enrollment protocol endpoints
- Error handling
- Authentication/authorization
- Tenant isolation (API level)

### 3. Component Unit Tests (Frontend)

**Files to Create:**
- `frontend/src/components/certificates/__tests__/CertificateList.test.tsx`
- `frontend/src/components/certificates/__tests__/CertificateDetail.test.tsx`
- `frontend/src/components/certificates/__tests__/EnrollmentProtocols.test.tsx`

**Test Framework:** Jest + React Testing Library

---

## How to Access the Feature

### Via UI Navigation

1. Log into SentinelGrid dashboard
2. Click "People & Access" in main sidebar
3. Click "Certificates" in IAM sub-navigation
4. You'll land on `/dashboard/iam/certificates`

### Direct URL

```
http://localhost:3000/dashboard/iam/certificates
```

### Quick Links

- **Certificate List:** `/dashboard/iam/certificates`
- **Enrollment:** `/dashboard/iam/certificates/enroll`
- **Certificate Detail:** `/dashboard/iam/certificates/{certificate_id}`

---

## Test Execution

### Run Backend Tests

```bash
# Run certificate service tenant isolation tests
cd backend/tests/cert_service
pytest test_tenant_isolation.py -v

# Run all certificate service tests (if more are added)
pytest backend/tests/cert_service/ -v
```

### Run Frontend Tests (When Created)

```bash
# Run Selenium UI tests (when created)
pytest backend/tests/test_certificates_ui_selenium.py -v

# Run with visible browser (for debugging)
HEADLESS=false pytest backend/tests/test_certificates_ui_selenium.py -v -s

# Run component unit tests (when created)
cd frontend
npm test -- certificates
```

---

## Summary

| Aspect | Status | Details |
|--------|--------|---------|
| **UI Location** | ✅ Complete | `/dashboard/iam/certificates` in IAM navigation |
| **Backend Tests** | ✅ Complete | Tenant isolation tests exist |
| **Frontend/UI Tests** | ❌ Missing | No Selenium or component tests |
| **API Tests** | ⚠️ Partial | Backend API tests exist, frontend API integration tests missing |

---

## Next Steps

1. **Create Selenium UI Tests**
   - Follow pattern from `test_iam_ui_selenium.py`
   - Test all certificate management flows
   - Test enrollment protocols page

2. **Create Component Unit Tests**
   - Test React components in isolation
   - Test user interactions
   - Test error states

3. **Create API Integration Tests**
   - Test API client functions
   - Test error handling
   - Test authentication

4. **Add to CI/CD Pipeline**
   - Include certificate tests in automated test runs
   - Run on every PR

---

**Last Updated:** 2025-01-28

