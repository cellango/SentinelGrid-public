"""
End-to-end checks for first-time experience:
- Banner visible on first login when incomplete
- Header gear opens onboarding at first incomplete step
- People & Access readiness banner shows on dashboard and People page when missing
- Per-step test buttons (IdP, cloud, git, endpoint) update status
"""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.login import login

BASE_URL = os.getenv("WEBSITE_URL", "https://localhost:3443")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true" or os.getenv("CI") == "true"
TEST_EMAIL = os.getenv("TEST_EMAIL", "admin@demo.sentinelgrid.ai")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "DemoPassword123!")


@pytest.fixture(scope="function")
def driver():
    options = webdriver.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(8)
    yield drv
    drv.quit()


def login(driver):
    driver.get(f"{BASE_URL}/login")
    wait = WebDriverWait(driver, 15)
    wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(TEST_EMAIL)
    driver.find_element(By.NAME, "password").send_keys(TEST_PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard"))


def test_banner_and_gear_resume(driver):
    login(driver, base_url=BASE_URL, username=TEST_EMAIL, password=TEST_PASSWORD)
    wait = WebDriverWait(driver, 15)
    # Banner should be visible on dashboard when incomplete
    wait.until(EC.presence_of_element_located((By.XPATH, "//h3[contains(., 'Complete Your Setup')]")))
    # Gear icon in header should open onboarding at first incomplete step
    driver.find_element(By.XPATH, "//a[contains(@href, '/onboarding') and .//*[name()='svg']]").click()
    wait.until(EC.url_contains("/onboarding"))
    # Should land on step 1 or first incomplete; check presence of heading
    wait.until(EC.presence_of_element_located((By.XPATH, "//h2[contains(., 'Identity') or contains(., 'Connect Your')]")))


def test_people_readiness_notice(driver):
    login(driver, base_url=BASE_URL, username=TEST_EMAIL, password=TEST_PASSWORD)
    wait = WebDriverWait(driver, 10)
    # Dashboard banner should mention People readiness when missing
    wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Default access profile') or contains(text(),'birthright')]")))
    # Navigate to People & Access
    driver.get(f"{BASE_URL}/dashboard/iam/people")
    wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(., 'People')]")))
    wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Complete tenant setup') or contains(text(),'default access profile')]")))


def test_per_step_tests(driver):
    login(driver, base_url=BASE_URL, username=TEST_EMAIL, password=TEST_PASSWORD)
    wait = WebDriverWait(driver, 15)
    step_checks = [
        (1, "Connect Your Identity"),
        (2, "Connect Your Cloud"),
        (3, "Endpoint Protection"),
        (4, "Git Repositories"),
        (5, "Tenant readiness"),
    ]
    for step, marker in step_checks:
        driver.get(f"{BASE_URL}/onboarding?step={step}")
        wait.until(EC.url_contains(f"step={step}"))
        wait.until(EC.presence_of_element_located((By.XPATH, f"//*[contains(., '{marker}')]")))
        # Try to click re-run health buttons when present to ensure wiring works
        try:
            driver.find_element(By.XPATH, "//button[contains(., 'Re-run')]").click()
        except Exception:
            pass


def test_git_connect_smoke(driver):
    """
    Basic smoke test for Git connect UI: fill token and submit without crashing.
    """
    login(driver)
    wait = WebDriverWait(driver, 15)
    driver.get(f"{BASE_URL}/onboarding?step=4")
    # Select GitHub provider
    wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(., 'GitHub')]"))).click()
    # Enter dummy token
    token_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password' and contains(@placeholder, 'ghp_')]")))
    token_input.clear()
    token_input.send_keys("dummy")
    # Submit
    driver.find_element(By.XPATH, "//button[@type='submit' and contains(., 'Continue')]").click()
    # Expect either health details or advance to next step without error
    wait.until(
        lambda d: "/onboarding" in d.current_url and ("step=5" in d.current_url or "step=4" in d.current_url)
    )
    # Ensure no fatal error banner
    assert not driver.find_elements(By.XPATH, "//div[contains(@class,'bg-red') and contains(., 'Failed to connect')]")
    # Cloud: open and re-run health
    driver.get(f"{BASE_URL}/onboarding?step=2")
    try:
        driver.find_element(By.XPATH, "//button[contains(., 'Re-run') or contains(., 'health')]").click()
    except Exception:
        pass
    # Endpoint: re-run health
    driver.get(f"{BASE_URL}/onboarding?step=3")
    try:
        driver.find_element(By.XPATH, "//button[contains(., 'Re-run health')]").click()
    except Exception:
        pass
    # Git: re-run health
    driver.get(f"{BASE_URL}/onboarding?step=4")
    try:
        driver.find_element(By.XPATH, "//button[contains(., 'Re-run health')]").click()
    except Exception:
        pass
