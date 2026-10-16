"""
Integration tests for IDP gateway flows (OIDC/SAML).

These assume docker-compose.dev is running with Keycloak + IAM gateway
and that test IdPs/clients are seeded. We keep assertions minimal:
- OIDC happy path: state + code exchange -> redirect + cookies.
- State replay/missing state failures.
"""

import pytest
import httpx
import os

GATEWAY_BASE = os.getenv("GATEWAY_BASE", "https://localhost:3443")


@pytest.mark.asyncio
async def test_oidc_happy_path():
    # Get state/nonce
    async with httpx.AsyncClient(verify=False) as client:
        state_resp = await client.get(f"{GATEWAY_BASE}/auth/oidc/state", params={"tenant_id": "demo-tenant", "idp": "demo-idp"})
        state_resp.raise_for_status()
        data = state_resp.json()
        state = data["state"]
        # This test assumes a pre-seeded auth code is available (placeholder)
        # In a real test, drive the browser or stub the token endpoint.
        code = os.getenv("TEST_OIDC_CODE")
        if not code:
            pytest.skip("TEST_OIDC_CODE not set; skipping auth code exchange test")
        resp = await client.get(
            f"{GATEWAY_BASE}/auth/oidc/callback",
            params={"code": code, "state": state, "tenant_id": "demo-tenant", "idp": "demo-idp"},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 303)
        assert "access_token" in resp.cookies


@pytest.mark.asyncio
async def test_oidc_missing_state_rejected():
    async with httpx.AsyncClient(verify=False) as client:
        resp = await client.get(
            f"{GATEWAY_BASE}/auth/oidc/callback",
            params={"code": "dummy", "tenant_id": "demo-tenant", "idp": "demo-idp"},
            follow_redirects=False,
        )
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_oidc_replay_state_rejected():
    async with httpx.AsyncClient(verify=False) as client:
        state_resp = await client.get(f"{GATEWAY_BASE}/auth/oidc/state", params={"tenant_id": "demo-tenant", "idp": "demo-idp"})
        state_resp.raise_for_status()
        state = state_resp.json()["state"]
        for _ in range(2):
            resp = await client.get(
                f"{GATEWAY_BASE}/auth/oidc/callback",
                params={"code": "dummy", "state": state, "tenant_id": "demo-tenant", "idp": "demo-idp"},
                follow_redirects=False,
            )
        assert resp.status_code == 400
