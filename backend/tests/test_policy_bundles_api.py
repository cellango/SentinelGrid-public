import os
import pytest
import requests
from uuid import uuid4

BASE_URL = os.getenv("IAM_AGENT_URL", "http://localhost:8000")
TOKEN = os.getenv("TEST_TOKEN")  # supply a valid bearer token with tenant_id claim


@pytest.mark.skipif(not TOKEN, reason="TEST_TOKEN not set for IAM agent auth")
def test_list_seed_bundles():
    resp = requests.get(f"{BASE_URL}/api/iam-portal/policies/bundles", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.skipif(not TOKEN, reason="TEST_TOKEN not set for IAM agent auth")
def test_clone_seed_bundle_not_found():
    bogus_id = str(uuid4())
    resp = requests.post(f"{BASE_URL}/api/iam-portal/policies/bundles/{bogus_id}/clone", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status_code in (400, 404)


@pytest.mark.skipif(not TOKEN, reason="TEST_TOKEN not set for IAM agent auth")
def test_clone_seed_bundle_happy_path():
    # Try to clone the first available seed if present
    list_resp = requests.get(f"{BASE_URL}/api/iam-portal/policies/bundles", headers={"Authorization": f"Bearer {TOKEN}"})
    assert list_resp.status_code == 200
    bundles = list_resp.json()
    if not bundles:
        pytest.skip("No seed bundles available to clone")
    first = bundles[0]
    clone_resp = requests.post(
        f"{BASE_URL}/api/iam-portal/policies/bundles/{first['id']}/clone",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    assert clone_resp.status_code in (200, 201), clone_resp.text
    data = clone_resp.json()
    assert data.get("tenant_id") != first.get("tenant_id")
