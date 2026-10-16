# IAM UI Selenium Test Specification

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Comprehensive Selenium coverage for IAM features surfaced in the frontend:
- **People & Access** (left navbar)
- **Governance** section (Access Reviews, Privileged Access, Security Events, Reports)

## Preconditions / Test Data
- Frontend reachable at `https://localhost:3443` (self-signed cert accepted).
- Demo tenant with admin user: `admin@demo.sentinelgrid.ai / DemoPassword123!`.
- Access token set via UI login (tests rely on browser session cookies).
- At least one existing user, access profile, app, certificate, and access review to validate read flows; ability to create temporary objects is required.
- Multi-tenant headers enforced by the gateway; all calls must succeed with `Authorization` + tenant context.

## Test Categories

### 1) Authentication & Session
- Login succeeds with valid credentials; redirects to dashboard.
- Invalid password shows error and does not set cookies.
- Session persistence across hard refresh; token expiry triggers re-login prompt.
- Logout clears cookies/storage and redirects to login.

### 2) Navigation & Layout
- From dashboard, left nav links open:
  - People & Access
  - Governance → Access Reviews, Privileged Access, Security Events, Reports
- Breadcrumbs/top bars render tenant name; no missing assets or flicker on first load.
- All external links (if present) open in new tab without mixed-content warnings.

### 3) People & Access (core CRUD + UX)
- **People list**: loads without 4xx/5xx; pagination, search, and filters work; columns sortable.
- **People detail**: roles, groups, devices, and certificates panels render; API calls return 200.
- **Create user**: opens modal/form, validates required fields, submits successfully, new user appears in list.
- **Edit user**: change role/access profile, save, and verify persistence on reload.
- **Deactivate / Reactivate user**: status badge updates; deactivated users cannot be edited until reactivated.
- **Access Profiles**: list displays; create/edit/delete an access profile; assignment to a user reflects in UI.
- **Devices**: devices tab loads; search by hostname works; device detail shows certificates/last-seen data.
- **Apps / API Keys (if present)**: list, create, revoke, and confirm revoked keys disappear from active view.

### 4) Certificates (IAM → Certificates)
- List renders; search by CN works; filters for status (valid/expiring/expired) work.
- Download certificate/key buttons are present but require confirmation; cancellations do not trigger downloads.
- “Enroll” flow: submit CSR or request new cert, receive success toast, new cert appears in list with correct status.

### 5) Governance
- **Access Reviews**: list loads; filters (open/closed/past-due) work; opening a review shows assignees and decisions; approve/deny action updates status and reflects on reload.
- **Privileged Access**: list renders; request flow (if enabled) submits; approval/deny updates status; audit trail shows entry.
- **Security Events**: table renders; severity/status filters work; clicking an event opens detail with timeline and linked user/app; exporting (if present) triggers download without error.
- **Reports**: list shows available reports; filters by report type work; PDF/CSV download buttons return 200 and non-empty files; scheduled toggle (if present) can be enabled/disabled and persists.

### 6) Search, Filters, Sorting (cross-cutting)
- Text search debounces and returns matching rows.
- Sortable columns change order and persist across pagination.
- Clearing filters restores full result set.

### 7) Error & Negative Paths
- API 4xx/5xx surfaces user-friendly toast/banner; UI does not crash.
- Form validation blocks submit on missing required fields or invalid email format.
- Unauthorized access (manually navigate without token) redirects to login.

### 8) Multi-tenant & Headers
- For every API call observed in Network tab, `Authorization` and tenant headers are present; no 403s in steady state.
- Switching tenant (if UI supports) reloads data scoped to the new tenant; previous tenant’s data does not appear.

### 9) Performance / Stability (smoke)
- Hard refresh on People & Access and Governance pages does not cause infinite spinners; all key widgets resolve < 5s.
- No mixed-content errors in console; no repeated 403s on polling endpoints.

## Selenium Flow Skeletons (to implement)
- `test_login_and_nav`: login, visit People & Access, Governance subsections, assert titles and HTTP 200s.
- `test_people_crud`: create user → verify list → edit role → deactivate/reactivate → delete/cleanup.
- `test_access_profiles_crud`: create/edit/delete profile; assign to a user and verify assignment badge.
- `test_certificates_enroll`: request/enroll certificate; verify status and download buttons present.
- `test_access_reviews`: open review, approve/deny, verify status change and audit trail entry.
- `test_privileged_access`: submit request (if enabled), approve/deny, verify status.
- `test_security_events_filters`: apply severity/status filters, open detail, verify timeline.
- `test_reports_downloads`: filter by type, trigger PDF/CSV downloads, assert non-empty content length.
- `test_negative_validation`: submit empty required fields; assert validation messages and blocked submit.
- `test_session_expiry`: clear token, reload protected page → redirected to login.

## Additional Coverage: Apps, Roles, Teams, Birthrights, CMDB Devices

### IAM Applications (SSO / OAuth / BYO)
- App list renders; filters by type (SSO/OAuth/BYO) work.
- Create SSO app: fill metadata (ACS/EntityID/redirect), save, verify appears in list with correct type.
- Create OAuth app: client type (confidential/public), redirect URIs, scopes; save and verify client_id/client_secret presented once.
- BYO app registration: upload metadata/config, save, status active; editing updates endpoints; delete/disable works.
- Negative: missing redirect/metadata blocks submit; duplicate redirect URI triggers validation.

### Roles
- Roles list loads; search/sort works.
- Create role with permissions; assign to a user; role badge appears on user detail and persists after reload.
- Edit role permissions; verify change reflected on assigned users.
- Delete role blocked if in use (if enforced) or succeeds and unassigns from users.

### Teams
- Teams list renders; create team (name + members); verify members appear on team detail and user profiles.
- Edit team (add/remove members); changes persist after reload.
- Delete team; ensure removed from member profiles.

### Birthrights
- Birthright policy list renders; create birthright (apps/roles/groups); assign to population (all users or filtered); new users receive birthright on creation (create a test user, verify assigned roles/apps).
- Edit birthright to change included assets; verify delta applies on next sync/refresh.
- Disable/delete birthright; ensure no new assignments occur; existing assignments remain or are removed per policy (assert expected behavior).

### CMDB Devices
- Devices list loads; create device (hostname, owner, platform); new device appears with correct metadata.
- Edit device attributes; changes persist after reload.
- Negative: duplicate hostname or missing required fields blocks submit with validation message.

## Execution Notes
- Accept self-signed certs in the Selenium driver.
- Use explicit waits for API-driven components (tables, modals) instead of sleeps.
- Capture console/network errors; fail test on recurring 4xx/5xx for first-party endpoints.
- Ensure created test data is cleaned up (users, profiles, certs) to keep the environment stable.
