# EJBCA Implementation - Component Clarification

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-01-28  
**Purpose:** Clarify what existing components to keep vs. what to create new

---

## Important Distinction

### Two Different Concepts

1. **IAM Certifications** (Existing) - Access entitlement reviews
   - Users certifying their access rights
   - Part of compliance/governance
   - **KEEP ALL EXISTING COMPONENTS**

2. **PKI Certificates** (New) - X.509/TLS certificates
   - TLS/mTLS certificates for services and agents
   - Certificate lifecycle management
   - **CREATE NEW COMPONENTS**

---

## Existing Components (KEEP AS-IS)

### Backend
- ✅ `backend/services/cert_service/` - **KEEP** (will enhance with EJBCA provider)
- ✅ `backend/services/cert_service/app/providers/step_ca.py` - **KEEP** (will add EJBCA alongside)
- ✅ `backend/services/cert_service/app/models.py` - **KEEP** (may enhance schema)
- ✅ `backend/services/cert_service/app/api/certificates.py` - **KEEP** (may add endpoints)
- ✅ `backend/services/cert_service/app/services/cert_service.py` - **KEEP** (will enhance)

### Frontend - IAM Certifications (KEEP)
- ✅ `frontend/src/components/certifications/` - **KEEP ALL**
  - `CertificationList.tsx` - IAM entitlement certification list
  - `CertificationCard.tsx` - IAM entitlement certification card
  - `BulkCertificationActions.tsx` - Bulk IAM certification actions
  - `ReviewPanel.tsx` - IAM entitlement review panel
- ✅ `frontend/src/app/(dashboard)/dashboard/certifications/page.tsx` - **KEEP**
- ✅ `frontend/src/lib/hooks/useCertifications.ts` - **KEEP**
- ✅ `frontend/src/lib/api/governance.ts` - **KEEP** (IAM certification API)

---

## New Components to Create

### Backend
- 🆕 `backend/services/cert_service/app/providers/ejbca.py` - **NEW** EJBCA provider
- 🆕 Additional API endpoints in `certificates.py` (if needed)
- 🆕 Database migrations for EJBCA-specific fields (if needed)

### Frontend - PKI Certificates (CREATE NEW)
- 🆕 `frontend/src/components/certificates/` - **NEW DIRECTORY**
  - `CertificateList.tsx` - PKI certificate list table
  - `CertificateCard.tsx` - PKI certificate summary card
  - `CertificateDetail.tsx` - PKI certificate details view
  - `CertificateChainViewer.tsx` - Certificate chain visualization
  - `RevokeCertificateModal.tsx` - Certificate revocation dialog
  - `RenewCertificateModal.tsx` - Certificate renewal dialog
  - `BootstrapTokenGenerator.tsx` - Bootstrap token creation UI
  - `ACMEConfigWizard.tsx` - ACME endpoint configuration
  - `SCEPEnrollmentGuide.tsx` - SCEP enrollment instructions
  - `CertificateExpiryAlert.tsx` - Expiration warnings
- 🆕 `frontend/src/app/(dashboard)/dashboard/iam/certificates/` - **NEW DIRECTORY** (under IAM section)
  - `page.tsx` - Certificate list page
  - `[id]/page.tsx` - Certificate detail page
  - `ca/page.tsx` - CA management page
  - `enroll/page.tsx` - Enrollment wizard page
- 🆕 Update `frontend/src/app/(dashboard)/dashboard/iam/layout.tsx` - **MODIFY** (add Certificates to navigation)
- 🆕 `frontend/src/lib/api/certificates.ts` - **NEW** PKI certificate API client
- 🆕 `frontend/src/lib/hooks/useCertificates.ts` - **NEW** React Query hooks for PKI certificates

---

## Naming Convention

### IAM Certifications (Existing)
- Path: `/dashboard/certifications` (plural)
- Components: `certifications/` (plural)
- API: `/api/v1/governance/certifications`
- Purpose: Access entitlement reviews

### PKI Certificates (New)
- Path: `/dashboard/iam/certificates` (under IAM section)
- Components: `certificates/` (plural, but different directory)
- API: `/api/v1/certificates` (existing backend API)
- Purpose: X.509/TLS certificate management
- Navigation: Added to IAM section sidebar (alongside Secrets, API Keys)

---

## No Duplication Strategy

1. **Different Routes:**
   - IAM: `/dashboard/certifications` → IAM entitlement reviews (Compliance section)
   - PKI: `/dashboard/iam/certificates` → X.509 certificate management (IAM section)

2. **Different Component Directories:**
   - IAM: `components/certifications/` → IAM components
   - PKI: `components/certificates/` → PKI components

3. **Different API Endpoints:**
   - IAM: `/api/v1/governance/certifications` → Governance service
   - PKI: `/api/v1/certificates` → Certificate service

4. **Different Data Models:**
   - IAM: Certification records (entitlement reviews)
   - PKI: Certificate records (X.509 certificates)

---

## Implementation Checklist

### Phase 1: Backend Enhancement
- [ ] Create `ejbca.py` provider (NEW)
- [ ] Enhance `cert_service.py` to support EJBCA (MODIFY)
- [ ] Keep Step-CA provider (KEEP)
- [ ] Add EJBCA configuration to docker-compose (NEW)

### Phase 2: Frontend Creation
- [ ] Create `components/certificates/` directory (NEW)
- [ ] Create certificate management pages (NEW)
- [ ] Create certificate API client (NEW)
- [ ] Create certificate hooks (NEW)
- [ ] **DO NOT** modify `components/certifications/` (KEEP)
- [ ] **DO NOT** modify `/dashboard/certifications` page (KEEP)

---

## Summary

**KEEP:**
- All existing `certifications/` components (IAM entitlement reviews)
- All existing `cert_service` backend code (will enhance, not replace)
- Step-CA provider (will add EJBCA alongside)

**CREATE NEW:**
- `certificates/` components (PKI certificate management)
- EJBCA provider (new provider alongside Step-CA)
- Certificate management UI pages

**NO DUPLICATION:**
- Different routes, directories, and purposes
- Clear separation between IAM certifications and PKI certificates

