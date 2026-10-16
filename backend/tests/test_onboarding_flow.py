"""Onboarding smoke: dev-mode happy path (skip payments, use defaults)."""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import os
import time

from utils.login import login

BASE_URL = os.getenv("WEBSITE_URL", "https://localhost:3443")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true" or os.getenv("CI") == "true"
TEST_TENANT_ID = os.getenv("TEST_TENANT_ID", None)


@pytest.fixture(scope="function")
def driver():
    """Create and configure WebDriver."""
    options = webdriver.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.set_capability('acceptInsecureCerts', True)
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


@pytest.fixture(scope="function")
def authenticated_session(driver):
    """Create an authenticated session by logging in (demo admin by default)."""
    login(driver, base_url=BASE_URL)
    return driver


class TestOnboardingSmoke:
    """Dev-mode onboarding smoke: use defaults and skip payments."""

    def test_onboarding_happy_path(self, authenticated_session):
        driver = authenticated_session
        wait = WebDriverWait(driver, 10)

        # Identity step (default SentinelGrid IdP)
        driver.get(f"{BASE_URL}/onboarding?step=1")
        try:
            sentinelgrid_option = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='radio' and contains(@value, 'sentinelgrid')]"))
            )
            sentinelgrid_option.click()
        except TimeoutException:
            pass
        driver.find_element(By.XPATH, "//button[contains(., 'Continue') or contains(., 'Next')]").click()

        # Cloud step (skip if allowed)
        try:
            skip_cloud = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Skip')]"))
            )
            skip_cloud.click()
        except TimeoutException:
            driver.find_element(By.XPATH, "//button[contains(., 'Continue') or contains(., 'Next')]").click()

        # Endpoint step (skip)
        try:
            skip_endpoint = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Skip')]"))
            )
            skip_endpoint.click()
        except TimeoutException:
            driver.find_element(By.XPATH, "//button[contains(., 'Continue') or contains(., 'Next')]").click()

        # Git/AppSec step (choose default or skip)
        try:
            skip_git = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Skip')]"))
            )
            skip_git.click()
        except TimeoutException:
            driver.find_element(By.XPATH, "//button[contains(., 'Continue') or contains(., 'Next')]").click()

        # Confirm we land on dashboard
        WebDriverWait(driver, 10).until(EC.url_contains("/dashboard"))
        assert "/dashboard" in driver.current_url

    def test_onboarding_config_variants(self, authenticated_session):
        driver = authenticated_session
        wait = WebDriverWait(driver, 10)

        selections = {
            "soc": None,
            "ticketing": [],
            "ai_mode": None,
            "git_selected": False,
        }

        # Identity step: SentinelGrid IdP
        driver.get(f"{BASE_URL}/onboarding?step=1")
        try:
            sg_option = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='radio' and contains(@value, 'sentinelgrid')]") )
            )
            sg_option.click()
        except TimeoutException:
            pass
        driver.find_element(By.XPATH, "//button[contains(., 'Continue') or contains(., 'Next')]").click()

        # SOC/ticketing step (if present): choose customer SOC, default ticketing SentinelGrid, options Jira/ServiceNow visible
        try:
            ticket_step = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(., 'SOC') and contains(., 'ticket')]"))
            )
            # Choose customer SOC if available
            try:
                cust_soc = driver.find_element(By.XPATH, "//input[@type='radio' and contains(@value, 'customer_soc')]")
                cust_soc.click()
                selections["soc"] = "customer"
            except Exception:
                pass
            # Ensure ticketing defaults rendered
            if driver.find_elements(By.XPATH, "//label[contains(., 'SentinelGrid')] | //input[contains(@value,'sentinelgrid_ticket')]"):
                selections["ticketing"].append("sentinelgrid")
            if driver.find_elements(By.XPATH, "//label[contains(., 'Jira')] | //input[contains(@value,'jira')]"):
                selections["ticketing"].append("jira")
            if driver.find_elements(By.XPATH, "//label[contains(., 'ServiceNow')] | //input[contains(@value,'servicenow')]"):
                selections["ticketing"].append("servicenow")
            driver.find_element(By.XPATH, "//button[contains(., 'Continue') or contains(., 'Next')]").click()
        except TimeoutException:
            pass

        # AI proxy choice (if present)
        try:
            ai_step = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(., 'AI') and contains(., 'proxy')]") )
            )
            # Choose hosted mode if option exists
            try:
                hosted = driver.find_element(By.XPATH, "//input[@type='radio' and contains(@value, 'hosted')]")
                hosted.click()
                selections["ai_mode"] = "hosted"
            except Exception:
                pass
            driver.find_element(By.XPATH, "//button[contains(., 'Continue') or contains(., 'Next')]").click()
        except TimeoutException:
            pass

        # AppSec/Git step
        driver.get(f"{BASE_URL}/onboarding?step=4")
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Git') or contains(., 'AppSec')]") ))
            # If Git selection exists, choose default and continue
            try:
                git_default = driver.find_element(By.XPATH, "//input[@type='radio' and contains(@value, 'default')]")
                git_default.click()
                selections["git_selected"] = True
            except Exception:
                pass
            driver.find_element(By.XPATH, "//button[contains(., 'Continue') or contains(., 'Next')]").click()
        except TimeoutException:
            pass

        WebDriverWait(driver, 10).until(EC.url_contains("/dashboard"))
        assert "/dashboard" in driver.current_url

        # Basic UI confirmation: check badges showing completed steps
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Tenant readiness') or contains(., 'Tenant readiness pending')]")))
        except TimeoutException:
            pass

        # Optional backend persistence validation via onboarding_progress API if env is provided
        if TEST_TENANT_ID:
            import httpx

            # API gateway likely on 8082 in docker-compose.minimal; allow override
            api_base = os.getenv("API_GATEWAY_URL", "http://localhost:8082")
            token = os.getenv("TEST_ACCESS_TOKEN", "")
            headers = {"X-Tenant-ID": TEST_TENANT_ID}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            with httpx.Client(timeout=10.0, verify=False) as client:
                resp = client.get(f"{api_base}/internal/onboarding/progress", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    services = data.get("services_selected", {})
                    if selections["soc"] == "customer":
                        assert services.get("soc") in ["customer", "customer_soc", True]
                    if "sentinelgrid" in selections["ticketing"]:
                        assert services.get("ticketing", {}).get("default", "") in ["sentinelgrid", True, "sg"]
                    if selections["ai_mode"]:
                        assert services.get("aiShield") in [selections["ai_mode"], True]
                    if selections["git_selected"]:
                        assert services.get("appsec") in [True, "true", "enabled"]
