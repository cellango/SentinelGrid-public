"""
Selenium smoke test for Compliance Reports page.
Verifies the page loads and renders at least one report card for the demo tenant.
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
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    return driver


@pytest.mark.selenium
def test_compliance_reports_page_renders_cards():
    base_url = os.getenv("BASE_URL", "https://localhost:3443")
    email = os.getenv("TEST_EMAIL", "admin@demo.sentinelgrid.ai")
    password = os.getenv("TEST_PASSWORD", "DemoPassword123!")

    driver = make_driver()
    try:
        perform_login(driver, base_url=base_url, username=email, password=password)
        driver.get(f"{base_url}/dashboard/compliance/reports")

        # Wait for page heading
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h1[contains(., 'Compliance Reports')]"))
        )

        # Capture whether the API call carries Authorization
        logs = driver.execute_script("return performance.getEntries().map(e => e.name);")
        # Wait for either report cards or empty state message
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//div[contains(@class,'rounded-lg') and .//h3] | //p[contains(., 'No reports generated yet')]",
                )
            )
        )

        cards = driver.find_elements(By.XPATH, "//div[contains(@class,'rounded-lg') and .//h3]")
        assert len(cards) > 0, "Expected at least one compliance report card to render"
    finally:
        time.sleep(1)
        driver.quit()
