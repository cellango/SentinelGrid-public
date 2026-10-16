"""
Selenium smoke test for the public marketing site (pricing plans table).

Validates that the three-tier plan table renders and the hero CTA anchors to #plans.
Defaults to the marketing site on https://localhost:3444; override with WEBSITE_PUBLIC_URL or WEBSITE_URL.
"""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_URL = os.getenv("WEBSITE_PUBLIC_URL", os.getenv("WEBSITE_URL", "https://localhost:3444"))
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
    drv = webdriver.Chrome(options=opts)
    drv.implicitly_wait(5)
    yield drv
    drv.quit()


def _wait_for_text(driver, locator, text, timeout=15):
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))
    WebDriverWait(driver, timeout).until(
        lambda d: text.lower() in d.find_element(*locator).text.lower()
    )


class TestWebsitePricing:
    def test_hero_cta_and_three_tiers_present(self, driver):
        driver.get(BASE_URL)

        # Click the hero CTA to scroll to plans
        cta = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "See plans"))
        )
        cta.click()

        # Plans section should be present
        plans = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "plans")))

        # Validate the three column headings are present
        _wait_for_text(driver, (By.ID, "plans"), "Protect")
        _wait_for_text(driver, (By.ID, "plans"), "Protect & Defend")
        _wait_for_text(driver, (By.ID, "plans"), "Protect, Defend & Comply")

        # Spot-check that the compliance row reflects inclusion for the top tier
        plans_text = plans.text.lower()
        assert "compliance & governance" in plans_text
        assert "included" in plans_text, "Compliance should be included for the top tier"
