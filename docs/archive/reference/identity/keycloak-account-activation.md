# Keycloak Account Activation Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This document describes the account activation process for Keycloak users and provides solutions for automated testing.

## Problem

Keycloak v25.0 requires users with temporary passwords to complete required actions (like password update) via the UI before Direct Access Grants (password grant type) can be used. This blocks automated token generation for testing.

**Error Message:** `"Account is not fully set up"` or `"invalid_grant"`

## Solutions

### Solution 1: API-Based Activation (Preferred)

We provide a Python helper that attempts to activate accounts via the Keycloak Admin API:

```python
from backend.tests.helpers.keycloak_account_setup import setup_test_user

success = setup_test_user(
    keycloak_url="http://localhost:8081",
    realm="agribotsai",
    username="admin@agribotsai.com",
    password="ChangeMe123!",
    admin_username="admin",
    admin_password="admin"
)
```

**Limitations:** 
- May not work for all Keycloak configurations
- Some required actions may still require UI interaction
- Password policies may block API-based password setting

### Solution 2: UI-Based Activation (Selenium)

For cases where API activation doesn't work, we provide a Selenium-based solution:

```python
from backend.tests.selenium_test_account_activation import KeycloakUIActivation

browser = KeycloakUIActivation(headless=True)
try:
    success = browser.activate_account_via_ui(
        keycloak_url="http://localhost:8081",
        realm="agribotsai",
        username="admin@agribotsai.com",
        current_password="ChangeMe123!",
        new_password="ChangeMe123!",
        client_id="agribotsai-web",
        redirect_uri="http://localhost:3000"
    )
finally:
    browser.close()
```

### Solution 3: Command-Line Script

We provide a command-line script that tries both approaches:

```bash
# Try API first, fall back to UI
python3 scripts/activate-keycloak-account.py \
  --username admin@agribotsai.com \
  --password ChangeMe123!

# Force UI-based activation
python3 scripts/activate-keycloak-account.py \
  --username admin@agribotsai.com \
  --password ChangeMe123! \
  --use-ui
```

## How It Works

### API-Based Activation

1. **Get Admin Token**: Authenticate as admin user to master realm
2. **Get User Info**: Retrieve user details from Admin API
3. **Clear Required Actions**: Remove all required actions from user
4. **Set Password**: Set password as non-temporary
5. **Verify Email**: Mark email as verified

### UI-Based Activation

1. **Navigate to Login**: Open Keycloak login page via OAuth flow
2. **Login**: Enter username and current password
3. **Detect Required Actions**: Check if password update is required
4. **Update Password**: Fill in new password form if needed
5. **Complete**: Verify redirect to confirm activation

## Installation

### For API-Based Activation

```bash
pip install httpx
```

### For UI-Based Activation

```bash
# Install Selenium
pip install selenium webdriver-manager

# Install ChromeDriver (or use webdriver-manager for auto-install)
# macOS:
brew install chromedriver

# Or download from: https://chromedriver.chromium.org/
```

## Usage in Tests

### Pytest Fixture

```python
@pytest.fixture(scope="session", autouse=True)
def activate_test_account():
    """Activate test account before running tests."""
    from backend.tests.helpers.keycloak_account_setup import setup_test_user
    
    success = setup_test_user(
        KEYCLOAK_URL,
        TEST_REALM,
        TEST_USERNAME,
        TEST_PASSWORD
    )
    
    if not success:
        pytest.skip("Could not activate test account")
```

### Manual Activation Before Tests

```bash
# Activate account before running tests
python3 scripts/activate-keycloak-account.py \
  --username admin@agribotsai.com \
  --password ChangeMe123!

# Then run tests
pytest backend/tests/test_auth_flow_e2e.py
```

## Troubleshooting

### API Activation Fails

**Symptom:** `setup_test_user()` returns `False` or token generation still fails.

**Solutions:**
1. Check admin credentials are correct
2. Verify user exists in Keycloak
3. Try UI-based activation instead
4. Check Keycloak logs for errors

### UI Activation Fails

**Symptom:** Selenium test fails or browser doesn't load.

**Solutions:**
1. Install ChromeDriver: `brew install chromedriver` (macOS)
2. Check Chrome/Firefox is installed
3. Run with `--headless=false` to see what's happening
4. Check Keycloak is accessible from browser
5. Verify OAuth redirect URI is correct

### Browser Not Found

**Error:** `selenium.common.exceptions.WebDriverException`

**Solutions:**
1. Install Chrome or Firefox
2. Install ChromeDriver
3. Or use `webdriver-manager` for automatic driver management

### Still Getting "Account is not fully set up"

**Possible Causes:**
1. Realm has additional authentication flows requiring UI
2. Password policy requires UI interaction
3. Multi-factor authentication (MFA) is enabled
4. Other custom required actions

**Solutions:**
1. Check realm authentication flows in Keycloak Admin Console
2. Disable MFA for test realm
3. Review password policies
4. Check user's required actions via Admin API

## Best Practices

1. **Pre-activate Accounts**: Activate test accounts once and reuse them
2. **Use API First**: Try API-based activation before UI-based
3. **Cache Tokens**: Don't recreate accounts unnecessarily
4. **Isolate Tests**: Each test should work with pre-activated accounts
5. **Document Requirements**: Note which accounts need activation

## Keycloak Configuration Recommendations

For testing environments, consider:

1. **Disable Email Verification**: `verifyEmail=false` in realm settings
2. **Allow Password Grant**: Enable Direct Access Grants on test clients
3. **Relax Password Policies**: Use simpler policies for test users
4. **Disable MFA**: Turn off multi-factor authentication for test realm
5. **Skip Required Actions**: Configure realm to skip required actions where possible

## Related Files

- `backend/tests/helpers/keycloak_account_setup.py` - API-based activation
- `backend/tests/selenium_test_account_activation.py` - UI-based activation
- `scripts/activate-keycloak-account.py` - Command-line script
- `backend/tests/test_keycloak_setup.py` - Tests for activation helpers

## References

- [Keycloak Admin REST API](https://www.keycloak.org/docs-api/latest/rest-api/)
- [Keycloak Required Actions](https://www.keycloak.org/docs/latest/server_admin/#_required-actions)
- [Selenium Documentation](https://selenium-python.readthedocs.io/)

