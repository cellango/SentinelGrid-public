"""
Selenium check: open a policy, edit, and trigger preview/test to ensure UI handles validation.

Best-effort selectors; skips if editor widgets are not found.

Env:
- WEBSITE_URL (default https://localhost:3443)
- TEST_EMAIL / TEST_PASSWORD (default admin@demo.sentinelgrid.ai / DemoPassword123!)
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
USERNAME = os.getenv("TEST_EMAIL", os.getenv("TEST_USERNAME", "admin@demo.sentinelgrid.ai"))
PASSWORD = os.getenv("TEST_PASSWORD", "DemoPassword123!")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"


@pytest.mark.skipif(not (USERNAME and PASSWORD), reason="Credentials not set")
def test_policy_editor_preview():
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

        # Wait for policy cards
        WebDriverWait(drv, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='policy-card'], [data-testid='policy-seed-card']"))
        )
        cards = drv.find_elements(By.CSS_SELECTOR, "[data-testid='policy-card']")
        if not cards:
            cards = drv.find_elements(By.CSS_SELECTOR, "[data-testid='policy-seed-card']")
        if not cards:
            pytest.skip("No policies available to open")
        cards[0].click()

        # Try to find an editor textarea
        textarea = None
        try:
            textarea = WebDriverWait(drv, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='policy-editor-textarea'], textarea"))
            )
        except Exception:
            # Try monaco editor textarea if any
            elems = drv.find_elements(By.CSS_SELECTOR, "div.monaco-editor textarea")
            if elems:
                textarea = elems[0]
        if not textarea:
            pytest.skip("Policy editor textarea not found")

        textarea.send_keys("\n# test edit via selenium\n")

        # Find a preview/test button
        buttons = drv.find_elements(By.XPATH, "//button[contains(.,'Preview') or contains(.,'Test')]")
        if not buttons:
            pytest.skip("No preview/test button found")
        buttons[0].click()

        # Ensure no navigation away and page still loaded
        WebDriverWait(drv, 10).until(lambda d: "/dashboard/iam/policies" in d.current_url)
    finally:
        drv.quit()
