"""
API-level checks for onboarding status and health rechecks.
Targets the running stack (BASE_URL env). These tests are tolerant of auth/state;
when responses are 200, they validate shape/content.
"""

import os
import pytest
pytest.skip(
    "Legacy root onboarding API suite quarantined; replaced by owner-local gateway and IAM onboarding tests.",
    allow_module_level=True,
)
import requests

BASE_URL = os.getenv("API_URL", "https://localhost:3443/api/v1")


def _allowed(status_code: int) -> bool:
    return status_code in [200, 400, 401, 403, 404, 422, 500]


def test_onboarding_status_shape():
    resp = requests.get(f"{BASE_URL}/onboarding/status", verify=False)
    assert _allowed(resp.status_code), f"unexpected status {resp.status_code}"
    if resp.status_code == 200:
        data = resp.json()
        # Core fields should be present
        assert "overall_complete" in data
        assert "steps" in data
        assert isinstance(data.get("steps"), list)
        # Readiness flags should be present
        assert "access_profile_ready" in data
        assert "birthright_ready" in data
        # Each step should have id/done
        if data["steps"]:
            assert "id" in data["steps"][0] and "done" in data["steps"][0]


@pytest.mark.parametrize(
    "target",
    ["idp", "endpoint", "cloud", "git", "appsec", "ai", "ticketing"],
)
def test_onboarding_recheck_health_targets(target: str):
    resp = requests.post(
        f"{BASE_URL}/onboarding/recheck-health",
        json={"target": target},
        verify=False,
    )
    assert _allowed(resp.status_code), f"{target}: unexpected status {resp.status_code}"
    if resp.status_code == 200:
        data = resp.json()
        # Expect health payload when successful
        assert "health" in data
        assert isinstance(data["health"], dict)
