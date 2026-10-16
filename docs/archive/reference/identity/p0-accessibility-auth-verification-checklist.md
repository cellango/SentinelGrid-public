# P0 Accessibility + Auth Verification Checklist

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Use this checklist for the final manual smoke pass on the P0 accessibility and auth hardening work.

## Keyboard Focus QA

### Shell + Header
- Confirm the skip link moves focus into the main dashboard region.
- Tab from the header into page content and verify the sticky header never obscures the focused control.
- Verify `Shift+Tab` returns focus predictably from page content back into header controls.

### Dashboard + Queue
- Open `/dashboard` and tab through the `Now Queue` dock, then expand and collapse it with keyboard only.
- Confirm focus stays visible while moving through queue item links and AI transparency controls.

### Alerts
- Open `/dashboard/alerts` and tab through row actions, bulk actions, filters, and graph links.
- Open an alert detail page and verify focus remains visible through:
  - recommended response actions
  - ownership panel
  - AI transparency panels
  - playbook confirm dialog

### Incidents
- Open `/dashboard/incidents` and tab through row actions for assign, containment, ticket, detail, and graph.
- Open an incident detail page and verify focus remains visible through quick remediation controls and comment entry.

### Compliance
- Open `/dashboard/compliance` and `/dashboard/compliance/reports`.
- Verify focus visibility through report actions, schedule actions, and remediation links.

### IAM
- Open `/dashboard/iam/people`.
- Verify keyboard access for:
  - search and filters
  - table rows
  - user detail drawer
  - birthright rules drawer

### Overlay + Drawer Behavior
- Open the mobile sidebar drawer and confirm `Tab` and `Shift+Tab` stay trapped inside it.
- Open any slide-over or modal and verify:
  - focus moves into the surface on open
  - `Escape` closes it
  - focus returns to the invoking trigger

## Auth Verification

### Source Audit Notes
- No `onPaste` handlers exist in:
  - `frontend/src/app/(marketing)/login/page.tsx`
  - `frontend/src/components/auth/PasswordResetModal.tsx`
- The `preventDefault()` calls in `PasswordResetModal` are only for:
  - `Tab` focus trapping
  - the empty-focus fallback case
- Login and MFA fields use native inputs with explicit `name` and `autoComplete` metadata.

### Browser Smoke Pass
- In Chrome, Safari, and one password-manager-enabled browser profile if available:
  - verify email/username autofill appears on `/login`
  - verify password autofill appears on `/login`
  - verify the submitted credentials work with autofill-filled fields

### MFA
- Trigger the MFA-required state on `/login`.
- Confirm the OTP field accepts:
  - typed numeric input
  - pasted one-time code input
  - platform one-time-code autofill where supported

### Password Reset Modal
- Open the password reset modal.
- Confirm password managers recognize the new password field.
- Confirm paste works in:
  - new password
  - confirm password
- Confirm the realm field does not auto-capitalize or auto-correct.

## Sign-off

- Date:
- Tester:
- Browsers used:
- Issues found:
