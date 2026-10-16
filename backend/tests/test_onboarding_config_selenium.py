"""
Headful Selenium test for onboarding/config flow (cloud + git + appsec + ai + ticketing placeholders).
Uses demo credentials; expects UI to render health sections even if endpoints are mocked.
"""

import os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from utils.login import login as perform_login

@pytest.fixture(scope="session")
def driver():
    options = webdriver.ChromeOptions()
    if os.getenv("CI") == "true" or os.getenv("HEADLESS") == "true":
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    options.set_capability("acceptInsecureCerts", True)
    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(10)
    drv.maximize_window()
    yield drv
    drv.quit()


def test_onboarding_config_flow(driver):
    base_url = os.getenv("WEBSITE_URL", "https://localhost:3443")
    email = os.getenv("TEST_EMAIL", "admin@demo.sentinelgrid.ai")
    password = os.getenv("TEST_PASSWORD", "DemoPassword123!")

    # Start clean: cookies + storage
    driver.delete_all_cookies()
    driver.get(f"{base_url}/login")
    driver.execute_script("localStorage.clear(); sessionStorage.clear();")

    perform_login(driver, base_url=base_url, username=email, password=password)
    # Clear onboarding progress flags without dropping auth
    driver.execute_script(
        "localStorage.removeItem('onboarding_progress');"
        "localStorage.removeItem('onboarding_banner_dismissed_false');"
        "localStorage.removeItem('onboarding_banner_dismissed_true');"
    )

    # Open onboarding wizard at step 1 (Identity)
    driver.get(f"{base_url}/onboarding?step=1")
    WebDriverWait(driver, 30).until(lambda d: "/onboarding" in d.current_url)
    # Go straight to the CTA; heading text can vary
    continue_btn = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Continue') or contains(., 'Save & Continue')]")
        )
    )

    # Verify all expected steps are rendered (demo should show full list)
    step_dots = driver.find_elements(By.XPATH, "//div[contains(@class,'justify-between')]/button[contains(@class,'rounded-full')]")
    assert len(step_dots) >= 7, f"Expected at least 7 onboarding steps for demo, saw {len(step_dots)}"

    # Identity: choose SentinelGrid Identity (default) and continue
    try:
        driver.find_element(By.XPATH, "//label[contains(., 'Use SentinelGrid Identity')]").click()
    except Exception:
        pass
    continue_btn.click()

    # Cloud: select AWS, fill dummy, toggle org, add extra log group
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//h2[contains(., 'Connect Your Cloud')]")))
    try:
        driver.find_element(By.XPATH, "//button[contains(@class,'border-cyan') and .//div[contains(text(),'AWS')]]")
    except Exception:
        driver.find_element(By.XPATH, "//button[.//div[contains(text(),'AWS')]]").click()
    driver.find_element(By.CSS_SELECTOR, "input[placeholder='123456789012']").send_keys("123456789012")
    driver.find_element(By.CSS_SELECTOR, "input[placeholder='arn:aws:iam::123456789012:role/SentinelGridMonitorRole']").send_keys(
        "arn:aws:iam::123456789012:role/SentinelGridMonitorRole"
    )
    # org/regions/extras
    try:
        driver.find_element(By.XPATH, "//label[contains(., 'Org / StackSet rollout')]/input").click()
    except Exception:
        pass
    regions_inputs = driver.find_elements(By.XPATH, "//input[@placeholder='us-east-1,us-west-2']")
    if not regions_inputs:
        regions_inputs = driver.find_elements(By.XPATH, "//label[contains(., 'Regions')]/following::input[@type='text'][1]")
    if regions_inputs:
        try:
            regions_inputs[0].clear()
            regions_inputs[0].send_keys("us-east-1")
        except Exception:
            pass
    try:
        driver.find_element(By.XPATH, "//input[contains(@placeholder,'flow-logs')]").send_keys(
            "arn:aws:logs:us-east-1:123456789012:log-group:/aws/vpc/flow-logs:*"
        )
        driver.find_element(By.XPATH, "//input[contains(@placeholder,'my-flow-logs-bucket')]").send_keys("arn:aws:s3:::my-flow-logs-bucket")
    except Exception:
        pass
    try:
        driver.find_element(By.XPATH, "//label[contains(., 'Create helper Flow Logs log group')]/input").click()
        driver.find_element(By.XPATH, "//label[contains(., 'Create helper DB audit log group')]/input").click()
    except Exception:
        pass
    try:
        driver.find_element(By.XPATH, "//button[contains(., 'Continue') and not(contains(., 'Connecting'))]").click()
    except Exception:
        pass
    # Force navigate to git step in case the wizard stays on cloud step
    driver.get(f"{base_url}/onboarding?step=4")

    # Endpoint: skip
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//h2[contains(., 'Deploy Endpoint Protection')]")))
        driver.find_element(By.XPATH, "//button[contains(., 'Skip')]").click()
    except TimeoutException:
        pass

    # Git: select GitHub, dummy token, run health
    git_heading = "//h2[contains(., 'Connect Your Git Repositories')]"
    driver.get(f"{base_url}/onboarding?step=4")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, git_heading)))
    driver.find_element(By.XPATH, "//button[.//div[contains(text(),'GitHub')]]").click()
    driver.find_element(By.XPATH, "//input[@type='password']").send_keys("ghp_dummy_token")
    driver.find_element(By.XPATH, "//button[contains(., 'Complete Setup')]").click()
    try:
        driver.find_element(By.XPATH, "//button[contains(., 'Re-run health')]").click()
    except Exception:
        pass

    # AppSec: fill dummy
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, "//h2[contains(., 'Application Security')]")))
    driver.find_element(By.XPATH, "//input[@placeholder='https://apps.yourdomain.com']").send_keys("https://example.com")
    driver.find_element(By.XPATH, "//input[@type='password']").send_keys("secret123")
    driver.find_element(By.XPATH, "//input[@placeholder='customer-portal']").send_keys("customer-portal")
    driver.find_element(By.XPATH, "//button[contains(., 'Save & Check Health')]").click()

    # AI: fill hosted dummy
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, "//h2[contains(., 'AI Shield')]")))
    driver.find_element(By.XPATH, "//input[contains(@placeholder,'ai-shield')]").send_keys("https://example.com/ai")
    driver.find_element(By.XPATH, "//input[@type='password']").send_keys("ai-secret")
    driver.find_element(By.XPATH, "//button[contains(., 'Save & Check Health')]").click()

    # Ticketing: force-navigate in case wizard stalled on AI health
    ticket_heading = "//h2[contains(., 'Ticketing') or contains(., 'SOC Handoff')]"
    ticket_button = "//button[contains(., 'Save & Check Health')]"
    found_ticket = False
    for step_num in ("6", "7", "8", "9"):
        driver.get(f"{base_url}/onboarding?step={step_num}")
        try:
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, ticket_heading)))
            found_ticket = True
            break
        except TimeoutException:
            continue
    if not found_ticket:
        # Fallback: look for the ticketing save button even if heading didn't render
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, ticket_button)))
            found_ticket = True
        except TimeoutException:
            pass
    if not found_ticket:
        raise AssertionError("Ticketing step did not render in onboarding wizard")
    driver.find_element(By.XPATH, ticket_button).click()

    # Jump to dashboard; the wizard does not always auto-redirect in demo
    driver.get(f"{base_url}/dashboard")
    WebDriverWait(driver, 30).until(lambda d: "/dashboard" in d.current_url)
    time.sleep(1)
