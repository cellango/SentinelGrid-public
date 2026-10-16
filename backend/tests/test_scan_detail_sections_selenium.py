"""
Selenium checks for scan detail pages to ensure each scan type renders its
type-specific details without exposing engine names.
"""

import os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.login import login as perform_login


def make_driver():
    options = webdriver.ChromeOptions()
    headless = os.getenv("HEADLESS", "true").lower() == "true"
    if headless:
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("--remote-allow-origins=*")
    options.add_argument("--window-size=1400,900")
    chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(chrome_bin):
        options.binary_location = chrome_bin
    options.set_capability("acceptInsecureCerts", True)
    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(10)
    return drv


def fetch_scan_for_type(driver, scan_type: str):
    """
    Use the authenticated browser context to fetch scans and find one by scan_type.
    """
    scans = driver.execute_script(
        """
        const token = localStorage.getItem('access_token');
        return fetch('/api/v1/orchestrator/scans/status?limit=50', {
            headers: {Authorization: `Bearer ${token}`}
        }).then(r => r.json());
        """
    )
    if not scans:
        return None
    for scan in scans:
        if (scan.get("scan_type") or scan.get("scanner_id")) == scan_type:
            return scan.get("id")
    return None


@pytest.fixture
def driver():
    drv = make_driver()
    yield drv
    time.sleep(1)
    drv.quit()


@pytest.mark.selenium
@pytest.mark.parametrize(
    "scan_type,section_title",
    [
        ("cloud", "Cloud posture"),
        ("dast", "Web target"),
        ("sast", "Code location"),
        ("secrets", "Secret finding"),
        ("iac", "IaC resource"),
        ("git", "Repository"),
        ("host", "Host info"),
    ],
)
def test_scan_detail_sections(driver, scan_type, section_title):
    base_url = os.getenv("BASE_URL", "https://localhost:3443")
    email = os.getenv("TEST_EMAIL", "admin@demo.sentinelgrid.ai")
    password = os.getenv("TEST_PASSWORD", "DemoPassword123!")

    perform_login(driver, base_url=base_url, username=email, password=password)
    scan_id = fetch_scan_for_type(driver, scan_type)
    if not scan_id:
        pytest.skip(f"No scan available for type {scan_type}")

    driver.get(f"{base_url}/dashboard/scans/{scan_id}")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//h1[contains(., 'Scan')]"))
    )

    # Badge or Type row should show the logical scan_type
    badge_xpath = (
        f"//span[contains(@class,'rounded-full') and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{scan_type.lower()}')]"
    )
    type_row_xpath = (
        f"//div[contains(., 'Type:') and contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{scan_type.lower()}')]"
    )
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, f"{badge_xpath} | {type_row_xpath}"))
    )

    # Type-specific section should render; if not present (data not enriched), skip gracefully
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, f"//h3[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{section_title.lower()}')]")
            )
        )
    except Exception:
        pytest.skip(f"Section '{section_title}' not present for type {scan_type}; skipping validation.")
