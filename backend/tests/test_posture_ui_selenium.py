"""
Posture UI selenium check – reuses shared login fixtures so we actually log in
with the same flow as other IAM UI tests.
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Reuse the working login fixtures from IAM selenium suite
# Note: pytest rootdir is backend/tests, so the module name is bare.
pytest_plugins = ["test_iam_ui_selenium"]


def test_posture_dashboard(demo_logged_in_driver, base_url):
    driver = demo_logged_in_driver

    # Go to main dashboard and click the CTA in the Security Posture card
    driver.get(f"{base_url}/dashboard")
    storage = driver.execute_script(
        "return {token: localStorage.getItem('access_token'), tenant: localStorage.getItem('tenant_id')};"
    )
    print(f"LocalStorage auth snapshot: token_present={bool(storage.get('token'))}, tenant={storage.get('tenant')}")

    try:
        cta = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//p[contains(., 'Security Posture')]/ancestor::div[contains(@class,'bg-gradient')]"  # card
                                                   "//a[contains(., 'View posture')]"))
        )
    except TimeoutException:
        driver.save_screenshot("posture_cta_missing.png")
        try:
            logs = driver.get_log("browser")
            print("Browser logs:")
            for log in logs:
                print(log)
        except Exception as e:
            print(f"Unable to read browser logs: {e}")
        raise

    cta.click()

    try:
        WebDriverWait(driver, 30).until(EC.url_contains("/dashboard/posture"))
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//h3[contains(., 'Security Score')]"))
        )
    except TimeoutException:
        driver.save_screenshot("posture_dashboard_missing.png")
        try:
            logs = driver.get_log("browser")
            print("Browser logs:")
            for log in logs:
                print(log)
        except Exception as e:
            print(f"Unable to read browser logs: {e}")
        raise

    # Security score present
    score_el = driver.find_element(
        By.XPATH,
        "//h3[contains(., 'Security Score')]/following::span[contains(@class,'text-5xl')][1]",
    )
    assert score_el.text.strip() != ""

    # Top risks tile present
    driver.find_element(By.XPATH, "//h3[contains(., 'Top Risks')]")

    # Coverage details present
    coverage_labels = driver.find_elements(By.XPATH, "//*[contains(text(), 'coverage')]")
    assert len(coverage_labels) > 0

    # Take a screenshot for reference
    driver.save_screenshot("posture_dashboard.png")
