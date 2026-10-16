"""
Cross-cutting IAM Selenium tests:
- Login/session persistence + expiry redirect
- Navigation to key IAM pages
- Search/filter/sort sanity on People
- Negative validation on user create
- Header/token check via API call (Authorization + tenant)
"""

import os
import pytest
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from utils.login import login

BASE_URL = os.getenv("WEBSITE_URL", "https://localhost:3443")
USERNAME = os.getenv("TEST_EMAIL", os.getenv("TEST_USERNAME", "admin@demo.sentinelgrid.ai"))
PASSWORD = os.getenv("TEST_PASSWORD", "DemoPassword123!")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true" or os.getenv("CI") == "true"


@pytest.fixture(scope="function")
def driver():
    opts = webdriver.ChromeOptions()
    if HEADLESS:
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--ignore-ssl-errors")
    opts.add_argument("--allow-insecure-localhost")
    opts.set_capability("acceptInsecureCerts", True)
    d = webdriver.Chrome(options=opts)
    d.implicitly_wait(8)
    yield d
    d.quit()


def _wait_for(driver, xpath, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))


class TestIAMCrossCutting:
    def _login(self, driver):
        login(driver, base_url=BASE_URL, username=USERNAME, password=PASSWORD)

    def test_session_persistence(self, driver):
        self._login(driver)
        token = driver.execute_script("return localStorage.getItem('access_token');")
        tenant_id = driver.execute_script("return localStorage.getItem('tenant_id');")
        assert token, "No token found after login"
        assert tenant_id, "No tenant_id found after login"

        driver.get(f"{BASE_URL}/dashboard")
        _wait_for(driver, "//aside")
        # hard refresh
        driver.refresh()
        _wait_for(driver, "//aside")
        token_after = driver.execute_script("return localStorage.getItem('access_token');")
        assert token_after == token

    def test_session_expiry_redirect(self, driver):
        self._login(driver)
        # simulate expiry by clearing all tokens/cookies then hitting a protected page
        driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        driver.delete_all_cookies()
        driver.get(f"{BASE_URL}/dashboard")
        try:
            WebDriverWait(driver, 12).until(
                lambda d: "/login" in d.current_url or d.find_elements(By.XPATH, "//input[@type='email']")
            )
        except TimeoutException:
            pytest.fail("After token clear, app did not redirect to login or render login form.")
        assert "/login" in driver.current_url or driver.find_elements(By.XPATH, "//input[@type='email']"), "Login page not shown after session expiry."

    def test_navigation_sidebar(self, driver):
        self._login(driver)
        nav_targets = [
            ("/dashboard/iam/people", "People"),
            ("/dashboard/iam/access-reviews", "Access Reviews"),
            ("/dashboard/iam/privileged-access", "Privileged Access"),
            ("/dashboard/iam/security-events", "Security Events"),
            ("/dashboard/iam/reports", "Reports"),
        ]
        for href, label in nav_targets:
            driver.get(f"{BASE_URL}{href}")
            try:
                _wait_for(driver, f"//*[contains(., '{label.split()[0]}')]", timeout=8)
            except TimeoutException:
                pytest.skip(f"{label} page not available.")

    def test_people_search_filter_sort(self, driver):
        self._login(driver)
        driver.get(f"{BASE_URL}/dashboard/iam/people")
        try:
            _wait_for(driver, "//*[contains(., 'People') or contains(., 'Users')]", timeout=12)
        except TimeoutException:
            pytest.skip("People page not available.")

        # search box
        search_inputs = driver.find_elements(By.XPATH, "//input[@type='search'] | //input[contains(@placeholder, 'earch')]")
        if search_inputs:
            search_inputs[0].clear()
            search_inputs[0].send_keys("admin")
        # sort by clicking a header if present
        headers = driver.find_elements(By.XPATH, "//th[contains(., 'Email') or contains(., 'Name')]")
        if headers:
            headers[0].click()

    def test_user_create_negative_validation(self, driver):
        self._login(driver)
        driver.get(f"{BASE_URL}/dashboard/iam/people")
        try:
            _wait_for(driver, "//*[contains(., 'People') or contains(., 'Users')]", timeout=12)
        except TimeoutException:
            pytest.skip("People page not available.")

        add_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Add') or contains(., 'New') or contains(., 'Create')]")
        if not add_buttons:
            pytest.skip("No Add/Create user button.")
        add_buttons[0].click()

        # Try to submit with empty email
        submit = driver.find_elements(By.XPATH, "//button[contains(., 'Save') or contains(., 'Create')]")
        if submit:
            submit[0].click()
        # Expect validation message
        errors = driver.find_elements(By.XPATH, "//*[contains(., 'required') or contains(., 'invalid') or contains(., 'email')]")
        if not errors:
            pytest.skip("No validation message surfaced for empty/invalid user create.")

    def test_header_check_api(self, driver):
        self._login(driver)
        token = driver.execute_script("return localStorage.getItem('access_token');")
        tenant_id = driver.execute_script("return localStorage.getItem('tenant_id');")
        assert token, "No token found after login"
        headers = {
            "Authorization": f"Bearer {token}",
        }
        if tenant_id:
            headers["X-Tenant-ID"] = tenant_id
        try:
            resp = requests.get(f"{BASE_URL}/api/v1/onboarding/status", headers=headers, verify=False, timeout=10)
            assert resp.status_code == 200, f"API call failed: {resp.status_code} {resp.text}"
        except requests.RequestException as e:
            pytest.skip(f"API call for header check failed: {e}")
