"""
Headful Selenium smoke test for the Scans page.

Checks:
- Table renders at least one row after login.
- Header does not include "Scanner".
- Type column values are logical scan types (not raw scanner engine names like trivy/prowler).
"""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.login import login as perform_login


FORBIDDEN_SCANNER_NAMES = {"trivy", "prowler", "semgrep", "gitleaks", "checkov", "zap", "git"}


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


def test_scans_page_hides_raw_scanners(driver):
    base_url = os.getenv("WEBSITE_URL", "https://localhost:3443")
    email = os.getenv("TEST_EMAIL", "admin@demo.sentinelgrid.ai")
    password = os.getenv("TEST_PASSWORD", "DemoPassword123!")

    driver.delete_all_cookies()
    driver.get(f"{base_url}/login")
    driver.execute_script("localStorage.clear(); sessionStorage.clear();")

    perform_login(driver, base_url=base_url, username=email, password=password)

    driver.get(f"{base_url}/dashboard/scans")
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, "//h1[contains(., 'Scans')]")))

    # Ensure the table is present and has rows
    rows = WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.XPATH, "//table//tbody/tr"))
    )
    assert len(rows) > 0, "Expected at least one scan row"

    # Header should not contain Scanner
    headers = [h.text.strip().lower() for h in driver.find_elements(By.XPATH, "//table//thead//th")]
    assert "scanner" not in headers, f"Scanner column is still visible: {headers}"

    # Type column (second column) should not show raw scanner names
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        assert len(cells) >= 2, "Unexpected table structure; expected at least two columns"
        scan_type = cells[1].text.strip().lower()
        assert scan_type not in FORBIDDEN_SCANNER_NAMES, f"Raw scanner name leaked: {scan_type}"
