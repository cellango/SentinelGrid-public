"""Manual test - opens browser and waits for manual inspection."""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Manual-only; avoid running in automated suites
pytest.skip("Manual Selenium check; skip in automated runs", allow_module_level=True)

# Set up browser
options = webdriver.ChromeOptions()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--allow-insecure-localhost")
options.set_capability('acceptInsecureCerts', True)

driver = webdriver.Chrome(options=options)
driver.maximize_window()

try:
    base_url = "https://localhost:3443"
    
    # Login
    print(f"Logging in...")
    driver.get(f"{base_url}/login")
    
    email_input = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
    )
    
    email_input.send_keys("admin@sentinelgrid.ai")
    password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    password_input.send_keys("admin123")
    
    login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in')]")
    login_button.click()
    
    time.sleep(5)
    
    print(f"✅ Logged in")
    print(f"Current URL: {driver.current_url}")
    
    # Navigate to alerts
    print(f"\nNavigating to /dashboard/alerts...")
    driver.get(f"{base_url}/dashboard/alerts")
    
    # Wait and check
    time.sleep(5)
    
    print(f"Current URL: {driver.current_url}")
    print(f"\nBrowser is open. Check the page manually.")
    print(f"Press Enter when done...")
    input()
    
finally:
    driver.quit()
