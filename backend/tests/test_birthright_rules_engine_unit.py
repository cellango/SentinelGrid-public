"""
Unit-style test for birthright rule evaluator with extended attributes.
"""

from __future__ import annotations

import os
import uuid
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Make app/ imports work when running from repo root
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

# Ensure we load the IAM Agent app package (not other service apps)
existing_app = sys.modules.get("app")
if existing_app:
    app_file = getattr(existing_app, "__file__", "") or ""
    if "iam_agent" not in app_file:
        sys.modules.pop("app", None)
        sys.modules.pop("app.services", None)

from app.services.birthright_service import BirthrightService


def test_birthright_rules_support_extended_attributes():
    db_url = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)

    tenant_id = str(uuid.uuid4())
    user_id = "br-user"
    app_id = str(uuid.uuid4())
    entitlement_id = str(uuid.uuid4())
    profile_id = str(uuid.uuid4())
    rule_id = str(uuid.uuid4())

    with SessionLocal() as db:
        # Ensure tables exist (for environments without migrations applied)
        db.execute(
            text(
                """
                CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
                CREATE TABLE IF NOT EXISTS apps (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    name TEXT,
                    display_name TEXT,
                    app_type TEXT,
                    is_active BOOLEAN DEFAULT TRUE
                );
                CREATE TABLE IF NOT EXISTS entitlements (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    app_id UUID NOT NULL,
                    name TEXT,
                    display_name TEXT,
                    entitlement_type TEXT,
                    is_privileged BOOLEAN DEFAULT FALSE,
                    requires_mfa BOOLEAN DEFAULT FALSE,
                    risk_level TEXT
                );
                CREATE TABLE IF NOT EXISTS access_profiles (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    name TEXT,
                    display_name TEXT,
                    description TEXT,
                    is_default BOOLEAN DEFAULT FALSE,
                    is_system BOOLEAN DEFAULT FALSE
                );
                CREATE TABLE IF NOT EXISTS access_profile_entitlements (
                    access_profile_id UUID,
                    entitlement_id UUID
                );
                CREATE TABLE IF NOT EXISTS birthright_rules (
                    id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    name TEXT,
                    attribute_key TEXT,
                    match_value TEXT,
                    access_profile_id UUID,
                    is_active BOOLEAN DEFAULT TRUE
                );
                CREATE TABLE IF NOT EXISTS user_entitlements (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    tenant_id UUID NOT NULL,
                    user_id TEXT NOT NULL,
                    entitlement_id UUID NOT NULL,
                    granted_by TEXT,
                    status TEXT DEFAULT 'active',
                    notes TEXT,
                    updated_at timestamptz DEFAULT now()
                );
                """
            )
        )
        db.commit()

        # Clean slate
        for table in [
            "user_entitlements",
            "birthright_rules",
            "access_profile_entitlements",
            "access_profiles",
            "entitlements",
            "apps",
        ]:
            db.execute(text(f"DELETE FROM {table} WHERE tenant_id = :t"), {"t": tenant_id}) if "tenant_id" in table else db.execute(text(f"DELETE FROM {table}"))
        db.commit()

        # Seed minimal app/entitlement/profile and rule (location-based)
        db.execute(
            text(
                "INSERT INTO apps (id, tenant_id, name, display_name, app_type, is_active) VALUES (:id, :tenant_id, 'demo', 'demo', 'custom', true)"
            ),
            {"id": app_id, "tenant_id": tenant_id},
        )
        db.execute(
            text(
                "INSERT INTO entitlements (id, tenant_id, app_id, name, display_name, entitlement_type) VALUES (:id, :tenant_id, :app_id, 'viewer', 'viewer', 'role')"
            ),
            {"id": entitlement_id, "tenant_id": tenant_id, "app_id": app_id},
        )
        db.execute(
            text(
                "INSERT INTO access_profiles (id, tenant_id, name, display_name, description, is_default, is_system) VALUES (:id, :tenant_id, 'base', 'base', 'base profile', false, false)"
            ),
            {"id": profile_id, "tenant_id": tenant_id},
        )
        db.execute(
            text(
                "INSERT INTO access_profile_entitlements (access_profile_id, entitlement_id) VALUES (:pid, :eid)"
            ),
            {"pid": profile_id, "eid": entitlement_id},
        )
        db.execute(
            text(
                """
                INSERT INTO birthright_rules (id, tenant_id, name, attribute_key, match_value, access_profile_id, is_active)
                VALUES (:id, :tenant_id, 'loc-nyc', 'location', 'nyc', :pid, true)
                """
            ),
            {"id": rule_id, "tenant_id": tenant_id, "pid": profile_id},
        )
        db.commit()

        delta = BirthrightService.apply_attribute_rules(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            granted_by="tester",
            attributes={"location": "NYC"},
            remove_missing=True,
        )
        assert delta["inserted"] == 1

        row = db.execute(
            text(
                "SELECT entitlement_id, status, notes FROM user_entitlements WHERE tenant_id = :t AND user_id = :u"
            ),
            {"t": tenant_id, "u": user_id},
        ).fetchone()
        assert row is not None
        assert str(row.entitlement_id) == entitlement_id
        assert row.status == "active"
        assert "birthright:rule" in (row.notes or "")

        # Cleanup
        for table in [
            "user_entitlements",
            "birthright_rules",
            "access_profile_entitlements",
            "access_profiles",
            "entitlements",
            "apps",
        ]:
            db.execute(text(f"DELETE FROM {table} WHERE tenant_id = :t"), {"t": tenant_id}) if "tenant_id" in table else db.execute(text(f"DELETE FROM {table}"))
        db.commit()
