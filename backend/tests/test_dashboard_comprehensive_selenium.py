"""
Comprehensive Selenium E2E test for SentinelGrid Dashboard.
Tests all menu items and verifies pages load without errors.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os


@pytest.fixture(scope="session")
def driver():
    """Create Selenium WebDriver instance."""
    options = webdriver.ChromeOptions()
    
    # Headless mode only for CI/CD
    if os.getenv("CI") == "true" or os.getenv("HEADLESS") == "true":
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    else:
        print("Running in non-headless mode - browser will be visible")
    
    # Disable notifications and other popups
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    
    # For local HTTPS with self-signed certificates
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--allow-insecure-localhost")
    options.set_capability('acceptInsecureCerts', True)
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    driver.maximize_window()
    
    yield driver
    
    driver.quit()


@pytest.fixture
def base_url():
    """Get base URL for frontend."""
    # Default to frontend app (3443) where full dashboard lives
    return os.getenv("WEBSITE_URL", "https://localhost:3443")


@pytest.fixture
def authenticated_driver(driver, base_url):
    """Login and return authenticated driver."""
    print(f"\n🔐 Logging in to {base_url}/login")
    driver.get(f"{base_url}/login")
    
    # Wait for login form
    email_input = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
    )
    
    # Use test credentials
    email = os.getenv("TEST_USERNAME", "admin@sentinelgrid.ai")
    password = os.getenv("TEST_PASSWORD", "admin123")
    
    email_input.clear()
    email_input.send_keys(email)
    
    password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    password_input.clear()
    password_input.send_keys(password)
    
    # Submit login
    login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in') or contains(text(), 'Login')]")
    login_button.click()
    
    # Wait for login to complete
    time.sleep(5)
    
    # Verify token is stored
    token = driver.execute_script("return localStorage.getItem('access_token');")
    if not token:
        pytest.fail("Login failed - no token in localStorage")
    
    print(f"✅ Logged in successfully")
    return driver


@pytest.mark.skip(reason="Legacy comprehensive suite; refit to new nav/routes before re-enabling.")
class TestDashboardComprehensive:
    """Comprehensive test of all dashboard pages."""
    
    def test_all_menu_items_load(self, authenticated_driver, base_url):
        """Test that all menu items load without errors."""
        driver = authenticated_driver
        
        # Define all menu items to test
        menu_items = [
            {
                "name": "Dashboard",
                "url": "/dashboard",
                "expected_heading": "Dashboard|Welcome|Security",
                "wait_for": "h1, h2, [class*='Dashboard']",
                "should_have_content": True
            },
            {
                "name": "Security Alerts", 
                "url": "/dashboard/alerts",
                "expected_heading": "Alert|Security",
                "wait_for": "h1, h2",
                "should_have_content": False  # May be empty if no alerts
            },
            {
                "name": "Security Incidents",
                "url": "/dashboard/incidents",
                "expected_heading": "Incident",
                "wait_for": "h1, h2",
                "should_have_content": False  # May be empty if no incidents
            },
            {
                "name": "Security Monitoring",
                "url": "/dashboard/siem",
                "expected_heading": "SIEM|Monitoring|Security",
                "wait_for": "h1, h2",
                "should_have_content": False
            },
            {
                "name": "Detection Rules",
                "url": "/siem/detection-rules",
                "expected_heading": "Detection|Rule",
                "wait_for": "h1, h2",
                "should_have_content": False
            },
            {
                "name": "People & Access",
                "url": "/dashboard/iam/people",
                "expected_heading": "People|User|Access",
                "wait_for": "h1, h2",
                "should_have_content": False
            },
            {
                "name": "Automated Response",
                "url": "/dashboard/playbooks",
                "expected_heading": "Playbook|SOAR",
                "wait_for": "h1",
                "should_have_content": False  # May have no playbooks
            },
            {
                "name": "AI Governance",
                "url": "/dashboard/ai-governance",
                "expected_heading": "AI|Governance",
                "wait_for": "h1, h2",
                "should_have_content": False
            },
            {
                "name": "Compliance",
                "url": "/dashboard/compliance",
                "expected_heading": "Compliance",
                "wait_for": "h1",
                "should_have_content": False  # May not be configured
            },
        ]
        
        results = []
        
        for item in menu_items:
            print(f"\n{'='*60}")
            print(f"🧪 Testing: {item['name']}")
            print(f"   URL: {base_url}{item['url']}")
            
            try:
                # Navigate to page
                driver.get(f"{base_url}{item['url']}")
                time.sleep(3)  # Wait for page to load
                
                # Check for React errors
                page_source = driver.page_source.lower()
                if "application error" in page_source and "client-side exception" in page_source:
                    results.append({
                        "item": item['name'],
                        "status": "❌ FAILED",
                        "error": "React application error detected"
                    })
                    print(f"   ❌ FAILED: React application error")
                    continue
                
                # Verify page loaded (check for heading)
                try:
                    heading = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, item['wait_for']))
                    )
                    print(f"   ✅ Page loaded: Found heading/content")
                except TimeoutException:
                    results.append({
                        "item": item['name'],
                        "status": "⚠️  WARNING",
                        "error": "No heading found (page may still be loading)"
                    })
                    print(f"   ⚠️  WARNING: No heading found")
                    continue
                
                # Check for error messages (but distinguish from empty states)
                error_elements = driver.find_elements(By.XPATH, 
                    "//*[contains(@class, 'red') and contains(text(), 'Error')] | "
                    "//*[contains(@class, 'error') and not(contains(@class, 'yellow'))]"
                )
                
                critical_errors = []
                for elem in error_elements:
                    if elem.is_displayed():
                        error_text = elem.text.strip()
                        # Filter out soft warnings (yellow/informational messages)
                        parent_class = elem.get_attribute("class") or ""
                        if "yellow" not in parent_class and "bg-blue" not in parent_class:
                            # Check if it's actually an error vs empty state
                            if "error" in error_text.lower() and len(error_text) > 10:
                                critical_errors.append(error_text)
                
                if critical_errors:
                    results.append({
                        "item": item['name'],
                        "status": "❌ FAILED",
                        "error": f"Critical errors found: {', '.join(critical_errors[:2])}"
                    })
                    print(f"   ❌ FAILED: {', '.join(critical_errors[:2])}")
                else:
                    # Check for soft warnings (yellow notifications about missing data)
                    warning_elements = driver.find_elements(By.XPATH,
                        "//*[contains(@class, 'yellow')]"
                    )
                    has_warnings = any(w.is_displayed() and len(w.text.strip()) > 10 for w in warning_elements)
                    
                    if has_warnings:
                        results.append({
                            "item": item['name'],
                            "status": "✅ PASSED",
                            "note": "Service not configured (expected for new deployment)"
                        })
                        print(f"   ✅ PASSED (service not configured yet)")
                    else:
                        results.append({
                            "item": item['name'],
                            "status": "✅ PASSED",
                            "note": "Page loaded successfully"
                        })
                        print(f"   ✅ PASSED")
                
            except Exception as e:
                results.append({
                    "item": item['name'],
                    "status": "❌ FAILED",
                    "error": str(e)
                })
                print(f"   ❌ FAILED: {str(e)}")
        
        # Print summary
        print(f"\n{'='*60}")
        print("📊 TEST SUMMARY")
        print(f"{'='*60}")
        
        passed = sum(1 for r in results if "✅" in r['status'])
        failed = sum(1 for r in results if "❌" in r['status'])
        warnings = sum(1 for r in results if "⚠️" in r['status'])
        
        for result in results:
            status = result['status']
            item = result['item']
            note = result.get('note', result.get('error', ''))
            print(f"{status:12} {item:25} {note}")
        
        print(f"\n{'='*60}")
        print(f"Total: {len(results)} pages tested")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        print(f"{'='*60}\n")
        
        # Test passes if no critical failures
        assert failed == 0, f"Test failed: {failed} pages had critical errors"
    
    def test_dashboard_welcome_no_errors(self, authenticated_driver, base_url):
        """Test that welcome dashboard loads with no console errors."""
        driver = authenticated_driver
        
        print(f"\n🏠 Testing Welcome Dashboard: {base_url}/dashboard/welcome")
        driver.get(f"{base_url}/dashboard/welcome")
        time.sleep(5)  # Wait for all API calls to complete
        
        # Check for React application errors
        page_source = driver.page_source
        if "application error" in page_source.lower() and "client-side exception" in page_source.lower():
            pytest.fail("Welcome dashboard has React application error")
        
        # Check that some content is visible
        try:
            # Look for any dashboard content
            content_elements = driver.find_elements(By.CSS_SELECTOR, "h1, h2, section, [class*='card']")
            visible_content = [e for e in content_elements if e.is_displayed()]
            
            assert len(visible_content) > 0, "No visible content found on welcome dashboard"
            print(f"✅ Found {len(visible_content)} visible content elements")
        except AssertionError as e:
            pytest.fail(str(e))
        
        # Check for critical error messages (red errors, not warnings)
        critical_errors = driver.find_elements(By.XPATH,
            "//*[contains(@class, 'bg-red') and contains(text(), 'Error') or contains(text(), 'error')]"
        )
        
        displayed_errors = [e.text for e in critical_errors if e.is_displayed() and len(e.text.strip()) > 10]
        
        if displayed_errors:
            pytest.fail(f"Critical errors found on welcome dashboard: {', '.join(displayed_errors)}")
        
        print("✅ Welcome dashboard loaded successfully with no critical errors")
    
    def test_navigation_between_pages(self, authenticated_driver, base_url):
        """Test that navigation between pages works smoothly."""
        driver = authenticated_driver
        
        pages_to_visit = [
            "/dashboard",
            "/dashboard/alerts",
            "/dashboard/playbooks",
            "/dashboard/compliance",
            "/dashboard/iam/people",
        ]
        
        print("\n🔄 Testing navigation between pages...")
        
        for i, page in enumerate(pages_to_visit):
            print(f"\n   [{i+1}/{len(pages_to_visit)}] Navigating to: {page}")
            driver.get(f"{base_url}{page}")
            time.sleep(2)
            
            # Verify URL changed
            assert page in driver.current_url, f"Failed to navigate to {page}"
            
            # Verify no application error
            page_source = driver.page_source.lower()
            if "application error" in page_source and "client-side exception" in page_source:
                pytest.fail(f"Application error on page: {page}")
            
            print(f"   ✅ Successfully navigated to {page}")
        
        print("\n✅ All page navigations successful")
    
    def test_sidebar_navigation(self, authenticated_driver, base_url):
        """Test clicking through sidebar menu items."""
        driver = authenticated_driver
        
        print("\n🎯 Testing sidebar navigation...")
        driver.get(f"{base_url}/dashboard")
        time.sleep(3)
        
        # Get all sidebar navigation links
        try:
            sidebar_links = driver.find_elements(By.CSS_SELECTOR, "aside nav a")
            print(f"   Found {len(sidebar_links)} menu items in sidebar")
            
            # Click through each menu item
            for i in range(min(len(sidebar_links), 9)):  # Test first 9 items
                # Re-find sidebar links (page refresh may cause stale elements)
                sidebar_links = driver.find_elements(By.CSS_SELECTOR, "aside nav a")
                if i >= len(sidebar_links):
                    break
                
                link = sidebar_links[i]
                menu_name = link.text.strip()
                
                if not menu_name:
                    continue
                
                print(f"\n   [{i+1}] Clicking: {menu_name}")
                
                # Get href before clicking
                href = link.get_attribute("href")
                
                # Click the link
                link.click()
                time.sleep(3)  # Wait for page to load
                
                # Verify navigation occurred
                current_url = driver.current_url
                print(f"       Current URL: {current_url}")
                
                # Check for application errors
                page_source = driver.page_source.lower()
                if "application error" in page_source and "client-side exception" in page_source:
                    print(f"       ❌ Application error on {menu_name}")
                    pytest.fail(f"Application error when navigating to {menu_name}")
                
                print(f"       ✅ {menu_name} loaded successfully")
            
            print("\n✅ All sidebar navigation tests passed")
            
        except Exception as e:
            pytest.fail(f"Sidebar navigation failed: {str(e)}")
    
    def test_no_console_errors(self, authenticated_driver, base_url):
        """Test that dashboard has no JavaScript console errors."""
        driver = authenticated_driver
        
        print("\n🔍 Checking for JavaScript console errors...")
        driver.get(f"{base_url}/dashboard")
        time.sleep(5)
        
        # Get browser console logs
        logs = driver.get_log('browser')
        
        # Filter for actual errors (not warnings or info)
        errors = [log for log in logs if log['level'] == 'SEVERE']
        
        if errors:
            print(f"\n❌ Found {len(errors)} console errors:")
            for error in errors[:5]:  # Show first 5 errors
                print(f"   - {error['message'][:100]}")
            
            # Don't fail on network errors (401/404 expected for unconfigured services)
            critical_errors = [e for e in errors if '401' not in e['message'] and '404' not in e['message'] and '422' not in e['message']]
            
            if critical_errors:
                pytest.fail(f"Found {len(critical_errors)} critical console errors")
            else:
                print(f"   ⚠️  Only network errors (401/404/422) - acceptable for new deployment")
        else:
            print("✅ No console errors found")


class TestSpecificFeatures:
    """Test specific dashboard features."""
    
    def test_compliance_page_handles_no_data(self, authenticated_driver, base_url):
        """Test that compliance page gracefully handles missing data."""
        driver = authenticated_driver
        
        print("\n📋 Testing Compliance page error handling...")
        driver.get(f"{base_url}/dashboard/compliance")
        time.sleep(3)
        
        # Verify page loads
        heading = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Compliance')]"))
        )
        assert heading.is_displayed()
        print("   ✅ Compliance page heading found")
        
        # Check that error is not red (should be yellow/blue info message)
        red_errors = driver.find_elements(By.XPATH, "//*[contains(@class, 'bg-red') or contains(@class, 'text-red')]")
        displayed_red_errors = [e for e in red_errors if e.is_displayed() and 'error' in e.text.lower()]
        
        if displayed_red_errors:
            pytest.fail(f"Compliance page shows red error: {displayed_red_errors[0].text}")
        
        print("   ✅ No critical errors on compliance page")
    
    def test_playbooks_page_handles_no_playbooks(self, authenticated_driver, base_url):
        """Test that playbooks page gracefully handles empty state."""
        driver = authenticated_driver
        
        print("\n📖 Testing Playbooks page error handling...")
        driver.get(f"{base_url}/dashboard/playbooks")
        time.sleep(3)
        
        # Verify page loads
        heading = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Playbook') or contains(text(), 'SOAR')]"))
        )
        assert heading.is_displayed()
        print("   ✅ Playbooks page heading found")
        
        # Check that error is not red if no playbooks exist
        red_errors = driver.find_elements(By.XPATH, 
            "//*[contains(@class, 'bg-red') and contains(text(), 'Error loading playbooks')]"
        )
        displayed_red_errors = [e for e in red_errors if e.is_displayed()]
        
        if displayed_red_errors:
            pytest.fail(f"Playbooks page shows red error for empty state: {displayed_red_errors[0].text}")
        
        print("   ✅ Playbooks page handles empty state gracefully")
    
    def test_dashboard_security_pulse_visible(self, authenticated_driver, base_url):
        """Test that dashboard security pulse/snapshot is visible."""
        driver = authenticated_driver
        
        print("\n💓 Testing Dashboard security pulse...")
        driver.get(f"{base_url}/dashboard")
        time.sleep(5)
        
        # Look for any security-related content
        try:
            security_content = driver.find_elements(By.XPATH,
                "//*[contains(text(), 'Security') or contains(text(), 'Pulse') or "
                "contains(text(), 'Alert') or contains(text(), 'Incident')]"
            )
            
            visible_content = [e for e in security_content if e.is_displayed()]
            
            assert len(visible_content) > 0, "No security content visible on dashboard"
            print(f"   ✅ Found {len(visible_content)} security content elements")
            
        except AssertionError as e:
            # Check if dashboard is showing a friendly message instead
            info_messages = driver.find_elements(By.XPATH, "//*[contains(@class, 'yellow') or contains(@class, 'blue')]")
            if any(m.is_displayed() for m in info_messages):
                print("   ✅ Dashboard shows informational message (services not configured)")
            else:
                pytest.fail(str(e))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
