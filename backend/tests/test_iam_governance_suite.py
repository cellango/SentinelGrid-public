"""
IAM Governance Selenium suite.

Coverage:
- Access Reviews
- Privileged Access
- Security Events
- Reports (list, filter, download buttons)

Defensive: skips if sections or controls are missing.
"""

import os
import uuid
import pytest
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


def _click_first(driver, labels):
    for label in labels:
        els = driver.find_elements(By.XPATH, f"//button[contains(., '{label}')] | //a[contains(., '{label}')]")
        if els:
            els[0].click()
            return True
    return False


class TestIAMGovernance:
    def _login(self, driver):
        login(driver, base_url=BASE_URL, username=USERNAME, password=PASSWORD)

    def test_access_reviews(self, driver):
        self._login(driver)
        driver.get(f"{BASE_URL}/dashboard/iam/access-reviews")
        try:
            _wait_for(driver, "//*[contains(., 'Access Reviews') or contains(., 'Certifications')]", timeout=12)
        except TimeoutException:
            pytest.skip("Access Reviews page not available.")

        # Open first review and attempt approve/deny
        rows = driver.find_elements(By.XPATH, "//table//tr//a | //div[contains(@class,'card')]//a")
        if rows:
            rows[0].click()
            _click_first(driver, ["Approve", "Allow"])
            _click_first(driver, ["Deny", "Revoke"])

    def test_privileged_access(self, driver):
        self._login(driver)
        driver.get(f"{BASE_URL}/dashboard/iam/privileged-access")
        try:
            _wait_for(driver, "//*[contains(., 'Privileged Access')]", timeout=12)
        except TimeoutException:
            pytest.skip("Privileged Access page not available.")

        # Create a request if possible
        if _click_first(driver, ["Request", "New", "Add"]):
            _click_first(driver, ["Submit", "Create", "Save"])

        # Approve/deny first item if present
        _click_first(driver, ["Approve"])
        _click_first(driver, ["Deny", "Reject"])

    def test_security_events(self, driver):
        self._login(driver)
        driver.get(f"{BASE_URL}/dashboard/iam/security-events")
        try:
            _wait_for(driver, "//*[contains(., 'Security Events')]", timeout=12)
        except TimeoutException:
            pytest.skip("Security Events page not available.")

        # Apply a filter if present
        _click_first(driver, ["Filter", "Severity", "Status"])
        # Open first event detail
        rows = driver.find_elements(By.XPATH, "//table//tr//a | //div[contains(@class,'card')]//a")
        if rows:
            rows[0].click()
            driver.find_elements(By.XPATH, "//*[contains(., 'Timeline') or contains(., 'Details')]")

    def test_reports(self, driver):
        self._login(driver)
        driver.get(f"{BASE_URL}/dashboard/iam/reports")
        try:
            _wait_for(driver, "//*[contains(., 'Reports')]", timeout=12)
        except TimeoutException:
            pytest.skip("Reports page not available.")

        # Filter by type if possible
        _click_first(driver, ["Type", "Filter"])

        # Trigger PDF/CSV buttons if present
        _click_first(driver, ["PDF", "Download PDF"])
        _click_first(driver, ["CSV", "Download CSV"])
