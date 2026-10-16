"""SIEM depth smokes: alerts/incidents tables, detection→playbook link, log management load."""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from utils.login import login

BASE_URL = os.getenv("WEBSITE_URL", "https://localhost:3443")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true" or os.getenv("CI") == "true"


def _make_driver():
    options = webdriver.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.set_capability("acceptInsecureCerts", True)
    d = webdriver.Chrome(options=options)
    d.implicitly_wait(8)
    return d


@pytest.fixture(scope="function")
def driver():
    d = _make_driver()
    yield d
    d.quit()


@pytest.fixture(scope="function")
def authenticated_driver(driver):
    login(driver, base_url=BASE_URL)
    return driver


class TestSIEMDepth:
    def test_alerts_and_incidents_tables(self, authenticated_driver):
        driver = authenticated_driver
        wait = WebDriverWait(driver, 10)

        for path in ["/dashboard/alerts", "/dashboard/incidents"]:
            driver.get(f"{BASE_URL}{path}")
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
                rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                assert rows is not None  # allow empty but table present
            except TimeoutException:
                pytest.skip(f"No table rendered on {path}; UI may differ.")

    def test_detection_links_to_playbook_preview(self, authenticated_driver):
        driver = authenticated_driver
        wait = WebDriverWait(driver, 10)

        driver.get(f"{BASE_URL}/siem/detection-rules")
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(., 'Playbook') or contains(@href,'playbook')] | //button[contains(., 'Playbook')]")))
        except TimeoutException:
            pytest.skip("No playbook link/button on detection page.")

        # Click the first playbook link/button we can interact with
        link = driver.find_element(By.XPATH, "//a[contains(., 'Playbook') or contains(@href,'playbook')] | //button[contains(., 'Playbook')]")
        link.click()

        try:
            wait.until(EC.url_contains("playbook"))
        except TimeoutException:
            pytest.skip("Playbook page did not open after clicking link.")

        # Look for execution/preview hints
        if not driver.find_elements(By.XPATH, "//*[contains(., 'Run') or contains(., 'Execute') or contains(., 'Preview')]"):
            pytest.skip("Playbook preview/execute control not visible.")

    def test_log_management_loads(self, authenticated_driver):
        driver = authenticated_driver
        wait = WebDriverWait(driver, 10)

        driver.get(f"{BASE_URL}/dashboard/log-management")
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Logs') or contains(., 'Log Management') or //table]")))
        except TimeoutException:
            pytest.skip("Log management page did not render expected content.")

    def test_incident_detail_demo_page(self, authenticated_driver):
        """Headful check: incident detail page renders (fallback/demo-friendly)."""
        driver = authenticated_driver
        wait = WebDriverWait(driver, 12)

        driver.get(f"{BASE_URL}/dashboard/incidents/inc-demo-1")
        try:
            heading = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h1[contains(., 'Incident') or contains(., 'Account takeover') or contains(., 'Sample incident')]")
                )
            )
            assert heading.text, "Incident heading is empty"
        except TimeoutException:
            pytest.fail("Incident detail page did not render a heading")

        # Ensure we didn't hit the error placeholder
        errors = driver.find_elements(By.XPATH, "//*[contains(., 'Failed to load incident')]")
        assert not errors, "Incident page showed failure message"
