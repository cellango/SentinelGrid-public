"""
Negative Selenium check: user without permissions should not be able to clone seed policies.

Requires:
- WEBSITE_URL (defaults to https://localhost:3443)
- TEST_EMAIL_NOEDIT / TEST_PASSWORD_NOEDIT: credentials for a user without policy edit rights.
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


@pytest.mark.skipif(not (USERNAME and PASSWORD), reason="TEST_EMAIL_NOEDIT/TEST_PASSWORD_NOEDIT not set")
def test_clone_policy_bundle_not_allowed():
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
        drv.get(f"{BASE_URL}/dashboard/iam/policies?tab=authorization")
        WebDriverWait(drv, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='policy-seed-list']"))
        )
        clone_buttons = drv.find_elements(By.CSS_SELECTOR, "[data-testid='policy-seed-clone']")
        # Expect no clone buttons if user lacks permission
        assert len(clone_buttons) == 0
    finally:
        drv.quit()
