"""
Selenium smoke test for SOC 2 UI surfaces.
Validates SOC 2 dashboard, reports/scheduling link, and AI Activity page render for the demo tenant.
"""

import os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


@pytest.fixture(scope="module")
def driver():
    options = webdriver.ChromeOptions()
    if os.getenv("CI") != "true" and os.getenv("HEADLESS") != "true":
        print("Running in non-headless mode - browser will be visible")
    else:
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

    options.add_argument("--disable-notifications")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--allow-insecure-localhost")
    options.set_capability("acceptInsecureCerts", True)

    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(10)
    drv.maximize_window()
    yield drv
    drv.quit()


def _login(drv, base_url, email, password):
    drv.get(f"{base_url}/login")
    email_input = WebDriverWait(drv, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
    )
    email_input.send_keys(email)
    pwd_input = drv.find_element(By.CSS_SELECTOR, "input[type='password']")
    pwd_input.send_keys(password)
    drv.find_element(By.XPATH, "//button[contains(text(), 'Sign in')]").click()
    WebDriverWait(drv, 30).until(lambda d: d.execute_script("return localStorage.getItem('access_token')") is not None)


def test_soc2_ui_flows(driver):
    base_url = os.getenv("WEBSITE_URL", "https://localhost:3443")
    email = os.getenv("TEST_USERNAME", "admin@demo.sentinelgrid.ai")
    password = os.getenv("TEST_PASSWORD", "DemoPassword123!")

    _login(driver, base_url, email, password)

    # SOC 2 dashboard
    driver.get(f"{base_url}/dashboard/compliance")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//h1[contains(text(),'Compliance Dashboard')]"))
    )
    assert "SOC 2 Trust Services" in driver.page_source
    assert "SOC 2 Control Heatmap" in driver.page_source
    # CTA uses ampersand text on the button
    assert any(
        btn.text.strip().startswith("Reports") for btn in driver.find_elements(By.XPATH, "//a[contains(@href, '/compliance/reports')]")
    )

    # Reports page and schedule link
    driver.get(f"{base_url}/dashboard/compliance/reports")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//h1[contains(text(),'Compliance Reports')]"))
    )
    manage = driver.find_element(By.XPATH, "//a[contains(@href, '/compliance/reports/schedule')]")
    manage.click()
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//h1[contains(text(),'Report Scheduling')]"))
    )
    assert "Quarterly" in driver.page_source

    # AI Activity page
    driver.get(f"{base_url}/dashboard/compliance/ai-activity")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//h1[contains(text(),'AI Activity')]"))
    )
    assert "Export CSV" in driver.page_source
