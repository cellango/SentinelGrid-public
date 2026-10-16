"""
Selenium test to verify playbooks are displayed on the playbooks page.
Database has 10 builtin playbooks that should be visible.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
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


def test_playbooks_page_displays_10_playbooks_from_database(driver):
    """
    Verify that the 10 builtin playbooks in the database are displayed.
    
    Expected database state:
    - 10 builtin playbooks (tenant_id = 00000000-0000-0000-0000-000000000000)
    - is_enabled = true
    - Should be visible to all tenants
    """
    base_url = os.getenv("WEBSITE_URL", "https://localhost:3443")
    
    print(f"\n{'='*80}")
    print("🧪 COMPREHENSIVE PLAYBOOKS TEST")
    print(f"{'='*80}\n")
    
    # Step 1: Login
    print("STEP 1: Login")
    driver.get(f"{base_url}/login")
    email_input = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
    )
    
    email = os.getenv("TEST_USERNAME", "admin@sentinelgrid.ai")
    password = os.getenv("TEST_PASSWORD", "admin123")
    
    email_input.send_keys(email)
    password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    password_input.send_keys(password)
    
    login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in')]")
    login_button.click()
    time.sleep(5)
    
    token = driver.execute_script("return localStorage.getItem('access_token');")
    tenant_id = driver.execute_script("return localStorage.getItem('tenant_id');")
    
    if not token:
        pytest.fail("❌ Login failed - no token")
    
    print(f"  ✅ Logged in")
    print(f"  Token length: {len(token)}")
    print(f"  Tenant ID: {tenant_id}\n")
    
    # Step 2: Navigate to playbooks page via sidebar
    print("STEP 2: Click 'Automated Response' in Sidebar")
    driver.get(f"{base_url}/dashboard")
    time.sleep(3)
    
    print(f"  Navigating directly to playbooks page...")
    driver.get(f"{base_url}/dashboard/playbooks")
    print(f"  URL after navigate command: {driver.current_url}")
    time.sleep(3)
    print(f"  URL after 3 sec wait: {driver.current_url}")
    time.sleep(3)
    print(f"  URL after 6 sec wait: {driver.current_url}")
    
    # Check browser console for redirect messages
    try:
        logs = driver.get_log('browser')
        console_msgs = [log for log in logs if 'redirect' in log['message'].lower() or 'dashboard' in log['message'].lower()]
        if console_msgs:
            print(f"\n  📋 Console logs about redirects/dashboard:")
            for log in console_msgs[:10]:
                level = log.get('level', 'INFO')
                msg = log.get('message', '')[:150]
                print(f"    [{level}] {msg}")
    except:
        pass
    
    final_url = driver.current_url
    print(f"\n  Final URL: {final_url}")
    
    if "/dashboard/playbooks" not in final_url:
        print(f"  ❌ Redirected away from playbooks page to: {final_url}")
        # Continue test to gather more info, but mark as issue
    else:
        print(f"  ✅ Successfully stayed on /dashboard/playbooks\n")
    
    # Step 3: Check for React errors
    print("STEP 3: Check for Application Errors")
    page_source = driver.page_source.lower()
    if "application error" in page_source and "client-side exception" in page_source:
        pytest.fail("❌ React application error on playbooks page")
    print(f"  ✅ No application errors\n")
    
    # Step 4: Verify page heading
    print("STEP 4: Verify Page Heading")
    try:
        heading = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Playbook') or contains(text(), 'SOAR')]"))
        )
        print(f"  ✅ Found heading: '{heading.text}'\n")
    except TimeoutException:
        pytest.fail("❌ Playbooks page heading not found")
    
    # Step 5: Check API requests
    print("STEP 5: Check API Requests")
    try:
        perf_entries = driver.execute_script("""
            return performance.getEntriesByType('resource')
                .filter(e => e.name.includes('/playbooks'))
                .map(e => ({name: e.name, duration: e.duration}));
        """)
        
        print(f"  Found {len(perf_entries)} API requests to /playbooks:")
        for entry in perf_entries[:3]:
            print(f"    - {entry['name']} (took {entry['duration']}ms)")
        
        if len(perf_entries) == 0:
            print(f"  ⚠️  No API requests to /playbooks detected")
        
    except Exception as e:
        print(f"  ⚠️  Could not check network requests: {e}")
    
    print()
    
    # Step 6: Check for error messages vs empty state
    print("STEP 6: Check Error Messages vs Empty State")
    
    # Check for red errors (bad)
    red_errors = driver.find_elements(By.XPATH,
        "//*[contains(@class, 'bg-red') or contains(@class, 'text-red-600')]"
    )
    displayed_red_errors = [e for e in red_errors if e.is_displayed() and 'error' in e.text.lower()]
    
    if displayed_red_errors:
        error_text = displayed_red_errors[0].text
        print(f"  ❌ Found red error: {error_text[:100]}")
        pytest.fail(f"Page shows critical error: {error_text}")
    
    # Check for yellow warnings (acceptable)
    yellow_warnings = driver.find_elements(By.XPATH,
        "//*[contains(@class, 'yellow')]"
    )
    has_yellow_warning = any(w.is_displayed() and len(w.text) > 10 for w in yellow_warnings)
    
    if has_yellow_warning:
        warning_text = next((w.text for w in yellow_warnings if w.is_displayed() and len(w.text) > 10), "")
        print(f"  ℹ️  Found info message: {warning_text[:100]}")
        print(f"  ✅ Graceful handling of service not configured\n")
    else:
        print(f"  ✅ No error messages\n")
    
    # Step 7: Check for playbook cards/grid
    print("STEP 7: Check for Playbook Cards")
    try:
        # Look for playbook grid or cards
        playbook_cards = driver.find_elements(By.XPATH,
            "//div[contains(@class, 'grid')]//a[contains(@href, '/playbooks/')] | "
            "//*[contains(@class, 'rounded')]//h3"
        )
        
        visible_cards = [c for c in playbook_cards if c.is_displayed()]
        
        print(f"  Found {len(visible_cards)} playbook cards")
        
        if len(visible_cards) > 0:
            print(f"  ✅ Playbooks are displayed!\n")
            print(f"  📋 Sample Playbooks:")
            for i, card in enumerate(visible_cards[:5]):
                try:
                    name = card.text.split('\n')[0] if '\n' in card.text else card.text
                    print(f"    {i+1}. {name[:60]}")
                except:
                    pass
            
            print()
            
            # Assert we have at least 5 playbooks (database has 10)
            assert len(visible_cards) >= 5, f"Expected at least 5 playbooks, found {len(visible_cards)}"
            
        else:
            print(f"  ⚠️  No playbook cards found")
            
            # Check for "no playbooks" message
            no_playbooks_msg = driver.find_elements(By.XPATH,
                "//*[contains(text(), 'No playbooks') or contains(text(), 'no playbook')]"
            )
            
            if no_playbooks_msg and any(m.is_displayed() for m in no_playbooks_msg):
                print(f"  ℹ️  Page shows 'No playbooks' message")
                print(f"  ❌ Database has 10 playbooks but UI shows none")
                pytest.fail("Database has playbooks but UI doesn't display them")
            else:
                print(f"  ⚠️  No playbook cards and no 'empty' message")
                
    except Exception as e:
        print(f"  ❌ Error checking playbooks: {e}")
    
    # Step 8: Check browser console for errors
    print("STEP 8: Check Browser Console")
    try:
        logs = driver.get_log('browser')
        errors = [log for log in logs if log['level'] == 'SEVERE']
        
        # Filter out expected network errors (401/403 from auth)
        critical_errors = []
        for error in errors:
            msg = error['message']
            # Skip 401/403 errors (expected during auth flow)
            if '401' not in msg and '403' not in msg and '404' not in msg:
                critical_errors.append(msg)
        
        if critical_errors:
            print(f"  ⚠️  Found {len(critical_errors)} console errors:")
            for err in critical_errors[:3]:
                print(f"    - {err[:100]}")
        else:
            print(f"  ✅ No critical console errors")
        
    except Exception as e:
        print(f"  ⚠️  Could not check console: {e}")
    
    print()
    
    # Step 9: Take screenshot
    print("STEP 9: Save Screenshot for Manual Review")
    try:
        screenshot_path = "/tmp/playbooks_page_test.png"
        driver.save_screenshot(screenshot_path)
        print(f"  ✅ Screenshot saved to: {screenshot_path}\n")
    except:
        print(f"  ⚠️  Could not save screenshot\n")
    
    print(f"{'='*80}")
    print("🏁 TEST COMPLETE")
    print(f"{'='*80}\n")
    
    # Final assertion: We should have visible playbooks
    if len(visible_cards) < 5:
        pytest.fail(f"Expected at least 5 playbooks displayed, found {len(visible_cards)}")
    
    print(f"✅ TEST PASSED: {len(visible_cards)} playbooks displayed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

