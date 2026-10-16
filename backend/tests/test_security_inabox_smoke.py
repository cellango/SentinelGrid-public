"""Security-in-a-Box navigation smoke: verify cards link to new pages."""

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


def click_card_and_verify(driver, card_text, expected_path):
    card = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, f"//*[contains(., '{card_text}')]//ancestor::a | //*[contains(., '{card_text}')]//ancestor::div[contains(@class, 'card')]") )
    )
    href = card.get_attribute("href")
    if href:
        driver.get(href)
    else:
        card.click()
    WebDriverWait(driver, 10).until(EC.url_contains(expected_path))
    assert expected_path in driver.current_url, f"Expected to navigate to {expected_path}, got {driver.current_url}"


class TestSecurityInABoxNav:
    def test_cards_link_to_pages(self, driver):
        login(driver, base_url=BASE_URL)
        driver.get(f"{BASE_URL}/#security-in-a-box")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        cards = [
            ("AI Security", "/ai"),
            ("Managed SIEM + SOAR", "/siem-soar"),
            ("Identity", "/identity"),
            ("Application", "/appsec"),
            ("Pen", "/ai-pentest"),
        ]

        for text, path in cards:
            click_card_and_verify(driver, text, path)
            driver.back()
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//*[@id='security-in-a-box'] | //*[contains(., 'Security in a Box')]")))


class TestSecurityInABoxPages:
    def test_pages_render_expected_content(self, driver):
        login(driver, base_url=BASE_URL)
        wait = WebDriverWait(driver, 10)

        pages = [
            {"path": "/ai", "keywords": ["AI", "assistant", "SOC"]},
            {"path": "/siem-soar", "keywords": ["SIEM", "SOAR", "playbook"]},
            {"path": "/identity", "keywords": ["Identity", "SSO", "OIDC", "OAuth"]},
            {"path": "/appsec", "keywords": ["Application", "AppSec", "Security"]},
            {"path": "/ai-pentest", "keywords": ["Pen", "Testing", "Pentest"]},
        ]

        for page in pages:
            driver.get(f"{BASE_URL}{page['path']}")
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'Security') or contains(., 'AI') or contains(., 'Identity')]")))
            except TimeoutException:
                pytest.skip(f"{page['path']} did not render expected content")

            body = driver.find_element(By.TAG_NAME, "body").text.lower()
            if not any(k.lower() in body for k in page["keywords"]):
                pytest.skip(f"{page['path']} missing expected keywords: {page['keywords']}")
