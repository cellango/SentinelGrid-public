# Onboarding Flows - Quick Start Implementation Checklist

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Status:** Ready to Start  
**Estimated Total Time:** 7-10 days  
**Priority:** P1

---

## Pre-Implementation Checklist

- [ ] Review `docs/archive/reference/identity/onboarding-implementation-review.md`
- [ ] Review `docs/ONBOARDING_FLOWS_PLAN.md`
- [ ] Set up development environment
- [ ] Verify all services are running (tenant_service, connector_service, orchestrator)
- [ ] Test existing `/api/v1/tenants/provision` endpoint
- [ ] Create feature branch: `feature/onboarding-flows`

---

## Day 1-2: Backend API Completion

### Morning: Tenant Service Extensions
- [ ] Add `GET /api/v1/tenants/{id}/integration-status` endpoint
  - Check identity provider connection status
  - Check cloud provider connection status
  - Return formatted status object
- [ ] Add `POST /api/v1/tenants/{id}/alert-preferences` endpoint
  - Accept email notification preferences
  - Store in database
- [ ] Add `POST /api/v1/tenants/{id}/invitations` endpoint
  - Accept list of email addresses
  - Create user invitations (via IAM Agent or Keycloak)
- [ ] Add Pydantic models for new endpoints
- [ ] Write unit tests

### Afternoon: Connector Service OAuth
- [ ] Review existing connector structure
- [ ] Create `services/oauth_service.py`
- [ ] Implement `POST /api/v1/connectors/oauth/init`
  - Generate OAuth URL for provider
  - Store state token
  - Return OAuth URL to frontend
- [ ] Implement `POST /api/v1/connectors/oauth/callback`
  - Exchange code for tokens
  - Store credentials (encrypted)
  - Test connection
  - Sync initial users
- [ ] Add `POST /api/v1/connectors/{id}/test` endpoint
- [ ] Add `POST /api/v1/connectors/{id}/sync` endpoint
- [ ] Start with Google Workspace OAuth (simplest)

---

## Day 3-4: Frontend Wizard Foundation

### Morning: Setup & Structure
- [ ] Create `frontend/src/app/onboarding/` directory
- [ ] Create `frontend/src/lib/api/onboarding.ts`
  - Add all API client functions
  - Add error handling
  - Add TypeScript types
- [ ] Create wizard state management (Zustand store or Context)
- [ ] Create `WizardContainer.tsx` component
  - Progress indicator
  - Step navigation
  - State persistence (localStorage)

### Afternoon: Step 1 - Account Creation
- [ ] Create `Step1Account.tsx`
- [ ] Create `CompanyForm.tsx` component
- [ ] Create `PasswordStrength.tsx` component
  - Real-time password validation
  - Visual strength indicator
- [ ] Create `IdpModeSelector.tsx` component
- [ ] Add form validation (Zod schema)
- [ ] Integrate with `POST /api/v1/tenants/provision`
- [ ] Add error handling
- [ ] Test end-to-end

---

## Day 5-6: Identity & Cloud Integration

### Morning: Step 2 - Identity Provider
- [ ] Create `Step2Identity.tsx`
- [ ] Create `ProviderSelector.tsx` with provider cards
- [ ] Create `OAuthConnection.tsx` component
- [ ] Create `ConnectionVerification.tsx` component
- [ ] Create `app/onboarding/oauth/callback/page.tsx`
  - Handle OAuth callback
  - Exchange code via backend
  - Show verification status
- [ ] Integrate OAuth flow
- [ ] Add connection testing UI
- [ ] Test Google Workspace OAuth flow

### Afternoon: Step 3 - Cloud Integration
- [ ] Create `Step3Cloud.tsx`
- [ ] Create `CloudProviderSelector.tsx`
- [ ] Create `AWSSetup.tsx` component
  - CloudFormation link
  - IAM Role ARN input
  - Region selection
  - Service selection
- [ ] Create `CloudConnectionVerification.tsx`
- [ ] Integrate with connector API
- [ ] Add connection testing
- [ ] Test AWS connection flow

---

## Day 7: Configuration & Welcome

### Morning: Step 4 - Configuration
- [ ] Create `Step4Configuration.tsx`
- [ ] Create `DetectionRulesConfig.tsx`
  - Checkbox list of baseline rules
  - Rule descriptions
- [ ] Create `AlertPreferences.tsx`
  - Email notification toggles
  - Notification email input
- [ ] Create `UserInvitations.tsx`
  - Email input list
  - Role selection
- [ ] Integrate with APIs
- [ ] Add validation

### Afternoon: Step 5 - Welcome
- [ ] Create `Step5Welcome.tsx`
- [ ] Create `SecuritySnapshotCard.tsx`
  - Fetch from orchestrator
  - Display security posture
  - Show AI insights
- [ ] Create `QuickStartCard.tsx`
  - Integration status checklist
  - Next steps
- [ ] Create `IntegrationStatus.tsx`
  - Real-time status display
- [ ] Add "Go to Dashboard" button
- [ ] Test complete flow

---

## Day 8: Polish & Error Handling

### Morning: Error Handling
- [ ] Add error boundary to wizard
- [ ] Add retry logic for failed API calls
- [ ] Add offline detection
- [ ] Improve error messages (user-friendly)
- [ ] Add loading states everywhere
- [ ] Add success animations

### Afternoon: Responsive Design & Accessibility
- [ ] Make all steps mobile-responsive
- [ ] Add ARIA labels
- [ ] Test keyboard navigation
- [ ] Test screen reader
- [ ] Add focus management
- [ ] Polish UI/UX

---

## Day 9: Testing

### Unit Tests
- [ ] Test all API endpoints
- [ ] Test form validation
- [ ] Test OAuth state management
- [ ] Test error handling

### Integration Tests
- [ ] Test complete onboarding flow
- [ ] Test OAuth callback flow
- [ ] Test connection verification
- [ ] Test error scenarios

### E2E Tests
- [ ] Test full flow with real Keycloak
- [ ] Test Google OAuth flow
- [ ] Test AWS connection
- [ ] Test resume from saved state

---

## Day 10: Documentation & Deployment

### Documentation
- [ ] Update API documentation
- [ ] Add inline code comments
- [ ] Create user guide (optional)
- [ ] Update README

### Deployment Prep
- [ ] Environment variable configuration
- [ ] OAuth redirect URLs configuration
- [ ] CloudFormation template deployment
- [ ] Database migration (if needed)

---

## Quick Reference: API Endpoints

### Tenant Service
```bash
# Step 1: Create tenant
POST /api/v1/tenants/provision
{
  "company_name": "Acme Corp",
  "admin_email": "admin@acme.com",
  "admin_password": "SecurePass123!",
  "idp_mode": "sentinelgrid"
}

# Step 4: Alert preferences
POST /api/v1/tenants/{tenant_id}/alert-preferences
{
  "email_notifications": {
    "critical": true,
    "high": false
  },
  "notification_email": "security@acme.com"
}

# Step 4: Invitations
POST /api/v1/tenants/{tenant_id}/invitations
{
  "emails": ["user1@acme.com", "user2@acme.com"],
  "role": "soc_analyst"
}

# Step 5: Integration status
GET /api/v1/tenants/{tenant_id}/integration-status
```

### Connector Service
```bash
# Step 2: Init OAuth
POST /api/v1/connectors/oauth/init
{
  "provider": "google_workspace",
  "tenant_id": "uuid",
  "redirect_uri": "https://app.sentinelgrid.com/onboarding/oauth/callback"
}

# Step 2: OAuth callback
POST /api/v1/connectors/oauth/callback
{
  "provider": "google_workspace",
  "code": "auth-code",
  "state": "state-token"
}

# Step 3: Create connector
POST /api/v1/connectors
{
  "tenant_id": "uuid",
  "type": "aws",
  "config": {
    "iam_role_arn": "arn:aws:iam::...",
    "regions": ["us-east-1"],
    "services": ["cloudtrail", "guardduty"]
  }
}

# Step 2, 3: Test connection
POST /api/v1/connectors/{connector_id}/test
{
  "tenant_id": "uuid"
}
```

### Detection Service
```bash
# Step 4: Enable rules
POST /api/v1/detection/rules/enable
{
  "tenant_id": "uuid",
  "rule_keys": ["failed_logins", "new_admin", "suspicious_cloud"]
}
```

### Orchestrator
```bash
# Step 5: Security snapshot
GET /api/v1/orchestrator/tenant/{tenant_id}/security-snapshot
```

---

## Common Issues & Solutions

### Issue: OAuth callback fails
**Solution:** 
- Check redirect URI matches exactly
- Verify state token is valid
- Check OAuth credentials are correct

### Issue: Connection test fails
**Solution:**
- Verify credentials are stored correctly
- Check network connectivity
- Review error logs

### Issue: Tenant creation fails
**Solution:**
- Check Keycloak is running
- Verify database connection
- Check for duplicate slug

### Issue: Security snapshot empty
**Solution:**
- Wait a few minutes for initial sync
- Check orchestrator logs
- Verify integrations are connected

---

## Testing Checklist

### Manual Testing
- [ ] Complete onboarding with SentinelGrid IdP
- [ ] Complete onboarding with Google Workspace
- [ ] Test AWS connection
- [ ] Test error scenarios (invalid email, weak password, etc.)
- [ ] Test resume from saved state
- [ ] Test on mobile device
- [ ] Test with screen reader

### Automated Testing
- [ ] All API endpoints return correct status codes
- [ ] Form validation works correctly
- [ ] OAuth flow completes successfully
- [ ] Error messages are user-friendly
- [ ] Progress is saved correctly

---

## Success Metrics

- ✅ Onboarding completes in < 30 minutes
- ✅ All steps work without errors
- ✅ OAuth flows work for at least Google Workspace
- ✅ Cloud connection can be tested
- ✅ Security snapshot displays correctly
- ✅ Mobile-responsive design works
- ✅ Zero Keycloak UI exposure

---

**Ready to start!** Begin with Day 1 tasks. 🚀

