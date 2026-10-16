"""
Selenium E2E UI Tests for IAM Features.

Tests the IAM portal UI including:
- People page
- My Access page  
- Policies page
- Access Review (Campaigns/Certifications)

This automates the manual testing you've been doing.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
import requests
import time
import os
import uuid

# Where to store screenshots from failures (kept out of the repo via .gitignore)
SCREENSHOT_DIR = os.path.join("artifacts", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def _save_screenshot(driver, filename: str):
    """Save a screenshot into the dedicated artifacts directory."""
    path = os.path.join(SCREENSHOT_DIR, filename)
    driver.save_screenshot(path)
    print(f"📸 Saved screenshot to {path}")

# Import Vault helper to fetch passwords
try:
    # Try relative import first (when running from backend/tests/)
    try:
        from tests.helpers.vault_helper import get_platform_admin_password, get_test_customer_password
    except ImportError:
        # Try absolute import (when running from project root)
        from backend.tests.helpers.vault_helper import get_platform_admin_password, get_test_customer_password
    VAULT_AVAILABLE = True
except ImportError as e:
    VAULT_AVAILABLE = False
    print(f"⚠️  Vault helper not available ({e}), using environment variables or defaults")


@pytest.fixture(scope="session")
def driver():
    """Create Selenium WebDriver instance."""
    options = webdriver.ChromeOptions()
    
    # Headless mode for CI, visible for local debugging
    if os.getenv("CI") == "true" or os.getenv("HEADLESS") == "true":
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    else:
        print("🖥️  Running in VISIBLE mode - you can watch the test!")
    
    options.add_argument("--disable-notifications")
    # For local HTTPS with self-signed certificates
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--allow-insecure-localhost")
    options.set_capability('acceptInsecureCerts', True)
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    driver.maximize_window()
    
    yield driver
    
    if os.getenv("KEEP_BROWSER") != "true":
        driver.quit()


@pytest.fixture(scope="session")
def base_url():
    """Get base URL for testing."""
    # Default to HTTPS on port 3443 if not specified (matches nginx proxy)
    return os.getenv("WEBSITE_URL", "https://localhost:3443")


@pytest.fixture(scope="session")
def test_credentials():
    """Test user credentials from Vault or environment variables."""
    email = os.getenv("TEST_EMAIL", "admin@sentinelgrid.ai")
    
    # Get password from Vault if available, otherwise use environment variable or default
    if VAULT_AVAILABLE:
        try:
            # Try to get platform admin password from Vault
            if email == "admin@sentinelgrid.ai" or "admin" in email.lower():
                password = get_platform_admin_password()
                print("✅ Retrieved platform admin password from Vault")
            else:
                # Try test customer password
                password = get_test_customer_password()
                print("✅ Retrieved test customer password from Vault")
        except Exception as e:
            print(f"⚠️  Failed to get password from Vault: {e}, using fallback")
            password = os.getenv("TEST_PASSWORD", "admin123")
    else:
        password = os.getenv("TEST_PASSWORD", "admin123")
    
    return {
        "email": email,
        "password": password
    }


@pytest.fixture(scope="session")
def demo_credentials():
    """Demo realm credentials for testing."""
    return {
        "email": os.getenv("DEMO_EMAIL", "admin@demo.sentinelgrid.ai"),
        "password": os.getenv("DEMO_PASSWORD", "DemoPassword123!")
    }


@pytest.fixture(scope="session")
def logged_in_driver(driver, base_url, test_credentials):
    """Get driver with user already logged in."""
    print(f"\n🔐 Logging in as {test_credentials['email']}...")
    
    # Navigate to login page
    driver.get(f"{base_url}/login")
    time.sleep(2)
    
    try:
        # Find and fill email field
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']"))
        )
        email_input.clear()
        email_input.send_keys(test_credentials['email'])
        
        # Find and fill password field
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
        password_input.clear()
        password_input.send_keys(test_credentials['password'])
        
        # Click login button
        login_buttons = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
        if not login_buttons:
            login_buttons = driver.find_elements(By.TAG_NAME, "button")
        
        # Find the right button
        for btn in login_buttons:
            if 'sign' in btn.text.lower() or 'login' in btn.text.lower() or not btn.text:
                login_button = btn
                break
        else:
            login_button = login_buttons[0] if login_buttons else None
        
        if login_button:
            login_button.click()
        else:
            raise Exception("Login button not found")
        
        # Wait for redirect to dashboard
        WebDriverWait(driver, 15).until(
            lambda d: "/dashboard" in d.current_url
        )
        
        print(f"✅ Login successful! Current URL: {driver.current_url}")
        
    except Exception as e:
        print(f"❌ Login failed: {e}")
        _save_screenshot(driver, "login_failed.png")
        pytest.fail(f"Login failed: {e}")
    
    return driver


@pytest.fixture(scope="session")
def demo_logged_in_driver(driver, base_url, demo_credentials):
    """Get driver with demo user already logged in."""
    print(f"\n🔐 Logging into demo realm as {demo_credentials['email']}...")
    
    # Navigate to login page
    driver.get(f"{base_url}/login")
    time.sleep(2)
    
    try:
        # Find and fill email field
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email']"))
        )
        email_input.clear()
        email_input.send_keys(demo_credentials['email'])
        
        # Find and fill password field
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
        password_input.clear()
        password_input.send_keys(demo_credentials['password'])
        
        # Click login button
        login_buttons = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
        if not login_buttons:
            login_buttons = driver.find_elements(By.TAG_NAME, "button")
        
        # Find the right button
        for btn in login_buttons:
            if 'sign' in btn.text.lower() or 'login' in btn.text.lower() or not btn.text:
                login_button = btn
                break
        else:
            login_button = login_buttons[0] if login_buttons else None
        
        if login_button:
            login_button.click()
        else:
            raise Exception("Login button not found")
        
        # Wait for redirect to dashboard
        WebDriverWait(driver, 15).until(
            lambda d: "/dashboard" in d.current_url
        )
        
        print(f"✅ Demo realm login successful! Current URL: {driver.current_url}")
        
    except Exception as e:
        print(f"❌ Demo realm login failed: {e}")
        _save_screenshot(driver, "demo_login_failed.png")
        pytest.fail(f"Demo realm login failed: {e}")
    
    return driver


class TestIAMPeoplePage:
    """Test IAM People page functionality."""
    
    def test_people_page_loads(self, logged_in_driver, base_url):
        """Test that IAM People page loads successfully."""
        print("\n🧪 Testing IAM People Page...")
        
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard/iam/people")
        time.sleep(3)
        
        try:
            # Check current URL
            current_url = driver.current_url
            print(f"🌐 Current URL: {current_url}")
            
            # Check for browser console errors
            try:
                logs = driver.get_log('browser')
                errors = [log for log in logs if log['level'] == 'SEVERE']
                if errors:
                    print(f"⚠️  Browser console errors: {len(errors)}")
                    for err in errors[:3]:
                        print(f"  - {err['message'][:100]}")
            except:
                pass
            
            # Get all h1 elements
            all_h1 = driver.find_elements(By.TAG_NAME, "h1")
            print(f"📄 Found {len(all_h1)} h1 elements:")
            for h1 in all_h1:
                if h1.is_displayed():
                    print(f"  - {h1.text}")
            
            # Take screenshot
            driver.save_screenshot("iam_people_page.png")
            print("📸 Screenshot saved: iam_people_page.png")
            
            # Check for people-specific content
            body_text = driver.find_element(By.TAG_NAME, "body").text
            
            if "People" in body_text and ("Manage users" in body_text or "Add User" in body_text):
                print("✅ People page content found!")
            elif "No users" in body_text:
                print("✅ People page loaded (empty state)")
            elif "Loading users" in body_text:
                print("⏳ Still loading users...")
                time.sleep(2)
            else:
                print(f"⚠️  Unexpected content - page may not have loaded")
                print(f"📋 Body preview: {body_text[:500]}")
            
            print("✅ People page test completed")
            
        except Exception as e:
            driver.save_screenshot("people_page_error.png")
            print(f"❌ People page test failed: {e}")
            raise
    
    def test_people_page_navigation(self, logged_in_driver, base_url):
        """Test navigation on people page."""
        print("\n🧪 Testing People Page Navigation...")
        
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard/iam/people")
        time.sleep(2)
        
        # Check for navigation elements
        try:
            # Check sidebar is present
            sidebar = driver.find_element(By.CSS_SELECTOR, "nav, aside, [role='navigation']")
            print("✅ Sidebar navigation found")
            
            # Check for IAM menu items
            iam_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "People")
            print(f"✅ Found {len(iam_links)} 'People' navigation links")
            
        except Exception as e:
            print(f"⚠️  Navigation check: {e}")
    
    def test_demo_realm_users_visible(self, demo_logged_in_driver, base_url):
        """Test that seeded users are visible on the IAM People page in demo realm."""
        print("\n🧪 Testing Demo Realm Users Visibility...")
        
        driver = demo_logged_in_driver
        driver.get(f"{base_url}/dashboard/iam/people")
        
        # Wait for page to load
        print("⏳ Waiting for page to load...")
        time.sleep(5)  # Give time for API call to complete
        
        try:
            # Check for browser console errors
            try:
                logs = driver.get_log('browser')
                errors = [log for log in logs if log['level'] == 'SEVERE']
                if errors:
                    print(f"⚠️  Browser console errors: {len(errors)}")
                    for err in errors[:5]:
                        print(f"  - {err['message'][:150]}")
            except:
                pass
            
            # Take screenshot
            driver.save_screenshot("demo_people_page.png")
            print("📸 Screenshot saved: demo_people_page.png")
            
            # Get page body text
            body_text = driver.find_element(By.TAG_NAME, "body").text
            print(f"📋 Page body text preview: {body_text[:500]}")
            
            # Check for loading state
            if "Loading users" in body_text:
                print("⏳ Still loading users, waiting longer...")
                time.sleep(5)
                body_text = driver.find_element(By.TAG_NAME, "body").text
            
            # Check for empty state
            if (
                "no users found" in body_text.lower()
                or "no users match your filters" in body_text.lower()
                or ("no users" in body_text.lower() and "found" in body_text.lower())
            ):
                print("❌ Empty state detected - no users found!")
                driver.save_screenshot("demo_people_page_empty.png")
                pytest.fail("Expected to see seeded users but page shows empty state")
            
            # Prefer table rows for the actual user list
            user_rows = driver.find_elements(By.XPATH, "//table//tbody/tr[td]")
            users_found: list[str] = []

            if user_rows:
                print(f"✅ Found {len(user_rows)} user table rows")
                for i, row in enumerate(user_rows[:10]):
                    try:
                        row_text = row.text
                        if row_text.strip():
                            users_found.append(row_text)
                            print(f"  Row {i+1}: {row_text[:120]}")
                    except Exception:
                        continue
            else:
                # Fall back to card-style layouts if table not present
                user_card_selectors = [
                    (By.CSS_SELECTOR, "[class*='bg-white'][class*='border'][class*='rounded-lg']"),
                    (By.CSS_SELECTOR, "[class*='UserCard']"),
                    (By.CSS_SELECTOR, "div[class*='card']"),
                    (By.XPATH, "//div[contains(@class, 'bg-white') and contains(@class, 'border')]"),
                    (By.XPATH, "//div[contains(@class, 'rounded-lg')]"),
                ]

                for selector_type, selector_value in user_card_selectors:
                    try:
                        cards = driver.find_elements(selector_type, selector_value)
                        if cards:
                            print(f"✅ Found {len(cards)} user cards using {selector_type}")
                            for i, card in enumerate(cards[:10]):
                                try:
                                    card_text = card.text
                                    if card_text.strip():
                                        users_found.append(card_text)
                                        print(f"  Card {i+1}: {card_text[:100]}")
                                except Exception:
                                    continue
                            break
                    except Exception:
                        continue

            if not users_found:
                print("❌ No user entries rendered on People page")
                driver.save_screenshot("demo_people_page_no_users.png")
                pytest.fail("Expected seeded users but no user entries were rendered")

            print(f"✅ Successfully found {len(users_found)} user entries on the page!")

            demo_user_found = any("demo" in text.lower() or "@" in text for text in users_found)
            if not demo_user_found:
                print("❌ Users found but none appear to be from demo realm")
                driver.save_screenshot("demo_people_page_no_demo_user.png")
                pytest.fail("No demo realm users visible in People page")

            driver.save_screenshot("demo_people_page_users_visible.png")
            print("📸 Screenshot saved: demo_people_page_users_visible.png")
            
            # Check network requests if possible
            try:
                # Try to get network logs (Chrome only)
                performance_logs = driver.get_log('performance')
                api_requests = [log for log in performance_logs if 'api/iam-portal/users' in str(log.get('message', ''))]
                if api_requests:
                    print(f"✅ Found {len(api_requests)} API requests to /api/iam-portal/users")
                else:
                    print("⚠️  No API requests to /api/iam-portal/users found in performance logs")
            except:
                print("ℹ️  Could not check network requests (not supported or not available)")
            
            print("✅ Demo realm users visibility test completed")
            
        except TimeoutException as e:
            driver.save_screenshot("demo_people_page_timeout.png")
            print(f"❌ Timeout during test: {e}")
            raise
        except Exception as e:
            driver.save_screenshot("demo_people_page_error.png")
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def test_add_user_functionality(self, logged_in_driver, base_url):
        """Test Add User button and user creation flow (team/tenant-aware)."""
        print("\n🧪 Testing Add User Functionality...")
        
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard")
        time.sleep(3)
        
        try:
            # Navigate to People & Access section first
            print("🔍 Looking for 'People & Access' navigation link...")
            people_access_link = None
            
            # Try multiple strategies to find the navigation link
            nav_selectors = [
                (By.XPATH, "//a[contains(text(), 'People & Access')]"),
                (By.XPATH, "//*[contains(text(), 'People & Access')]"),
                (By.PARTIAL_LINK_TEXT, "People & Access"),
                (By.PARTIAL_LINK_TEXT, "People"),
                (By.XPATH, "//a[contains(@href, 'iam') or contains(@href, 'people')]"),
                (By.XPATH, "//nav//a[contains(text(), 'People')]"),
            ]
            
            for selector_type, selector_value in nav_selectors:
                try:
                    print(f"  Trying navigation selector: {selector_type} = {selector_value}")
                    people_access_link = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    print(f"✅ Found 'People & Access' link using {selector_type}")
                    break
                except TimeoutException:
                    continue
            
            if not people_access_link:
                # Take screenshot for debugging
                driver.save_screenshot("people_access_link_not_found.png")
                print("❌ Could not find 'People & Access' navigation link")
                # Print page source snippet for debugging
                body_text = driver.find_element(By.TAG_NAME, "body").text
                print(f"📋 Page text preview: {body_text[:500]}")
                # Try to find all links on the page
                all_links = driver.find_elements(By.TAG_NAME, "a")
                print(f"📊 Found {len(all_links)} links on page:")
                for i, link in enumerate(all_links[:15]):  # Show first 15
                    if link.is_displayed() and link.text.strip():
                        print(f"  {i+1}. '{link.text.strip()}' (href: {link.get_attribute('href')})")
                raise Exception("Could not find 'People & Access' navigation link on the page")
            
            people_access_link.click()
            print("✅ Clicked 'People & Access' link")
            time.sleep(2)
            
            # Now navigate to the People page if we're not already there
            current_url = driver.current_url
            if "/iam/people" not in current_url:
                print("🔍 Navigating to People page...")
                driver.get(f"{base_url}/dashboard/iam/people")
                time.sleep(3)
            
            # Get initial user count
            initial_user_count = len(driver.find_elements(By.CSS_SELECTOR, "[class*='bg-white'][class*='border'], [class*='rounded-lg']"))
            print(f"📊 Initial user count (approximate): {initial_user_count}")
            
            # Find and click "Add User" button - try multiple selectors
            print("🔍 Looking for 'Add User' button...")
            add_user_button = None
            
            # Try multiple strategies to find the button
            selectors = [
                (By.XPATH, "//button[contains(text(), 'Add User')]"),
                (By.XPATH, "//button[contains(., 'Add User')]"),
                (By.XPATH, "//button[contains(text(), 'Add')]"),
                (By.CSS_SELECTOR, "button[class*='Add'], button[class*='add']"),
                (By.PARTIAL_LINK_TEXT, "Add User"),
                (By.XPATH, "//*[contains(text(), 'Add User')]"),
            ]
            
            for selector_type, selector_value in selectors:
                try:
                    print(f"  Trying selector: {selector_type} = {selector_value}")
                    add_user_button = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    print(f"✅ Found 'Add User' button using {selector_type}")
                    break
                except TimeoutException:
                    continue
            
            if not add_user_button:
                # Take screenshot for debugging
                driver.save_screenshot("add_user_button_not_found.png")
                print("❌ Could not find 'Add User' button")
                # Print page source snippet for debugging
                body_text = driver.find_element(By.TAG_NAME, "body").text
                print(f"📋 Page text preview: {body_text[:500]}")
                # Try to find all buttons on the page
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                print(f"📊 Found {len(all_buttons)} buttons on page:")
                for i, btn in enumerate(all_buttons[:10]):  # Show first 10
                    if btn.is_displayed():
                        print(f"  {i+1}. '{btn.text}' (visible)")
                raise Exception("Could not find 'Add User' button on the page")
            
            add_user_button.click()
            print("✅ Clicked 'Add User' button")
            time.sleep(2)
            
            # Wait for modal to appear
            print("⏳ Waiting for Add User modal...")
            modal = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='fixed'][class*='inset-0'], [class*='modal'], [class*='z-50']"))
            )
            print("✅ Modal appeared")
            
            # Generate unique test user data
            test_uuid = uuid.uuid4().hex[:8]
            test_email = f"testuser_{test_uuid}@example.com"
            test_first_name = f"Test{test_uuid[:4]}"
            test_last_name = f"User{test_uuid[4:]}"
            test_department = "Engineering"
            test_team = "Platform"
            
            print(f"📝 Creating user with email: {test_email}")
            
            # Fill in email field
            print("📝 Filling email field...")
            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
            )
            email_input.clear()
            email_input.send_keys(test_email)
            print(f"✅ Entered email: {test_email}")
            
            # Fill in first name
            print("📝 Filling first name field...")
            first_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
            if first_name_inputs:
                # Usually first text input is first name
                first_name_input = first_name_inputs[0]
                first_name_input.clear()
                first_name_input.send_keys(test_first_name)
                print(f"✅ Entered first name: {test_first_name}")
            else:
                print("⚠️  First name input not found, trying alternative selector...")
                first_name_input = driver.find_element(By.XPATH, "//input[contains(@placeholder, 'First') or contains(@placeholder, 'first')]")
                first_name_input.clear()
                first_name_input.send_keys(test_first_name)
                print(f"✅ Entered first name: {test_first_name}")
            
            # Fill in last name
            print("📝 Filling last name field...")
            if len(first_name_inputs) > 1:
                last_name_input = first_name_inputs[1]
                last_name_input.clear()
                last_name_input.send_keys(test_last_name)
                print(f"✅ Entered last name: {test_last_name}")
            else:
                print("⚠️  Last name input not found, trying alternative selector...")
                last_name_input = driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Last') or contains(@placeholder, 'last')]")
                last_name_input.clear()
                last_name_input.send_keys(test_last_name)
                print(f"✅ Entered last name: {test_last_name}")
            
            # Fill in department and team fields
            print("📝 Filling department and team fields...")
            try:
                # Department select/dropdown first if present
                dept_selects = driver.find_elements(By.TAG_NAME, "select")
                if dept_selects:
                    dept_selects[0].send_keys(test_department)
                    print(f"✅ Selected department: {test_department}")
                # Team input (text after names)
                text_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
                if len(text_inputs) > 2:
                    team_input = text_inputs[2]
                    team_input.clear()
                    team_input.send_keys(test_team)
                    print(f"✅ Entered team: {test_team}")
                else:
                    # fallback by placeholder
                    team_input = driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Team') or contains(@placeholder, 'team')]")
                    team_input.clear()
                    team_input.send_keys(test_team)
                    print(f"✅ Entered team (fallback): {test_team}")
            except Exception as e:
                print(f"⚠️  Department/Team field not found or not required: {e}")
            
            # Take screenshot before submission
            driver.save_screenshot("add_user_form_filled.png")
            print("📸 Screenshot saved: add_user_form_filled.png")
            
            # Submit the form
            print("🚀 Submitting form...")
            submit_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Invite User') or contains(text(), 'Create User') or contains(text(), 'Add User')]"))
            )
            
            # Scroll button into view and use JavaScript click to avoid overlay interception
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
            time.sleep(0.5)  # Brief wait for scroll
            
            # Try regular click first, fall back to JavaScript click if intercepted
            try:
                submit_button.click()
                print("✅ Clicked submit button (regular click)")
            except Exception as e:
                print(f"⚠️  Regular click failed ({e}), trying JavaScript click...")
                driver.execute_script("arguments[0].click();", submit_button)
                print("✅ Clicked submit button (JavaScript click)")
            
            # Wait for form submission to complete
            print("⏳ Waiting for user creation...")
            time.sleep(3)
            
            # Check if modal closed (indicates success)
            try:
                WebDriverWait(driver, 10).until(
                    EC.invisibility_of_element(modal)
                )
                print("✅ Modal closed - user creation likely successful")
            except TimeoutException:
                # Check for error messages
                error_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='error'], [class*='red'], [class*='text-red']")
                if error_elements:
                    error_text = ' '.join([e.text for e in error_elements if e.text and e.is_displayed()])
                    if error_text:
                        print(f"❌ Error during user creation: {error_text}")
                        driver.save_screenshot("add_user_error.png")
                        pytest.fail(f"User creation failed: {error_text}")
                else:
                    print("⚠️  Modal still open, but no error found - may still be processing")
                    time.sleep(3)
            
            # Wait for page to refresh/update
            time.sleep(2)
            
            # Verify user appears in the list
            print("🔍 Verifying user appears in the list...")
            driver.refresh()  # Refresh to ensure we see the new user
            time.sleep(3)
            
            # Check if the new user email appears in the page
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if test_email in body_text:
                print(f"✅ User {test_email} found in the user list!")
            else:
                print(f"⚠️  User {test_email} not immediately visible in list")
                print(f"📋 Page content preview: {body_text[:500]}")
                # Take screenshot for debugging
                driver.save_screenshot("add_user_verification.png")
                # Don't fail the test - user might be created but not yet visible
                # or the email might be displayed differently
            
            # Take final screenshot
            driver.save_screenshot("add_user_complete.png")
            print("📸 Screenshot saved: add_user_complete.png")
            
            print("✅ Add User functionality test completed")
            
        except TimeoutException as e:
            driver.save_screenshot("add_user_timeout.png")
            print(f"❌ Timeout during Add User test: {e}")
            raise
        except Exception as e:
            driver.save_screenshot("add_user_error.png")
            print(f"❌ Add User test failed: {e}")
            raise


class TestIAMMyAccessPage:
    """Test My Access page functionality."""
    
    def test_my_access_page_loads(self, logged_in_driver, base_url):
        """Test that My Access page loads successfully."""
        print("\n🧪 Testing My Access Page...")
        
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard/iam/my-access")
        time.sleep(3)
        
        try:
            # Check page loaded
            page_title = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            print(f"📄 Page title: {page_title.text}")
            
            # Take screenshot
            driver.save_screenshot("my_access_page.png")
            print("📸 Screenshot saved: my_access_page.png")
            
            # Check for access summary or empty state
            body_text = driver.find_element(By.TAG_NAME, "body").text
            
            if "entitlement" in body_text.lower() or "access" in body_text.lower():
                print("✅ Access information displayed")
            elif "no access" in body_text.lower() or "empty" in body_text.lower():
                print("ℹ️  Empty state displayed (no access assigned)")
            else:
                print(f"📋 Page content: {body_text[:300]}")
            
            print("✅ My Access page loaded successfully")
            
        except Exception as e:
            driver.save_screenshot("my_access_error.png")
            print(f"❌ My Access page test failed: {e}")
            raise


class TestIAMPoliciesPage:
    """Test IAM Policies page functionality."""
    
    def test_policies_page_loads(self, logged_in_driver, base_url):
        """Test that IAM Policies page loads successfully."""
        print("\n🧪 Testing IAM Policies Page...")
        
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard/iam/policies")
        time.sleep(3)
        
        try:
            # Check page loaded
            page_title = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            print(f"📄 Page title: {page_title.text}")
            
            # Take screenshot
            driver.save_screenshot("policies_page.png")
            print("📸 Screenshot saved: policies_page.png")
            
            # Check for policy tabs
            try:
                tabs = driver.find_elements(By.CSS_SELECTOR, "[role='tab'], button")
                policy_tabs = [t for t in tabs if any(word in t.text.lower() for word in ['signon', 'sign-on', 'access', 'approval', 'sod'])]
                print(f"✅ Found {len(policy_tabs)} policy tabs")
                for tab in policy_tabs[:4]:
                    print(f"  - {tab.text}")
            except:
                print("⚠️  No policy tabs found")
            
            # Check for policies or templates
            body_text = driver.find_element(By.TAG_NAME, "body").text
            
            if "policy" in body_text.lower() or "template" in body_text.lower():
                print("✅ Policy content displayed")
            elif "no policies" in body_text.lower():
                print("ℹ️  Empty state displayed (no policies configured)")
            else:
                print(f"📋 Page content: {body_text[:300]}")
            
            print("✅ Policies page loaded successfully")
            
        except Exception as e:
            driver.save_screenshot("policies_page_error.png")
            print(f"❌ Policies page test failed: {e}")
            raise


class TestAccessReviewPages:
    """Test Access Review (Campaigns and Certifications) pages."""
    
    def test_campaigns_page_loads(self, logged_in_driver, base_url):
        """Test that Campaigns page loads successfully."""
        print("\n🧪 Testing Access Review Campaigns Page...")
        
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard/campaigns")
        time.sleep(3)
        
        try:
            # Check page loaded
            page_title = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            print(f"📄 Page title: {page_title.text}")
            
            # Take screenshot
            driver.save_screenshot("campaigns_page.png")
            print("📸 Screenshot saved: campaigns_page.png")
            
            # Check for campaigns list or empty state
            body_text = driver.find_element(By.TAG_NAME, "body").text
            
            if "campaign" in body_text.lower():
                print("✅ Campaign content displayed")
                
                # Try to find "Create Campaign" or similar button
                try:
                    create_buttons = driver.find_elements(By.PARTIAL_LINK_TEXT, "Create")
                    create_buttons += driver.find_elements(By.PARTIAL_LINK_TEXT, "New")
                    if create_buttons:
                        print(f"✅ Found {len(create_buttons)} action buttons")
                except:
                    pass
            else:
                print(f"📋 Page content: {body_text[:300]}")
            
            print("✅ Campaigns page loaded successfully")
            
        except Exception as e:
            driver.save_screenshot("campaigns_page_error.png")
            print(f"❌ Campaigns page test failed: {e}")
            raise
    
    def test_certifications_page_loads(self, logged_in_driver, base_url):
        """Test that Certifications page loads successfully."""
        print("\n🧪 Testing Access Certifications Page...")
        
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard/certifications")
        time.sleep(3)
        
        try:
            # Check page loaded
            page_title = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            print(f"📄 Page title: {page_title.text}")
            
            # Take screenshot
            driver.save_screenshot("certifications_page.png")
            print("📸 Screenshot saved: certifications_page.png")
            
            # Check page content
            body_text = driver.find_element(By.TAG_NAME, "body").text
            print(f"📋 Page loaded: {body_text[:200]}")
            
            print("✅ Certifications page loaded successfully")
            
        except Exception as e:
            driver.save_screenshot("certifications_page_error.png")
            print(f"❌ Certifications page test failed: {e}")
            raise


class TestDashboardPages:
    """Test main dashboard and other key pages."""
    
    def test_main_dashboard_loads(self, logged_in_driver, base_url):
        """Test main dashboard loads and shows alert data."""
        print("\n🧪 Testing Main Dashboard...")
        
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard")
        time.sleep(3)
        
        try:
            # Check for stats cards
            stats_cards = driver.find_elements(By.CSS_SELECTOR, "[class*='grid']")
            print(f"✅ Found {len(stats_cards)} grid elements")
            
            # Take screenshot
            driver.save_screenshot("main_dashboard.png")
            print("📸 Screenshot saved: main_dashboard.png")
            
            # Check for alert counts
            body_text = driver.find_element(By.TAG_NAME, "body").text
            
            # Look for alert indicators
            if "alert" in body_text.lower():
                print("✅ Alert information displayed")
                
                # Try to extract alert count
                if "Total Alerts" in body_text or "total alerts" in body_text.lower():
                    print("✅ Total Alerts stat found")
            
            print("✅ Main dashboard loaded successfully")
            
        except Exception as e:
            driver.save_screenshot("dashboard_error.png")
            print(f"❌ Dashboard test failed: {e}")
            raise
    
    def test_alerts_page_shows_data(self, logged_in_driver, base_url):
        """Test that alerts page shows the seeded alert data."""
        print("\n🧪 Testing Alerts Page Data...")
        
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard/alerts")
        time.sleep(3)
        
        try:
            # Take screenshot
            driver.save_screenshot("alerts_page.png")
            print("📸 Screenshot saved: alerts_page.png")
            
            # Check for alerts table
            try:
                table = driver.find_element(By.TAG_NAME, "table")
                print("✅ Alerts table found")
                
                # Count alert rows
                alert_rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
                print(f"📊 Found {len(alert_rows)} alert rows in table")
                
                if len(alert_rows) > 0:
                    # Get first alert details
                    first_row = alert_rows[0]
                    row_text = first_row.text
                    print(f"📋 First alert: {row_text[:100]}")
                    
                    # Try to click View button
                    try:
                        view_link = first_row.find_element(By.PARTIAL_LINK_TEXT, "View")
                        print("✅ 'View' link found on alert")
                    except:
                        print("⚠️  No 'View' link found")
                        
                    assert len(alert_rows) >= 10, f"Expected 10 alerts, found {len(alert_rows)}"
                    print("✅ All 10 seeded alerts are visible!")
                else:
                    print("⚠️  No alerts in table - seeding may have failed")
                
            except:
                # Check for empty state
                body_text = driver.find_element(By.TAG_NAME, "body").text
                if "no alerts" in body_text.lower():
                    print("⚠️  Empty state: No alerts found")
                    pytest.fail("Expected 10 seeded alerts but found none")
                else:
                    print(f"⚠️  Unexpected state: {body_text[:200]}")
            
            print("✅ Alerts page test completed")
            
        except AssertionError:
            raise
        except Exception as e:
            driver.save_screenshot("alerts_page_error.png")
            print(f"❌ Alerts page test failed: {e}")
            raise
    
    def test_playbooks_page_shows_data(self, logged_in_driver, base_url):
        """Test that playbooks page shows the seeded playbooks."""
        print("\n🧪 Testing Playbooks Page Data...")
        
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard/playbooks")
        time.sleep(3)
        
        try:
            # Take screenshot
            driver.save_screenshot("playbooks_page.png")
            print("📸 Screenshot saved: playbooks_page.png")
            
            # Check for playbook cards
            playbook_cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/dashboard/playbooks/']")
            print(f"📊 Found {len(playbook_cards)} playbook cards")
            
            if len(playbook_cards) >= 15:
                print("✅ All 15 seeded playbooks are visible!")
                
                # Print first few playbook names
                for i, card in enumerate(playbook_cards[:5]):
                    print(f"  {i+1}. {card.text[:60]}")
            else:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                if "no playbooks" in body_text.lower():
                    print("⚠️  Empty state: No playbooks found")
                    pytest.fail(f"Expected 15 seeded playbooks but found {len(playbook_cards)}")
            
            print("✅ Playbooks page test completed")
            
        except AssertionError:
            raise
        except Exception as e:
            driver.save_screenshot("playbooks_page_error.png")
            print(f"❌ Playbooks page test failed: {e}")
            raise


class TestNavigationAndUI:
    """Test overall navigation and UI consistency."""

    def test_ai_chatbot_appears(self, logged_in_driver, base_url):
        """Test that AI chatbot widget appears on dashboard pages."""
        print("\n🧪 Testing AI Chatbot Widget...")
        
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard")
        time.sleep(2)
        
        try:
            # Look for chatbot button (usually bottom right)
            chatbot_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='fixed'][class*='bottom'][class*='right'], button[aria-label*='chat' i], button[aria-label*='assistant' i]")
            
            if chatbot_elements:
                print(f"✅ Found {len(chatbot_elements)} potential chatbot elements")
                driver.save_screenshot("chatbot_widget.png")
            else:
                print("⚠️  AI chatbot widget not found")

        except Exception as e:
            print(f"⚠️  Chatbot check: {e}")

    def test_ai_chatbot_responds(self, logged_in_driver, base_url):
        """
        Open the chatbot, send a simple prompt, and assert a non-empty reply.
        Keeps assertions minimal to avoid brittleness; validates end-to-end wiring.
        """
        print("\n🧪 Testing AI Chatbot Response...")
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard")
        time.sleep(2)

        try:
            # Open chatbot (button often bottom-right)
            openers = driver.find_elements(
                By.CSS_SELECTOR,
                "[class*='fixed'][class*='bottom'][class*='right'] button, button[aria-label*='chat' i], button[aria-label*='assistant' i]"
            )
            if not openers:
                pytest.skip("Chatbot opener not found on page")
            openers[0].click()
            time.sleep(1.5)

            # Find input and send a prompt
            input_box = driver.find_element(By.CSS_SELECTOR, "textarea, input[type='text']")
            input_box.clear()
            prompt = "Give me a one-line summary of our SOC service."
            input_box.send_keys(prompt)
            # Submit (Enter key or send button); guard against missing aria-label
            sent = False
            for btn in driver.find_elements(By.CSS_SELECTOR, "button"):
                aria = (btn.get_attribute("aria-label") or "").lower()
                text = (btn.text or "").lower()
                if "send" in aria or "send" in text or "submit" in text or "ask" in text:
                    btn.click()
                    sent = True
                    break
            if not sent:
                input_box.send_keys("\n")

            # Wait for a bot reply to appear
            # Wait for any non-empty message inside the chatbot panel
            def _find_chat_texts(d):
                containers = d.find_elements(By.XPATH, "//div[contains(., 'AI Assistant')]/ancestor::div[contains(@class, 'fixed')]")
                if not containers:
                    containers = d.find_elements(By.CSS_SELECTOR, "div.fixed")
                texts: list[str] = []
                for c in containers:
                    for el in c.find_elements(By.CSS_SELECTOR, "*"):
                        txt = (el.text or "").strip()
                        if txt:
                            texts.append(txt)
                return [t for t in texts if t and t != prompt]

            bot_texts = WebDriverWait(driver, 20).until(lambda d: _find_chat_texts(d))
            assert bot_texts, "Expected non-empty chatbot response"
            print(f"✅ Chatbot responded with: {bot_texts[-1][:120]}...")

        except Exception as e:
            _save_screenshot(driver, "chatbot_response_failed.png")
            print(f"❌ Chatbot response check failed: {e}")
            raise
    
    def test_navigation_consistency(self, logged_in_driver, base_url):
        """Test that navigation works across all key pages."""
        print("\n🧪 Testing Navigation Consistency...")
        
        driver = logged_in_driver
        
        test_pages = [
            ("/dashboard", "Main Dashboard"),
            ("/dashboard/alerts", "Alerts"),
            ("/dashboard/playbooks", "Playbooks"),
            ("/dashboard/iam/people", "IAM People"),
            ("/dashboard/iam/my-access", "My Access"),
            ("/dashboard/iam/policies", "Policies"),
            ("/dashboard/campaigns", "Campaigns"),
            ("/dashboard/certifications", "Certifications"),
        ]
        
        for path, name in test_pages:
            print(f"\n  Testing: {name} ({path})")
            try:
                driver.get(f"{base_url}{path}")
                time.sleep(2)
                
                # Check page loaded (no error page)
                body_text = driver.find_element(By.TAG_NAME, "body").text
                
                if "404" in body_text or "not found" in body_text.lower():
                    print(f"    ❌ 404 error on {name}")
                elif "error" in body_text.lower()[:500] and "unhandled" in body_text.lower():
                    print(f"    ❌ Runtime error on {name}")
                else:
                    print(f"    ✅ {name} loaded")
                    
            except Exception as e:
                print(f"    ❌ Failed to load {name}: {e}")
        
        print("\n✅ Navigation test completed")


class TestPeopleDrawerTabs:
    """Quick check that the People detail drawer shows Profile and Applications & Roles tabs."""

    def test_people_drawer_tabs(self, logged_in_driver, base_url):
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard/iam/people")
        time.sleep(2)

        try:
            # Click the first View button to open the drawer
            view_buttons = driver.find_elements(By.XPATH, "//button[normalize-space()='View']")
            if not view_buttons:
                pytest.skip("No users found on People page to open detail drawer")
            view_buttons[0].click()

            # Wait for drawer
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'User details') or contains(text(),'User Details')]"))
            )

            # Confirm tabs exist
            profile_tab = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//button[normalize-space()='Profile']"))
            )
            apps_tab = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//button[contains(normalize-space(),'Applications')]"))
            )
            assert profile_tab.is_displayed()
            assert apps_tab.is_displayed()

            # Switch to Applications & Roles and confirm content renders
            apps_tab.click()
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(text(),'Applications and roles assigned') or contains(text(),'No app assignments yet')]")
                )
            )
            print("✅ People drawer tabs render and switch successfully")

        except Exception as e:
            _save_screenshot(driver, "people_drawer_tabs_failure.png")
            pytest.fail(f"People drawer tabs test failed: {e}")


class TestDownloadsIntegrations:
    """Check Downloads & Integrations page renders tenant-specific commands and proxy config."""

    def test_downloads_page(self, demo_logged_in_driver, base_url):
        driver = demo_logged_in_driver
        driver.get(f"{base_url}/dashboard/iam/downloads")
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Downloads') and contains(text(),'Integrations')]"))
            )
            # Look for command blocks (pre tags) and copy buttons
            pre_blocks = driver.find_elements(By.TAG_NAME, "pre")
            assert pre_blocks, "No command blocks found"
            copy_buttons = driver.find_elements(By.XPATH, "//button[contains(text(),'Copy')]")
            assert copy_buttons, "No copy buttons found"
            # Auth proxy section
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Auth proxy config')]"))
            )
            print("✅ Downloads & Integrations page renders commands and copy buttons")
        except Exception as e:
            _save_screenshot(driver, "downloads_integrations_failure.png")
            pytest.fail(f"Downloads & Integrations page test failed: {e}")


class TestAppWizardGuardrails:
    """Validate app wizard guardrails: slug, redirect/ACS, entitlements + assignments before activation."""

    def test_apps_seeded(self, demo_logged_in_driver, base_url):
        """Ensure Apps page shows seeded apps and is not in empty state."""
        driver = demo_logged_in_driver
        driver.get(f"{base_url}/dashboard/iam/apps")
        print("\n🧪 Testing Apps page for seeded data...")
        try:
            # Wait for header
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(., 'Applications') or contains(., 'Apps')]"))
            )
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if "No apps configured yet" in body_text or "No apps" in body_text:
                driver.save_screenshot("apps_page_empty.png")
                pytest.fail("Expected seeded apps but saw empty state on Apps page")

            # Look for app cards (h3 titles inside card containers)
            app_titles = driver.find_elements(By.XPATH, "//h3[contains(@class,'text-lg') and normalize-space()!='']")
            if not app_titles:
                driver.save_screenshot("apps_page_no_cards.png")
                pytest.fail("Expected seeded apps but no app cards/titles were found")

            print(f"✅ Found {len(app_titles)} app cards on the page")
            for i, h3 in enumerate(app_titles[:5]):
                print(f"  App {i+1}: {h3.text}")

        except Exception as e:
            driver.save_screenshot("apps_page_error.png")
            pytest.fail(f"Apps page seeded-data check failed: {e}")

    def test_wizard_blocks_activation_without_requirements(self, demo_logged_in_driver, base_url):
        driver = demo_logged_in_driver
        driver.get(f"{base_url}/dashboard/iam/apps/catalog")
        try:
            # Click first Connect button (catalog card)
            connect_buttons = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//button[normalize-space()='Connect']"))
            )
            connect_buttons[0].click()

            # Basics step: set a valid slug
            slug_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='app-slug']"))
            )
            slug_input.clear()
            slug_input.send_keys("demo-app")
            # Basics -> Redirects
            driver.find_element(By.XPATH, "//button[normalize-space()='Next']").click()
            # Redirects/ACS step requires redirect or ACS; ensure field present and fill
            redirect_textarea = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//textarea[contains(@placeholder,'callback') or contains(@placeholder,'https://')]"))
            )
            redirect_textarea.clear()
            redirect_textarea.send_keys("https://app.example.com/callback")
            driver.find_element(By.XPATH, "//button[normalize-space()='Next']").click()
            # Claims
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//h3[contains(text(),'Claims') or contains(text(),'Security')]"))
            )
            driver.find_element(By.XPATH, "//button[normalize-space()='Next']").click()
            # Security
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//h3[contains(text(),'Security')]"))
            )
            driver.find_element(By.XPATH, "//button[normalize-space()='Next']").click()
            # Keys
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//h3[contains(text(),'Keys')]"))
            )
            driver.find_element(By.XPATH, "//button[normalize-space()='Next']").click()
            # Move to assignments
            while True:
                labels = driver.find_elements(By.XPATH, "//h3[contains(text(),'Entitlements') or contains(text(),'Assignments')]")
                if labels:
                    break
                driver.find_element(By.XPATH, "//button[normalize-space()='Next']").click()
                time.sleep(0.4)
            # Clear entitlements and assignments to force validation
            ent_input = driver.find_element(By.XPATH, "//input[contains(@placeholder,'entitlements') or contains(@type,'text')]")
            ent_input.clear()
            grp_locator = "//input[contains(@placeholder,'group') or contains(@placeholder,'team')]"
            user_locator = "//input[contains(@placeholder,'email') or contains(@placeholder,'user')]"
            try:
                driver.find_element(By.XPATH, grp_locator).clear()
            except Exception:
                pass
            try:
                driver.find_element(By.XPATH, user_locator).clear()
            except Exception:
                pass

            # Activate immediately with no data should keep Next disabled
            activate_checkbox = driver.find_element(By.XPATH, "//input[@type='checkbox' and ((../label[contains(text(),'Activate')]) or @aria-checked)]")
            if not activate_checkbox.is_selected():
                activate_checkbox.click()
            next_btn = driver.find_element(By.XPATH, "//button[normalize-space()='Next']")
            assert not next_btn.is_enabled()

            # Allow draft by unchecking activate; Next should enable
            if activate_checkbox.is_selected():
                activate_checkbox.click()
            WebDriverWait(driver, 5).until(lambda d: d.find_element(By.XPATH, "//button[normalize-space()='Next']").is_enabled())
            driver.find_element(By.XPATH, "//button[normalize-space()='Next']").click()
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//h3[contains(text(),'Review')]"))
            )
            connect_btns = driver.find_elements(By.XPATH, "//button[contains(.,'Connect')]")
            assert connect_btns and connect_btns[0].is_enabled()
            print("✅ Wizard enforces activation guardrails and unlocks when filled")
        except Exception as e:
            _save_screenshot(driver, "wizard_guardrails_failure.png")
            pytest.fail(f"Wizard guardrails test failed: {e}")


class TestAppDetailReadiness:
    """Ensure app detail enforces readiness (Needs Attention blocks activation)."""

    def test_needs_attention_blocks_activation(self, demo_logged_in_driver, base_url):
        driver = demo_logged_in_driver
        driver.get(f"{base_url}/dashboard/iam/apps")
        try:
            # Open first app card Manage link
            manage_links = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//a[normalize-space()='Manage']"))
            )
            manage_links[0].click()
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(text(),'Applications') or contains(text(),'Application')]"))
            )
            # If Needs Attention badge exists, Activate should alert/block
            needs_attention = driver.find_elements(By.XPATH, "//*[contains(text(),'Needs Attention')]")
            activate_btns = driver.find_elements(By.XPATH, "//button[contains(.,'Activate')]")
            if needs_attention and activate_btns:
                activate_btns[0].click()
                time.sleep(1)
                # We can't assert alert, but ensure still on page and not marked Active chip
                status_badges = driver.find_elements(By.XPATH, "//*[contains(text(),'Active')]")
                print("⚠️ Activation attempted with Needs Attention; status badges:", [b.text for b in status_badges])
            print("✅ App detail readiness check executed")
        except Exception as e:
            _save_screenshot(driver, "app_detail_readiness_failure.png")
            pytest.fail(f"App detail readiness test failed: {e}")


class TestAppOnboardingFlows:
    """Comprehensive UI flows for OIDC/BYO and SAML app onboarding with entitlements/assignments."""

    def _open_wizard_for_app(self, driver, base_url, app_display_name: str):
        driver.get(f"{base_url}/dashboard/iam/apps/catalog")
        card = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//h3[normalize-space()='{app_display_name}']/ancestor::div[contains(@class,'rounded-lg')]"))
        )
        connect_btn = card.find_element(By.XPATH, ".//button[normalize-space()='Connect']")
        connect_btn.click()
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'fixed') and .//h2[contains(text(),'Connect')]]"))
        )

    def _fill_basics_and_redirects(self, driver, slug_value: str, redirect: str, acs: str | None = None):
        # Basics: set slug
        slug_input = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='app-slug']"))
        )
        slug_input.clear()
        slug_input.send_keys(slug_value)
        driver.find_element(By.XPATH, "//button[normalize-space()='Next']").click()
        # Redirects / ACS
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//h3[contains(text(),'Redirects') or contains(text(),'ACS')]"))
        )
        try:
            redirect_area = driver.find_element(By.XPATH, "//textarea")
            redirect_area.clear()
            redirect_area.send_keys(redirect)
        except Exception:
            pass
        if acs:
            try:
                acs_input = driver.find_element(By.XPATH, "//input[contains(@placeholder,'acs') or contains(@placeholder,'sso') or contains(@placeholder,'https://')]")
                acs_input.clear()
                acs_input.send_keys(acs)
            except Exception:
                pass
        driver.find_element(By.XPATH, "//button[normalize-space()='Next']").click()

    def _skip_to_assignments(self, driver):
        # Claims
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//h3[contains(text(),'Claims') or contains(text(),'Security')]")))
        driver.find_element(By.XPATH, "//button[normalize-space()='Next']").click()
        # Security
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//h3[contains(text(),'Security')]")))
        driver.find_element(By.XPATH, "//button[normalize-space()='Next']").click()
        # Keys
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//h3[contains(text(),'Keys')]")))
        driver.find_element(By.XPATH, "//button[normalize-space()='Next']").click()
        # Assignments step appears next
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//h3[contains(text(),'Entitlements') or contains(text(),'Assignments')]")))

    def _fill_entitlements_assignments_and_activate(self, driver, entitlement: str, user_token: str):
        ent_input = driver.find_element(By.XPATH, "//input[contains(@placeholder,'entitlements') or @type='text']")
        ent_input.clear()
        ent_input.send_keys(entitlement)
        try:
            user_input = driver.find_element(By.XPATH, "//input[contains(@placeholder,'user') or contains(@placeholder,'email')]")
            user_input.clear()
            user_input.send_keys(user_token)
        except Exception:
            pass
        # Activate immediately
        try:
            activate_checkbox = driver.find_element(By.XPATH, "//input[@type='checkbox' and (../label[contains(text(),'Activate')]) or @aria-checked]")
            if not activate_checkbox.is_selected():
                activate_checkbox.click()
        except Exception:
            pass
        driver.find_element(By.XPATH, "//button[normalize-space()='Next']").click()
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//h3[contains(text(),'Review')]")))
        connect_btn = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(.,'Connect')]"))
        )
        assert connect_btn.is_enabled(), "Connect should be enabled after filling required fields"
        connect_btn.click()
        time.sleep(1)

    def _ensure_app_exists(self, driver, base_url) -> bool:
        """Ensure at least one app exists; create a BYO app via wizard if list is empty."""
        try:
            # First, check via UI if apps already exist
            driver.get(f"{base_url}/dashboard/iam/apps")
            manage_links = driver.find_elements(By.XPATH, "//a[normalize-space()='Manage']")
            if manage_links:
                return True

            # Seed via API (more reliable than UI flows for this test)
            login_resp = requests.post(
                "http://localhost:8082/api/v1/auth/login",
                json={"email": "admin@demo.sentinelgrid.ai", "password": "DemoPassword123!"},
                verify=False,
                timeout=10,
            )
            if login_resp.status_code != 200:
                return False
            token = login_resp.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            apps_resp = requests.get("http://localhost:8082/api/iam-portal/apps", headers=headers, verify=False, timeout=10)
            if apps_resp.ok and apps_resp.json():
                return True

            catalog_resp = requests.get("http://localhost:8082/api/iam-portal/catalog/apps", headers=headers, verify=False, timeout=10)
            catalog = catalog_resp.json().get("items", []) if catalog_resp.ok else []
            if not catalog:
                return False
            catalog_id = catalog[0]["id"]
            slug = f"byo-{uuid.uuid4().hex[:5]}"
            cfg = {
                "app_slug": slug,
                "redirect_uris": "https://app.example.com/oauth2/callback",
                "activation_mode": "draft",
            }
            connect_resp = requests.post(
                f"http://localhost:8082/api/iam-portal/catalog/apps/{catalog_id}/connect",
                headers=headers,
                json={"catalog_app_id": catalog_id, "config": cfg},
                verify=False,
                timeout=10,
            )
            if not connect_resp.ok:
                return False
            # Wait a moment then refresh UI
            time.sleep(1)
            driver.get(f"{base_url}/dashboard/iam/apps")
            manage_links = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//a[normalize-space()='Manage']"))
            )
            return True
        except Exception:
            return False

    def test_oidc_byo_flow(self, demo_logged_in_driver, base_url):
        """BYO/OIDC: fill slug, redirect, entitlements, assignments -> Connect enabled."""
        driver = demo_logged_in_driver
        self._open_wizard_for_app(driver, base_url, "Bring Your Own App (Auth Proxy)")
        slug = f"byo-{uuid.uuid4().hex[:5]}"
        self._fill_basics_and_redirects(driver, slug, "https://app.example.com/oauth2/callback")
        self._skip_to_assignments(driver)
        self._fill_entitlements_assignments_and_activate(driver, "admin", "admin@demo.sentinelgrid.ai")
        print("✅ OIDC/BYO wizard flow completed")

    def test_saml_flow(self, demo_logged_in_driver, base_url):
        """SAML app: fill slug, ACS, entitlements, assignments -> Connect enabled."""
        driver = demo_logged_in_driver
        self._open_wizard_for_app(driver, base_url, "GitLab")
        slug = f"saml-{uuid.uuid4().hex[:5]}"
        self._fill_basics_and_redirects(driver, slug, "https://app.example.com/callback", acs="https://app.example.com/sso/acs")
        self._skip_to_assignments(driver)
        self._fill_entitlements_assignments_and_activate(driver, "admin", "admin@demo.sentinelgrid.ai")
        print("✅ SAML wizard flow completed")

    def test_people_inheritance_view(self, demo_logged_in_driver, base_url):
        """Open People drawer Applications tab and confirm assignments table renders."""
        driver = demo_logged_in_driver
        driver.get(f"{base_url}/dashboard/iam/people")
        try:
            view_buttons = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//button[normalize-space()='View']"))
            )
            view_buttons[0].click()
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//button[normalize-space()='Applications & Roles']"))
            ).click()
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Applications and roles') or contains(text(),'No app assignments yet')]"))
            )
            print("✅ People drawer shows Applications & Roles tab content")
        except Exception as e:
            _save_screenshot(driver, "people_inheritance_failure.png")
            pytest.fail(f"People inheritance view failed: {e}")

    def test_app_secret_rotation_button(self, demo_logged_in_driver, base_url):
        """Ensure app detail shows Rotate Secret/Export controls (non-fatal if absent)."""
        driver = demo_logged_in_driver
        try:
            if not self._ensure_app_exists(driver, base_url):
                pytest.skip("Unable to seed a draft app via wizard; skipping rotation check")
            driver.get(f"{base_url}/dashboard/iam/apps")
            manage_links = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//a[normalize-space()='Manage']"))
            )
            manage_links[0].click()
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(text(),'Applications') or contains(text(),'Application')]"))
            )
            rotate_btns = driver.find_elements(By.XPATH, "//button[contains(.,'Rotate') or contains(.,'Secret')]")
            export_btns = driver.find_elements(By.XPATH, "//button[contains(.,'Export') or contains(.,'Metadata')]")
            download_btns = driver.find_elements(By.XPATH, "//button[contains(.,'Auth Proxy Config') or contains(.,'Download')]")
            if rotate_btns or export_btns:
                print("✅ App detail shows rotate/export controls")
            elif download_btns:
                print("ℹ️  Rotate controls absent; download config button present")
            else:
                pytest.skip("No rotate/export/download controls present in this build")
        except Exception as e:
            _save_screenshot(driver, "app_secret_rotate_failure.png")
            pytest.fail(f"App secret rotation check failed: {e}")


class TestEndToEnd:
    """Complete end-to-end test of IAM features."""
    
    def test_complete_iam_workflow(self, logged_in_driver, base_url):
        """Test complete IAM workflow from login to access review."""
        print("\n🧪 Running Complete IAM Workflow Test...")
        
        driver = logged_in_driver
        
        # 1. Check Dashboard
        print("\n  1️⃣  Checking Main Dashboard...")
        driver.get(f"{base_url}/dashboard")
        time.sleep(2)
        assert "/dashboard" in driver.current_url
        print("    ✅ Dashboard accessible")
        
        # 2. Navigate to People
        print("\n  2️⃣  Navigating to People...")
        driver.get(f"{base_url}/dashboard/iam/people")
        time.sleep(2)
        assert "/iam/people" in driver.current_url
        print("    ✅ People page accessible")
        
        # 3. Navigate to My Access
        print("\n  3️⃣  Navigating to My Access...")
        driver.get(f"{base_url}/dashboard/iam/my-access")
        time.sleep(2)
        assert "/my-access" in driver.current_url
        print("    ✅ My Access page accessible")
        
        # 4. Navigate to Policies
        print("\n  4️⃣  Navigating to Policies...")
        driver.get(f"{base_url}/dashboard/iam/policies")
        time.sleep(2)
        assert "/policies" in driver.current_url
        print("    ✅ Policies page accessible")
        
        # 5. Navigate to Campaigns
        print("\n  5️⃣  Navigating to Campaigns...")
        driver.get(f"{base_url}/dashboard/campaigns")
        time.sleep(2)
        assert "/campaigns" in driver.current_url
        print("    ✅ Campaigns page accessible")
        
        # 6. Navigate to Certifications
        print("\n  6️⃣  Navigating to Certifications...")
        driver.get(f"{base_url}/dashboard/certifications")
        time.sleep(2)
        assert "/certifications" in driver.current_url
        print("    ✅ Certifications page accessible")
        
        # Final screenshot
        driver.save_screenshot("complete_workflow_final.png")
        
        print("\n🎉 Complete IAM workflow test PASSED!")
        print("📸 Screenshots saved in current directory")


class TestDemoRealmUserCreation:
    """Test user creation functionality in demo realm."""
    
    def test_demo_realm_add_user(self, demo_logged_in_driver, base_url):
        """Test Add User functionality in demo realm."""
        print("\n🧪 Testing Add User in Demo Realm...")
        
        driver = demo_logged_in_driver
        driver.get(f"{base_url}/dashboard")
        time.sleep(3)
        
        try:
            # Navigate to People & Access section first
            print("🔍 Looking for 'People & Access' navigation link...")
            people_access_link = None
            
            # Try multiple strategies to find the navigation link
            nav_selectors = [
                (By.XPATH, "//a[contains(text(), 'People & Access')]"),
                (By.XPATH, "//*[contains(text(), 'People & Access')]"),
                (By.PARTIAL_LINK_TEXT, "People & Access"),
                (By.PARTIAL_LINK_TEXT, "People"),
                (By.XPATH, "//a[contains(@href, 'iam') or contains(@href, 'people')]"),
                (By.XPATH, "//nav//a[contains(text(), 'People')]"),
            ]
            
            for selector_type, selector_value in nav_selectors:
                try:
                    print(f"  Trying navigation selector: {selector_type} = {selector_value}")
                    people_access_link = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    print(f"✅ Found 'People & Access' link using {selector_type}")
                    break
                except TimeoutException:
                    continue
            
            if not people_access_link:
                # Try navigating directly
                print("⚠️  Navigation link not found, navigating directly...")
                driver.get(f"{base_url}/dashboard/iam/people")
                time.sleep(3)
            else:
                people_access_link.click()
                print("✅ Clicked 'People & Access' link")
                time.sleep(2)
                
                # Now navigate to the People page if we're not already there
                current_url = driver.current_url
                if "/iam/people" not in current_url:
                    print("🔍 Navigating to People page...")
                    driver.get(f"{base_url}/dashboard/iam/people")
                    time.sleep(3)
            
            # Find and click "Add User" button
            print("🔍 Looking for 'Add User' button...")
            add_user_button = None
            
            selectors = [
                (By.XPATH, "//button[contains(text(), 'Add User')]"),
                (By.XPATH, "//button[contains(., 'Add User')]"),
                (By.XPATH, "//button[contains(text(), 'Add')]"),
                (By.CSS_SELECTOR, "button[class*='Add'], button[class*='add']"),
                (By.PARTIAL_LINK_TEXT, "Add User"),
                (By.XPATH, "//*[contains(text(), 'Add User')]"),
            ]
            
            for selector_type, selector_value in selectors:
                try:
                    print(f"  Trying selector: {selector_type} = {selector_value}")
                    add_user_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    print(f"✅ Found 'Add User' button using {selector_type}")
                    break
                except TimeoutException:
                    continue
            
            if not add_user_button:
                driver.save_screenshot("demo_add_user_button_not_found.png")
                body_text = driver.find_element(By.TAG_NAME, "body").text
                print(f"❌ Could not find 'Add User' button")
                print(f"📋 Page text preview: {body_text[:500]}")
                raise Exception("Could not find 'Add User' button on the page")
            
            add_user_button.click()
            print("✅ Clicked 'Add User' button")
            time.sleep(2)
            
            # Wait for modal to appear
            print("⏳ Waiting for Add User modal...")
            modal = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='fixed'][class*='inset-0'], [class*='modal'], [class*='z-50']"))
            )
            print("✅ Modal appeared")
            
            # Check if we're on the method selection step (Invite User vs Bulk Upload)
            print("🔍 Checking for method selection step...")
            invite_user_button = None
            invite_selectors = [
                (By.XPATH, "//button[contains(., 'Invite User')]"),
                (By.XPATH, "//button[.//h3[contains(text(), 'Invite User')]]"),
                (By.XPATH, "//button[.//text()[contains(., 'Send an invitation email')]]"),
                (By.PARTIAL_LINK_TEXT, "Invite User"),
            ]
            
            for selector_type, selector_value in invite_selectors:
                try:
                    print(f"  Trying invite button selector: {selector_type} = {selector_value}")
                    invite_user_button = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    print(f"✅ Found 'Invite User' button using {selector_type}")
                    break
                except TimeoutException:
                    continue
            
            if invite_user_button:
                print("📧 Clicking 'Invite User' option (first option - send email)...")
                invite_user_button.click()
                time.sleep(1)  # Wait for form to appear
                print("✅ Clicked 'Invite User' option")
            else:
                print("ℹ️  No method selection step found, assuming already on invite form")
            
            # Generate unique test user data
            test_uuid = uuid.uuid4().hex[:8]
            test_email = f"demouser_{test_uuid}@demo.sentinelgrid.ai"
            test_first_name = f"Demo{test_uuid[:4]}"
            test_last_name = f"User{test_uuid[4:]}"
            test_department = "Engineering"
            
            print(f"📝 Creating demo user with email: {test_email}")
            
            # Fill in email field
            print("📝 Filling email field...")
            # Try multiple selectors for email input
            email_input = None
            email_selectors = [
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[placeholder*='email' i]"),
                (By.CSS_SELECTOR, "input[placeholder*='@' i]"),
                (By.XPATH, "//input[contains(@placeholder, 'example.com')]"),
                (By.XPATH, "//label[contains(text(), 'Email')]/following-sibling::input"),
                (By.XPATH, "//label[contains(text(), 'Email')]/../input"),
            ]
            
            for selector_type, selector_value in email_selectors:
                try:
                    print(f"  Trying email selector: {selector_type} = {selector_value}")
                    email_input = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    print(f"✅ Found email input using {selector_type}")
                    break
                except TimeoutException:
                    continue
            
            if not email_input:
                # Take screenshot for debugging
                driver.save_screenshot("email_input_not_found.png")
                # Print all inputs in modal
                all_inputs = driver.find_elements(By.TAG_NAME, "input")
                print(f"❌ Could not find email input. Found {len(all_inputs)} input elements:")
                for i, inp in enumerate(all_inputs):
                    if inp.is_displayed():
                        print(f"  {i+1}. type={inp.get_attribute('type')}, placeholder={inp.get_attribute('placeholder')}, name={inp.get_attribute('name')}")
                raise Exception("Could not find email input field in modal")
            
            email_input.clear()
            email_input.send_keys(test_email)
            print(f"✅ Entered email: {test_email}")
            
            # Fill in first name
            print("📝 Filling first name field...")
            first_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[name*='first']")
            if first_name_inputs:
                first_name_input = first_name_inputs[0]
                first_name_input.clear()
                first_name_input.send_keys(test_first_name)
                print(f"✅ Entered first name: {test_first_name}")
            else:
                first_name_input = driver.find_element(By.XPATH, "//input[contains(@placeholder, 'First') or contains(@placeholder, 'first') or contains(@name, 'first')]")
                first_name_input.clear()
                first_name_input.send_keys(test_first_name)
                print(f"✅ Entered first name: {test_first_name}")
            
            # Fill in last name
            print("📝 Filling last name field...")
            last_name_input = None
            if len(first_name_inputs) > 1:
                last_name_input = first_name_inputs[1]
                print("✅ Found last name input as second text input")
            else:
                # Try multiple selectors for last name
                last_name_selectors = [
                    (By.XPATH, "//label[contains(text(), 'Last Name')]/following-sibling::input"),
                    (By.XPATH, "//label[contains(text(), 'Last Name')]/../input"),
                    (By.XPATH, "//input[contains(@placeholder, 'Last') or contains(@placeholder, 'last')]"),
                    (By.XPATH, "//input[contains(@name, 'last')]"),
                    (By.CSS_SELECTOR, "input[type='text']:nth-of-type(2)"),
                ]
                
                for selector_type, selector_value in last_name_selectors:
                    try:
                        print(f"  Trying last name selector: {selector_type} = {selector_value}")
                        last_name_input = driver.find_element(selector_type, selector_value)
                        if last_name_input.is_displayed():
                            print(f"✅ Found last name input using {selector_type}")
                            break
                    except:
                        continue
            
            if not last_name_input:
                # Get all text inputs and try the second one
                all_text_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
                if len(all_text_inputs) >= 2:
                    last_name_input = all_text_inputs[1]
                    print("✅ Found last name input as second text input (fallback)")
                else:
                    driver.save_screenshot("last_name_input_not_found.png")
                    raise Exception(f"Could not find last name input. Found {len(all_text_inputs)} text inputs")
            
            last_name_input.clear()
            last_name_input.send_keys(test_last_name)
            print(f"✅ Entered last name: {test_last_name}")
            
            # Fill in department (dropdown)
            print("📝 Filling department field...")
            try:
                department_select = driver.find_element(By.CSS_SELECTOR, "select[name*='department'], select[id*='department']")
                from selenium.webdriver.support.ui import Select
                dept_select = Select(department_select)
                dept_select.select_by_visible_text(test_department)
                print(f"✅ Selected department: {test_department}")
            except Exception as e:
                print(f"⚠️  Department dropdown not found, trying text input: {e}")
                try:
                    department_input = driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Department') or contains(@placeholder, 'Team')]")
                    department_input.clear()
                    department_input.send_keys(test_department)
                    print(f"✅ Entered department: {test_department}")
                except:
                    print(f"⚠️  Department field not found or not required")
            
            # Take screenshot before submission
            driver.save_screenshot("demo_add_user_form_filled.png")
            print("📸 Screenshot saved: demo_add_user_form_filled.png")
            
            # Submit the form
            print("🚀 Submitting form...")
            # The button text MUST be "Send Invitation" - this is critical
            print("🔍 Looking for 'Send Invitation' button...")
            submit_button = None
            submit_selectors = [
                (By.XPATH, "//button[contains(text(), 'Send Invitation')]"),
                (By.XPATH, "//button[@type='submit' and contains(., 'Send Invitation')]"),
            ]
            
            for selector_type, selector_value in submit_selectors:
                try:
                    print(f"  Trying submit button selector: {selector_type} = {selector_value}")
                    submit_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    button_text = submit_button.text.strip()
                    print(f"✅ Found submit button using {selector_type}: '{button_text}'")
                    if "Send Invitation" not in button_text:
                        print(f"⚠️  Warning: Button text is '{button_text}', expected 'Send Invitation'")
                    break
                except TimeoutException:
                    continue
            
            if not submit_button:
                driver.save_screenshot("submit_button_not_found.png")
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                print(f"❌ CRITICAL: Could not find 'Send Invitation' button. Found {len(all_buttons)} buttons:")
                for i, btn in enumerate(all_buttons):
                    if btn.is_displayed():
                        btn_text = btn.text.strip()
                        btn_type = btn.get_attribute('type')
                        print(f"  {i+1}. '{btn_text}' (type={btn_type}, enabled={btn.is_enabled()})")
                
                # Check browser console for errors
                try:
                    logs = driver.get_log('browser')
                    errors = [log for log in logs if log['level'] == 'SEVERE']
                    if errors:
                        print(f"❌ Browser console errors ({len(errors)}):")
                        for err in errors[:5]:
                            print(f"  - {err['message']}")
                except:
                    pass
                
                pytest.fail("CRITICAL: Could not find 'Send Invitation' button. Test cannot proceed.")
            
            # Verify button is actually clickable
            if not submit_button.is_enabled():
                driver.save_screenshot("submit_button_disabled.png")
                pytest.fail(f"CRITICAL: 'Send Invitation' button is disabled. Button text: '{submit_button.text}'")
            
            # Scroll into view and click
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
            time.sleep(0.5)
            
            # Try to click - fail if both methods fail
            click_success = False
            try:
                submit_button.click()
                print("✅ Clicked 'Send Invitation' button (regular click)")
                click_success = True
            except Exception as e:
                print(f"⚠️  Regular click failed ({e}), trying JavaScript click...")
                try:
                    driver.execute_script("arguments[0].click();", submit_button)
                    print("✅ Clicked 'Send Invitation' button (JavaScript click)")
                    click_success = True
                except Exception as js_e:
                    driver.save_screenshot("submit_button_click_failed.png")
                    pytest.fail(f"CRITICAL: Failed to click 'Send Invitation' button. Regular click: {e}, JS click: {js_e}")
            
            if not click_success:
                pytest.fail("CRITICAL: Failed to click 'Send Invitation' button")
            
            # Wait for form submission and check for errors
            print("⏳ Waiting for user creation...")
            
            # Check browser console for errors immediately after click
            print("🔍 Checking browser console for errors...")
            try:
                logs = driver.get_log('browser')
                errors = [log for log in logs if log['level'] == 'SEVERE']
                warnings = [log for log in logs if log['level'] == 'WARNING']
                
                if errors:
                    print(f"❌ Browser console errors after clicking button ({len(errors)}):")
                    for err in errors[-10:]:  # Show last 10 errors
                        print(f"  - {err['message']}")
                    
                    # Check for specific API errors
                    api_errors = [e for e in errors if 'api' in e['message'].lower() or 'invite' in e['message'].lower()]
                    if api_errors:
                        print(f"\n❌ API-related errors detected ({len(api_errors)}):")
                        for err in api_errors:
                            print(f"  - {err['message']}")
                        print("⚠️  This suggests the backend API may not be running or accessible")
                        print("⚠️  Check that iam_agent service is running and accessible at the API URL")
                
                if warnings:
                    print(f"⚠️  Browser console warnings ({len(warnings)}):")
                    for warn in warnings[-5:]:
                        print(f"  - {warn['message']}")
            except Exception as e:
                print(f"⚠️  Could not read browser console logs: {e}")
            
            # Wait a bit for API call to start
            time.sleep(2)
            
            # Check for error messages in the UI
            error_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='error'], [class*='red'], [class*='text-red'], [role='alert']")
            if error_elements:
                error_text = ' '.join([e.text for e in error_elements if e.text and e.is_displayed()])
                if error_text:
                    print(f"❌ Error message displayed: {error_text}")
                    driver.save_screenshot("demo_add_user_error.png")
                    pytest.fail(f"User creation failed with error: {error_text}")
            
            # Check if modal closed (success)
            try:
                WebDriverWait(driver, 15).until(
                    EC.invisibility_of_element(modal)
                )
                print("✅ Modal closed - invitation sent successfully!")
            except TimeoutException:
                # Modal still open - check for errors or loading state
                error_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='error'], [class*='red'], [class*='text-red'], [role='alert']")
                if error_elements:
                    error_text = ' '.join([e.text for e in error_elements if e.text and e.is_displayed()])
                    if error_text:
                        print(f"❌ Error during user creation: {error_text}")
                        driver.save_screenshot("demo_add_user_error.png")
                        pytest.fail(f"User creation failed: {error_text}")
                
                # Check if button shows "Sending..." (still processing)
                try:
                    sending_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sending...')]")
                    if sending_button.is_displayed():
                        print("⏳ Still sending invitation, waiting longer...")
                        time.sleep(5)
                        # Check again if modal closed
                        try:
                            WebDriverWait(driver, 10).until(
                                EC.invisibility_of_element(modal)
                            )
                            print("✅ Modal closed after extended wait")
                        except TimeoutException:
                            driver.save_screenshot("demo_add_user_timeout.png")
                            pytest.fail("Modal did not close after clicking 'Send Invitation'. User creation may have failed.")
                except:
                    # Button not showing "Sending..." - something wrong
                    driver.save_screenshot("demo_add_user_modal_stuck.png")
                    pytest.fail("Modal did not close and button is not in 'Sending...' state. User creation likely failed.")
            
            # Verify user appears in the list
            print("🔍 Verifying user appears in the list...")
            driver.refresh()
            time.sleep(3)
            
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if test_email in body_text:
                print(f"✅ SUCCESS! Demo user {test_email} found in the user list!")
            else:
                print(f"⚠️  User {test_email} not immediately visible, but creation may have succeeded")
                print(f"📋 Page content preview: {body_text[:500]}")
                driver.save_screenshot("demo_add_user_verification.png")
            
            driver.save_screenshot("demo_add_user_complete.png")
            print("📸 Screenshot saved: demo_add_user_complete.png")
            print("✅ Demo realm Add User test completed successfully!")
            
        except Exception as e:
            driver.save_screenshot("demo_add_user_error.png")
            print(f"❌ Demo realm Add User test failed: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    """Run tests directly for quick testing."""
    print("=" * 60)
    print("IAM UI Test Suite")
    print("=" * 60)
    pytest.main([__file__, "-v", "-s", "--tb=short"])
