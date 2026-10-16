"""
Selenium smoke test for the Compliance Report Scheduler UI.
Validates that SOC 2 templates load into the scheduler and that the
Quarterly cadence option is available (ensures new backend endpoints are wired).
"""

import os
import time
import pytest
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


@pytest.fixture(scope="module")
def driver():
    """Create Selenium WebDriver instance."""
    options = webdriver.ChromeOptions()

    if os.getenv("CI") != "true" and os.getenv("HEADLESS") != "true":
        print("Running in non-headless mode - browser will be visible")
    else:
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

    options.add_argument("--disable-notifications")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--allow-insecure-localhost")
    options.set_capability('acceptInsecureCerts', True)

    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(10)
    drv.maximize_window()
    yield drv
    drv.quit()


def test_report_scheduler_shows_soc2_templates_and_quarterly_option(driver):
    base_url = os.getenv("WEBSITE_URL", "https://localhost:3443")
    email = os.getenv("TEST_USERNAME", "admin@demo.sentinelgrid.ai")
    password = os.getenv("TEST_PASSWORD", "DemoPassword123!")

    # Step 1: Get token via API and inject into localStorage to avoid UI auth flakiness
    login_resp = requests.post(
        "http://localhost:8082/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=10,
        verify=False,
    )
    login_resp.raise_for_status()
    login_json = login_resp.json()
    access_token = login_json.get("access_token")
    tenant_id = login_json.get("user", {}).get("tenant_id")
    assert access_token, "No access token from login API"
    assert tenant_id, "No tenant_id from login API"

    driver.get(base_url)
    driver.execute_script(
        """
        localStorage.setItem('access_token', arguments[0]);
        localStorage.setItem('tenant_id', arguments[1]);
        """,
        access_token,
        tenant_id,
    )

    # Step 2: Navigate to scheduler page
    driver.get(f"{base_url}/compliance/reports/schedule")

    def scheduler_loaded(drv):
        try:
            return (
                len(drv.find_elements(By.XPATH, "//h1[contains(text(), 'Report Scheduling')]")) > 0
                or len(drv.find_elements(By.CSS_SELECTOR, "select[data-testid='schedule-template-select']")) > 0
            )
        except Exception:
            return False

    WebDriverWait(driver, 40).until(scheduler_loaded)

    # Step 3: Verify frequency dropdown includes Quarterly
    freq_select = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "select[data-testid='schedule-frequency-select']"))
    )
    option_texts = [opt.text.strip() for opt in freq_select.find_elements(By.TAG_NAME, "option")]
    assert "Quarterly" in option_texts, "Quarterly option not found in frequency select"

    # Step 4: Verify SOC 2 templates load into template dropdown
    template_select = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "select[data-testid='schedule-template-select']"))
    )

    # Allow async fetch to populate options
    def soc2_option_present(drv):
        opts = drv.find_elements(By.CSS_SELECTOR, "select[data-testid='schedule-template-select'] option")
        return any("SOC 2" in o.text for o in opts)

    WebDriverWait(driver, 20).until(soc2_option_present)
    soc2_options = [o.text for o in template_select.find_elements(By.TAG_NAME, "option") if "SOC 2" in o.text]
    assert soc2_options, "SOC 2 templates not populated in scheduler template dropdown"

    # Basic UX sanity: page should not show generic error text
    page_source = driver.page_source.lower()
    assert "application error" not in page_source, "React application error detected on scheduler page"
    assert "not found" not in page_source, "Scheduler page returned 404 content"
