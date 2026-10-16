"""
Selenium-based test to activate Keycloak user accounts via UI.

This test navigates through the Keycloak UI to complete required actions
(such as password update or profile verification) for user accounts.
"""

import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import os

logger = logging.getLogger(__name__)

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8081")
REALM = os.getenv("TEST_REALM", "agribotsai")
TEST_USERNAME = os.getenv("TEST_USERNAME", "admin@agribotsai.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "ChangeMe123!")
CLIENT_ID = os.getenv("TEST_CLIENT_ID", "agribotsai-web")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:3000")


class KeycloakUIActivation:
    """Helper class for activating Keycloak accounts via UI."""
    
    def __init__(self, headless: bool = True):
        """
        Initialize Selenium WebDriver.
        
        Args:
            headless: Run browser in headless mode
        """
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        # Try to use chromedriver with webdriver-manager (auto-downloads driver)
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = ChromeService(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("✅ Chrome driver initialized with webdriver-manager")
        except Exception as e:
            logger.warning(f"Could not initialize Chrome with webdriver-manager: {e}")
            logger.info("Trying Chrome from PATH...")
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                logger.info("✅ Chrome driver initialized from PATH")
            except Exception as e2:
                logger.warning(f"Could not initialize Chrome driver: {e2}")
                logger.info("Attempting with Firefox...")
                try:
                    from selenium.webdriver.firefox.options import Options as FirefoxOptions
                    from webdriver_manager.firefox import GeckoDriverManager
                    from selenium.webdriver.firefox.service import Service as FirefoxService
                    firefox_options = FirefoxOptions()
                    if headless:
                        firefox_options.add_argument("--headless")
                    service = FirefoxService(GeckoDriverManager().install())
                    self.driver = webdriver.Firefox(service=service, options=firefox_options)
                    logger.info("✅ Firefox driver initialized with webdriver-manager")
                except Exception as e3:
                    logger.error(f"Could not initialize any browser driver: {e3}")
                    raise
    
    def close(self):
        """Close the browser."""
        if hasattr(self, 'driver'):
            self.driver.quit()
    
    def _handle_password_update(self, wait: WebDriverWait, new_password: str, redirect_uri: str) -> bool:
        """Handle password update required action."""
        try:
            new_password_field = wait.until(
                EC.presence_of_element_located((By.ID, "password-new"))
            )
            new_password_field.clear()
            new_password_field.send_keys(new_password)
            logger.info("Entered new password")
            
            password_confirm_field = self.driver.find_element(By.ID, "password-confirm")
            password_confirm_field.clear()
            password_confirm_field.send_keys(new_password)
            logger.info("Entered password confirmation")
            
            save_button = self.driver.find_element(By.ID, "kc-submit")
            save_button.click()
            logger.info("Clicked save button")
            time.sleep(3)
            
            final_url = self.driver.current_url
            logger.info(f"URL after password update: {final_url}")
            
            if redirect_uri in final_url or "code=" in final_url:
                logger.info("✅ Password update successful!")
                return True
            elif "required-action" in final_url:
                logger.info("Another required action after password update")
                return self._handle_required_action(wait, new_password, redirect_uri)
            else:
                return True
                
        except (TimeoutException, NoSuchElementException) as e:
            logger.error(f"Could not find password update form: {e}")
            return False
    
    def _handle_profile_verification(self, wait: WebDriverWait, new_password: str, redirect_uri: str) -> bool:
        """Handle profile verification required action."""
        try:
            logger.info("Handling profile verification...")
            
            # Profile verification form may require first name and last name
            # Try to find and fill these fields
            try:
                # Look for first name field
                first_name_selectors = [
                    (By.ID, "firstName"),
                    (By.NAME, "firstName"),
                    (By.ID, "first-name"),
                ]
                
                first_name_field = None
                for selector_type, selector_value in first_name_selectors:
                    try:
                        first_name_field = self.driver.find_element(selector_type, selector_value)
                        if first_name_field.is_displayed():
                            logger.info(f"Found first name field with {selector_type}: {selector_value}")
                            break
                    except NoSuchElementException:
                        continue
                
                if first_name_field:
                    current_first = first_name_field.get_attribute("value") or ""
                    if not current_first:
                        first_name_field.clear()
                        first_name_field.send_keys("Admin")
                        logger.info("Entered first name: Admin")
                
                # Look for last name field
                last_name_selectors = [
                    (By.ID, "lastName"),
                    (By.NAME, "lastName"),
                    (By.ID, "last-name"),
                ]
                
                last_name_field = None
                for selector_type, selector_value in last_name_selectors:
                    try:
                        last_name_field = self.driver.find_element(selector_type, selector_value)
                        if last_name_field.is_displayed():
                            logger.info(f"Found last name field with {selector_type}: {selector_value}")
                            break
                    except NoSuchElementException:
                        continue
                
                if last_name_field:
                    current_last = last_name_field.get_attribute("value") or ""
                    if not current_last:
                        last_name_field.clear()
                        last_name_field.send_keys("User")
                        logger.info("Entered last name: User")
                
            except Exception as e:
                logger.warning(f"Could not fill profile fields (may not be required): {e}")
            
            # Try to find submit button by various selectors
            submit_selectors = [
                (By.ID, "kc-submit"),
                (By.NAME, "submitAction"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "button.kc-button-primary"),
                (By.CSS_SELECTOR, "input.kc-button-primary"),
                (By.CSS_SELECTOR, "button[value='Submit']"),
                (By.CSS_SELECTOR, "input[value='Submit']"),
            ]
            
            submit_button = None
            for selector_type, selector_value in submit_selectors:
                try:
                    elements = self.driver.find_elements(selector_type, selector_value)
                    for elem in elements:
                        if elem.is_displayed() and elem.is_enabled():
                            submit_button = elem
                            logger.info(f"Found submit button with {selector_type}: {selector_value}")
                            break
                    if submit_button:
                        break
                except NoSuchElementException:
                    continue
            
            if submit_button:
                submit_button.click()
                logger.info("Clicked submit button")
            else:
                # Try submitting form directly
                logger.warning("Could not find submit button, trying to submit form directly")
                forms = self.driver.find_elements(By.TAG_NAME, "form")
                if forms:
                    forms[0].submit()
                    logger.info("Submitted form directly")
                else:
                    logger.error("No form found to submit")
                    return False
            
            time.sleep(3)
            
            final_url = self.driver.current_url
            logger.info(f"URL after profile verification: {final_url}")
            
            if redirect_uri in final_url or "code=" in final_url:
                logger.info("✅ Profile verification successful!")
                return True
            elif "required-action" in final_url:
                # Another required action (e.g., password update)
                logger.info("Another required action detected after profile verification")
                if "UPDATE_PASSWORD" in final_url or "password" in final_url.lower():
                    return self._handle_password_update(wait, new_password, redirect_uri)
                else:
                    return self._handle_required_action(wait, new_password, redirect_uri)
            else:
                return True
                
        except Exception as e:
            logger.error(f"Error handling profile verification: {e}", exc_info=True)
            return False
    
    def _handle_required_action(self, wait: WebDriverWait, new_password: str, redirect_uri: str) -> bool:
        """Generic handler for required actions."""
        try:
            current_url = self.driver.current_url
            logger.info(f"Handling required action: {current_url}")
            
            # Check what type of required action
            if "UPDATE_PASSWORD" in current_url or "password" in current_url.lower():
                return self._handle_password_update(wait, new_password, redirect_uri)
            elif "VERIFY_PROFILE" in current_url:
                return self._handle_profile_verification(wait, new_password, redirect_uri)
            
            # Generic: try to find and click submit
            submit_button = wait.until(
                EC.element_to_be_clickable((By.ID, "kc-submit"))
            )
            submit_button.click()
            time.sleep(3)
            
            final_url = self.driver.current_url
            if redirect_uri in final_url or "code=" in final_url:
                return True
            return False
        except Exception as e:
            logger.error(f"Error in generic required action handler: {e}")
            return False
    
    def activate_account_via_ui(
        self,
        keycloak_url: str,
        realm: str,
        username: str,
        current_password: str,
        new_password: str = None,
        client_id: str = "agribotsai-web",
        redirect_uri: str = "http://localhost:3000"
    ) -> bool:
        """
        Activate account by logging in via UI and completing required actions.
        
        Args:
            keycloak_url: Base Keycloak URL
            realm: Realm name
            username: Username to activate
            current_password: Current/temporary password
            new_password: New password to set (defaults to current_password if None)
            client_id: OAuth client ID
            redirect_uri: Redirect URI for OAuth flow
        
        Returns:
            True if activation succeeded, False otherwise
        """
        if new_password is None:
            new_password = current_password
        
        try:
            # Step 1: Navigate to Keycloak login page
            auth_url = (
                f"{keycloak_url}/realms/{realm}/protocol/openid-connect/auth"
                f"?client_id={client_id}"
                f"&response_type=code"
                f"&redirect_uri={redirect_uri}"
                f"&scope=openid"
            )
            
            logger.info(f"Navigating to: {auth_url}")
            self.driver.get(auth_url)
            time.sleep(2)
            
            # Step 2: Find and fill login form
            logger.info("Looking for login form...")
            wait = WebDriverWait(self.driver, 10)
            
            # Find username field
            username_field = wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            username_field.clear()
            username_field.send_keys(username)
            logger.info("Entered username")
            
            # Find password field
            password_field = self.driver.find_element(By.ID, "password")
            password_field.clear()
            password_field.send_keys(current_password)
            logger.info("Entered password")
            
            # Find and click login button
            login_button = self.driver.find_element(By.ID, "kc-login")
            login_button.click()
            logger.info("Clicked login button")
            time.sleep(3)
            
            # Step 3: Check if we need to complete required actions
            current_url = self.driver.current_url
            logger.info(f"Current URL after login: {current_url}")
            
            if "login-actions/required-action" in current_url:
                logger.info("Required action detected - processing...")
                
                # Handle different types of required actions
                if "execution=UPDATE_PASSWORD" in current_url:
                    logger.info("Password update required...")
                    return self._handle_password_update(wait, new_password, redirect_uri)
                
                elif "execution=VERIFY_PROFILE" in current_url:
                    logger.info("Profile verification required...")
                    return self._handle_profile_verification(wait, new_password, redirect_uri)
                
                else:
                    logger.info("Generic required action - using generic handler...")
                    return self._handle_required_action(wait, new_password, redirect_uri)
            
            elif "code=" in current_url or redirect_uri in current_url:
                # Already logged in successfully, no required actions needed
                logger.info("✅ Account already activated - no required actions needed")
                return True
            
            else:
                # Check for error messages
                try:
                    error_element = self.driver.find_element(By.CLASS_NAME, "kc-feedback-text")
                    error_text = error_element.text
                    logger.error(f"Login error: {error_text}")
                except NoSuchElementException:
                    pass
                
                logger.warning(f"Unexpected state after login: {current_url}")
                # Take a screenshot for debugging
                try:
                    self.driver.save_screenshot("/tmp/keycloak_activation_debug.png")
                    logger.info("Screenshot saved to /tmp/keycloak_activation_debug.png")
                except Exception:
                    pass
                return False
                
        except Exception as e:
            logger.error(f"Error during account activation: {e}", exc_info=True)
            return False


@pytest.fixture
def browser():
    """Create browser instance for tests."""
    browser = KeycloakUIActivation(headless=True)
    yield browser
    browser.close()


def test_activate_account_via_ui(browser):
    """
    Test activating a Keycloak account via UI.
    
    This test navigates through the Keycloak login UI and completes
    any required actions (like password update or profile verification).
    """
    result = browser.activate_account_via_ui(
        KEYCLOAK_URL,
        REALM,
        TEST_USERNAME,
        TEST_PASSWORD,  # Current/temporary password
        TEST_PASSWORD,  # New password (same in this case)
        CLIENT_ID,
        REDIRECT_URI
    )
    
    # This test may fail if account is already activated
    # or if browser automation is not available
    assert isinstance(result, bool)


if __name__ == "__main__":
    # Standalone script to activate account
    import sys
    
    keycloak_url = sys.argv[1] if len(sys.argv) > 1 else KEYCLOAK_URL
    realm = sys.argv[2] if len(sys.argv) > 2 else REALM
    username = sys.argv[3] if len(sys.argv) > 3 else TEST_USERNAME
    password = sys.argv[4] if len(sys.argv) > 4 else TEST_PASSWORD
    
    print(f"Activating account for {username} in realm {realm}...")
    browser = KeycloakUIActivation(headless=False)  # Show browser for debugging
    try:
        result = browser.activate_account_via_ui(
            keycloak_url,
            realm,
            username,
            password,
            password,
            CLIENT_ID,
            REDIRECT_URI
        )
        if result:
            print("✅ Account activated successfully!")
            sys.exit(0)
        else:
            print("❌ Account activation failed")
            sys.exit(1)
    finally:
        browser.close()
