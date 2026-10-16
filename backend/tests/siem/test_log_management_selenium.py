"""
Selenium test for the Log Management page.

Navigates to https://localhost:3443/dashboard/log-management, logs in,
and verifies that log cards render (or loads sample logs if empty).
"""

import os
import time
import pytest
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


@pytest.fixture(scope="session")
def base_url():
    """Base URL (defaults to nginx TLS proxy)."""
    return os.getenv("WEBSITE_URL", "https://localhost:3443")


@pytest.fixture(scope="session")
def credentials():
    """Login credentials (prefer demo realm defaults)."""
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
    """Best-effort: ensure demo users have the known password via Keycloak admin API."""
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
                    continue
                user_id = items[0].get("id")
                if not user_id:
                    continue

                requests.put(
                    f"{kc_url}/admin/realms/{realm}/users/{user_id}",
                    headers=headers,
                    json={"requiredActions": [], "emailVerified": True, "enabled": True},
                    timeout=10,
                    verify=False,
                )

                requests.put(
                    f"{kc_url}/admin/realms/{realm}/users/{user_id}/reset-password",
                    headers=headers,
                    json={"type": "password", "value": password, "temporary": False},
                    timeout=10,
                    verify=False,
                )
            except Exception:
                continue
    except Exception:
        # Best-effort only
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
    driver.save_screenshot(f"{safe_name}.png")
    try:
        with open(f"{safe_name}.html", "w") as f:
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

    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    submit_btn.click()

    try:
        wait.until(lambda d: "/dashboard" in d.current_url)
    except Exception:
        _snapshot(driver, "login_failed_log_management")
        raise AssertionError("Login via UI failed")


@pytest.mark.selenium
@pytest.mark.e2e
def test_log_management_shows_logs(driver, base_url, credentials):
    """Verify the log-management page renders log cards (loads samples if empty)."""
    try:
        _ensure_demo_passwords(credentials["password"])
    except Exception:
        pass

    _login(driver, base_url, credentials)

    driver.get(f"{base_url}/dashboard/log-management?nocache={int(time.time())}")
    wait = WebDriverWait(driver, 45)

    # Wait for page header
    try:
        wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//h1[contains(., 'Explore logs') or contains(., 'Log Management')]")
            )
        )
    except Exception:
        _snapshot(driver, "log_mgmt_header_missing")
        raise

    def _log_cards_present(drv):
        return len(drv.find_elements(By.XPATH, "//summary[contains(., 'View raw')]")) > 0

    # Wait for cards or "No logs found"
    try:
        wait.until(
            lambda d: _log_cards_present(d)
            or len(d.find_elements(By.XPATH, "//*[contains(text(), 'No logs found')]")) > 0
        )
    except Exception:
        _snapshot(driver, "log_mgmt_no_content")
        raise

    if not _log_cards_present(driver):
        # Trigger sample ingestion from the UI
        try:
            load_btn = driver.find_element(By.XPATH, "//button[contains(., 'Load sample logs')]")
            load_btn.click()
            # Wait for at least one card to appear
            wait.until(lambda d: _log_cards_present(d))
        except Exception:
            _snapshot(driver, "log_mgmt_load_failed")
            pytest.fail("Log Management page rendered but no logs appeared after loading samples.")

    # Exercise category filters (Identity/Auth and Network/Flow) and ensure cards remain
    for label in ["Identity/Auth", "Network/Flow"]:
        try:
            btn = driver.find_element(By.XPATH, f"//button[contains(., '{label}')]")
            btn.click()
            wait.until(lambda d: _log_cards_present(d))
        except Exception:
            _snapshot(driver, f"log_mgmt_filter_{label.replace('/', '_')}_failed")
            pytest.fail(f"Log Management filter '{label}' did not render logs.")

    # Final assertion: at least one log card visible
    cards = driver.find_elements(By.XPATH, "//summary[contains(., 'View raw')]")
    assert cards, "Log Management page did not display any log cards."
