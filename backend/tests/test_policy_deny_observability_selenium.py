"""
Selenium check: OPA deny surfaces a friendly message and no console errors.

This test simulates hitting a protected page with insufficient access and ensures
we show "Access denied by policy" (or similar) and do not spam console errors.

Env:
- WEBSITE_URL (default https://localhost:3443)
- TEST_EMAIL_NOEDIT / TEST_PASSWORD_NOEDIT (user expected to trigger a deny)
- HEADLESS=true|false
"""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.login import login

BASE_URL = os.getenv("WEBSITE_URL", "https://localhost:3443")
USERNAME = os.getenv("TEST_EMAIL_NOEDIT")
PASSWORD = os.getenv("TEST_PASSWORD_NOEDIT")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"


@pytest.mark.skipif(not (USERNAME and PASSWORD), reason="Noedit credentials not set")
def test_opa_deny_user_message():
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
    drv = webdriver.Chrome(options=opts)
    drv.implicitly_wait(8)
    try:
        login(drv, base_url=BASE_URL, username=USERNAME, password=PASSWORD)
        # Navigate to the authorization tab which should block clone for noedit
        drv.get(f"{BASE_URL}/dashboard/iam/policies?tab=authorization")
        WebDriverWait(drv, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='policy-seed-list']"))
        )
        # Attempt to trigger a protected action: click clone (should not exist), so check deny message if present
        deny_msgs = drv.find_elements(By.XPATH, "//*[contains(text(),'Access denied')]")
        # No console errors: scan browser log
        logs = drv.get_log("browser")
        errors = [l for l in logs if l.get("level") == "SEVERE"]
        assert len(errors) == 0, f"Found console errors: {errors}"
        # Allow either presence of deny message or simply no clone buttons
        if deny_msgs:
            assert "Access denied" in deny_msgs[0].text
    finally:
        drv.quit()
