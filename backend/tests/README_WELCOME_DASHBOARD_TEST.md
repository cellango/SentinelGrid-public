# Welcome Dashboard E2E Test

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This Selenium test verifies the complete flow from login → onboarding → welcome dashboard.

## Test Overview

The test (`test_welcome_dashboard_flow.py`) performs the following:

1. **Login**: Logs in with test credentials
2. **Onboarding**: Goes through onboarding steps (skips optional steps)
3. **Welcome Dashboard Verification**: Verifies that:
   - Welcome dashboard is shown when onboarding is incomplete
   - All dashboard tiles load correctly (Security Pulse, Incidents, Cloud Posture, People & Access, Usage & Health)
   - Recommended Actions section is present
   - AI Chatbot button is available
   - Environment validation banner is displayed

## Prerequisites

1. **Services Running**: Make sure all services are up:
   ```bash
   docker-compose -f docker-compose.dev.yml up
   ```

2. **Chrome/Chromium**: Chrome browser must be installed for Selenium

3. **Python Dependencies**:
   ```bash
   pip install pytest selenium webdriver-manager
   ```

4. **Test Credentials**: Set environment variables (or use defaults):
   ```bash
   export TEST_USERNAME="admin@sentinelgrid.ai"
   export TEST_PASSWORD="admin123"
   export WEBSITE_URL="https://localhost:3443"
   ```

## Running the Test

### Option 1: Using the Test Script (Recommended)

The script automatically builds the frontend without cache and runs the test:

```bash
./scripts/run-welcome-dashboard-test.sh
```

### Option 2: Manual Steps

1. **Build frontend without cache**:
   ```bash
   cd frontend
   npm run build:no-cache
   cd ..
   ```

2. **Run the test**:
   ```bash
   cd backend
   pytest tests/test_welcome_dashboard_flow.py::TestWelcomeDashboardFlow::test_complete_flow_login_onboarding_dashboard -v -s
   ```

### Option 3: Run All Welcome Dashboard Tests

```bash
cd backend
pytest tests/test_welcome_dashboard_flow.py -v -s
```

## Test Configuration

### Environment Variables

- `WEBSITE_URL`: Frontend URL (default: `https://localhost:3443`)
- `TEST_USERNAME`: Login email (default: `admin@sentinelgrid.ai`)
- `TEST_PASSWORD`: Login password (default: `admin123`)
- `HEADLESS`: Run browser in headless mode (default: `false`)
- `CI`: Set to `true` for CI/CD environments (enables headless mode)

### Headless Mode

To run in headless mode (no browser window):

```bash
HEADLESS=true ./scripts/run-welcome-dashboard-test.sh
```

## Test Structure

### Main Test: `test_complete_flow_login_onboarding_dashboard`

This test:
1. Logs in with credentials
2. Navigates through onboarding steps (skips optional steps)
3. Verifies welcome dashboard loads with all components

### Helper Methods

- `_complete_onboarding()`: Handles onboarding wizard navigation
- `_verify_welcome_dashboard()`: Verifies dashboard tiles and components

## Expected Behavior

### When Onboarding is Incomplete

- User is redirected to `/dashboard/welcome`
- Welcome dashboard shows:
  - Environment validation banner
  - 5 main tiles (Security Pulse, Incidents, Cloud Posture, People & Access, Usage & Health)
  - Recommended Actions section
  - AI Chatbot button
  - Agent selection panels

### When Onboarding is Complete

- User is redirected to `/dashboard` (main dashboard)
- Welcome dashboard redirects to main dashboard if accessed directly

## Troubleshooting

### Test Fails at Login

- Check that services are running
- Verify credentials are correct
- Check browser console for errors (run in non-headless mode)

### Test Fails at Onboarding

- Onboarding steps may have changed - update selectors in `_complete_onboarding()`
- Check that Skip/Continue buttons are present

### Test Fails at Dashboard Verification

- Dashboard may still be loading - increase wait times
- Check that API endpoints are returning data
- Verify frontend build completed successfully

### Frontend Build Fails

- Clean build artifacts: `rm -rf frontend/.next`
- Clear npm cache: `npm cache clean --force`
- Reinstall dependencies: `cd frontend && npm install`

## Screenshots

Screenshots are saved to `/tmp/` on test failures:
- `/tmp/signup_test_timeout.png`
- `/tmp/payment_redirect_issue.png`
- `/tmp/dashboard_load_failure.png`

## CI/CD Integration

For CI/CD pipelines, set:
```bash
export CI=true
export HEADLESS=true
export WEBSITE_URL="https://your-test-environment"
```

The test will automatically run in headless mode and use appropriate timeouts.

