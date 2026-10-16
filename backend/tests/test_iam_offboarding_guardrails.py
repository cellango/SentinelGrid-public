"""
Unit tests for offboarding/suspend guardrails (last admin protection).

These tests do not require a running Keycloak/Postgres stack; they validate
the IAMPortalService guardrail logic in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

# Path setup so IAM Agent's absolute imports (`from app...`) resolve in local tests
import sys
from pathlib import Path

iam_agent_root = Path(__file__).parent.parent / "agents" / "iam_agent"
iam_agent_app = iam_agent_root / "app"
for p in (iam_agent_root, iam_agent_app):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Add shared libs (sg_core)
libs_path = Path(__file__).parent.parent / "libs"
if str(libs_path) not in sys.path:
    sys.path.insert(0, str(libs_path))

# Ensure we import the IAM Agent app package, not another service's "app"
existing_app = sys.modules.get("app")
if existing_app:
    app_file = getattr(existing_app, "__file__", "") or ""
    if "iam_agent" not in app_file:
        sys.modules.pop("app", None)
        sys.modules.pop("app.services", None)

from app.services.iam_portal_service import IAMPortalService  # noqa: E402


@dataclass
class _StubKeycloak:
    users: List[Dict[str, Any]]

    async def get_users_with_role(self, role_name: str) -> List[Dict[str, Any]]:
        return self.users


@pytest.mark.asyncio
async def test_bulk_offboard_blocks_last_enabled_tenant_admin():
    tenant_id = uuid4()
    svc = IAMPortalService(MagicMock(), tenant_id, "demo")
    last_admin_id = "user-last-admin"
    svc.keycloak = _StubKeycloak(
        users=[
            {
                "id": last_admin_id,
                "enabled": True,
                "attributes": {"tenant_id": [str(tenant_id)]},
            }
        ]
    )

    with pytest.raises(ValueError, match="last tenant admin"):
        await svc.bulk_update_users("offboard", [last_admin_id], actor_id="actor")


@pytest.mark.asyncio
async def test_bulk_suspend_blocks_last_enabled_tenant_admin():
    tenant_id = uuid4()
    svc = IAMPortalService(MagicMock(), tenant_id, "demo")
    last_admin_id = "user-last-admin"
    svc.keycloak = _StubKeycloak(
        users=[
            {
                "id": last_admin_id,
                "enabled": True,
                "attributes": {"tenant_id": [str(tenant_id)]},
            }
        ]
    )

    with pytest.raises(ValueError, match="last tenant admin"):
        await svc.bulk_update_users("suspend", [last_admin_id], actor_id="actor")


@pytest.mark.asyncio
async def test_disabled_admins_do_not_count_towards_last_admin_set():
    tenant_id = uuid4()
    svc = IAMPortalService(MagicMock(), tenant_id, "demo")
    svc.keycloak = _StubKeycloak(
        users=[
            {
                "id": "disabled-admin",
                "enabled": False,
                "attributes": {"tenant_id": [str(tenant_id)]},
            }
        ]
    )

    admin_ids = await svc._get_tenant_admin_user_ids()
    assert admin_ids == set()
