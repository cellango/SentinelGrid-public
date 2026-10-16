"""
Selenium check: bundle visibility by permission.

Case 1 (demo/admin): seed list is visible.
Case 2 (no-edit user): seed list present but clone buttons hidden.

Env:
- WEBSITE_URL (default https://localhost:3443)
- TEST_EMAIL / TEST_PASSWORD (admin/demo)
- TEST_EMAIL_NOEDIT / TEST_PASSWORD_NOEDIT (no edit rights)
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
ADMIN_USER = os.getenv("TEST_EMAIL", os.getenv("TEST_USERNAME", "admin@demo.sentinelgrid.ai"))
ADMIN_PASS = os.getenv("TEST_PASSWORD", "DemoPassword123!")
NOEDIT_USER = os.getenv("TEST_EMAIL_NOEDIT")
NOEDIT_PASS = os.getenv("TEST_PASSWORD_NOEDIT")
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


@pytest.mark.skipif(not (ADMIN_USER and ADMIN_PASS), reason="Admin credentials not set")
def test_bundle_visible_for_admin():
    drv = _make_driver()
    try:
        login(drv, base_url=BASE_URL, username=ADMIN_USER, password=ADMIN_PASS)
        drv.get(f"{BASE_URL}/dashboard/iam/policies?tab=authorization")
        WebDriverWait(drv, 15).until(
          EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='policy-seed-list']"))
        )
        cards = drv.find_elements(By.CSS_SELECTOR, "[data-testid='policy-seed-card']")
        assert len(cards) > 0, "Expected seed policies to be visible in Authorization tab"
    finally:
        drv.quit()


@pytest.mark.skipif(not (NOEDIT_USER and NOEDIT_PASS), reason="No-edit credentials not set")
def test_clone_hidden_for_noedit_user():
    drv = _make_driver()
    try:
        login(drv, base_url=BASE_URL, username=NOEDIT_USER, password=NOEDIT_PASS)
        drv.get(f"{BASE_URL}/dashboard/iam/policies?tab=authorization")
        WebDriverWait(drv, 15).until(
          EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='policy-seed-list']"))
        )
        cards = drv.find_elements(By.CSS_SELECTOR, "[data-testid='policy-seed-card']")
        assert cards, "Seed policies should render even for no-edit users"
        clone_buttons = drv.find_elements(By.CSS_SELECTOR, "[data-testid='policy-seed-clone']")
        assert len(clone_buttons) == 0
    finally:
        drv.quit()
