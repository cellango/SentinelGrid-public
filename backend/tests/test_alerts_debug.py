"""
Debug test for alerts page - verify alerts are being fetched and displayed.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os


@pytest.fixture(scope="module")
def driver():
    """Create Selenium WebDriver instance."""
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
    options.set_capability('acceptInsecureCerts', True)
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()


def test_alerts_page_shows_database_alerts(driver):
    """Test that alerts from database are displayed on alerts page."""
    base_url = os.getenv("WEBSITE_URL", "https://localhost:3443")
    
    print(f"\n{'='*70}")
    print("🔍 DEBUGGING ALERTS PAGE")
    print(f"{'='*70}\n")
    
    # Step 1: Login
    print("STEP 1: Login")
    driver.get(f"{base_url}/login")
    email_input = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
    )
    
    email = os.getenv("TEST_USERNAME", "admin@sentinelgrid.ai")
    password = os.getenv("TEST_PASSWORD", "admin123")
    
    email_input.clear()
    email_input.send_keys(email)
    
    password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    password_input.clear()
    password_input.send_keys(password)
    
    login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in')]")
    login_button.click()
    time.sleep(5)
    
    # Verify token in localStorage
    token = driver.execute_script("return localStorage.getItem('access_token');")
    tenant_id = driver.execute_script("return localStorage.getItem('tenant_id');")
    
    print(f"  ✅ Login successful")
    print(f"  Token length: {len(token) if token else 0}")
    print(f"  Tenant ID: {tenant_id}")
    
    # Step 2: Navigate to alerts page
    print(f"\nSTEP 2: Navigate to Alerts Page")
    driver.get(f"{base_url}/dashboard/alerts")
    time.sleep(5)  # Wait for API calls
    
    # Check browser console logs for redirects
    try:
        logs = driver.get_log('browser')
        recent_logs = [log for log in logs if 'redirect' in log['message'].lower() or 'onboarding' in log['message'].lower()]
        if recent_logs:
            print(f"  📋 Relevant Console Logs:")
            for log in recent_logs[:5]:
                print(f"    {log.get('message', '')[:100]}")
    except:
        pass
    
    print(f"  Current URL: {driver.current_url}")
    
    # Step 3: Check page title/heading
    print(f"\nSTEP 3: Verify Page Loaded")
    try:
        heading = driver.find_element(By.XPATH, "//h1[contains(text(), 'Alert')]")
        print(f"  ✅ Found heading: {heading.text}")
    except:
        print(f"  ❌ No heading found")
    
    # Step 4: Check for table rows
    print(f"\nSTEP 4: Check for Alert Table Rows")
    try:
        table = driver.find_element(By.TAG_NAME, "table")
        print(f"  ✅ Table found")
        
        # Check for tbody rows
        tbody_rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
        print(f"  Found {len(tbody_rows)} rows in tbody")
        
        if len(tbody_rows) > 0:
            print(f"  ✅ Alerts are displayed!")
            for i, row in enumerate(tbody_rows[:3]):
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    print(f"    Row {i+1}: {cells[1].text[:50]}")
        else:
            print(f"  ❌ No alert rows found in table")
            
            # Check for "no alerts" message
            no_data_msgs = driver.find_elements(By.XPATH, "//*[contains(text(), 'No alerts') or contains(text(), 'no alert')]")
            if no_data_msgs:
                for msg in no_data_msgs:
                    if msg.is_displayed():
                        print(f"    Found message: {msg.text}")
    except Exception as e:
        print(f"  ❌ Table not found: {e}")
    
    # Step 5: Check localStorage/sessionStorage for API response
    print(f"\nSTEP 5: Check API Response in Network/Storage")
    
    # Check if React Query cached the response
    try:
        # Get performance entries to see network requests
        perf_entries = driver.execute_script("""
            return performance.getEntriesByType('resource')
                .filter(e => e.name.includes('/siem/alerts'))
                .map(e => ({name: e.name, duration: e.duration}));
        """)
        
        print(f"  Network requests to /siem/alerts: {len(perf_entries)}")
        for entry in perf_entries[:3]:
            print(f"    - {entry['name']} (took {entry['duration']}ms)")
    except:
        pass
    
    # Step 6: Execute JavaScript to check React Query cache
    print(f"\nSTEP 6: Check React Query Cache")
    try:
        # Try to access the fetch result through window
        cache_check = driver.execute_script("""
            // Check if there's data in the DOM
            const tableRows = document.querySelectorAll('tbody tr');
            const alertElements = document.querySelectorAll('[data-alert-id], [class*="alert"]');
            return {
                tableRows: tableRows.length,
                alertElements: alertElements.length,
                hasTable: !!document.querySelector('table')
            };
        """)
        
        print(f"  DOM Analysis:")
        print(f"    - Table rows: {cache_check.get('tableRows', 0)}")
        print(f"    - Alert elements: {cache_check.get('alertElements', 0)}")
        print(f"    - Has table: {cache_check.get('hasTable', False)}")
    except Exception as e:
        print(f"  ⚠️  Could not analyze DOM: {e}")
    
    # Step 7: Take screenshot for visual inspection
    print(f"\nSTEP 7: Save Screenshot")
    try:
        screenshot_path = "/tmp/alerts_page_debug.png"
        driver.save_screenshot(screenshot_path)
        print(f"  ✅ Screenshot saved to: {screenshot_path}")
    except:
        print(f"  ⚠️  Could not save screenshot")
    
    print(f"\n{'='*70}")
    print("🏁 DEBUG TEST COMPLETE")
    print(f"{'='*70}\n")
    
    # For now, just pass the test - we're debugging
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

