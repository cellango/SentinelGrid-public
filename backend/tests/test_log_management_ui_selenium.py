"""
Selenium smoke: Log Management page shows seeded logs.
"""

import os
import re
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from utils.login import login

BASE_URL = os.getenv("WEBSITE_URL", "https://localhost:3443")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true" or os.getenv("CI") == "true"
USERNAME = os.getenv("TEST_USERNAME", os.getenv("TEST_EMAIL", "admin@demo.sentinelgrid.ai"))
PASSWORD = os.getenv("TEST_PASSWORD", "DemoPassword123!")


@pytest.fixture(scope="function")
def driver():
    opts = webdriver.ChromeOptions()
    if HEADLESS:
        opts.add_argument("--headless")
        # Increase stability in CI/headless mode
        opts.add_argument("--disable-features=VizDisplayCompositor")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1440,900")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--ignore-ssl-errors")
    opts.set_capability("acceptInsecureCerts", True)
    d = webdriver.Chrome(options=opts)
    d.implicitly_wait(8)
    yield d
    d.quit()


def _parse_log_count(text: str) -> int:
    """
    Extract integer from strings like "12 logs" or "1 log".
    """
    m = re.search(r"(\d+)\s+log", text.lower())
    return int(m.group(1)) if m else 0


def test_logs_visible_after_seed(driver):
    login(driver, base_url=BASE_URL, username=USERNAME, password=PASSWORD)
    wait = WebDriverWait(driver, 20)

    driver.get(f"{BASE_URL}/dashboard/log-management")

    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Log Management')]")))
    except TimeoutException:
        pytest.fail("Log Management page did not load (header missing)")

    # Wait for Results header to show a non-zero log count.
    try:
        count_el = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//p[contains(., 'Results')]/following::h3[1]")
            )
        )
    except TimeoutException:
        pytest.fail("Could not find results count on Log Management page")

    # Poll for up to ~90s for non-zero logs (UI can take time post-seed).
    last_text = ""
    cards = []
    for _ in range(90):
        last_text = count_el.text or ""
        cards = driver.find_elements(By.CSS_SELECTOR, "div.border-slate-800.bg-slate-900")
        if _parse_log_count(last_text) > 0 or cards:
            break
        driver.refresh()
        wait.until(EC.staleness_of(count_el))
        count_el = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//p[contains(., 'Results')]/following::h3[1]")
            )
        )
    else:
        pytest.fail(f"Logs not visible after seeding (last text: '{last_text}')")

    # Basic smoke: ensure at least one log item is rendered.
    cards = driver.find_elements(By.CSS_SELECTOR, "div.border-slate-800.bg-slate-900")
    assert cards, "Expected at least one log card after seeding"
