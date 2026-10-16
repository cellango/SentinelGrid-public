import os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = os.environ.get("BASE_URL", "https://localhost:3443")
USERNAME = os.environ.get("DEMO_USERNAME", "admin@demo.sentinelgrid.ai")
PASSWORD = os.environ.get("DEMO_PASSWORD", "DemoPassword123!")


@pytest.fixture(scope="module")
def driver():
    opts = webdriver.ChromeOptions()
    headless = os.environ.get("HEADLESS", "false").lower() == "true"
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--allow-insecure-localhost")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--no-sandbox")
    opts.set_capability("acceptInsecureCerts", True)
    drv = webdriver.Chrome(options=opts)
    drv.set_window_size(1440, 900)
    yield drv
    drv.quit()


def ensure_logged_in(drv):
    # Frontend login form
    drv.get(f"{BASE_URL}/login")
    wait = WebDriverWait(drv, 30)
    user_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
    user_field.clear(); user_field.send_keys(USERNAME)
    pwd_field = drv.find_element(By.CSS_SELECTOR, "input[type='password']")
    pwd_field.clear(); pwd_field.send_keys(PASSWORD)
    drv.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    WebDriverWait(drv, 30).until(lambda d: "/dashboard" in d.current_url or "/app" in d.current_url)
    WebDriverWait(drv, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='dashboard-root']")))


def test_playbook_to_detection_links(driver):
    drv = driver
    ensure_logged_in(drv)

    drv.get(f"{BASE_URL}/dashboard/playbooks")
    WebDriverWait(drv, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Search playbooks...']")))
    links = drv.find_elements(By.LINK_TEXT, "Linked detections")
    assert links, "Expected at least one Linked detections link"
    links[0].click()

    WebDriverWait(drv, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Search detection rules...']")))
    cards = drv.find_elements(By.CSS_SELECTOR, "[data-testid='detection-card']")
    assert cards, "Expected detection cards after navigating from playbook"


def test_detection_to_playbook_link(driver):
    drv = driver
    ensure_logged_in(drv)

    drv.get(f"{BASE_URL}/siem/detection-rules")
    WebDriverWait(drv, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Search detection rules...']")))
    cards = drv.find_elements(By.CSS_SELECTOR, "[data-testid='detection-card'] a")
    assert cards, "Expected detection cards"
    cards[0].click()

    WebDriverWait(drv, 30).until(EC.presence_of_element_located((By.XPATH, "//h2[contains(text(),'Linked Playbook')]")))
    link_btns = drv.find_elements(By.LINK_TEXT, "View playbook")
    assert link_btns, "Expected View playbook link on detection detail"
    link_btns[0].click()

    WebDriverWait(drv, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Search playbooks...']")))
    cards = drv.find_elements(By.CSS_SELECTOR, "[data-testid='playbook-card']")
    assert cards, "Expected playbook cards after navigating from detection"
