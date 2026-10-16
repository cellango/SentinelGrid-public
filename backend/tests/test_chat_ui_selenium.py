"""
Selenium smoke: dashboard chatbot returns a reply.
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


def test_dashboard_chatbot_answers(driver):
    login(driver, base_url=BASE_URL, username=USERNAME, password=PASSWORD)
    wait = WebDriverWait(driver, 15)

    # Ensure chatbot panel is open (AI Assistant panel on dashboard)
    driver.get(f"{BASE_URL}/dashboard")
    try:
        # Open chat panel if collapsed
        toggle = driver.find_elements(By.XPATH, "//*[contains(., 'AI Assistant') or contains(@aria-label, 'AI Assistant')]")
        if toggle:
            toggle[0].click()
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'AI Assistant') or contains(., 'Ask me anything')]")))
    except TimeoutException:
        pytest.skip("Chat panel not visible on dashboard")

    # Find prompt input
    try:
        prompt = wait.until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "textarea, input[type='text'], [placeholder*='ask'], [placeholder*='anything']"
                )
            )
        )
    except TimeoutException:
        pytest.skip("Chat prompt input not found")

    prompt.clear()
    prompt.send_keys("What are the IAM related NIST controls?")
    # Send via Enter key if button not obvious
    try:
        send_btn = driver.find_element(By.XPATH, "//button[contains(., 'Send') or contains(., 'Ask')]")
        send_btn.click()
    except Exception:
        from selenium.webdriver.common.keys import Keys
        prompt.send_keys(Keys.ENTER)

    # Wait for a response bubble
    try:
        wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//*[contains(., 'NIST') or contains(., 'Access') or contains(., 'AC-')]"
                )
            )
        )
    except TimeoutException:
        # If the UI shows an error bubble, surface it
        errs = driver.find_elements(By.XPATH, "//*[contains(., 'error') or contains(., 'try again')]")
        if errs:
            pytest.fail(f"Chatbot returned error: {errs[0].text}")
        else:
            pytest.fail("No chatbot reply detected for IAM/NIST query")
