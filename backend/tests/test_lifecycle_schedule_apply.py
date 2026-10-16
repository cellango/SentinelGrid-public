"""
Exercise lifecycle scheduler: start-date activation and end-date offboarding.

This keeps the background job MVP-ready by ensuring we toggle Keycloak users and
clear due dates once processed.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Ensure app/ modules resolve when running tests from repo root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
iam_agent_root = PROJECT_ROOT / "agents" / "iam_agent"
iam_agent_app = iam_agent_root / "app"
for p in (iam_agent_root, iam_agent_app):
    if str(p) not in sys.path:
        sys.path.append(str(p))
# Add shared libs (sg_core)
libs_path = PROJECT_ROOT / "libs"
if str(libs_path) not in sys.path:
    sys.path.append(str(libs_path))

# Ensure we import the IAM Agent app package (not other services named app)
existing_app = sys.modules.get("app")
if existing_app:
    app_file = getattr(existing_app, "__file__", "") or ""
    if "iam_agent" not in app_file:
        sys.modules.pop("app", None)
        sys.modules.pop("app.services", None)

from app.services.iam_portal_service import IAMPortalService
from app.services.birthright_service import BirthrightService


class _StubKeycloak:
    def __init__(self):
        self.users: dict[str, dict] = {}
        self.realm = "demo"

    async def get_user(self, user_id: str):
        return self.users.get(user_id)

    async def update_user(self, user_id: str, payload: dict):
        # Persist payload to simulate Keycloak state change
        self.users[user_id] = payload
        return True

    async def get_users_with_role(self, role_name: str):
        # No admins returned; guardrail is exercised separately
        return []


@pytest.mark.asyncio
async def test_apply_lifecycle_schedules_act_and_offboard(monkeypatch):
    db_url = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)

    tenant_id = uuid.uuid4()
    user_activate = "lc-activate"
    user_offboard = "lc-offboard"

    # Stub Keycloak so we don't hit the real service
    kc = _StubKeycloak()
    kc.users[user_activate] = {"id": user_activate, "enabled": False, "attributes": {"department": ["eng"]}}
    kc.users[user_offboard] = {"id": user_offboard, "enabled": True, "attributes": {}}

    with SessionLocal() as db:
        # Ensure table exists for environments where migrations have not been applied
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS user_lifecycle_schedule (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    user_id TEXT NOT NULL,
                    activate_at timestamptz,
                    deactivate_at timestamptz,
                    created_at timestamptz DEFAULT now(),
                    updated_at timestamptz DEFAULT now()
                );
                """
            )
        )
        db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_lifecycle_unique ON user_lifecycle_schedule (tenant_id, user_id);"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_user_lifecycle_activate ON user_lifecycle_schedule (tenant_id, activate_at);"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_user_lifecycle_deactivate ON user_lifecycle_schedule (tenant_id, deactivate_at);"))
        db.commit()

        # Clean slate
        db.execute(
            text("DELETE FROM user_lifecycle_schedule WHERE tenant_id = :tenant_id"),
            {"tenant_id": str(tenant_id)},
        )
        db.commit()

        # Seed one activation and one deactivation
        db.execute(
            text(
                """
                INSERT INTO user_lifecycle_schedule (id, tenant_id, user_id, activate_at)
                VALUES (:id, :tenant_id, :user_id, :activate_at)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": str(tenant_id),
                "user_id": user_activate,
                "activate_at": datetime.now(timezone.utc) - timedelta(minutes=5),
            },
        )
        db.execute(
            text(
                """
                INSERT INTO user_lifecycle_schedule (id, tenant_id, user_id, deactivate_at)
                VALUES (:id, :tenant_id, :user_id, :deactivate_at)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "tenant_id": str(tenant_id),
                "user_id": user_offboard,
                "deactivate_at": datetime.now(timezone.utc) - timedelta(minutes=5),
            },
        )
        db.commit()

        svc = IAMPortalService(db, tenant_id, "demo")
        svc.keycloak = kc  # type: ignore[assignment]

        # Avoid hitting IAM audit or birthright DB state during the job
        monkeypatch.setattr(svc, "_log_audit_event", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            BirthrightService,
            "apply_default_access_profile",
            staticmethod(lambda *args, **kwargs: 0),
        )
        monkeypatch.setattr(
            BirthrightService,
            "apply_attribute_rules",
            staticmethod(lambda *args, **kwargs: {"inserted": 0, "revoked": 0}),
        )

        offboarded: dict[str, str] = {}

        async def _fake_offboard(user_id: str, actor_id: str):
            offboarded["user_id"] = user_id
            kc.users[user_id] = {"id": user_id, "enabled": False}
            return True

        monkeypatch.setattr(svc, "offboard_user", _fake_offboard)

        stats = await svc.apply_lifecycle_schedules(actor_id="tester")

        assert stats["activated"] == 1
        assert stats["offboarded"] == 1
        # Activation clears the schedule and flips the flag in Keycloak
        row = db.execute(
            text("SELECT activate_at FROM user_lifecycle_schedule WHERE user_id = :u"),
            {"u": user_activate},
        ).fetchone()
        assert row[0] is None
        assert kc.users[user_activate]["enabled"] is True

        # Offboarding clears the schedule and invokes our stub
        row = db.execute(
            text("SELECT deactivate_at FROM user_lifecycle_schedule WHERE user_id = :u"),
            {"u": user_offboard},
        ).fetchone()
        assert row[0] is None
        assert offboarded.get("user_id") == user_offboard

        # Cleanup rows created by this test
        db.execute(
            text("DELETE FROM user_lifecycle_schedule WHERE tenant_id = :tenant_id"),
            {"tenant_id": str(tenant_id)},
        )
        db.commit()
