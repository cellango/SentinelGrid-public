"""Chat API smoke for dashboard endpoint."""

import os
import httpx
import pytest
from pathlib import Path

GATEWAY_URL = os.getenv("API_GATEWAY_URL", "https://localhost:8082")
TENANT_ID = os.getenv("TEST_TENANT_ID", "1b2eaa87-3407-4761-8edd-9485e945486b")
REALM = os.getenv("TEST_REALM", "demo")


def _get_token():
    env_token = os.getenv("TEST_ACCESS_TOKEN")
    if env_token:
        return env_token
    token_file = Path("backend/tests/.secrets/chat_api_token")
    if token_file.exists():
        return token_file.read_text().strip()
    pytest.skip("No access token provided for chat API smoke (set TEST_ACCESS_TOKEN or backend/tests/.secrets/chat_api_token)")


def _headers():
    token = _get_token()
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": TENANT_ID,
        "X-Realm": REALM,
    }


def test_dashboard_chat_api_smoke():
    payload = {"query": "Hello"}
    with httpx.Client(verify=False, timeout=15.0) as client:
        resp = client.post(f"{GATEWAY_URL}/api/v1/chat/dashboard", json=payload, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
        assert "reply" in data


def test_dashboard_chat_vector_reply():
    # Regression: asking AC-2 should return a non-empty reply when baseline KB is seeded
    payload = {"query": "What is AC-2 Account Management?"}
    with httpx.Client(verify=False, timeout=20.0) as client:
        resp = client.post(f"{GATEWAY_URL}/api/v1/chat/dashboard", json=payload, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
        reply = data.get("reply", "")
        assert isinstance(reply, str)
        assert reply.strip(), "Expected non-empty reply for AC-2 query"
