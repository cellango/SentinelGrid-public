"""
Selenium smoke test: login as system admin and verify detection rule count.

Defaults:
- TEST_EMAIL: admin@sentinelgrid.ai
- TEST_PASSWORD: Admin123!@#SentinelGrid
- BASE_URL: https://localhost:3443
- API_BASE: http://localhost:8082  (api_gateway)
- EXPECTED_DETECTION_COUNT: 110 (system tenant currently has 110 rules)

Usage:
  HEADLESS=true TEST_EMAIL=... TEST_PASSWORD=... pytest backend/tests/test_detection_count_system.py -v -s
"""

import os
import time
import requests
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


def make_driver():
    options = webdriver.ChromeOptions()
    if os.getenv("HEADLESS", "true").lower() == "true":
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    options.set_capability("acceptInsecureCerts", True)
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    return driver


def login_and_get_token(driver, base_url: str, email: str, password: str) -> str:
    driver.get(f"{base_url}/login")
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
    except TimeoutException:
        pytest.fail("Login page did not load")

    driver.find_element(By.CSS_SELECTOR, "input[type='email']").clear()
    driver.find_element(By.CSS_SELECTOR, "input[type='email']").send_keys(email)
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").clear()
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(password)
    driver.find_element(By.XPATH, "//button[contains(normalize-space(.), 'Sign in')]").click()

    try:
        WebDriverWait(driver, 20).until(lambda d: "/dashboard" in d.current_url or "/app" in d.current_url)
    except TimeoutException:
        # Capture any inline error for easier debugging
        try:
            err = driver.find_element(By.CSS_SELECTOR, "[role='alert'], [class*='red']")
            pytest.fail(f"Login failed: {err.text}")
        except Exception:
            pytest.fail("Login did not redirect to dashboard")

    token = None
    for cookie in driver.get_cookies():
        if cookie.get("name") == "access_token":
            token = cookie.get("value")
            break
    if not token:
        pytest.fail("access_token cookie not found after login")
    return token


def fetch_detection_count(api_base: str, token: str, realm: str) -> int:
    resp = requests.get(
        f"{api_base}/api/v1/siem/detection-rules",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Realm": realm,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        pytest.fail(f"Detection rules API returned {resp.status_code}: {resp.text[:200]}")
    try:
        data = resp.json()
    except Exception as e:
        pytest.fail(f"Failed to parse detection rules response: {e}")
    if not isinstance(data, list):
        pytest.fail(f"Unexpected detection rules payload shape: {type(data)}")
    return len(data)


class TestSystemDetectionCount:
    def test_detection_count_matches_expected(self):
        base_url = os.getenv("BASE_URL", "https://localhost:3443")
        api_base = os.getenv("API_BASE", "http://localhost:8082")
        email = os.getenv("TEST_EMAIL", "admin@sentinelgrid.ai")
        password = os.getenv("TEST_PASSWORD", "Admin123!@#SentinelGrid")
        realm = os.getenv("REALM", "sg-admin")
        expected = int(os.getenv("EXPECTED_DETECTION_COUNT", "110"))

        driver = make_driver()
        try:
            token = login_and_get_token(driver, base_url, email, password)
            count = fetch_detection_count(api_base, token, realm)
            print(f"Detected {count} detection rules for user {email}")
            assert (
                count == expected
            ), f"Expected {expected} detection rules, found {count}"
        finally:
            driver.quit()
