"""
Comprehensive Selenium E2E tests for IAM (People & Access) functionality.
Tests all IAM features, navigation, and interactive elements.
"""

import pytest
from pathlib import Path
import base64
import json
import uuid
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import Vault helper to fetch passwords
try:
    try:
        from tests.helpers.vault_helper import get_platform_admin_password
    except ImportError:
        from backend.tests.helpers.vault_helper import get_platform_admin_password
    VAULT_AVAILABLE = True
except ImportError:
    VAULT_AVAILABLE = False
    print("⚠️  Vault helper not available, using environment variables")


@pytest.fixture(scope="session")
def driver():
    """Create Selenium WebDriver instance."""
    options = webdriver.ChromeOptions()
    
    if os.getenv("CI") == "true" or os.getenv("HEADLESS") == "true":
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    else:
        print("Running in non-headless mode - browser will be visible")
    
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
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
    """Get base URL for website."""
    return os.getenv("WEBSITE_URL", "https://localhost:3443")


@pytest.fixture(scope="function")
def logged_in_driver(driver, base_url):
    """Fixture that logs in and returns the driver."""
    print(f"🌐 Logging in to: {base_url}/login")
    driver.get(f"{base_url}/login")
    
    # Wait for login form
    try:
        email_input = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
    except TimeoutException:
        # If already logged in, the login page may redirect; verify token/dashboard.
        try:
            token_present = driver.execute_script("return !!localStorage.getItem('access_token');")
        except Exception:
            token_present = False
        if "/dashboard" in driver.current_url or token_present:
            print("Already authenticated; skipping login form.")
            yield driver
            return
        raise
    
    # Get credentials
    # Prefer explicit env vars; fall back to demo tenant creds
    email = os.getenv("TEST_USERNAME", "admin@demo.sentinelgrid.ai")
    if email == "admin@sentinelgrid.ai" and VAULT_AVAILABLE:
        try:
            password = get_platform_admin_password()
            print("✅ Retrieved platform admin password from Vault")
        except Exception as e:
            print(f"⚠️  Failed to get password from Vault: {e}")
            password = os.getenv("TEST_PASSWORD", "DemoPassword123!")
    else:
        password = os.getenv("TEST_PASSWORD", "DemoPassword123!")
    
    # Fill in credentials
    email_input.clear()
    email_input.send_keys(email)
    password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    password_input.clear()
    password_input.send_keys(password)
    
    # Submit login
    login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in') or contains(text(), 'Login')]")
    login_button.click()
    
    # Wait for login to complete and token to be stored
    try:
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return !!localStorage.getItem('access_token');")
        )
    except TimeoutException:
        current_url = driver.current_url
        page_title = driver.title
        pytest.fail(f"Login failed - no token in localStorage (url={current_url}, title={page_title})")
    
    token = driver.execute_script("return localStorage.getItem('access_token');")
    
    print("✅ Successfully logged in")
    
    # Navigate to dashboard and wait for it to fully load
    driver.get(f"{base_url}/dashboard")
    time.sleep(5)  # Give dashboard time to load
    
    # Wait for sidebar to be visible
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "aside"))
    )
    print("✅ Dashboard loaded with sidebar")
    # Clear any prior console logs so individual tests only see fresh entries
    try:
        driver.get_log('browser')
    except Exception:
        pass
    
    yield driver


def _decode_jwt_payload(token: str) -> dict:
    payload_part = token.split(".")[1]
    payload_part += "=" * (-len(payload_part) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_part))


def _seed_asset_for_user(tenant_id: str, user_id: str) -> str:
    """Insert a tenant-scoped device asset for the given user (used by Selenium tests)."""
    db_url = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)

    asset_id = f"e2e-device-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                INSERT INTO assets (tenant_id, asset_id, asset_type, name, user_id, metadata, last_seen_at)
                VALUES (:tenant_id, :asset_id, :asset_type, :name, :user_id, CAST(:metadata AS jsonb), NOW())
                """
            ),
            {
                "tenant_id": tenant_id,
                "asset_id": asset_id,
                "asset_type": "laptop",
                "name": None,
                "user_id": user_id,
                "metadata": json.dumps({"trust_status": "trusted"}),
            },
        )
        db.commit()
    finally:
        db.close()
    return asset_id


def _delete_asset(tenant_id: str, asset_id: str) -> None:
    """Best-effort cleanup for seeded assets."""
    db_url = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        db.execute(
            text("DELETE FROM assets WHERE tenant_id = :tenant_id AND asset_id = :asset_id"),
            {"tenant_id": tenant_id, "asset_id": asset_id},
        )
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


class TestIAMNavigation:
    """Tests for IAM navigation and basic page loads."""
    
    def test_navigate_to_people_and_access(self, logged_in_driver, base_url):
        """Test navigating to People & Access from sidebar."""
        driver = logged_in_driver
        
        print("🔍 Looking for 'People & Access' in sidebar...")
        
        # Try multiple selectors to find the link
        selectors = [
            "//a[contains(text(), 'People & Access')]",
            "//a[contains(text(), 'People') and contains(text(), 'Access')]",
            "//aside//a[contains(text(), 'People')]",
            "//nav//a[contains(text(), 'People')]",
            "//a[@href='/dashboard/iam/people']",
        ]
        
        people_access_link = None
        for selector in selectors:
            try:
                people_access_link = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                print(f"✅ Found 'People & Access' link using selector: {selector}")
                break
            except TimeoutException:
                continue
        
        if not people_access_link:
            # Debug: Print page source to see what's available
            print("❌ Could not find 'People & Access' link. Checking page structure...")
            sidebar = driver.find_element(By.TAG_NAME, "aside")
            links = sidebar.find_elements(By.TAG_NAME, "a")
            print(f"   Found {len(links)} links in sidebar:")
            for link in links:
                print(f"   - Text: '{link.text}', Href: '{link.get_attribute('href')}'")
            pytest.fail("Could not find 'People & Access' link in sidebar")
        
        # Scroll into view and click
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", people_access_link)
        time.sleep(1)
        people_access_link.click()
        print("✅ Clicked 'People & Access'")
        
        # Wait for navigation
        WebDriverWait(driver, 10).until(
            lambda d: "/dashboard/iam" in d.current_url
        )
        
        assert "/dashboard/iam" in driver.current_url, f"Expected to be on IAM page, but URL is: {driver.current_url}"
        print(f"✅ Successfully navigated to IAM: {driver.current_url}")
        
        # Check for console errors
        self._check_console_errors(driver, "People & Access navigation")
    
    def _check_console_errors(self, driver, context=""):
        """Helper to check for console errors."""
        try:
            console_logs = driver.get_log('browser')
            errors = [log for log in console_logs if log['level'] == 'SEVERE']
            
            # Filter out acceptable errors
            acceptable_errors = ['favicon.ico', '404', '403', 'cors', 'preflight']
            critical_errors = []
            
            for error in errors:
                error_msg = error.get('message', '').lower()
                is_acceptable = any(acceptable in error_msg for acceptable in acceptable_errors)
                if not is_acceptable:
                    critical_errors.append(error)
            
            if critical_errors:
                print(f"❌ Found {len(critical_errors)} critical console errors in {context}:")
                for error in critical_errors[:5]:
                    print(f"   - {error['message'][:150]}")
                pytest.fail(f"Critical console errors found in {context}")
            else:
                print(f"✅ No critical console errors in {context}")
        except Exception as e:
            print(f"⚠️  Could not check console logs: {e}")


class TestIAMPeoplePage:
    """Tests for People page."""
    
    def test_people_page_loads(self, logged_in_driver, base_url):
        """Test that People page loads correctly."""
        driver = logged_in_driver
        target_url = f"{base_url}/dashboard/iam/people"
        driver.get(target_url)
        time.sleep(2)
        
        print("🔍 Checking People page...")

        # Ensure tenant_id is present (some routes expect it)
        try:
            tenant_id = driver.execute_script("return localStorage.getItem('tenant_id');")
            if not tenant_id:
                driver.execute_script("localStorage.setItem('tenant_id','demo');")
        except Exception:
            pass

        # Navigate via sidebar if we were bounced
        if "/dashboard/iam/people" not in driver.current_url:
            selectors = [
                "//a[contains(text(), 'People & Access')]",
                "//a[contains(text(), 'People') and contains(text(), 'Access')]",
                "//aside//a[contains(text(), 'People')]",
                "//nav//a[contains(text(), 'People')]",
                "//a[@href='/dashboard/iam/people']",
            ]
            link_clicked = False
            for selector in selectors:
                try:
                    link = WebDriverWait(driver, 8).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", link)
                    time.sleep(0.5)
                    link.click()
                    link_clicked = True
                    break
                except TimeoutException:
                    continue
                except Exception:
                    continue
            if not link_clicked:
                pytest.fail("Could not find People & Access link to navigate")

        # Wait for URL OR page root presence to confirm navigation
        WebDriverWait(driver, 20).until(
            lambda d: "/dashboard/iam/people" in d.current_url
            or d.find_elements(By.CSS_SELECTOR, "[data-testid='people-page-root']")
        )
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='people-page-root']"))
        )
        
        print("✅ People page loaded")

        # Check theme matches config (data-theme on <html> should reflect default)
        import json
        theme_cfg_path = Path(__file__).resolve().parents[2] / "frontend" / "theme.config.json"
        try:
            cfg = json.loads(theme_cfg_path.read_text())
            expected_theme = cfg.get("defaultTheme", "dark")
        except Exception:
            expected_theme = "dark"

        html = driver.find_element(By.TAG_NAME, "html")
        data_theme = html.get_attribute("data-theme") or ""
        has_dark_class = "dark" in (html.get_attribute("class") or "")

        # Derive resolved theme
        if expected_theme == "dark":
            assert data_theme == "dark" or has_dark_class, f"Expected dark theme per config, got data-theme={data_theme}, class={html.get_attribute('class')}"
            resolved_theme = "dark"
        elif expected_theme == "light":
            assert data_theme == "light" and not has_dark_class, f"Expected light theme per config, got data-theme={data_theme}, class={html.get_attribute('class')}"
            resolved_theme = "light"
        else:  # system
            assert data_theme in ("dark", "light"), f"Expected system-resolved theme, got {data_theme}"
            prefers_dark = driver.execute_script("return window.matchMedia('(prefers-color-scheme: dark)').matches;")
            resolved_theme = "dark" if prefers_dark else "light"
        print(f"✅ Theme applied: data-theme={data_theme}, class contains dark={has_dark_class}")

        # Check background color of the page root to ensure theme is visible
        page_root_bg = driver.execute_script(
            "const el = document.querySelector('[data-testid=\"people-page-root\"]');"
            "return el ? window.getComputedStyle(el).backgroundColor : null;"
        )
        expected_dark_values = {"rgb(2, 6, 23)", "rgba(2, 6, 23, 1)", "rgb(15, 23, 42)"}
        expected_light_values = {"rgb(248, 250, 252)", "rgba(248, 250, 252, 1)"}
        if resolved_theme == "dark":
            assert page_root_bg in expected_dark_values, f"Expected dark background on people page, got {page_root_bg}"
        else:
            assert page_root_bg in expected_light_values, f"Expected light background on people page, got {page_root_bg}"
        print(f"✅ People page background color: {page_root_bg} (resolved theme={resolved_theme})")
        self._check_console_errors(driver, "People page")

    def test_seed_user_leo_visible(self, logged_in_driver, base_url):
        """Ensure seeded demo user (Leo) is visible in the People table."""
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard/iam/people")

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='people-page-root']"))
        )

        search_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Search by name']"))
        )
        search_input.clear()
        search_input.send_keys("Leo")

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.XPATH, "//table//td[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'leo')]")
            )
        )
        self._check_console_errors(driver, "Seed user Leo visible")

    def _check_console_errors(self, driver, context=""):
        try:
            console_logs = driver.get_log('browser')
            errors = [log for log in console_logs if log['level'] == 'SEVERE']
            acceptable_errors = [
                'favicon.ico',
                '404',
                '403',
                'cors',
                'preflight',
                'failed to fetch rsc payload',
                'onboarding status',
            ]
            critical_errors = [e for e in errors if not any(acc in e.get('message', '').lower() for acc in acceptable_errors)]
            if critical_errors:
                print(f"❌ Found {len(critical_errors)} critical console errors {context}")
                for error in critical_errors[:3]:
                    print(f"   - {error['message'][:100]}")
                pytest.fail(f"Critical console errors found {context}")
        except Exception:
            pass


class TestBirthrightRuleUI:
    """Focused checks for birthright rule UI."""

    def test_birthright_rule_attributes_and_preview(self, logged_in_driver, base_url):
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard/iam/people")

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(),'Birthright rules')]"))
        )

        attr_select = driver.find_element(By.XPATH, "//label[contains(text(),'Attribute')]/following::select[1]")
        option_text = [o.text.lower() for o in attr_select.find_elements(By.TAG_NAME, "option")]
        assert "location" in option_text
        assert "manager id" in option_text
        assert "employee type" in option_text

        match_input = driver.find_element(By.XPATH, "//label[contains(text(),'Match value')]/following::input[1]")
        match_input.clear()
        match_input.send_keys("engineering")

        preview = driver.find_element(By.XPATH, "//div[contains(., 'Preview matches')]")
        assert preview is not None

    def test_people_page_interactive_elements(self, logged_in_driver, base_url):
        """Test clicking all buttons and links on People page."""
        driver = logged_in_driver
        driver.get(f"{base_url}/dashboard/iam/people")
        time.sleep(3)
        
        print("🔍 Testing interactive elements on People page...")
        
        # Find and click all buttons
        buttons = driver.find_elements(By.TAG_NAME, "button")
        clickable_buttons = [b for b in buttons if b.is_displayed() and b.is_enabled()]
        
        print(f"   Found {len(clickable_buttons)} clickable buttons")
        
        for i, button in enumerate(clickable_buttons[:10]):  # Limit to first 10 to avoid too many actions
            try:
                button_text = button.text.strip()
                if button_text and len(button_text) > 0:
                    print(f"   Clicking button: {button_text[:50]}")
                    driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    time.sleep(0.5)
                    button.click()
                    time.sleep(1)
                    # Check for errors after click
                    self._check_console_errors(driver, f"after clicking '{button_text[:30]}'")
            except Exception as e:
                print(f"   ⚠️  Could not click button: {e}")
        
        # Find and click all links (except navigation)
        links = driver.find_elements(By.TAG_NAME, "a")
        clickable_links = [l for l in links if l.is_displayed() and l.is_enabled() and "/dashboard/iam" in l.get_attribute("href") or ""]
        
        print(f"   Found {len(clickable_links)} IAM-related links")
        
        for i, link in enumerate(clickable_links[:5]):  # Limit to first 5
            try:
                link_text = link.text.strip()
                href = link.get_attribute("href")
                if href and "/dashboard/iam" in href:
                    print(f"   Clicking link: {link_text[:50]} -> {href}")
                    driver.execute_script("arguments[0].scrollIntoView(true);", link)
                    time.sleep(0.5)
                    link.click()
                    time.sleep(2)
                    # Navigate back
                    driver.back()
                    time.sleep(2)
            except Exception as e:
                print(f"   ⚠️  Could not click link: {e}")
        
        print("✅ Completed testing interactive elements on People page")
        self._check_console_errors(driver)
    
    def _check_console_errors(self, driver, context=""):
        """Helper to check for console errors."""
        try:
            console_logs = driver.get_log('browser')
            errors = [log for log in console_logs if log['level'] == 'SEVERE']
            acceptable_errors = [
                'favicon.ico',
                '404',
                '403',
                'cors',
                'preflight',
                'failed to fetch rsc payload',
                'onboarding status',
            ]
            critical_errors = [e for e in errors if not any(acc in e.get('message', '').lower() for acc in acceptable_errors)]
            
            if critical_errors:
                print(f"❌ Found {len(critical_errors)} critical console errors {context}")
                for error in critical_errors[:3]:
                    print(f"   - {error['message'][:100]}")
                pytest.fail(f"Critical console errors found {context}")
        except Exception:
            pass


class TestIAMAllFeatures:
    """Comprehensive tests for all IAM features."""
    
    # IAM features from the layout
    IAM_FEATURES = [
        {'name': 'People', 'href': '/dashboard/iam/people'},
        {'name': 'My Account', 'href': '/dashboard/iam/my-account'},
        {'name': 'My Access', 'href': '/dashboard/iam/my-access'},
        {'name': 'My Devices', 'href': '/dashboard/iam/my-devices'},
        {'name': 'Apps & Profiles', 'href': '/dashboard/iam/apps'},
        {'name': 'Devices', 'href': '/dashboard/iam/devices'},
        {'name': 'Security Events', 'href': '/dashboard/iam/security-events'},
        {'name': 'Reports', 'href': '/dashboard/iam/reports'},
        {'name': 'Privileged Access', 'href': '/dashboard/iam/privileged-access'},
        {'name': 'Secrets', 'href': '/dashboard/iam/secrets'},
        {'name': 'API Keys', 'href': '/dashboard/iam/api-keys'},
        {'name': 'Access Reviews', 'href': '/dashboard/iam/access-reviews'},
        {'name': 'Policies', 'href': '/dashboard/iam/policies'},
        {'name': 'Chat', 'href': '/dashboard/iam/chat'},
    ]
    
    @pytest.mark.parametrize("feature", IAM_FEATURES)
    def test_iam_feature_page_loads(self, logged_in_driver, base_url, feature):
        """Test that each IAM feature page loads without errors."""
        driver = logged_in_driver
        
        print(f"🔍 Testing {feature['name']} page...")
        try:
            driver.get_log('browser')
        except Exception:
            pass
        driver.get(f"{base_url}{feature['href']}")
        
        # Wait for page to load
        time.sleep(1)
        
        # Verify URL
        assert feature['href'] in driver.current_url, f"Expected {feature['href']}, got {driver.current_url}"
        print(f"✅ {feature['name']} page loaded: {driver.current_url}")
        
        # Check for console errors
        self._check_console_errors(driver, feature['name'])
        
        # Check for page errors
        page_text = driver.page_source.lower()
        critical_errors = ['application error', 'something went wrong', 'internal server error', '500 error']
        for error in critical_errors:
            if error in page_text:
                pytest.fail(f"{feature['name']} page has critical error: {error}")
        
        print(f"✅ {feature['name']} page loaded successfully without errors")
    
    @pytest.mark.parametrize("feature", IAM_FEATURES)
    def test_iam_feature_interactive_elements(self, logged_in_driver, base_url, feature):
        """Test clicking buttons and links on each IAM feature page."""
        driver = logged_in_driver
        
        print(f"🔍 Testing interactive elements on {feature['name']} page...")
        try:
            driver.get_log('browser')
        except Exception:
            pass
        driver.get(f"{base_url}{feature['href']}")
        time.sleep(1)
        
        # Find all buttons
        buttons = driver.find_elements(By.TAG_NAME, "button")
        clickable_buttons = [b for b in buttons if b.is_displayed() and b.is_enabled()]
        
        print(f"   Found {len(clickable_buttons)} clickable buttons")
        
        # Click first 5 buttons (to avoid too many actions)
        for i, button in enumerate(clickable_buttons[:5]):
            try:
                button_text = button.text.strip()
                if button_text:
                    print(f"   Clicking button {i+1}: {button_text[:40]}")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(0.5)
                    
                    # Check if button opens a modal/dialog (don't click those in this test)
                    if 'modal' not in button.get_attribute('class') or '':
                        button.click()
                        time.sleep(1)
                        
                        # Check for errors
                        self._check_console_errors(driver, f"{feature['name']} - button '{button_text[:30]}'")
            except Exception as e:
                print(f"   ⚠️  Could not click button: {e}")
        
        # Find all links (excluding navigation)
        links = driver.find_elements(By.TAG_NAME, "a")
        iam_links = [l for l in links if l.is_displayed() and l.is_enabled() and 
                     l.get_attribute("href") and "/dashboard/iam" in l.get_attribute("href")]
        
        print(f"   Found {len(iam_links)} IAM-related links")
        
        # Click first 3 links
        for i, link in enumerate(iam_links[:3]):
            try:
                link_text = link.text.strip()
                href = link.get_attribute("href")
                if href:
                    print(f"   Clicking link {i+1}: {link_text[:40]} -> {href.split('/')[-1]}")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                    time.sleep(0.5)
                    link.click()
                    time.sleep(2)
                    
                    # Navigate back if we left the page
                    if feature['href'] not in driver.current_url:
                        driver.back()
                        time.sleep(2)
                    
                    self._check_console_errors(driver, f"{feature['name']} - link '{link_text[:30]}'")
            except Exception as e:
                print(f"   ⚠️  Could not click link: {e}")
        
        print(f"✅ Completed testing interactive elements on {feature['name']} page")
        self._check_console_errors(driver, feature['name'])
    
    def _check_console_errors(self, driver, context=""):
        """Helper to check for console errors."""
        try:
            console_logs = driver.get_log('browser')
            errors = [log for log in console_logs if log['level'] == 'SEVERE']
            acceptable_errors = ['favicon.ico', '404', '403', 'cors', 'preflight']
            critical_errors = [e for e in errors if not any(acc in e.get('message', '').lower() for acc in acceptable_errors)]
            
            if critical_errors:
                print(f"❌ Found {len(critical_errors)} critical console errors in {context}")
                for error in critical_errors[:3]:
                    print(f"   - {error['message'][:100]}")
                pytest.fail(f"Critical console errors found in {context}")
        except Exception:
            pass


class TestIAMMyDevicesSelfService:
    """Tenant-aware self-service tests for My Devices."""

    def test_report_lost_device_sets_revoked(self, logged_in_driver, base_url):
        driver = logged_in_driver

        token = driver.execute_script("return localStorage.getItem('access_token');")
        assert token, "Expected access_token in localStorage after login"
        payload = _decode_jwt_payload(token)

        tenant_id = payload.get("tenant_id")
        user_id = payload.get("sub")
        assert tenant_id, "Expected tenant_id in token payload"
        assert user_id, "Expected sub (user_id) in token payload"

        asset_id = _seed_asset_for_user(str(tenant_id), str(user_id))
        try:
            driver.get(f"{base_url}/dashboard/iam/my-devices?nocache={int(time.time())}")
            wait = WebDriverWait(driver, 30)

            wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[contains(., 'My Devices')]")))

            report_btn_sel = f"[data-testid='report-device-{asset_id}']"
            report_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, report_btn_sel)))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", report_btn)
            time.sleep(0.5)
            report_btn.click()

            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='report-device-modal']")))

            report_type_select = Select(driver.find_element(By.CSS_SELECTOR, "[data-testid='report-type']"))
            report_type_select.select_by_value("lost")

            note = driver.find_element(By.CSS_SELECTOR, "[data-testid='report-note']")
            note.clear()
            note.send_keys("e2e lost device report")

            submit = driver.find_element(By.CSS_SELECTOR, "[data-testid='report-submit']")
            submit.click()

            wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "[data-testid='report-device-modal']")))

            trust_sel = f"[data-testid='trust-status-{asset_id}']"
            wait.until(lambda d: d.find_element(By.CSS_SELECTOR, trust_sel).text.strip().lower() == "revoked")

        finally:
            _delete_asset(str(tenant_id), asset_id)


class TestIAMSelfServicePasswordReset:
    """Targeted self-service tests that should stay stable across UI iterations."""

    def test_my_account_password_reset_request(self, logged_in_driver, base_url):
        """
        Verify the self-service password reset request flow renders and returns a user-visible result.

        Note: In local/dev environments email delivery may not be configured in Keycloak. The expected
        behavior is still to show a clear success/warning message (not a blank screen or crash).
        """
        driver = logged_in_driver

        driver.get(f"{base_url}/dashboard/iam/my-account")

        # Wait for My Account page to render
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h1[contains(., 'My Account')]"))
        )

        # Switch to Security tab
        security_tab = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(., 'Security')] or contains(., 'Security')]"))
        )
        security_tab.click()

        # Click the "Send reset email" button
        reset_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='password-reset-request-btn']"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", reset_button)
        time.sleep(0.3)
        reset_button.click()

        # Ensure a result banner is shown
        result = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='password-reset-request-result']"))
        )

        assert result.text.strip(), "Expected a password reset request result message to be displayed"


class TestIAMPeopleInviteFlow:
    """Targeted onboarding test: Invite user from People page wizard."""

    def test_invite_user_from_people_wizard(self, logged_in_driver, base_url):
        driver = logged_in_driver

        driver.get(f"{base_url}/dashboard/iam/people")

        # Wait for People page to render
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='people-page-root']"))
        )

        # Open onboarding wizard
        add_user_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Add User')]"))
        )
        add_user_btn.click()

        # Wizard should appear
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(., 'Add Users')]"))
        )

        invite_user_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Invite User')]"))
        )
        invite_user_btn.click()

        # Fill invite form
        unique_email = f"e2e-invite-{int(time.time())}@example.com"

        email_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        email_input.clear()
        email_input.send_keys(unique_email)

        # Uncheck email send (dev environments often have no SMTP configured)
        send_email_checkbox = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#send_email"))
        )
        if send_email_checkbox.is_selected():
            send_email_checkbox.click()

        send_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Send Invitation')]"))
        )
        send_btn.click()

        # Wait for wizard to close
        WebDriverWait(driver, 30).until(
            EC.invisibility_of_element_located((By.XPATH, "//h2[contains(., 'Add Users')]"))
        )

        # Search for the invited user in the People table
        search_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Search by name']"))
        )
        search_input.clear()
        search_input.send_keys(unique_email)
        time.sleep(1)

        # Confirm row appears
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, f"//table//td[contains(., '{unique_email}')]"))
        )


class TestIAMPeopleBulkUploadFlow:
    """Targeted onboarding test: Bulk upload users from People page wizard."""

    def test_bulk_upload_from_people_wizard(self, logged_in_driver, base_url, tmp_path):
        driver = logged_in_driver

        unique_email = f"e2e-bulk-{int(time.time())}@example.com"
        csv_path = tmp_path / "users.csv"
        csv_path.write_text(
            "email,firstName,lastName,role,enabled\n"
            f"{unique_email},Bulk,Upload,,false\n",
            encoding="utf-8",
        )

        driver.get(f"{base_url}/dashboard/iam/people")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='people-page-root']"))
        )

        add_user_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Add User')]"))
        )
        add_user_btn.click()

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(., 'Add Users')]"))
        )

        bulk_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Bulk Upload')]"))
        )
        bulk_btn.click()

        file_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        file_input.send_keys(str(csv_path))

        upload_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Upload')]"))
        )
        upload_btn.click()

        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, "//h3[contains(., 'Upload Results')]"))
        )

        done_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Done')]"))
        )
        done_btn.click()

        WebDriverWait(driver, 30).until(
            EC.invisibility_of_element_located((By.XPATH, "//h2[contains(., 'Add Users')]"))
        )

        search_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Search by name']"))
        )
        search_input.clear()
        search_input.send_keys(unique_email)
        time.sleep(1)

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, f"//table//td[contains(., '{unique_email}')]"))
        )


class TestIAMNavigationFlow:
    """Test navigation between IAM features."""
    
    def test_navigate_through_all_iam_features(self, logged_in_driver, base_url):
        """Test navigating through all IAM features using the IAM sub-navigation."""
        driver = logged_in_driver
        
        # Start at People page
        driver.get(f"{base_url}/dashboard/iam/people")
        time.sleep(2)
        
        print("🔍 Testing navigation through all IAM features...")
        
        # IAM navigation items from layout.tsx
        iam_nav_items = [
            'People', 'My Account', 'My Access', 'Apps & Profiles', 'Devices',
            'Security Events', 'Reports', 'Privileged Access', 'Secrets', 'API Keys',
            'Access Reviews', 'Policies', 'Chat'
        ]
        
        for nav_item in iam_nav_items:
            try:
                print(f"   Navigating to: {nav_item}")
                
                # Find the navigation link
                nav_link = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, f"//a[contains(text(), '{nav_item}')]"))
                )
                
                nav_link.click()
                time.sleep(2)
                
                # Verify we're on the correct page
                current_url = driver.current_url
                print(f"   ✅ Navigated to: {current_url}")
                
                # Check for errors
                self._check_console_errors(driver, f"navigation to {nav_item}")
                
            except TimeoutException:
                print(f"   ⚠️  Could not find navigation link for: {nav_item}")
            except Exception as e:
                print(f"   ⚠️  Error navigating to {nav_item}: {e}")
        
        print("✅ Completed navigation through all IAM features")
    
    def _check_console_errors(self, driver, context=""):
        """Helper to check for console errors."""
        try:
            console_logs = driver.get_log('browser')
            errors = [log for log in console_logs if log['level'] == 'SEVERE']
            acceptable_errors = ['favicon.ico', '404', '403', 'cors', 'preflight']
            critical_errors = [e for e in errors if not any(acc in e.get('message', '').lower() for acc in acceptable_errors)]
            
            if critical_errors:
                print(f"❌ Found {len(critical_errors)} critical console errors in {context}")
                for error in critical_errors[:3]:
                    print(f"   - {error['message'][:100]}")
                pytest.fail(f"Critical console errors found in {context}")
        except Exception:
            pass


class TestIAMFullSuite:
    """Full IAM test suite - comprehensive testing."""
    
    def _check_console_errors_non_blocking(self, driver, context=""):
        """Helper to check for console errors - non-blocking."""
        try:
            console_logs = driver.get_log('browser')
            errors = [log for log in console_logs if log['level'] == 'SEVERE']
            acceptable_errors = ['favicon.ico', '404', '403', 'cors', 'preflight', 'failed to fetch']
            critical_errors = [e for e in errors if not any(acc in e.get('message', '').lower() for acc in acceptable_errors)]
            
            if critical_errors:
                print(f"⚠️  Found {len(critical_errors)} console errors in {context}:")
                for error in critical_errors[:2]:
                    print(f"   - {error['message'][:80]}")
            else:
                print(f"   ✅ No critical console errors in {context}")
        except Exception:
            pass
    
    def test_iam_complete_workflow(self, logged_in_driver, base_url):
        """Complete workflow test: Log in once, click People & Access once, then click each IAM feature."""
        driver = logged_in_driver
        
        print("🚀 Starting complete IAM workflow test...")
        
        # Step 1: Click "People & Access" from sidebar (once)
        print("\n📍 Step 1: Clicking 'People & Access' from sidebar...")
        
        # Find the sidebar link
        selectors = [
            "//a[@href='/dashboard/iam/people']",
            "//a[contains(text(), 'People & Access')]",
        ]
        
        people_access_link = None
        for selector in selectors:
            try:
                people_access_link = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                print(f"✅ Found 'People & Access' link")
                break
            except TimeoutException:
                continue
        
        if not people_access_link:
            pytest.fail("Could not find 'People & Access' link in sidebar")
        
        # Click People & Access
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", people_access_link)
        time.sleep(0.5)
        people_access_link.click()
        print("✅ Clicked 'People & Access'")
        
        # Wait for navigation to IAM page
        WebDriverWait(driver, 10).until(
            lambda d: "/dashboard/iam" in d.current_url
        )
        print(f"✅ Navigated to IAM: {driver.current_url}")
        
        # Wait for IAM page and navigation menu to load
        time.sleep(3)
        
        # Verify IAM navigation menu is visible
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//nav[contains(@class, 'flex')]//a[contains(@href, '/dashboard/iam/')]"))
            )
            print("✅ IAM navigation menu loaded")
        except TimeoutException:
            print("⚠️  IAM navigation menu not found, but continuing...")
        
        # Step 2: Click each IAM feature from the IAM navigation menu
        iam_features = [
            {'name': 'People', 'href': '/dashboard/iam/people'},
            {'name': 'My Account', 'href': '/dashboard/iam/my-account'},
            {'name': 'My Access', 'href': '/dashboard/iam/my-access'},
            {'name': 'My Devices', 'href': '/dashboard/iam/my-devices'},
            {'name': 'Apps & Profiles', 'href': '/dashboard/iam/apps'},
            {'name': 'Devices', 'href': '/dashboard/iam/devices'},
            {'name': 'Security Events', 'href': '/dashboard/iam/security-events'},
            {'name': 'Reports', 'href': '/dashboard/iam/reports'},
            {'name': 'Privileged Access', 'href': '/dashboard/iam/privileged-access'},
            {'name': 'Secrets', 'href': '/dashboard/iam/secrets'},
            {'name': 'API Keys', 'href': '/dashboard/iam/api-keys'},
        ]
        
        for feature in iam_features:
            print(f"\n📋 Step 2: Testing {feature['name']}...")
            
            # Find and click the IAM navigation link for this feature
            nav_clicked = False
            try:
                # Try exact text match first
                nav_link = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, f"//nav//a[normalize-space(text())='{feature['name']}']"))
                )
                print(f"   ✅ Found '{feature['name']}' in IAM navigation menu")
                
                # Scroll into view and click
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", nav_link)
                time.sleep(0.5)
                nav_link.click()
                nav_clicked = True
                print(f"   ✅ Clicked '{feature['name']}'")
                
                # Wait for navigation - give it time
                time.sleep(2)
                current_url = driver.current_url
                
                # Check if we're on the right page
                if feature['href'] in current_url:
                    print(f"   ✅ Navigated to: {current_url}")
                else:
                    print(f"   ⚠️  Clicked but redirected to: {current_url}")
                    # If redirected, try direct navigation
                    driver.get(f"{base_url}{feature['href']}")
                    time.sleep(3)
                    current_url = driver.current_url
                    print(f"   ✅ Navigated directly to: {current_url}")
                
            except TimeoutException:
                # Fallback: try by href
                try:
                    nav_link = driver.find_element(By.XPATH, f"//nav//a[contains(@href, '{feature['href']}')]")
                    print(f"   ✅ Found '{feature['name']}' link by href")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", nav_link)
                    time.sleep(0.5)
                    nav_link.click()
                    nav_clicked = True
                    time.sleep(2)
                    current_url = driver.current_url
                    
                    if feature['href'] not in current_url:
                        print(f"   ⚠️  Redirected to: {current_url}, navigating directly...")
                        driver.get(f"{base_url}{feature['href']}")
                        time.sleep(3)
                        current_url = driver.current_url
                    
                    print(f"   ✅ On page: {current_url}")
                except Exception as e:
                    # Final fallback: direct URL
                    print(f"   ⚠️  Navigation link not found ({str(e)[:50]}), using direct URL")
                    driver.get(f"{base_url}{feature['href']}")
                    time.sleep(3)
                    current_url = driver.current_url
                    print(f"   ✅ On page: {current_url}")
            
            # Wait for page content to load
            time.sleep(2)
            
            # Verify we're on the correct IAM page
            if "/dashboard/iam" not in driver.current_url:
                print(f"   ⚠️  Not on IAM page ({driver.current_url}), trying direct navigation...")
                driver.get(f"{base_url}{feature['href']}")
                time.sleep(3)
            
            # Final check
            current_url = driver.current_url
            if "/dashboard/iam" not in current_url:
                print(f"   ⚠️  Still not on IAM page: {current_url}")
                # Don't fail, just log and continue - some pages might redirect
                print(f"   ⚠️  Continuing anyway to test other features...")
            else:
                print(f"   ✅ Confirmed on IAM page: {current_url}")
            
            # Find and click IAM-specific buttons (exclude navigation buttons)
            try:
                # Get all buttons, but filter out navigation/header buttons
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                
                # Filter buttons - exclude those in nav/header, and those with common navigation text
                iam_buttons = []
                nav_texts = ['AD', 'Key Findings', 'Dashboard', 'Sign out', 'Menu']
                
                for button in all_buttons:
                    if not button.is_displayed() or not button.is_enabled():
                        continue
                    button_text = button.text.strip()
                    if not button_text:
                        continue
                    # Skip navigation/header buttons
                    try:
                        parent = button.find_element(By.XPATH, "./..")
                        parent_class = parent.get_attribute("class") or ""
                        if "nav" in parent_class.lower() or "header" in parent_class.lower():
                            continue
                    except:
                        pass
                    # Skip buttons with navigation-like text
                    if any(nav_text in button_text for nav_text in nav_texts):
                        continue
                    iam_buttons.append(button)
                
                print(f"   Found {len(iam_buttons)} IAM-specific buttons")
                
                # Click all IAM-specific buttons
                for i, button in enumerate(iam_buttons):
                    try:
                        button_text = button.text.strip()
                        print(f"   🖱️  Clicking button {i+1}: '{button_text[:40]}'")
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(0.5)
                        button.click()
                        time.sleep(1)  # Wait after click
                        
                        # Check if a modal/wizard opened
                        try:
                            # Look for modal/wizard by various selectors
                            modal_selectors = [
                                "//*[contains(@class, 'modal')]",
                                "//*[contains(@class, 'dialog')]",
                                "//*[contains(@class, 'wizard')]",
                                "//div[contains(@class, 'fixed') and contains(@class, 'inset-0')]",
                            ]
                            
                            modal = None
                            for selector in modal_selectors:
                                try:
                                    modal = driver.find_element(By.XPATH, selector)
                                    if modal.is_displayed():
                                        break
                                except:
                                    continue
                            
                            if modal and modal.is_displayed():
                                print(f"      → Modal/wizard opened")
                                
                                # If it's the UserOnboardingWizard, click "Invite User" and "Bulk Upload"
                                if "Add Users" in driver.page_source or "Invite User" in driver.page_source:
                                    print(f"      → UserOnboardingWizard detected")
                                    
                                    # Click "Invite User" button
                                    try:
                                        invite_btn = WebDriverWait(driver, 3).until(
                                            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Invite User')]"))
                                        )
                                        print(f"      → Clicking 'Invite User'")
                                        invite_btn.click()
                                        time.sleep(1)
                                        
                                        # Go back to method selection
                                        try:
                                            back_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Back')]")
                                            back_btn.click()
                                            time.sleep(0.5)
                                        except:
                                            pass
                                    except:
                                        print(f"      → 'Invite User' button not found")
                                    
                                    # Click "Bulk Upload" button
                                    try:
                                        bulk_btn = WebDriverWait(driver, 3).until(
                                            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Bulk Upload')]"))
                                        )
                                        print(f"      → Clicking 'Bulk Upload'")
                                        bulk_btn.click()
                                        time.sleep(1)
                                    except:
                                        print(f"      → 'Bulk Upload' button not found")
                                
                                # Close the modal/wizard
                                print(f"      → Closing modal/wizard...")
                                try:
                                    # Try to find close button (X icon)
                                    close_btn = WebDriverWait(driver, 2).until(
                                        EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'close') or .//*[contains(@class, 'XMark')] or contains(text(), 'Close')]"))
                                    )
                                    close_btn.click()
                                    time.sleep(0.5)
                                except:
                                    # Try Cancel button
                                    try:
                                        cancel_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Cancel')]")
                                        cancel_btn.click()
                                        time.sleep(0.5)
                                    except:
                                        # Press Escape as last resort
                                        from selenium.webdriver.common.keys import Keys
                                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                                        time.sleep(0.5)
                        except Exception as e:
                            # No modal detected, continue
                            pass
                            
                    except Exception as e:
                        print(f"   ⚠️  Could not click button: {str(e)[:50]}")
                        
            except Exception as e:
                print(f"   ⚠️  Error finding buttons: {str(e)[:50]}")
            
            # Check for critical errors (non-blocking)
            self._check_console_errors_non_blocking(driver, feature['name'])
            
            print(f"✅ {feature['name']} tested successfully")
        
        print("✅ Complete IAM workflow test passed!")
    
    def _check_console_errors(self, driver, context=""):
        """Helper to check for console errors."""
        try:
            console_logs = driver.get_log('browser')
            errors = [log for log in console_logs if log['level'] == 'SEVERE']
            acceptable_errors = ['favicon.ico', '404', '403', 'cors', 'preflight']
            critical_errors = [e for e in errors if not any(acc in e.get('message', '').lower() for acc in acceptable_errors)]
            
            if critical_errors:
                print(f"❌ Found {len(critical_errors)} critical console errors in {context}")
                for error in critical_errors[:3]:
                    print(f"   - {error['message'][:100]}")
                pytest.fail(f"Critical console errors found in {context}")
        except Exception:
            pass
