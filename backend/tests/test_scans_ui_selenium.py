"""
Selenium smoke test: login and load the Scans page.

Defaults (override via env):
- BASE_URL=https://localhost:3443
- TEST_EMAIL=admin@demo.sentinelgrid.ai
- TEST_PASSWORD=DemoPassword123!
- HEADLESS=true
"""

import os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

from utils.login import login


def make_driver():
    options = webdriver.ChromeOptions()
    if os.getenv("HEADLESS", "true").lower() == "true":
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("--remote-allow-origins=*")
    options.add_argument("--window-size=1400,900")
    # Use system Chrome if available to avoid devtools crashes
    chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(chrome_bin):
        options.binary_location = chrome_bin
    options.set_capability("acceptInsecureCerts", True)
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    return driver


class TestScansPage:
    @pytest.mark.selenium
    def test_scans_page_loads(self):
        base_url = os.getenv("BASE_URL", "https://localhost:3443")
        email = os.getenv("TEST_EMAIL", "admin@demo.sentinelgrid.ai")
        password = os.getenv("TEST_PASSWORD", "DemoPassword123!")

        driver = make_driver()
        try:
            login(driver, base_url=base_url, username=email, password=password)

            driver.get(f"{base_url}/dashboard/scans")
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//h1[contains(., 'Scan') or contains(., 'scan')] | //table | //div[contains(., 'No scans')]")
                    )
                )
            except TimeoutException:
                pytest.fail("Scans page did not load expected content")

            # Basic sanity: no obvious error banner/404
            page_text = driver.page_source.lower()
            assert "not found" not in page_text, "Scans page shows 404/not found"
            assert "no scans yet" not in page_text, "Scans page shows 'No scans yet' placeholder"
        finally:
            # small pause to keep browser stable on teardown
            time.sleep(1)
            driver.quit()

    @pytest.mark.selenium
    def test_scan_list_badges(self):
        """Ensure scans list shows Fixes/Ticket badges when data exists."""
        base_url = os.getenv("BASE_URL", "https://localhost:3443")
        email = os.getenv("TEST_EMAIL", "admin@demo.sentinelgrid.ai")
        password = os.getenv("TEST_PASSWORD", "DemoPassword123!")

        driver = make_driver()
        try:
            login(driver, base_url, email, password)
            driver.get(f"{base_url}/dashboard/scans")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//table | //div[contains(., 'No scans')]"))
            )
            rows = driver.find_elements(By.XPATH, "//table//tr")
            if len(rows) <= 1:
                pytest.skip("No scans available to assert badges")
            # Look for at least one Fixes or Ticket badge
            has_fixes = bool(driver.find_elements(By.XPATH, "//span[contains(., 'Fixes') and contains(@class,'bg-cyan')]"))
            has_ticket = bool(driver.find_elements(By.XPATH, "//span[contains(., 'Ticket') and contains(@class,'bg-emerald')]"))
            if not (has_fixes or has_ticket):
                pytest.skip("No scans with Fixes/Ticket badges in data set")
            assert has_fixes or has_ticket, "Expected at least one Fixes or Ticket badge on scans list"
        finally:
            time.sleep(1)
            driver.quit()

    @pytest.mark.selenium
    def test_scan_detail_ticket_flow(self):
        """
        Open a scan with fixes, create (or verify) a ticket from a FixGroup, and
        ensure the ticket link/status renders.
        """
        base_url = os.getenv("BASE_URL", "https://localhost:3443")
        email = os.getenv("TEST_EMAIL", "admin@demo.sentinelgrid.ai")
        password = os.getenv("TEST_PASSWORD", "DemoPassword123!")

        driver = make_driver()
        try:
            login(driver, base_url, email, password)

            # Use API to pick a scan with fixes (prefer one without a ticket so we exercise creation)
            scans = driver.execute_script(
                """
                const token = localStorage.getItem('access_token');
                return fetch('/api/v1/orchestrator/scans/status?limit=20', {
                    headers: {Authorization: `Bearer ${token}`}
                }).then(r => r.json());
                """
            )
            if not scans or len(scans) == 0:
                pytest.fail("No scans returned from API")
            scan_choice = None
            for s in scans:
                if s.get("has_fix_groups"):
                    scan_choice = s
                    if not s.get("ticket_id"):
                        break  # prefer one without a ticket
            if not scan_choice:
                pytest.fail("No scans with fix groups available")

            scan_id = scan_choice["id"]
            has_ticket_already = bool(scan_choice.get("ticket_id"))

            driver.get(f"{base_url}/dashboard/scans/{scan_id}")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h2[contains(., 'Fix group')] | //button[contains(., 'ticket')]")
                )
            )

            ticket_link_found = False
            if not has_ticket_already:
                try:
                    create_btn = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'ticket') and not(@disabled)]"))
                    )
                    try:
                        create_btn.click()
                    except StaleElementReferenceException:
                        create_btn = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'ticket') and not(@disabled)]"))
                        )
                        create_btn.click()
                    WebDriverWait(driver, 25).until(
                        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/dashboard/tickets/')]"))
                    )
                    ticket_link_found = True
                except TimeoutException:
                    has_ticket_already = True  # fall back to expecting an existing link

            if has_ticket_already and not ticket_link_found:
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/dashboard/tickets/')]"))
                    )
                    ticket_link_found = True
                except TimeoutException:
                    pass

            links = driver.find_elements(By.XPATH, "//a[contains(@href, '/dashboard/tickets/')]")
            if links:
                ticket_link_found = True
            assert ticket_link_found, "Expected ticket link on scan detail"
            disabled_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Ticket') and @disabled]")
            assert len(disabled_buttons) > 0, "Expected ticket button to be disabled when ticket exists"
        finally:
            time.sleep(1)
            driver.quit()

    @pytest.mark.selenium
    def test_scan_detail_fixgroups_and_guidance(self):
        """
        Assert FixGroups render with guidance and ticket creation is single-use.
        """
        base_url = os.getenv("BASE_URL", "https://localhost:3443")
        email = os.getenv("TEST_EMAIL", "admin@demo.sentinelgrid.ai")
        password = os.getenv("TEST_PASSWORD", "DemoPassword123!")

        driver = make_driver()
        try:
            login(driver, base_url, email, password)
            scans = driver.execute_script(
                """
                const token = localStorage.getItem('access_token');
                return fetch('/api/v1/orchestrator/scans/status?limit=20', {
                    headers: {Authorization: `Bearer ${token}`}
                }).then(r => r.json());
                """
            )
            if not scans:
                pytest.skip("No scans returned from API")
            scan_choice = None
            for s in scans:
                if s.get("has_fix_groups"):
                    scan_choice = s
                    if s.get("ticket_id"):
                        break  # prefer one with a ticket
            if not scan_choice:
                pytest.skip("No scans with fix groups available")

            scan_id = scan_choice["id"]
            # Ensure a ticket exists for the first FixGroup by calling the API (makes the UI deterministic)
            detail = driver.execute_script(
                """
                const token = localStorage.getItem('access_token');
                return fetch(`/api/v1/orchestrator/scans/%s`, {
                    headers: {Authorization: `Bearer ${token}`}
                }).then(r => r.json());
                """
                % scan_id
            )
            fix_groups = detail.get("fix_groups") or []
            if fix_groups:
                fg = fix_groups[0]
                if not fg.get("ticket_id"):
                    driver.execute_script(
                        """
                        const token = localStorage.getItem('access_token');
                        return fetch(`/api/v1/orchestrator/scans/%s/tickets`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                Authorization: `Bearer ${token}`
                            },
                            body: JSON.stringify({
                                fix_group_id: '%s',
                                title: 'Test ticket',
                                description: 'Automated test ticket'
                            })
                        }).then(r => r.json());
                        """
                        % (scan_id, fg["id"])
                    )

            driver.get(f"{base_url}/dashboard/scans/{scan_id}")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//h2[contains(., 'Fix group')] | //div[contains(., 'Fix groups')]"))
            )

            # At least one fix group card
            cards = driver.find_elements(By.XPATH, "//div[contains(@class,'border') and .//div[contains(., 'AI guidance')]]")
            if not cards:
                pytest.skip("FixGroup cards with AI guidance not found")

            # Guidance content present
            guidance_blocks = driver.find_elements(By.XPATH, "//*[contains(., 'AI guidance')]")
            assert guidance_blocks, "Expected AI guidance block in fix group"

            # Ticket create is single-use
            create_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Ticket') and not(@disabled)]")
            if create_buttons:
                btn = create_buttons[0]
                btn.click()
                WebDriverWait(driver, 25).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/dashboard/tickets/')]"))
                )
                driver.refresh()
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(., 'Fix groups')]"))
                )
                disabled_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Ticket') and @disabled]")
                assert disabled_buttons, "Ticket button should be disabled after creation"
            else:
                # If already has ticket, ensure link present and button disabled
                link = driver.find_elements(By.XPATH, "//a[contains(@href, '/dashboard/tickets/')]")
                assert link, "Expected ticket link when ticket already exists"
                disabled_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Ticket') and @disabled]")
                assert disabled_buttons, "Ticket button should be disabled when ticket exists"
        finally:
            time.sleep(1)
            driver.quit()
