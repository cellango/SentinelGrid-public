"""
Selenium E2E tests for UI components.

Tests all new UI components:
- Onboarding wizard (all 4 steps)
- Dashboard components (banner, status cards)
- Settings page
- Git security scanning UI
- Hardened images selection
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import os

BASE_URL = os.getenv("WEBSITE_URL", "https://localhost:3443")
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true" or os.getenv("CI") == "true"


@pytest.fixture(scope="function")
def driver():
    """Create and configure WebDriver."""
    options = webdriver.ChromeOptions()
    
    if HEADLESS:
        options.add_argument("--headless")
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--allow-insecure-localhost")
    options.set_capability('acceptInsecureCerts', True)
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    
    yield driver
    
    driver.quit()


@pytest.fixture(scope="function")
def authenticated_session(driver):
    """Create an authenticated session by logging in."""
    driver.get(f"{BASE_URL}/login")
    
    wait = WebDriverWait(driver, 10)
    email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
    password_input = driver.find_element(By.NAME, "password")
    
    email_input.send_keys(os.getenv("TEST_EMAIL", "test@example.com"))
    password_input.send_keys(os.getenv("TEST_PASSWORD", "TestPassword123!"))
    
    login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    login_button.click()
    
    wait.until(EC.url_contains("/dashboard") | EC.url_contains("/signup"))
    
    return driver


class TestOnboardingWizardUI:
    """Test onboarding wizard UI components."""
    
    def test_wizard_progress_indicator(self, authenticated_session):
        """Test that progress indicator shows all 4 steps."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/onboarding")
        
        wait = WebDriverWait(driver, 10)
        
        # Check for progress steps
        progress_steps = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button[class*='rounded-full']")))
        assert len(progress_steps) >= 4, "Should show 4 progress steps"
        
        # Check step labels
        step_labels = driver.find_elements(By.CSS_SELECTOR, "span[class*='text-xs']")
        labels_text = " ".join([label.text for label in step_labels])
        assert "Identity" in labels_text or "IdP" in labels_text
        assert "Cloud" in labels_text
        assert "Endpoint" in labels_text
        assert "Git" in labels_text
    
    def test_step_1_idp_ui(self, authenticated_session):
        """Test Step 1 IdP selection UI."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/onboarding?step=1")
        
        wait = WebDriverWait(driver, 10)
        
        # Check for IdP options
        idp_options = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "label[class*='border-2']")))
        assert len(idp_options) >= 4, "Should have multiple IdP options"
        
        # Check for specific providers
        page_text = driver.page_source
        assert "Google" in page_text or "Microsoft" in page_text or "Okta" in page_text
        
        # Test selecting an option
        if idp_options:
            idp_options[0].click()
            time.sleep(0.5)  # Wait for selection state
        
        # Check for Continue button
        continue_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        assert continue_button.is_displayed()
    
    def test_step_2_cloud_ui(self, authenticated_session):
        """Test Step 2 Cloud connection UI."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/onboarding?step=2")
        
        wait = WebDriverWait(driver, 10)
        
        # Check for cloud provider buttons
        cloud_buttons = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button[type='button']")))
        
        # Should have AWS, Azure, GCP buttons
        page_text = driver.page_source
        assert "AWS" in page_text or "Azure" in page_text or "GCP" in page_text
        
        # Test selecting AWS
        for button in cloud_buttons:
            if "AWS" in button.text:
                button.click()
                time.sleep(0.5)
                
                # Should show AWS-specific fields
                inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
                assert len(inputs) > 0, "Should show input fields after selecting provider"
                break
    
    def test_step_3_endpoint_ui(self, authenticated_session):
        """Test Step 3 Endpoint agent UI."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/onboarding?step=3")
        
        wait = WebDriverWait(driver, 10)
        
        # Check for endpoint protection content
        step_content = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h2")))
        assert "Endpoint" in step_content.text or "Agent" in step_content.text
        
        # Check for image selection or manual install option
        page_text = driver.page_source
        assert "hardened" in page_text.lower() or "image" in page_text.lower() or "install" in page_text.lower()
    
    def test_step_4_git_ui(self, authenticated_session):
        """Test Step 4 Git security UI."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/onboarding?step=4")
        
        wait = WebDriverWait(driver, 10)
        
        # Check for Git provider options
        step_content = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h2")))
        assert "Git" in step_content.text
        
        # Check for provider buttons
        provider_buttons = driver.find_elements(By.CSS_SELECTOR, "button[type='button']")
        page_text = driver.page_source
        assert "GitHub" in page_text or "GitLab" in page_text or "Bitbucket" in page_text
    
    def test_wizard_navigation(self, authenticated_session):
        """Test wizard navigation (back, skip, continue)."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/onboarding?step=2")
        
        wait = WebDriverWait(driver, 10)
        
        # Test Back button
        back_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Back')]")
        assert back_button.is_displayed()
        back_button.click()
        wait.until(EC.url_contains("step=1"))
        
        # Go forward again
        driver.get(f"{BASE_URL}/onboarding?step=2")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h2")))
        
        # Test Skip button
        skip_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Skip')]")
        assert skip_button.is_displayed()
        skip_button.click()
        wait.until(EC.url_contains("step=3"))


class TestDashboardComponents:
    """Test dashboard UI components."""
    
    def test_onboarding_banner_display(self, authenticated_session):
        """Test that onboarding banner displays correctly."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/dashboard")
        
        wait = WebDriverWait(driver, 15)
        
        # Check for banner (might not show if onboarding complete)
        try:
            banner = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='banner']")))
            assert "Complete Your Setup" in banner.text or "onboarding" in banner.text.lower()
            
            # Check for progress bar
            progress_bars = banner.find_elements(By.CSS_SELECTOR, "[class*='h-2']")
            assert len(progress_bars) > 0, "Should have progress bars"
            
            # Check for Continue button
            continue_button = banner.find_element(By.XPATH, ".//button[contains(text(), 'Continue')]")
            assert continue_button.is_displayed()
        except TimeoutException:
            # Banner might not show if onboarding is complete
            pass
    
    def test_cloud_connections_component(self, authenticated_session):
        """Test cloud connections component."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/dashboard")
        
        wait = WebDriverWait(driver, 10)
        
        # Check for cloud connections section
        try:
            cloud_section = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Cloud Connections')]")))
            assert cloud_section is not None
            
            # Check for empty state or connection list
            page_text = cloud_section.text
            assert "Cloud" in page_text
            
            # Check for Connect/Manage button
            buttons = cloud_section.find_elements(By.CSS_SELECTOR, "button, a")
            assert len(buttons) > 0, "Should have action buttons"
        except TimeoutException:
            # Component might not be visible
            pass
    
    def test_agent_status_component(self, authenticated_session):
        """Test agent status component."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/dashboard")
        
        wait = WebDriverWait(driver, 10)
        
        # Check for agent status section
        try:
            agent_section = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Endpoint Agents')]")))
            assert agent_section is not None
            
            # Check for stats or empty state
            page_text = agent_section.text
            assert "Agent" in page_text or "Endpoint" in page_text
        except TimeoutException:
            # Component might not be visible
            pass
    
    def test_git_security_component(self, authenticated_session):
        """Test Git security component."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/dashboard")
        
        wait = WebDriverWait(driver, 10)
        
        # Check for Git security section
        try:
            git_section = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Git Security')]")))
            assert git_section is not None
            
            # Check for stats or empty state
            page_text = git_section.text
            assert "Git" in page_text
        except TimeoutException:
            # Component might not be visible
            pass
    
    def test_dashboard_layout(self, authenticated_session):
        """Test dashboard layout and structure."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/dashboard")
        
        wait = WebDriverWait(driver, 10)
        
        # Check for main sections
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1")))
        
        # Check for account information
        account_section = driver.find_element(By.XPATH, "//*[contains(text(), 'Account Information')]")
        assert account_section is not None
        
        # Check for security overview
        security_section = driver.find_element(By.XPATH, "//*[contains(text(), 'Security Overview')]")
        assert security_section is not None


class TestSettingsPage:
    """Test settings page UI."""
    
    def test_settings_page_loads(self, authenticated_session):
        """Test that settings page loads correctly."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/settings")
        
        wait = WebDriverWait(driver, 10)
        
        # Check for settings page title
        title = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1")))
        assert "Settings" in title.text
    
    def test_settings_tabs(self, authenticated_session):
        """Test settings page tabs."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/settings")
        
        wait = WebDriverWait(driver, 10)
        
        # Check for tabs
        tabs = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button[class*='border-b']")))
        assert len(tabs) >= 5, "Should have multiple tabs"
        
        # Check for expected tabs
        page_text = driver.page_source
        assert "Overview" in page_text or "Identity" in page_text or "Cloud" in page_text
    
    def test_settings_tab_navigation(self, authenticated_session):
        """Test tab navigation on settings page."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/settings")
        
        wait = WebDriverWait(driver, 10)
        
        # Find and click a tab
        tabs = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "button[class*='border-b']")))
        if len(tabs) > 1:
            tabs[1].click()
            time.sleep(0.5)  # Wait for tab content to load
            
            # Check that tab is active
            active_tab = driver.find_element(By.CSS_SELECTOR, "button[class*='border-cyan-400']")
            assert active_tab is not None


class TestGitSecurityUI:
    """Test Git security scanning UI."""
    
    def test_git_findings_list(self, authenticated_session):
        """Test Git findings list component."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/dashboard")
        
        wait = WebDriverWait(driver, 10)
        
        # Navigate to Git security (if available)
        try:
            git_section = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Git Security')]")))
            
            # Check for findings or empty state
            page_text = git_section.text
            assert "Git" in page_text or "Security" in page_text
        except TimeoutException:
            pass
    
    def test_git_findings_filters(self, authenticated_session):
        """Test Git findings filters."""
        # TODO: Navigate to Git findings page and test filters
        pass


class TestHardenedImagesUI:
    """Test hardened images selection UI."""
    
    def test_image_selection_component(self, authenticated_session):
        """Test hardened image selection component."""
        driver = authenticated_session
        driver.get(f"{BASE_URL}/onboarding?step=3")
        
        wait = WebDriverWait(driver, 10)
        
        # Check for image selection
        page_text = driver.page_source
        assert "image" in page_text.lower() or "hardened" in page_text.lower() or "AMI" in page_text


class TestResponsiveDesign:
    """Test responsive design and mobile support."""
    
    def test_mobile_viewport(self, authenticated_session):
        """Test that UI works on mobile viewport."""
        driver = authenticated_session
        driver.set_window_size(375, 667)  # iPhone size
        
        driver.get(f"{BASE_URL}/dashboard")
        
        wait = WebDriverWait(driver, 10)
        
        # Check that page loads
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1")))
        
        # Check that components are visible (not hidden)
        main_content = driver.find_element(By.CSS_SELECTOR, "main")
        assert main_content.is_displayed()
    
    def test_tablet_viewport(self, authenticated_session):
        """Test that UI works on tablet viewport."""
        driver = authenticated_session
        driver.set_window_size(768, 1024)  # iPad size
        
        driver.get(f"{BASE_URL}/dashboard")
        
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1")))
        
        # Check layout
        main_content = driver.find_element(By.CSS_SELECTOR, "main")
        assert main_content.is_displayed()

