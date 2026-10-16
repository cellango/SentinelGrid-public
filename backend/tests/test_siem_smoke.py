"""SIEM smoke: ensure SIEM pages load post-login."""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.login import login

BASE_URL = os.getenv("WEBSITE_URL", "https://localhost:3443")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true" or os.getenv("CI") == "true"


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
    options.set_capability('acceptInsecureCerts', True)
    d = webdriver.Chrome(options=options)
    d.implicitly_wait(10)
    yield d
    d.quit()


@pytest.fixture(scope="function")
def authenticated_driver(driver):
    login(driver, base_url=BASE_URL)
    return driver


class TestSIEMSmoke:
    def test_siem_pages_load(self, authenticated_driver):
        driver = authenticated_driver
        wait = WebDriverWait(driver, 10)

        pages = [
            {"name": "Alerts", "path": "/dashboard/alerts", "selector": "h1, h2"},
            {"name": "Incidents", "path": "/dashboard/incidents", "selector": "h1, h2"},
            {"name": "SIEM", "path": "/dashboard/siem", "selector": "h1, h2"},
            {"name": "Detections", "path": "/siem/detection-rules", "selector": "h1, h2"},
        ]

        for page in pages:
            driver.get(f"{BASE_URL}{page['path']}")
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, page["selector"])))
            assert page["path"] in driver.current_url, f"Failed to load {page['name']}"
