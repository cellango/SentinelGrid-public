"""
Selenium smoke that verifies detection/playbook counts and playbook cloning in the demo realm.
Runs headless=false locally so you can observe the flow.
"""

import os
import time
import uuid
import requests
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


@pytest.fixture(scope="module")
def base_url():
    return os.getenv("FRONTEND_URL", "https://localhost:3443")


@pytest.fixture(scope="module")
def credentials():
    return {
        "username": os.getenv("TEST_USERNAME", "admin@demo.sentinelgrid.ai"),
        "password": os.getenv("TEST_PASSWORD", "DemoPassword123!"),
        "realm": os.getenv("TEST_REALM", "demo"),
    }


@pytest.fixture(scope="module")
def driver():
    opts = Options()
    # Run headed locally so you can see the browser; disable sandbox for CI containers
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--window-size=1400,900")

    drv = webdriver.Chrome(options=opts)
    drv.implicitly_wait(10)
    yield drv
    drv.quit()


def _get_auth_context(driver):
    """Pull access token/tenant/realm out of localStorage after login."""
    token = driver.execute_script("return localStorage.getItem('access_token');")
    tenant_id = driver.execute_script("return localStorage.getItem('tenant_id');")
    realm = driver.execute_script("return localStorage.getItem('realm');") or "demo"
    assert token, "Missing access_token in localStorage"
    assert tenant_id, "Missing tenant_id in localStorage"
    return token, tenant_id, realm


def _api_get(url, token, tenant_id, realm):
    resp = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": tenant_id,
            "X-Realm": realm,
        },
        verify=False,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _api_post(url, token, tenant_id, realm, payload):
    resp = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": tenant_id,
            "X-Realm": realm,
            "Content-Type": "application/json",
        },
        verify=False,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def test_detection_and_playbook_clone(driver, base_url, credentials):
    # Login
    driver.get(f"{base_url}/login")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
    driver.find_element(By.CSS_SELECTOR, "input[type='email']").send_keys(credentials["username"])
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(credentials["password"])
    driver.find_element(By.XPATH, "//button[contains(., 'Sign in')]").click()
    WebDriverWait(driver, 30).until(EC.url_contains("/dashboard"))

    token, tenant_id, realm = _get_auth_context(driver)

    # Detection count (expect catalog ~100+)
    detections = _api_get("http://localhost:8082/api/v1/siem/detection-rules", token, tenant_id, realm)
    assert isinstance(detections, list)
    assert len(detections) >= 100, f"Expected at least 100 detections, saw {len(detections)}"

    # Playbook count before clone (built-ins + any existing tenant copies)
    playbooks = _api_get("http://localhost:8082/api/v1/soar/playbooks", token, tenant_id, realm)
    assert isinstance(playbooks, list)
    baseline = len(playbooks)
    assert baseline >= 25, f"Expected at least 25 playbooks, saw {baseline}"

    # Clone first playbook into tenant
    first_pb = playbooks[0]
    clone_name = f"{first_pb['name']} Clone {uuid.uuid4().hex[:6]}"
    clone_key = f"{first_pb.get('key','pb')}-clone-{uuid.uuid4().hex[:6]}"
    cloned = _api_post(
        f"http://localhost:8082/api/v1/soar/playbooks/{first_pb['id']}/copy",
        token,
        tenant_id,
        realm,
        {"new_name": clone_name, "new_key": clone_key},
    )
    # Some auth flows return tenant from token instead of header; accept either and
    # continue using the effective tenant from the API response.
    assert cloned["key"] == clone_key
    effective_tenant = cloned.get("tenant_id") or tenant_id

    # Confirm count increased
    playbooks_after = _api_get("http://localhost:8082/api/v1/soar/playbooks", token, effective_tenant, realm)
    assert len(playbooks_after) == baseline + 1

    # UI checks: detection and playbook pages render and expose category chips + search
    driver.get(f"{base_url}/siem/detection-rules")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//h1[contains(., 'Detection Rules')]")))
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//button[contains(., 'All categories')]")))
    assert driver.find_elements(By.XPATH, "//input[@placeholder='Search detection rules...']")

    driver.get(f"{base_url}/dashboard/playbooks")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//h1[contains(., 'Playbooks')]")))
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//button[contains(., 'All categories')]")))
    assert driver.find_elements(By.XPATH, "//input[@placeholder='Search playbooks...']")
    # ensure we have at least one category chip beyond "All categories"
    chips = driver.find_elements(By.XPATH, "//button[contains(@class,'rounded-full') and contains(., 'All categories')]/following::button")
    assert chips, "Expected at least one category chip beyond 'All categories'"
