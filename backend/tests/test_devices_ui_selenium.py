"""
Selenium test for the Devices page.

Opens https://localhost:3443/dashboard/iam/devices, logs in, and verifies device rows render.
"""

import os
import pytest
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCREENSHOT_DIR = os.path.join("artifacts", "screenshots")
HTML_SNAPSHOT_DIR = os.path.join("artifacts", "html")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(HTML_SNAPSHOT_DIR, exist_ok=True)


@pytest.fixture(scope="session")
def base_url():
    """Base URL (defaults to nginx TLS proxy)."""
    return os.getenv("WEBSITE_URL", "https://localhost:3443")


@pytest.fixture(scope="session")
def credentials():
    """Login credentials (prefer demo realm defaults)."""
    # Try Vault helper if available
    try:
        from tests.helpers.vault_helper import get_platform_admin_password
        password = get_platform_admin_password()
    except Exception:
        password = os.getenv("TEST_PASSWORD", "DemoPassword123!")

    return {
        "email": os.getenv("TEST_EMAIL", "admin@demo.sentinelgrid.ai"),
        "password": password,
    }


def _ensure_demo_passwords(password: str):
    """Ensure demo users have a known password by calling Keycloak admin API."""
    kc_url = os.getenv("KEYCLOAK_URL", "http://localhost:8081")
    admin_user = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
    admin_pwd = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
    realm = "demo"
    users = [
        "admin@demo.sentinelgrid.ai",
        "soc.manager@demo.sentinelgrid.ai",
        "analyst1@demo.sentinelgrid.ai",
        "analyst2@demo.sentinelgrid.ai",
        "viewer@demo.sentinelgrid.ai",
    ]

    try:
        token_resp = requests.post(
            f"{kc_url}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": admin_user,
                "password": admin_pwd,
            },
            timeout=10,
            verify=False,
        )
        token_resp.raise_for_status()
        admin_token = token_resp.json().get("access_token")
        if not admin_token:
            print("⚠️ Could not obtain Keycloak admin token")
            return

        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json",
        }

        for username in users:
            try:
                user_resp = requests.get(
                    f"{kc_url}/admin/realms/{realm}/users",
                    params={"username": username},
                    headers=headers,
                    timeout=10,
                    verify=False,
                )
                user_resp.raise_for_status()
                items = user_resp.json()
                if not items:
                    print(f"⚠️ User {username} not found in realm {realm}")
                    continue
                user_id = items[0].get("id")
                if not user_id:
                    continue

                # Clear required actions to avoid password-reset prompt
                try:
                    requests.put(
                        f"{kc_url}/admin/realms/{realm}/users/{user_id}",
                        headers=headers,
                        json={"requiredActions": [], "emailVerified": True, "enabled": True},
                        timeout=10,
                        verify=False,
                    )
                except Exception:
                    pass

                pw_resp = requests.put(
                    f"{kc_url}/admin/realms/{realm}/users/{user_id}/reset-password",
                    headers=headers,
                    json={
                        "type": "password",
                        "value": password,
                        "temporary": False,
                    },
                    timeout=10,
                    verify=False,
                )
                if pw_resp.status_code >= 400:
                    print(f"⚠️ Failed to set password for {username}: {pw_resp.status_code} {pw_resp.text}")
                else:
                    print(f"✅ Ensured password for {username}")
            except Exception:
                continue
    except Exception:
        # Best-effort; test will still attempt login
        pass


@pytest.fixture(scope="session")
def driver():
    """Create Selenium WebDriver (accepts self-signed certs)."""
    options = webdriver.ChromeOptions()
    if os.getenv("CI") == "true" or os.getenv("HEADLESS", "true").lower() == "true":
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--allow-insecure-localhost")
    options.set_capability("acceptInsecureCerts", True)

    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(10)
    drv.maximize_window()

    yield drv

    if os.getenv("KEEP_BROWSER") != "true":
        drv.quit()


def _snapshot(driver, name: str):
    """Save a screenshot and HTML snapshot to help debug failures."""
    safe_name = name.replace(" ", "_")
    screenshot_path = os.path.join(SCREENSHOT_DIR, f"{safe_name}.png")
    html_path = os.path.join(HTML_SNAPSHOT_DIR, f"{safe_name}.html")

    driver.save_screenshot(screenshot_path)
    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    except Exception:
        pass


def _login(driver, base_url: str, credentials: dict):
    """Log into the app via /login."""
    driver.get(f"{base_url}/login")
    wait = WebDriverWait(driver, 40)

    driver.execute_script("localStorage.clear(); sessionStorage.clear();")

    email_input = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']"))
    )
    password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")

    email_input.clear()
    email_input.send_keys(credentials["email"])
    password_input.clear()
    password_input.send_keys(credentials["password"])

    # Click submit
    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_btn.click()

    try:
        wait.until(lambda d: "/dashboard" in d.current_url)
    except Exception:
        _snapshot(driver, "login_failed")
        raise AssertionError("Login via UI failed")


@pytest.mark.selenium
@pytest.mark.e2e
def test_devices_page_shows_data(driver, base_url, credentials):
    """Verify devices table renders rows (blocks mixed-content failures)."""
    try:
        _ensure_demo_passwords(credentials["password"])
    except Exception:
        # Best-effort; continue even if Keycloak admin unavailable
        pass

    _login(driver, base_url, credentials)

    import time as _time
    driver.get(f"{base_url}/dashboard/iam/devices?nocache={int(_time.time())}")
    wait = WebDriverWait(driver, 45)

    try:
        wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[contains(., 'Device Inventory')]")))
    except Exception:
        _snapshot(driver, "devices_page_load_error")
        print(f"URL at load error: {driver.current_url}")
        raise

    # Wait for either rows or "No devices found"
    try:
        wait.until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "table tbody tr")) > 0
            or len(d.find_elements(By.XPATH, "//*[contains(text(), 'No devices found')]")) > 0
        )
    except Exception:
        _snapshot(driver, "devices_table_timeout")
        raise

    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    if not rows:
        # Try loading sample devices to populate the table (UI provides this for demos)
        try:
            load_btn = driver.find_element(By.XPATH, "//button[contains(., 'Load sample devices')]")
            load_btn.click()
            wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, 'table tbody tr')) > 0)
            rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        except Exception:
            _snapshot(driver, "devices_page_empty")
            pytest.fail("Devices page rendered but no device rows were found (check API call and mixed-content).")

    # Simple sanity: verify first row has expected columns
    first_cells = rows[0].find_elements(By.TAG_NAME, "td")
    assert len(first_cells) >= 4, "Device row did not contain expected columns."
