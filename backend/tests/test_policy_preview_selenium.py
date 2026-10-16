"""
Selenium check: preview a seed policy in the visual editor (read-only).

Requires:
- WEBSITE_URL (defaults to https://localhost:3443)
- TEST_EMAIL / TEST_PASSWORD (defaults to admin@demo.sentinelgrid.ai / DemoPassword123!)
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


def _make_driver():
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
    return drv


@pytest.mark.skipif(not (USERNAME and PASSWORD), reason="Admin credentials not set")
def test_preview_seed_policy_readonly():
    drv = _make_driver()
    try:
        login(drv, base_url=BASE_URL, username=USERNAME, password=PASSWORD)
        drv.get(f"{BASE_URL}/dashboard/iam/policies?tab=authorization")

        # Ensure Authorization tab visible
        auth_tab = WebDriverWait(drv, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Authorization') and contains(., 'Visual')]"))
        )
        auth_tab.click()

        # Wait for seed cards and click Preview
        WebDriverWait(drv, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='policy-seed-card']"))
        )
        preview_links = drv.find_elements(By.CSS_SELECTOR, "[data-testid='policy-seed-preview']")
        assert preview_links, "No preview links found on seed cards"
        drv.execute_script("arguments[0].scrollIntoView(true);", preview_links[0])
        preview_links[0].click()

        # Wait for navigation to builder
        WebDriverWait(drv, 25).until(
            EC.url_contains("/dashboard/policies/builder")
        )

        # In builder: expect title first, then read-only badge and a non-empty name input
        WebDriverWait(drv, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='policy-builder-title']"))
        )
        WebDriverWait(drv, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='policy-builder-readonly']"))
        )
        name_input = WebDriverWait(drv, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Policy name']"))
        )
        WebDriverWait(drv, 20).until(
            lambda d: name_input.get_attribute("value") not in (None, "")
        )
        # Canvas should render at least one node for the seed policy preview
        WebDriverWait(drv, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".react-flow__node"))
        )
    finally:
        drv.quit()
