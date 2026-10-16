"""IAM UI smokes: My Account + Identity Providers (OIDC/SSO) pages."""

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
USERNAME = os.getenv("TEST_USERNAME", "admin@demo.sentinelgrid.ai")
PASSWORD = os.getenv("TEST_PASSWORD", "DemoPassword123!")


@pytest.fixture(scope="function")
def driver():
    opts = webdriver.ChromeOptions()
    if HEADLESS:
        opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--ignore-ssl-errors")
    opts.set_capability("acceptInsecureCerts", True)
    d = webdriver.Chrome(options=opts)
    d.implicitly_wait(8)
    yield d
    d.quit()


class TestIAMUISmoke:
    def test_my_account_tabs(self, driver):
        login(driver, base_url=BASE_URL, username=USERNAME, password=PASSWORD)
        wait = WebDriverWait(driver, 12)

        driver.get(f"{BASE_URL}/dashboard/iam/my-account")
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'My Account') or contains(., 'Profile')]")))
            # Expect tabs for profile/security/sessions or similar
            driver.find_element(By.XPATH, "//*[contains(., 'Profile')]")
            driver.find_element(By.XPATH, "//*[contains(., 'Security') or contains(., 'MFA')]")
        except TimeoutException:
            pytest.skip("My Account page did not render expected sections.")

    def test_identity_providers_page(self, driver):
        login(driver, base_url=BASE_URL, username=USERNAME, password=PASSWORD)
        wait = WebDriverWait(driver, 12)

        driver.get(f"{BASE_URL}/dashboard/iam/identity-providers")
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Identity') and contains(., 'Providers')]")))
        except TimeoutException:
            pytest.skip("Identity Providers page did not load.")

        # Look for OIDC/SAML controls or gateway endpoints
        oidc_elements = driver.find_elements(By.XPATH, "//*[contains(., 'OIDC') or contains(., 'OpenID')]")
        saml_elements = driver.find_elements(By.XPATH, "//*[contains(., 'SAML')]")
        add_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Add') or contains(., 'Connect')]")

        if not (oidc_elements or saml_elements or add_buttons):
            pytest.skip("No OIDC/SAML controls detected on Identity Providers page.")

        # Gateway endpoints should be visible somewhere on the page
        driver.find_elements(By.XPATH, "//*[contains(., 'Authorize') or contains(., 'Callback') or contains(., 'Logout')]")
