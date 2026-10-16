"""
Selenium E2E test for configuration/onboarding flow.
Headful by default so the user can watch the run.
"""

import os
import json
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from utils.login import login

@pytest.fixture(scope="session")
def driver():
    options = webdriver.ChromeOptions()
    if os.getenv("CI") == "true" or os.getenv("HEADLESS") == "true":
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    options.set_capability("acceptInsecureCerts", True)
    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(10)
    drv.maximize_window()
    yield drv
    drv.quit()



def _set_signup_services(driver, services: dict):
    # Ensure we are on the correct origin before touching localStorage
    driver.execute_script("localStorage.setItem('signup_services', arguments[0]);", json.dumps(services))


def _click(driver, xpath: str, timeout: int = 10):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath))).click()


def _fill(driver, selector: str, value: str, by: By = By.CSS_SELECTOR, timeout: int = 10):
    el = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
    el.clear()
    el.send_keys(value)
    return el


def _wait_for_step(driver, heading_text: str, timeout: int = 10) -> bool:
    """Wait for a step heading; return False if not visible in timeout."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, f"//h2[contains(., '{heading_text}')]"))
        )
        return True
    except TimeoutException:
        return False


class TestOnboardingFlow:
    def test_onboarding_paths_headful(self, driver):
        """
        Full headful run through onboarding with all service paths enabled.
        In dev mode, simulates payment completion to enter onboarding; runs through wizard.
        """
        base_url = os.getenv("WEBSITE_URL", "https://localhost:3443")
        email = os.getenv("TEST_EMAIL", "admin@demo.sentinelgrid.ai")
        password = os.getenv("TEST_PASSWORD", "DemoPassword123!")

        # Login
        login(driver, base_url=base_url, username=email, password=password)

        # Seed services so wizard shows every step (cloud/git/appsec/ai/ticketing)
        _set_signup_services(
            driver,
            {
                "cloud": True,
                "git": True,
                "appsec": True,
                "aiShield": "hosted",
                "socManaged": False,  # show ticketing step
            },
        )

        # Start onboarding wizard directly
        driver.get(f"{base_url}/onboarding")
        WebDriverWait(driver, 30).until(lambda d: "/onboarding" in d.current_url or "/dashboard" in d.current_url)
        if "/dashboard" in driver.current_url:
            print("Onboarding already complete; skipping wizard.")
            return

        # Step 1: Identity (choose SentinelGrid Identity) — skip if already completed
        if _wait_for_step(driver, "Connect Your Identity", timeout=12):
            try:
                _click(driver, "//label[contains(., 'SentinelGrid Identity')]", timeout=5)
                _click(driver, "//button[contains(., 'Continue') and not(contains(., 'Connecting'))]", timeout=10)
            except TimeoutException:
                print("Identity step likely completed; moving to next step.")

        # Step 2: Cloud (pick AWS, enter dummy values)
        if _wait_for_step(driver, "Connect Your Cloud", timeout=15):
            _click(driver, "//button[.//div[contains(text(),'AWS')]]", timeout=10)
            _fill(driver, "input[placeholder='123456789012']", "123456789012")
            _fill(driver, "input[placeholder='arn:aws:iam::123456789012:role/SentinelGridMonitorRole']", "arn:aws:iam::123456789012:role/SentinelGridMonitorRole")
            _click(driver, "//button[contains(., 'Continue') and not(contains(., 'Connecting'))]", timeout=10)

        # Step 3: Endpoint — mark done so the step turns green
        if _wait_for_step(driver, "Deploy Endpoint Protection", timeout=12):
            try:
                _click(driver, "//button[contains(., 'Mark done') or contains(., 'Mark Done') or contains(., 'Mark done / test')]", timeout=10)
            except TimeoutException:
                print("Endpoint step action not found; continuing.")

        # Step 4: Git (select GitHub, provide token)
        if _wait_for_step(driver, "Connect Your Git Repositories", timeout=12):
            _click(driver, "//button[.//div[contains(text(),'GitHub')]]", timeout=10)
            _fill(driver, "input[placeholder='ghp_xxxxxxxxxxxx']", "ghp_dummy_token_for_test")
            _click(driver, "//button[contains(., 'Complete Setup')]", timeout=10)

        # Step 5: AppSec
        if _wait_for_step(driver, "Application Security", timeout=12):
            _fill(driver, "input[placeholder='https://apps.yourdomain.com']", "https://example.com")
            _fill(driver, "form input[type='password']", "test-secret-123")
            _fill(driver, "input[placeholder='customer-portal']", "customer-portal")
            _fill(driver, "input[placeholder='https://apps.yourdomain.com/openapi.json']", "https://example.com/openapi.json")
            _click(driver, "//button[contains(., 'Save & Check Health')]", timeout=10)

        # Step 6: AI Shield (hosted)
        if _wait_for_step(driver, "AI Shield", timeout=12):
            _fill(driver, "input[placeholder='https://ai-shield.sentinelgrid.ai/gateway']", "https://example.com/ai")
            _fill(driver, "//input[@type='password']", "ai-secret-123", by=By.XPATH)
            _click(driver, "//button[contains(., 'Save & Check Health')]", timeout=10)

        # Step 7: Ticketing (keep internal)
        if _wait_for_step(driver, "Ticketing", timeout=12):
            _click(driver, "//button[contains(., 'Save & Check Health')]", timeout=10)

        # Final: Tenant readiness (skip so we can reach dashboard in test)
        if _wait_for_step(driver, "Tenant readiness", timeout=12):
            try:
                _click(driver, "//button[contains(., 'Skip')]", timeout=5)
            except TimeoutException:
                print("Skip not found on tenant readiness; continuing.")

        # After last step we should land on dashboard
        WebDriverWait(driver, 60).until(lambda d: "/dashboard" in d.current_url)
