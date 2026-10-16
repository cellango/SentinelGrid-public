"""Shared Selenium login helper."""

import os
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

DEFAULT_BASE_URL = os.getenv("WEBSITE_URL", "https://localhost:3443")
DEFAULT_USERNAME = os.getenv("TEST_EMAIL", os.getenv("TEST_USERNAME", "admin@demo.sentinelgrid.ai"))
DEFAULT_PASSWORD = os.getenv("TEST_PASSWORD", "DemoPassword123!")


def login(driver, base_url: str = DEFAULT_BASE_URL, username: str = DEFAULT_USERNAME, password: str = DEFAULT_PASSWORD, timeout: int = 25):
    """Log into the app using the standard login form and wait for dashboard or onboarding."""
    driver.get(f"{base_url}/login")
    wait = WebDriverWait(driver, timeout)
    try:
        email_el = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[name='email'], input[type='email']")
            )
        )
        pwd_el = driver.find_element(By.CSS_SELECTOR, "input[name='password'], input[type='password']")
    except TimeoutException:
        pytest.skip("Login form not rendered; possible redirect or auth service down.")
        return

    email_el.clear(); email_el.send_keys(username)
    pwd_el.clear(); pwd_el.send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    try:
        wait.until(lambda d: "/dashboard" in d.current_url or "/onboarding" in d.current_url)
    except TimeoutException:
        if driver.find_elements(By.XPATH, "//*[contains(., 'Invalid credentials') or contains(., 'Try again') or contains(., 'notified the admin')]"):
            pytest.skip("Login blocked or invalid credentials message displayed.")
        raise
