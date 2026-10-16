# PKI Certificate Management - UI Placement Decision

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-01-28  
**Decision:** Place PKI certificate management in IAM section

---

## Decision Summary

**PKI Certificates will be located at:** `/dashboard/iam/certificates`

**Rationale:**
1. **Logical Grouping:** Certificates are a form of machine/service identity, similar to API Keys and Secrets
2. **Existing Pattern:** IAM section already manages infrastructure credentials (Secrets, API Keys)
3. **User Mental Model:** Users expect to find certificate management alongside other identity/credential management
4. **Clear Separation:** IAM Certifications (access reviews) remain in Compliance section, separate from PKI certificates

---

## Navigation Structure

### Main Dashboard Sidebar
```
Dashboard
Security Alerts
Security Incidents
Security Monitoring
Detection Rules
People & Access → /dashboard/iam/people
Automated Response
AI Security
Compliance → /dashboard/compliance (includes IAM Certifications)
```

### IAM Section Sub-Navigation
```
People
My Account
My Access
Apps & Profiles
Devices
Security Events
Reports
Privileged Access
Secrets
API Keys
Certificates ← NEW (PKI certificate management)
Access Reviews
Policies
Chat
```

---

## Route Structure

### IAM Certifications (Existing - Compliance)
- **Route:** `/dashboard/certifications`
- **Purpose:** IAM entitlement access reviews
- **Section:** Compliance (top-level)
- **Components:** `components/certifications/`

### PKI Certificates (New - IAM)
- **Route:** `/dashboard/iam/certificates`
- **Purpose:** X.509/TLS certificate management
- **Section:** IAM (sub-navigation)
- **Components:** `components/certificates/`

---

## Implementation

### Files to Create/Modify

1. **Modify:** `frontend/src/app/(dashboard)/dashboard/iam/layout.tsx`
   - Add "Certificates" to `iamNavigation` array
   - Add `DocumentTextIcon` from Heroicons

2. **Create:** `frontend/src/app/(dashboard)/dashboard/iam/certificates/page.tsx`
   - Certificate list page

3. **Create:** `frontend/src/app/(dashboard)/dashboard/iam/certificates/[id]/page.tsx`
   - Certificate detail page

4. **Create:** `frontend/src/app/(dashboard)/dashboard/iam/certificates/ca/page.tsx`
   - CA management page

5. **Create:** `frontend/src/app/(dashboard)/dashboard/iam/certificates/enroll/page.tsx`
   - Enrollment wizard page

6. **Create:** `frontend/src/components/certificates/` directory
   - All certificate management components

---

## User Experience

### Accessing Certificates
1. User clicks "People & Access" in main sidebar
2. User sees IAM sub-navigation
3. User clicks "Certificates" 
4. User lands on `/dashboard/iam/certificates`

### Visual Consistency
- Certificates page will use same styling as other IAM pages
- Follows IAM section design patterns
- Consistent with Secrets and API Keys pages

---

## Benefits

✅ **Clear Organization:** Certificates grouped with related identity management features  
✅ **Intuitive Navigation:** Users find certificates where they expect (with other credentials)  
✅ **No Confusion:** Separate from IAM Certifications (access reviews)  
✅ **Scalable:** Easy to add more certificate-related features in the future  
✅ **Consistent UX:** Follows existing IAM section patterns  

---

## Future Considerations

If certificate management grows significantly, we could:
- Create a dedicated "Infrastructure" or "Security Infrastructure" section
- Add certificate management to multiple sections (IAM for management, Compliance for reporting)
- Create certificate-specific dashboards

For now, IAM section is the best fit.

