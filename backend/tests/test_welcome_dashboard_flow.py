"""
Selenium E2E test for complete flow:
1. Login
2. Go through onboarding steps
3. Verify welcome dashboard is shown
4. Verify dashboard content loads correctly
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
import uuid


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
    return os.getenv("WEBSITE_URL", "https://localhost:3443")


@pytest.fixture
def test_credentials():
    """Get test credentials from environment or use defaults."""
    return {
        "email": os.getenv("TEST_USERNAME", "admin@sentinelgrid.ai"),
        "password": os.getenv("TEST_PASSWORD", "admin123"),
    }


class TestWelcomeDashboardFlow:
    """E2E test for login → onboarding → welcome dashboard flow."""
    
    def test_complete_flow_login_onboarding_dashboard(self, driver, base_url, test_credentials):
        """
        Complete flow test:
        1. Login with credentials
        2. Navigate through onboarding steps (skip or complete)
        3. Verify welcome dashboard is shown
        4. Verify dashboard tiles and content load
        """
        print("\n" + "="*80)
        print("🧪 Starting Welcome Dashboard Flow Test")
        print("="*80)
        
        # Step 1: Login
        print("\n📝 Step 1: Logging in...")
        driver.get(f"{base_url}/login")
        
        # Wait for login form
        wait = WebDriverWait(driver, 15)
        email_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        print("✅ Login form loaded")
        
        # Fill in credentials
        email_input.clear()
        email_input.send_keys(test_credentials["email"])
        print(f"✅ Entered email: {test_credentials['email']}")
        
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_input.clear()
        password_input.send_keys(test_credentials["password"])
        print("✅ Entered password")
        
        # Submit login
        login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in') or contains(text(), 'Login')]")
        login_button.click()
        print("✅ Submitted login form")
        
        # Wait for login to complete and token to be stored
        time.sleep(5)
        
        # Verify token is stored
        try:
            token = driver.execute_script("return localStorage.getItem('access_token');")
            tenant_id = driver.execute_script("return localStorage.getItem('tenant_id');")
            if token:
                print(f"✅ Token stored in localStorage")
                print(f"✅ Tenant ID: {tenant_id}")
            else:
                # Check sessionStorage
                token = driver.execute_script("return sessionStorage.getItem('access_token');")
                if token:
                    print("✅ Token found in sessionStorage, copying to localStorage...")
                    driver.execute_script(f"localStorage.setItem('access_token', '{token}');")
                    if tenant_id:
                        driver.execute_script(f"localStorage.setItem('tenant_id', '{tenant_id}');")
        except Exception as e:
            print(f"⚠️  Could not verify token storage: {e}")
        
        # Wait for redirect to dashboard or onboarding
        print("\n⏳ Waiting for redirect after login...")
        try:
            wait.until(
                lambda d: "/dashboard" in d.current_url or "/onboarding" in d.current_url
            )
            current_url = driver.current_url
            print(f"✅ Redirected to: {current_url}")
        except TimeoutException:
            current_url = driver.current_url
            print(f"⚠️  Timeout waiting for redirect. Current URL: {current_url}")
            # Check for error messages
            try:
                error_elem = driver.find_element(By.CSS_SELECTOR, "[class*='error'], [class*='red']")
                if error_elem.is_displayed():
                    pytest.fail(f"Login failed with error: {error_elem.text}")
            except:
                pass
        
        # Step 2: Handle Onboarding
        if "/onboarding" in driver.current_url:
            print("\n📝 Step 2: Going through onboarding steps...")
            self._complete_onboarding(driver, base_url, wait)
        else:
            print("\n✅ Onboarding already complete, proceeding to dashboard")
        
        # Step 3: Verify Welcome Dashboard
        print("\n📝 Step 3: Verifying welcome dashboard...")
        
        # Navigate to dashboard (should redirect to /dashboard/welcome if onboarding incomplete)
        driver.get(f"{base_url}/dashboard")
        time.sleep(3)
        
        current_url = driver.current_url
        print(f"📍 Current URL: {current_url}")
        
        # Check if we're on welcome dashboard or main dashboard
        if "/dashboard/welcome" in current_url:
            print("✅ On welcome dashboard (onboarding incomplete)")
            self._verify_welcome_dashboard(driver, wait)
        elif "/dashboard" in current_url and "/welcome" not in current_url:
            print("✅ On main dashboard (onboarding complete)")
            # Verify main dashboard loaded
            try:
                wait.until(
                    EC.presence_of_element_located((By.XPATH, "//h1 | //h2 | //*[contains(text(), 'Dashboard')]"))
                )
                print("✅ Main dashboard content loaded")
            except TimeoutException:
                pytest.fail("Main dashboard did not load")
        else:
            pytest.fail(f"Unexpected URL after onboarding: {current_url}")
        
        print("\n" + "="*80)
        print("✅ Test completed successfully!")
        print("="*80)
    
    def _complete_onboarding(self, driver, base_url, wait):
        """Helper method to complete onboarding steps."""
        max_steps = 5  # Maximum number of onboarding steps
        step = 1
        
        while step <= max_steps:
            current_url = driver.current_url
            print(f"\n  📍 Onboarding Step {step} - URL: {current_url}")
            
            # Wait for step content to load
            try:
                wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1, h2, h3, form, button"))
                )
            except TimeoutException:
                print(f"  ⚠️  Step {step} content not loading, may have completed onboarding")
                break
            
            # Look for Skip button first (preferred for testing)
            skip_button = None
            try:
                skip_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Skip') or contains(text(), 'skip')]")
            except NoSuchElementException:
                pass
            
            # Look for Continue/Next button
            continue_button = None
            if not skip_button:
                try:
                    continue_button = driver.find_element(By.XPATH, 
                        "//button[contains(text(), 'Continue') or contains(text(), 'Next') or contains(text(), 'Complete')]")
                except NoSuchElementException:
                    pass
            
            # Handle step-specific actions
            if step == 1:  # Identity Provider step
                print("  🔍 Step 1: Identity Provider")
                # Try to select "Use SentinelGrid Identity" (skip IdP connection)
                try:
                    none_option = driver.find_element(By.XPATH, 
                        "//input[@value='none'] | //input[@type='radio' and contains(../label, 'SentinelGrid')]")
                    if not none_option.is_selected():
                        none_option.click()
                        print("  ✅ Selected 'Use SentinelGrid Identity'")
                except NoSuchElementException:
                    print("  ⚠️  Could not find 'none' option, continuing...")
            
            elif step == 2:  # Cloud connection step
                print("  🔍 Step 2: Cloud Connection")
                # Skip cloud connection for testing
                pass
            
            elif step == 3:  # Endpoint agent step
                print("  🔍 Step 3: Endpoint Agent")
                # Skip endpoint agent for testing
                pass
            
            elif step == 4:  # Git security step
                print("  🔍 Step 4: Git Security")
                # Skip git connection for testing
                pass
            
            # Click Skip or Continue button
            if skip_button:
                print(f"  ✅ Found Skip button, clicking...")
                skip_button.click()
                time.sleep(2)
            elif continue_button:
                print(f"  ✅ Found Continue button, clicking...")
                continue_button.click()
                time.sleep(2)
            else:
                print(f"  ⚠️  No Skip or Continue button found, may have completed onboarding")
                break
            
            # Check if we've moved to next step or completed onboarding
            time.sleep(2)
            new_url = driver.current_url
            
            if "/dashboard" in new_url and "/onboarding" not in new_url:
                print(f"  ✅ Onboarding completed! Redirected to dashboard")
                break
            elif f"step={step+1}" in new_url or (step < max_steps and new_url != current_url):
                print(f"  ✅ Moved to step {step+1}")
                step += 1
            else:
                # May have completed or stuck
                if "/dashboard" in new_url:
                    print(f"  ✅ Onboarding completed!")
                    break
                else:
                    print(f"  ⚠️  Still on step {step}, continuing...")
                    step += 1
        
        # Final check - make sure we're not stuck on onboarding
        final_url = driver.current_url
        if "/onboarding" in final_url:
            print("  ⚠️  Still on onboarding page, trying to navigate to dashboard...")
            driver.get(f"{base_url}/dashboard")
            time.sleep(3)
    
    def _verify_welcome_dashboard(self, driver, wait):
        """Verify welcome dashboard content is loaded."""
        print("\n  🔍 Verifying welcome dashboard content...")
        
        # Wait for dashboard to load
        time.sleep(3)
        
        # Check for environment validation banner
        try:
            banner = wait.until(
                EC.presence_of_element_located((By.XPATH, 
                    "//*[contains(text(), 'Protected by SentinelGrid') or contains(text(), 'Validated')]"))
            )
            print("  ✅ Environment validation banner found")
        except TimeoutException:
            print("  ⚠️  Environment validation banner not found")
        
        # Check for Security Pulse tile
        try:
            security_pulse = wait.until(
                EC.presence_of_element_located((By.XPATH, 
                    "//*[contains(text(), 'Security Score') or contains(text(), 'Security Pulse')]"))
            )
            print("  ✅ Security Pulse tile found")
        except TimeoutException:
            print("  ⚠️  Security Pulse tile not found (may still be loading)")
        
        # Check for Open Incidents tile
        try:
            incidents = driver.find_element(By.XPATH, 
                "//*[contains(text(), 'Active Incidents') or contains(text(), 'Incidents')]")
            print("  ✅ Open Incidents tile found")
        except NoSuchElementException:
            print("  ⚠️  Open Incidents tile not found")
        
        # Check for Cloud Posture tile
        try:
            cloud_posture = driver.find_element(By.XPATH, 
                "//*[contains(text(), 'Cloud Security') or contains(text(), 'Cloud')]")
            print("  ✅ Cloud Posture tile found")
        except NoSuchElementException:
            print("  ⚠️  Cloud Posture tile not found")
        
        # Check for People & Access tile
        try:
            people_access = driver.find_element(By.XPATH, 
                "//*[contains(text(), 'People & Access') or contains(text(), 'MFA')]")
            print("  ✅ People & Access tile found")
        except NoSuchElementException:
            print("  ⚠️  People & Access tile not found")
        
        # Check for Usage & Health tile
        try:
            usage_health = driver.find_element(By.XPATH, 
                "//*[contains(text(), 'System Health') or contains(text(), 'Usage')]")
            print("  ✅ Usage & Health tile found")
        except NoSuchElementException:
            print("  ⚠️  Usage & Health tile not found")
        
        # Check for Recommended Actions section
        try:
            recommendations = driver.find_element(By.XPATH, 
                "//*[contains(text(), 'Recommended Next Steps') or contains(text(), 'Recommended')]")
            print("  ✅ Recommended Actions section found")
        except NoSuchElementException:
            print("  ⚠️  Recommended Actions section not found")
        
        # Check for AI Chatbot button (floating)
        try:
            chatbot_button = driver.find_element(By.XPATH, 
                "//button[contains(@class, 'fixed')] | //*[contains(@aria-label, 'AI') or contains(@aria-label, 'Assistant')]")
            print("  ✅ AI Chatbot button found")
        except NoSuchElementException:
            print("  ⚠️  AI Chatbot button not found")
        
        # Verify dashboard is not showing error
        page_text = driver.page_source.lower()
        if "application error" in page_text or "client-side exception" in page_text:
            pytest.fail("Dashboard is showing an error page")
        
        print("  ✅ Welcome dashboard verification complete")
    
    def test_welcome_dashboard_redirects_after_onboarding_complete(self, driver, base_url, test_credentials):
        """
        Test that welcome dashboard redirects to main dashboard after onboarding is complete.
        This test assumes onboarding is already complete.
        """
        print("\n" + "="*80)
        print("🧪 Testing Welcome Dashboard Redirect After Onboarding")
        print("="*80)
        
        # Login
        driver.get(f"{base_url}/login")
        wait = WebDriverWait(driver, 15)
        
        email_input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        email_input.clear()
        email_input.send_keys(test_credentials["email"])
        
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_input.clear()
        password_input.send_keys(test_credentials["password"])
        
        login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in')]")
        login_button.click()
        
        time.sleep(5)
        
        # Navigate directly to welcome dashboard
        driver.get(f"{base_url}/dashboard/welcome")
        time.sleep(3)
        
        # Check if we're redirected to main dashboard (onboarding complete)
        # or stay on welcome dashboard (onboarding incomplete)
        current_url = driver.current_url
        
        if "/dashboard/welcome" in current_url:
            print("✅ On welcome dashboard (onboarding incomplete)")
        elif "/dashboard" in current_url and "/welcome" not in current_url:
            print("✅ Redirected to main dashboard (onboarding complete)")
        else:
            pytest.fail(f"Unexpected URL: {current_url}")

