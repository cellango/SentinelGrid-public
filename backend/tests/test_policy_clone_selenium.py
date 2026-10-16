"""
Selenium check: clone a seed policy into the current tenant from the authorization tab.

Requires:
- WEBSITE_URL (defaults to https://localhost:3443)
- TEST_EMAIL / TEST_PASSWORD (defaults to admin@demo.sentinelgrid.ai / DemoPassword123!)
- HEADLESS=false to watch; defaults to headless in CI.
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
    drv = webdriver.Chrome(options=opts)
    drv.implicitly_wait(8)
    yield drv
    drv.quit()


def test_clone_policy_bundle(driver):
    login(driver, base_url=BASE_URL, username=USERNAME, password=PASSWORD)
    driver.get(f"{BASE_URL}/dashboard/iam/policies?tab=authorization")

    # Ensure Authorization tab is active (click if needed)
    try:
        auth_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Authorization') and contains(., 'Visual')]"))
        )
        auth_tab.click()
    except Exception:
        pytest.fail("Authorization tab not found/clickable")

    # Wait for seed bundles section and at least one seed card
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='policy-seed-card']"))
    )

    # Preview the first seed in read-only visual editor
    preview_links = driver.find_elements(By.CSS_SELECTOR, "[data-testid='policy-seed-preview']")
    assert preview_links, "No preview links found on seed policies"
    preview_links[0].click()
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='policy-builder-readonly']"))
    )
    driver.back()

    # Clone the first seed
    clone_buttons = driver.find_elements(By.CSS_SELECTOR, "[data-testid='policy-seed-clone']")
    assert clone_buttons, "No seed policies exposed to clone"
    clone_buttons[0].click()

    # Wait for refresh
    WebDriverWait(driver, 15).until(
        lambda d: "Cloning..." not in d.page_source
    )

    # Verify a policy card appears (best-effort check)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='policy-card']"))
    )

    # Open the cloned policy in visual editor (tenant-owned, not read-only)
    open_links = driver.find_elements(By.CSS_SELECTOR, "[data-testid='policy-open-visual']")
    assert open_links, "No visual editor links found on tenant policies"
    open_links[0].click()
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='policy-builder-title']"))
    )
