# Onboarding Flows - Implementation Review & Plan

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-01-28  
**Status:** 📋 Ready to Implement  
**Priority:** P1 (Critical for Hero Flow 1)  
**Version:** 1.0

---

## Executive Summary

This document provides a comprehensive review of the codebase and documentation for implementing customer-facing onboarding flows. The goal is to enable new customers to onboard in < 30 minutes and see real security findings within 24 hours.

**Key Finding:** We have excellent documentation and partial backend infrastructure, but need to build the complete frontend onboarding wizard and connect all the pieces.

---

## Current State Assessment

### ✅ What Exists

#### 1. **Documentation** (Excellent)
- ✅ `docs/ONBOARDING_FLOWS_PLAN.md` - Comprehensive 5-step onboarding plan
- ✅ `docs/AGRIBOTSAI_ONBOARDING_PLAN.md` - Manual onboarding guide (Terraform-based)
- ✅ `docs/DASHBOARD_REPORTING_STRATEGY.md` - Includes onboarding wizard design
- ✅ `docs/archive/reference/platform/next-steps-detailed.md` - Step-by-step execution guide

#### 2. **Backend Services** (Partially Complete)

**Tenant Service** ✅ **READY**
- Location: `backend/services/tenant_service/`
- Status: **Functional**
- Capabilities:
  - ✅ `POST /api/v1/tenants/provision` - Creates tenant + Keycloak realm + admin user
  - ✅ Database tenant creation
  - ✅ Keycloak realm creation
  - ✅ Client creation (web, api)
  - ✅ Admin user creation with tenant_id attribute
  - ✅ Role assignment (TENANT_ADMIN)
  - ✅ Protocol mapper configuration
- Files:
  - `app/api/provisioning.py` - API endpoint
  - `app/services/provisioning_service.py` - Business logic
  - `app/models/tenant.py` - Request/response models

**Connector Service** 🟡 **PARTIAL**
- Location: `backend/services/connector_service/`
- Status: **Structure exists, needs OAuth implementation**
- Existing:
  - ✅ Base connector structure
  - ✅ AWS connector (`connectors/aws.py`)
  - ✅ Google Workspace connector (`connectors/google_workspace.py`)
  - ✅ API endpoints (`api/connectors.py`)
- Missing:
  - 🔴 OAuth flow endpoints (`/oauth/init`, `/oauth/callback`)
  - 🔴 Connection testing endpoints
  - 🔴 Sync service integration

**IAM Agent** ✅ **READY**
- Location: `backend/services/iam_agent/`
- Status: **Functional**
- Capabilities:
  - ✅ Token validation
  - ✅ Keycloak admin API integration
  - ✅ User/role management
- Note: Can be used for custom auth endpoints if needed

**Orchestrator** ✅ **READY**
- Location: `backend/services/orchestrator/`
- Status: **Has security snapshot endpoint**
- Capabilities:
  - ✅ `GET /api/v1/orchestrator/tenant/{id}/security-snapshot`
  - ✅ AI-powered security analysis
  - ✅ Integration status tracking

**Detection Service** 🟡 **UNKNOWN**
- Location: `backend/services/detection_service/`
- Status: **Needs investigation**
- Required for: Step 4 (Enable baseline detection rules)

#### 3. **Infrastructure** ✅ **READY**
- ✅ Terraform configurations for Keycloak (`infra/customers/agribotsai/keycloak/terraform/`)
- ✅ Onboarding script (`infra/shared/scripts/onboard-customer.sh`)
- ✅ Database schema with tenants table
- ✅ Keycloak v25.x setup

#### 4. **Frontend** 🔴 **MISSING**
- Location: `frontend/src/app/`
- Status: **No onboarding UI exists**
- Existing:
  - ✅ Dashboard structure (`app/dashboard/`)
  - ✅ Layout components
  - ✅ API client structure (`lib/api/`)
- Missing:
  - 🔴 Onboarding wizard (`app/onboarding/`)
  - 🔴 Step components
  - 🔴 OAuth callback handler
  - 🔴 Integration with tenant service API

---

## Implementation Plan

### Phase 1: Backend API Completion (2-3 days)

#### 1.1 Tenant Service - Add Integration Status Endpoint
**File:** `backend/services/tenant_service/app/api/provisioning.py`

```python
@router.get("/{tenant_id}/integration-status")
def get_integration_status(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """Get integration status for onboarding Step 5."""
    # Check identity provider connection
    # Check cloud provider connection
    # Return status
```

**Estimated Effort:** 0.5 day

#### 1.2 Connector Service - OAuth Flow
**Files:**
- `backend/services/connector_service/app/api/connectors.py` - Add OAuth endpoints
- `backend/services/connector_service/app/services/oauth_service.py` - NEW

**Endpoints to Add:**
```python
POST /api/v1/connectors/oauth/init
POST /api/v1/connectors/oauth/callback
POST /api/v1/connectors/{id}/test
POST /api/v1/connectors/{id}/sync
```

**Providers to Support:**
- Google Workspace (priority)
- Microsoft 365 / Entra ID
- Okta
- SentinelGrid (skip OAuth)

**Estimated Effort:** 1.5-2 days

#### 1.3 Detection Service - Enable Rules Endpoint
**File:** `backend/services/detection_service/app/api/rules.py` (may need to create)

```python
POST /api/v1/detection/rules/enable
{
  "tenant_id": "uuid",
  "rule_keys": ["failed_logins", "new_admin", "suspicious_cloud"]
}
```

**Estimated Effort:** 0.5 day

#### 1.4 Tenant Service - Alert Preferences & Invitations
**File:** `backend/services/tenant_service/app/api/provisioning.py`

```python
POST /api/v1/tenants/{tenant_id}/alert-preferences
POST /api/v1/tenants/{tenant_id}/invitations
```

**Estimated Effort:** 0.5 day

---

### Phase 2: Frontend Onboarding Wizard (5-7 days)

#### 2.1 Wizard Container & Routing
**Files:**
- `frontend/src/app/onboarding/page.tsx` - Main wizard container
- `frontend/src/app/onboarding/oauth/callback/page.tsx` - OAuth callback handler

**Features:**
- Multi-step wizard with progress indicator
- Step navigation (back/next)
- State management (localStorage for resume)
- Step validation
- Error boundary

**Estimated Effort:** 1 day

#### 2.2 Step 1: Account Creation
**File:** `frontend/src/app/onboarding/steps/Step1Account.tsx`

**Components:**
- `CompanyForm.tsx` - Company name input
- `PasswordStrength.tsx` - Password validation UI
- `IdpModeSelector.tsx` - SentinelGrid vs Existing SSO

**API Integration:**
- `POST /api/v1/tenants/provision`

**Estimated Effort:** 1 day

#### 2.3 Step 2: Identity Provider Setup
**File:** `frontend/src/app/onboarding/steps/Step2Identity.tsx`

**Components:**
- `ProviderSelector.tsx` - Provider cards (Google, M365, Okta, SentinelGrid)
- `OAuthConnection.tsx` - OAuth flow UI
- `ConnectionVerification.tsx` - Status display

**API Integration:**
- `POST /api/v1/connectors/oauth/init`
- `POST /api/v1/connectors/oauth/callback`
- `POST /api/v1/connectors/{id}/test`

**Estimated Effort:** 1.5-2 days

#### 2.4 Step 3: Cloud Integration
**File:** `frontend/src/app/onboarding/steps/Step3Cloud.tsx`

**Components:**
- `CloudProviderSelector.tsx` - AWS, Azure, GCP cards
- `AWSSetup.tsx` - CloudFormation link + IAM Role ARN input
- `AzureSetup.tsx` - Azure setup instructions
- `GCPSetup.tsx` - GCP setup instructions
- `CloudConnectionVerification.tsx` - Connection test UI

**API Integration:**
- `POST /api/v1/connectors`
- `POST /api/v1/connectors/{id}/test`
- `POST /api/v1/connectors/{id}/sync`

**Estimated Effort:** 1.5-2 days

#### 2.5 Step 4: Initial Configuration
**File:** `frontend/src/app/onboarding/steps/Step4Configuration.tsx`

**Components:**
- `DetectionRulesConfig.tsx` - Rule checkboxes
- `AlertPreferences.tsx` - Email notification settings
- `UserInvitations.tsx` - Team member invitations

**API Integration:**
- `POST /api/v1/detection/rules/enable`
- `POST /api/v1/tenants/{tenant_id}/alert-preferences`
- `POST /api/v1/tenants/{tenant_id}/invitations`

**Estimated Effort:** 0.5-1 day

#### 2.6 Step 5: Welcome & Dashboard
**File:** `frontend/src/app/onboarding/steps/Step5Welcome.tsx`

**Components:**
- `WelcomeHeader.tsx` - Welcome message
- `SecuritySnapshotCard.tsx` - Security snapshot display
- `QuickStartCard.tsx` - Checklist and next steps
- `IntegrationStatus.tsx` - Integration status display

**API Integration:**
- `GET /api/v1/orchestrator/tenant/{id}/security-snapshot`
- `GET /api/v1/tenants/{id}/integration-status`

**Estimated Effort:** 1 day

---

### Phase 3: Integration & Testing (2-3 days)

#### 3.1 API Client Setup
**File:** `frontend/src/lib/api/onboarding.ts` - NEW

**Functions:**
- `provisionTenant()`
- `initOAuth()`
- `handleOAuthCallback()`
- `testConnection()`
- `enableDetectionRules()`
- `setAlertPreferences()`
- `inviteUsers()`
- `getSecuritySnapshot()`
- `getIntegrationStatus()`

**Estimated Effort:** 0.5 day

#### 3.2 Error Handling & Validation
- Form validation (Zod schemas)
- API error mapping
- Retry logic
- Offline handling
- Progress persistence

**Estimated Effort:** 0.5 day

#### 3.3 Testing
- Unit tests for components
- Integration tests for API flows
- E2E tests for complete flow
- Error scenario testing

**Estimated Effort:** 1-2 days

---

## Detailed Implementation Checklist

### Backend Tasks

#### Tenant Service
- [ ] Add `GET /api/v1/tenants/{id}/integration-status` endpoint
- [ ] Add `POST /api/v1/tenants/{id}/alert-preferences` endpoint
- [ ] Add `POST /api/v1/tenants/{id}/invitations` endpoint
- [ ] Add integration status model
- [ ] Add alert preferences model
- [ ] Add invitation model
- [ ] Write tests for new endpoints

#### Connector Service
- [ ] Create `oauth_service.py` for OAuth flow management
- [ ] Add `POST /api/v1/connectors/oauth/init` endpoint
- [ ] Add `POST /api/v1/connectors/oauth/callback` endpoint
- [ ] Add `POST /api/v1/connectors/{id}/test` endpoint
- [ ] Add `POST /api/v1/connectors/{id}/sync` endpoint
- [ ] Implement Google Workspace OAuth
- [ ] Implement Microsoft 365 OAuth
- [ ] Implement Okta OAuth
- [ ] Add OAuth state token management
- [ ] Add credential storage (encrypted)
- [ ] Write tests for OAuth flows

#### Detection Service
- [ ] Create `api/rules.py` if missing
- [ ] Add `POST /api/v1/detection/rules/enable` endpoint
- [ ] Add rule definitions (failed_logins, new_admin, suspicious_cloud)
- [ ] Write tests

### Frontend Tasks

#### Setup
- [ ] Create `app/onboarding/` directory structure
- [ ] Create `lib/api/onboarding.ts` API client
- [ ] Add onboarding state management (Zustand or Context)
- [ ] Create wizard container component
- [ ] Create progress indicator component
- [ ] Create error boundary component

#### Step 1: Account Creation
- [ ] Create `Step1Account.tsx`
- [ ] Create `CompanyForm.tsx`
- [ ] Create `PasswordStrength.tsx`
- [ ] Create `IdpModeSelector.tsx`
- [ ] Add form validation
- [ ] Add API integration
- [ ] Add error handling
- [ ] Add loading states

#### Step 2: Identity Provider
- [ ] Create `Step2Identity.tsx`
- [ ] Create `ProviderSelector.tsx`
- [ ] Create `ProviderCard.tsx` (Google, M365, Okta, SentinelGrid)
- [ ] Create `OAuthConnection.tsx`
- [ ] Create `ConnectionVerification.tsx`
- [ ] Add OAuth flow handling
- [ ] Add OAuth callback page
- [ ] Add connection testing
- [ ] Add error handling

#### Step 3: Cloud Integration
- [ ] Create `Step3Cloud.tsx`
- [ ] Create `CloudProviderSelector.tsx`
- [ ] Create `AWSSetup.tsx`
- [ ] Create `AzureSetup.tsx`
- [ ] Create `GCPSetup.tsx`
- [ ] Create `CloudFormationLink.tsx`
- [ ] Create `CloudConnectionVerification.tsx`
- [ ] Add CloudFormation template (if needed)
- [ ] Add connection testing
- [ ] Add error handling

#### Step 4: Configuration
- [ ] Create `Step4Configuration.tsx`
- [ ] Create `DetectionRulesConfig.tsx`
- [ ] Create `AlertPreferences.tsx`
- [ ] Create `UserInvitations.tsx`
- [ ] Add API integration
- [ ] Add validation
- [ ] Add error handling

#### Step 5: Welcome
- [ ] Create `Step5Welcome.tsx`
- [ ] Create `WelcomeHeader.tsx`
- [ ] Create `SecuritySnapshotCard.tsx`
- [ ] Create `QuickStartCard.tsx`
- [ ] Create `IntegrationStatus.tsx`
- [ ] Add API integration
- [ ] Add dashboard tour (optional)
- [ ] Add "Go to Dashboard" button

#### Common
- [ ] Add responsive design (mobile-friendly)
- [ ] Add loading skeletons
- [ ] Add error states
- [ ] Add success animations
- [ ] Add accessibility (ARIA labels)
- [ ] Add analytics tracking

---

## API Endpoints Summary

### Tenant Service
```
POST   /api/v1/tenants/provision              # Step 1
GET    /api/v1/tenants/{id}/integration-status # Step 5
POST   /api/v1/tenants/{id}/alert-preferences  # Step 4
POST   /api/v1/tenants/{id}/invitations        # Step 4
```

### Connector Service
```
POST   /api/v1/connectors/oauth/init          # Step 2
POST   /api/v1/connectors/oauth/callback      # Step 2
POST   /api/v1/connectors                     # Step 3
POST   /api/v1/connectors/{id}/test          # Step 2, 3
POST   /api/v1/connectors/{id}/sync          # Step 3
```

### Detection Service
```
POST   /api/v1/detection/rules/enable         # Step 4
```

### Orchestrator
```
GET    /api/v1/orchestrator/tenant/{id}/security-snapshot # Step 5
```

---

## File Structure

### Backend
```
backend/services/
├── tenant_service/
│   └── app/
│       ├── api/
│       │   └── provisioning.py          # ADD: integration-status, alert-preferences, invitations
│       └── models/
│           └── tenant.py                # ADD: IntegrationStatus, AlertPreferences, Invitation models
│
├── connector_service/
│   └── app/
│       ├── api/
│       │   └── connectors.py            # ADD: OAuth endpoints
│       └── services/
│           └── oauth_service.py         # NEW: OAuth flow management
│
└── detection_service/
    └── app/
        └── api/
            └── rules.py                # NEW or UPDATE: enable rules endpoint
```

### Frontend
```
frontend/src/
├── app/
│   └── onboarding/
│       ├── page.tsx                    # NEW: Wizard container
│       ├── steps/
│       │   ├── Step1Account.tsx        # NEW
│       │   ├── Step2Identity.tsx       # NEW
│       │   ├── Step3Cloud.tsx          # NEW
│       │   ├── Step4Configuration.tsx  # NEW
│       │   └── Step5Welcome.tsx        # NEW
│       ├── components/
│       │   ├── WizardContainer.tsx     # NEW
│       │   ├── ProgressIndicator.tsx  # NEW
│       │   ├── CompanyForm.tsx         # NEW
│       │   ├── PasswordStrength.tsx    # NEW
│       │   ├── ProviderSelector.tsx    # NEW
│       │   ├── OAuthConnection.tsx      # NEW
│       │   ├── CloudProviderSelector.tsx # NEW
│       │   ├── AWSSetup.tsx            # NEW
│       │   ├── DetectionRulesConfig.tsx # NEW
│       │   ├── AlertPreferences.tsx    # NEW
│       │   ├── UserInvitations.tsx      # NEW
│       │   ├── SecuritySnapshotCard.tsx # NEW
│       │   └── QuickStartCard.tsx       # NEW
│       └── oauth/
│           └── callback/
│               └── page.tsx             # NEW: OAuth callback handler
│
└── lib/
    └── api/
        └── onboarding.ts               # NEW: API client functions
```

---

## Dependencies & Prerequisites

### Backend
- ✅ FastAPI (already in use)
- ✅ Keycloak Admin API client (already in use)
- ✅ SQLAlchemy (already in use)
- 🔴 OAuth libraries (need to add):
  - `google-auth` for Google Workspace
  - `msal` for Microsoft 365
  - `okta` SDK for Okta

### Frontend
- ✅ Next.js 14 (already in use)
- ✅ React Hook Form (check if exists)
- ✅ Zod (check if exists)
- ✅ Tailwind CSS (already in use)
- 🔴 OAuth flow handling (built-in Next.js)

---

## Success Criteria

### Functional
- ✅ User can complete onboarding in < 30 minutes
- ✅ All 5 steps work end-to-end
- ✅ OAuth flows work for Google, M365, Okta
- ✅ Cloud integrations can be tested
- ✅ Security snapshot displays correctly
- ✅ Progress can be saved and resumed
- ✅ Errors are handled gracefully

### Technical
- ✅ Zero Keycloak UI exposure
- ✅ All operations via API
- ✅ Mobile-responsive design
- ✅ Accessible (WCAG 2.1 AA)
- ✅ Error logging and monitoring
- ✅ API response times < 2 seconds

### User Experience
- ✅ Clear instructions at each step
- ✅ Visual feedback for all actions
- ✅ Helpful error messages
- ✅ Progress indication
- ✅ Ability to go back and edit
- ✅ Welcome screen shows accurate status

---

## Risk Assessment

### High Risk
1. **OAuth Flow Complexity** - Multiple providers, different flows
   - **Mitigation:** Start with Google Workspace, add others incrementally
   - **Fallback:** Allow manual credential entry for advanced users

2. **Cloud Integration Setup** - Requires customer action in AWS/Azure/GCP
   - **Mitigation:** Provide clear instructions and CloudFormation templates
   - **Fallback:** Allow skipping and configuring later

3. **Connection Testing** - Need to verify integrations work
   - **Mitigation:** Implement robust test endpoints with clear error messages
   - **Fallback:** Allow proceeding with warnings

### Medium Risk
1. **State Management** - Complex wizard state
   - **Mitigation:** Use proven state management (Zustand/Context)
   - **Fallback:** Simplify to fewer steps if needed

2. **Error Recovery** - Users may encounter errors mid-flow
   - **Mitigation:** Save progress, allow resume, clear error messages
   - **Fallback:** Support contact option

### Low Risk
1. **UI/UX Polish** - May need iteration
   - **Mitigation:** Follow design system, user testing
   - **Fallback:** Can improve incrementally

---

## Next Steps

1. **Immediate (This Week)**
   - Review this plan with team
   - Prioritize backend API completion
   - Set up development environment
   - Create feature branch

2. **Week 1-2: Backend**
   - Complete Tenant Service endpoints
   - Implement OAuth flow in Connector Service
   - Add Detection Service endpoint
   - Write API tests

3. **Week 2-3: Frontend**
   - Build wizard container
   - Implement Steps 1-3
   - Add OAuth callback handling
   - Integrate with backend APIs

4. **Week 3-4: Frontend Completion**
   - Implement Steps 4-5
   - Add error handling
   - Add responsive design
   - Write component tests

5. **Week 4: Integration & Testing**
   - End-to-end testing
   - Error scenario testing
   - Performance optimization
   - Documentation

---

## References

- `docs/ONBOARDING_FLOWS_PLAN.md` - Detailed step-by-step plan
- `docs/AGRIBOTSAI_ONBOARDING_PLAN.md` - Manual onboarding reference
- `docs/DASHBOARD_REPORTING_STRATEGY.md` - UI/UX design guidance
- `backend/services/tenant_service/` - Existing provisioning service
- `backend/services/connector_service/` - Connector service structure

---

**Document Owner:** Product & Engineering  
**Last Updated:** 2025-01-28  
**Next Review:** After Phase 1 completion

