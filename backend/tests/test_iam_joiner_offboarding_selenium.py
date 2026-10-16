"""
Selenium tests for IAM joiner wizard (device assignment) and offboarding drawer UX.
Run headful by setting HEADLESS=false to observe the flow.
"""

import os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.login import login as shared_login


@pytest.fixture(scope="session")
def base_url():
    return os.getenv("WEBSITE_URL", "https://localhost:3443")


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


def login(driver, base_url):
    shared_login(driver, base_url=base_url)


def go_people_page(driver, base_url):
    driver.get(f"{base_url}/dashboard/iam/people?nocache={int(time.time())}")
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='people-page-root']")))


@pytest.mark.selenium
def test_joiner_wizard_device_section(driver, base_url):
    login(driver, base_url)
    go_people_page(driver, base_url)

    wait = WebDriverWait(driver, 15)
    wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Add Employee')]"))).click()
    wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Add New Joiner')]")))

    # Fill minimal fields
    driver.find_element(By.CSS_SELECTOR, "input[name='firstName']").send_keys("Auto")
    driver.find_element(By.CSS_SELECTOR, "input[name='lastName']").send_keys("Joiner")
    driver.find_element(By.CSS_SELECTOR, "input[name='email']").send_keys("auto.joiner@example.com")

    # Device step should be present
    driver.find_element(By.XPATH, "//button[contains(., 'Next')]").click()
    wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Device') or contains(., 'Laptop')]")))


@pytest.mark.selenium
def test_offboarding_drawer(driver, base_url):
    login(driver, base_url)
    go_people_page(driver, base_url)
    wait = WebDriverWait(driver, 15)

    # Open an offboarding drawer (use first row)
    try:
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='people-row'] button"))).click()
    except Exception:
        pytest.skip("No people rows available to offboard")

    # Drawer should show offboarding controls
    wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Offboard') or contains(., 'Deactivate')]")))
