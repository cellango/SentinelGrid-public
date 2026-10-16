"""
Plan tier gating Selenium checks.

We simulate plan tiers via localStorage override (plan_tier_override) to validate
nav visibility for Protect vs Protect, Defend & Comply.
"""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

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


def _set_plan_override(driver, tier: str):
    driver.get(BASE_URL)
    driver.execute_script("localStorage.setItem('plan_tier_override', arguments[0]);", tier)
    driver.refresh()


def _sidebar_text_now(driver) -> str:
    text = driver.execute_script("return document.querySelector('aside')?.innerText || '';")
    return (text or "").lower()


class TestPlanTierNav:
    def test_protect_hides_respond_and_prove_sections(self, driver):
        _set_plan_override(driver, "protect")
        login(driver, base_url=BASE_URL, username=USERNAME, password=PASSWORD)
        _set_plan_override(driver, "protect")  # reinforce after login
        driver.get(f"{BASE_URL}/dashboard")
        override_val = driver.execute_script("return localStorage.getItem('plan_tier_override');")
        assert override_val == "protect"
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script(
                "return Array.from(document.querySelectorAll('[data-section=\"respond\"],[data-section=\"prove\"],[data-nav-item=\"identity-events\"],[data-nav-item=\"access-reviews\"],[data-nav-item=\"privileged-access\"],[data-nav-item=\"iam-reports\"]')).filter(el => el.offsetParent !== null).length === 0;"
            )
        )
        # Visibility check above is authoritative; text may still contain hidden sections due to innerText

    def test_comply_shows_prove_and_identity_governance_items(self, driver):
        _set_plan_override(driver, "protect_defend_comply")
        login(driver, base_url=BASE_URL, username=USERNAME, password=PASSWORD)
        nav_text = _sidebar_text_now(driver)
        assert "prove & report" in nav_text, "Prove & Report section should be visible for comply tier"
        assert "identity events" in nav_text, "Identity Events should be visible for comply tier"
        assert "access reviews" in nav_text, "Access Reviews should be visible for comply tier"
