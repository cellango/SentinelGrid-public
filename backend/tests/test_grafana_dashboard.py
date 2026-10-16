"""
Selenium smoke test for Grafana.
Logs in with the provisioned admin credentials and verifies the Dashboards landing page loads.
"""

import os
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
    options.add_argument("--disable-quic")
    options.add_argument("--host-resolver-rules=MAP localhost 127.0.0.1")
    options.set_capability("acceptInsecureCerts", True)

    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(10)
    drv.maximize_window()
    yield drv
    drv.quit()


def _login(drv, base_url, username, password):
    drv.get(f"{base_url}/login")
    user_input = WebDriverWait(drv, 20).until(
        EC.presence_of_element_located((By.NAME, "user"))
    )
    user_input.clear()
    user_input.send_keys(username)
    pwd_input = drv.find_element(By.NAME, "password")
    pwd_input.clear()
    pwd_input.send_keys(password)
    drv.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    # Grafana may prompt for password change on first login
    try:
        WebDriverWait(drv, 10).until(lambda d: "/login" not in d.current_url)
    except Exception:
        pass

    # Handle forced password change flow
    if "/login" in drv.current_url:
        try:
            new_pwd = os.getenv("GRAFANA_NEW_PASSWORD", "Admin12345!")
            new_pwd_input = WebDriverWait(drv, 15).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//input[@name='newPassword' or @name='new_password' or @type='password' and contains(@aria-label,'New password')]",
                    )
                )
            )
            new_pwd_input.clear()
            new_pwd_input.send_keys(new_pwd)
            confirm_input = drv.find_element(
                By.XPATH,
                "//input[@name='confirmNew' or @name='confirm_new_password' or @type='password' and contains(@aria-label,'Confirm')]",
            )
            confirm_input.clear()
            confirm_input.send_keys(new_pwd)
            drv.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            WebDriverWait(drv, 20).until(lambda d: "/login" not in d.current_url)
        except Exception:
            print(f"DEBUG current_url={drv.current_url}")
            print(f"DEBUG page snippet={drv.page_source[:500]}")
            raise AssertionError("Grafana login did not progress past the login/change-password page")

    WebDriverWait(drv, 20).until(
        lambda d: "/login" not in d.current_url and "login" not in d.title.lower()
    )


def test_grafana_dashboards_page(driver):
    base_url = os.getenv("GRAFANA_URL", "https://127.0.0.1:3000")
    username = os.getenv("GRAFANA_USERNAME", "admin")
    password = os.getenv("GRAFANA_PASSWORD", "admin")

    _login(driver, base_url, username, password)

    # Open the provisioned dashboard and verify it renders
    driver.get(f"{base_url}/d/obs-overview/observability-overview")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//h1[contains(text(),'Observability Overview')]"))
    )
    assert "Observability Overview" in driver.page_source
