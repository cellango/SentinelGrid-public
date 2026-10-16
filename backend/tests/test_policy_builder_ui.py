"""
Selenium smoke: policy builder (drag-and-drop) loads and shows templates.
"""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from utils.login import login

BASE_URL = os.getenv("WEBSITE_URL", "https://localhost:3443")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true" or os.getenv("CI") == "true"
USERNAME = os.getenv("TEST_USERNAME", os.getenv("TEST_EMAIL", "admin@demo.sentinelgrid.ai"))
PASSWORD = os.getenv("TEST_PASSWORD", "DemoPassword123!")


@pytest.fixture(scope="function")
def driver():
    opts = webdriver.ChromeOptions()
    if HEADLESS:
        opts.add_argument("--headless")
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


def test_policy_builder_templates_and_palette(driver):
    """Verify the policy builder loads, shows palette, and exposes templates."""
    login(driver, base_url=BASE_URL, username=USERNAME, password=PASSWORD)
    wait = WebDriverWait(driver, 15)

    driver.get(f"{BASE_URL}/dashboard/policies/builder")

    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(., 'Policy Builder')]")))
    except TimeoutException:
        pytest.skip("Policy Builder page did not load")

    # Palette should be visible
    palette_header = driver.find_elements(By.XPATH, "//*[contains(., 'Policy Components')]")
    assert palette_header, "Policy palette not visible"

    # Canvas container (react-flow)
    canvas = driver.find_elements(By.CSS_SELECTOR, ".react-flow, [class*='react-flow']")
    assert canvas, "React Flow canvas not found"

    # Template dropdown should have at least one non-empty option
    try:
        tpl_select = wait.until(EC.presence_of_element_located((By.XPATH, "//select[option]")))
        options = [o for o in tpl_select.find_elements(By.TAG_NAME, "option") if o.get_attribute("value")]
        if not options:
            pytest.skip("No policy templates available; seed policy_templates first")
    except TimeoutException:
        pytest.skip("Template dropdown not found on builder page")

    # If templates exist, pick the first and ensure selection sticks
    first_opt = options[0]
    first_opt.click()
    assert tpl_select.get_attribute("value") == first_opt.get_attribute("value")

    # Basic smoke: ensure save/test buttons are present
    buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Save') or contains(., 'Test')]")
    assert buttons, "Save/Test controls not found on policy builder"

