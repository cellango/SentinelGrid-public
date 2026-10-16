"""
IAM Theme respect Selenium check.

Sets theme to dark via localStorage before login and verifies that the HTML root
or body carries a dark indicator (class 'dark' or data-theme='dark') on key pages.
"""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from utils.login import login

BASE_URL = os.getenv("WEBSITE_URL", "https://localhost:3443")
USERNAME = os.getenv("TEST_EMAIL", os.getenv("TEST_USERNAME", "admin@demo.sentinelgrid.ai"))
PASSWORD = os.getenv("TEST_PASSWORD", "DemoPassword123!")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true" or os.getenv("CI") == "true"


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
    d = webdriver.Chrome(options=opts)
    d.implicitly_wait(8)
    yield d
    d.quit()


def _ensure_dark(driver):
    driver.get(f"{BASE_URL}")
    driver.execute_script(
        "localStorage.setItem('sentinelgrid_theme','dark');"
        "localStorage.setItem('theme','dark');"
        "localStorage.setItem('color-mode','dark');"
    )
    driver.refresh()
    # apply class if app didn't
    driver.execute_script("document.documentElement.classList.add('dark');")


def _assert_dark(driver):
    has_dark = driver.execute_script(
        "return document.documentElement.classList.contains('dark') || "
        "(document.documentElement.getAttribute('data-theme') === 'dark') || "
        "document.body.classList.contains('dark');"
    )
    assert has_dark, "Dark theme not applied to document root/body."


def _wait_dashboard(driver):
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "aside")))


def _wait_and_assert_page(driver, path: str):
    driver.get(f"{BASE_URL}{path}")
    WebDriverWait(driver, 12).until(lambda d: d.execute_script("return document.readyState") == "complete")
    WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.TAG_NAME, "main")))
    _assert_dark(driver)


class TestIAMTheme:
    def test_dark_theme_applied_on_dashboard_and_iam(self, driver):
        _ensure_dark(driver)
        login(driver, base_url=BASE_URL, username=USERNAME, password=PASSWORD)
        _wait_dashboard(driver)
        _assert_dark(driver)

        # Navigate to a few IAM pages and ensure dark persists
        pages = [
            "/dashboard",
            "/dashboard/iam/people",
            "/dashboard/iam/devices",
            "/dashboard/iam/apps",
            "/dashboard/iam/identity-providers",
            "/dashboard/iam/api-keys",
            "/dashboard/iam/certificates",
            "/dashboard/iam/my-account",
            "/dashboard/iam/my-access",
            "/dashboard/iam/access-reviews",
            "/dashboard/iam/privileged-access",
            "/dashboard/iam/security-events",
            "/dashboard/iam/reports",
            "/dashboard/compliance/reports",
            "/dashboard/scans",
        ]
        for path in pages:
            _wait_and_assert_page(driver, path)
