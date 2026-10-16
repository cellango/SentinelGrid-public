"""SIEM UI smoke: detection rules and playbooks pages load."""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.login import login as perform_login

BASE_URL = os.getenv("WEBSITE_URL", "https://localhost:3443")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true" or os.getenv("CI") == "true"
USERNAME = os.getenv("TEST_USERNAME", "admin@demo.sentinelgrid.ai")
PASSWORD = os.getenv("TEST_PASSWORD", "DemoPassword123!")


@pytest.fixture(scope="function")
def driver():
    opts = webdriver.ChromeOptions()
    if HEADLESS:
        opts.add_argument("--headless")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--allow-insecure-localhost")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1440,900")
    opts.set_capability("acceptInsecureCerts", True)
    drv = webdriver.Chrome(options=opts)
    drv.implicitly_wait(5)
    yield drv
    drv.quit()


def assert_page_heading(drv, css_selector, text_hint):
    wait = WebDriverWait(drv, 15)
    heading = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
    assert text_hint.lower() in heading.text.lower()


class TestSIEMDetectionPlaybookUI:
    def test_detection_rules_page_loads(self, driver):
        perform_login(driver, base_url=BASE_URL, username=USERNAME, password=PASSWORD)
        driver.get(f"{BASE_URL}/siem/detection-rules")
        cards = WebDriverWait(driver, 20).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "[data-testid='detection-card']")
        )
        visible = [c for c in cards if c.is_displayed()]
        print(f"Found {len(visible)} detection cards")
        if len(visible) == 0:
            driver.save_screenshot("/tmp/detections_empty.png")
            pytest.fail("Expected detections to be visible, found 0")

    def test_playbooks_page_loads(self, driver):
        perform_login(driver, base_url=BASE_URL, username=USERNAME, password=PASSWORD)
        driver.get(f"{BASE_URL}/dashboard/playbooks")
        cards = WebDriverWait(driver, 20).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "[data-testid='playbook-card']")
        )
        visible = [c for c in cards if c.is_displayed()]
        print(f"Found {len(visible)} playbook cards")
        if len(visible) == 0:
            driver.save_screenshot("/tmp/playbooks_empty.png")
            pytest.fail("Expected playbooks to be visible, found 0")
