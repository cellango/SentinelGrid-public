"""
Integration test: attribute-based birthright rule applies on mover (department change).

Flow:
- Login as demo admin to IAM Agent -> get tenant_id + realm.
- Seed an app + entitlement + access profile in Postgres.
- Create a birthright rule: IF department=engineering -> assign profile.
- Create a user via IAM Portal API (tenant-scoped).
- Update the user department to "engineering".
- Verify user_entitlements contains the seeded entitlement (birthright rule applied).
"""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
from typing import Dict

import pytest
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def _decode_jwt_payload(token: str) -> Dict:
    payload_part = token.split(".")[1]
    payload_part += "=" * (-len(payload_part) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_part))


def _get_admin_token() -> str:
    kc_url = os.getenv("KEYCLOAK_URL", "https://localhost:8443").rstrip("/")
    resp = requests.post(
        f"{kc_url}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": os.getenv("KEYCLOAK_ADMIN_USER", "admin"),
            "password": os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin"),
        },
        timeout=15,
        verify=False,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _delete_keycloak_user(user_id: str, realm: str) -> None:
    token = _get_admin_token()
    kc_url = os.getenv("KEYCLOAK_URL", "https://localhost:8443").rstrip("/")
    try:
        requests.delete(
            f"{kc_url}/admin/realms/{realm}/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
            verify=False,
        )
    except Exception:
        pass


@pytest.mark.integration
def test_birthright_rule_applies_on_department_change():
    iam_base = os.getenv("IAM_AGENT_HTTP_URL", "http://localhost:8005").rstrip("/")

    login = requests.post(
        f"{iam_base}/api/v1/auth/login",
        json={"email": "admin@demo.sentinelgrid.ai", "password": "DemoPassword123!"},
        timeout=20,
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    payload = _decode_jwt_payload(token)
    tenant_id = payload.get("tenant_id")
    assert tenant_id, "Expected tenant_id in token payload"
    realm = payload.get("iss", "").split("/realms/")[-1] if "/realms/" in payload.get("iss", "") else "demo"

    db_url = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    suffix = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
    app_id = uuid.uuid4()
    entitlement_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    user_email = f"br-mover-{suffix}@example.com"
    user_username = f"br-mover-{suffix}"

    try:
        # Ensure birthright_rules table exists (migration may not have run)
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS birthright_rules (
                    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
                    tenant_id uuid NOT NULL,
                    name text,
                    attribute_key text NOT NULL,
                    match_value text NOT NULL,
                    access_profile_id uuid NOT NULL,
                    is_active boolean NOT NULL DEFAULT true,
                    created_at timestamptz NOT NULL DEFAULT now(),
                    updated_at timestamptz NOT NULL DEFAULT now()
                );
                """
            )
        )
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_birthright_rules_tenant ON birthright_rules (tenant_id);"))
        db.execute(
            text("CREATE INDEX IF NOT EXISTS idx_birthright_rules_attr ON birthright_rules (tenant_id, attribute_key);")
        )
        db.commit()

        # Seed app/entitlement/profile
        db.execute(
            text(
                """
                INSERT INTO apps (id, tenant_id, name, display_name, app_type, is_active)
                VALUES (:id, :tenant_id, :name, :display_name, 'custom', true)
                """
            ),
            {
                "id": str(app_id),
                "tenant_id": tenant_id,
                "name": f"br-app-{suffix}",
                "display_name": f"br-app-{suffix}",
            },
        )
        db.execute(
            text(
                """
                INSERT INTO entitlements (id, tenant_id, app_id, name, display_name, entitlement_type, is_privileged, requires_mfa, risk_level)
                VALUES (:id, :tenant_id, :app_id, :name, :display_name, 'role', false, false, 'low')
                """
            ),
            {
                "id": str(entitlement_id),
                "tenant_id": tenant_id,
                "app_id": str(app_id),
                "name": f"br-ent-{suffix}",
                "display_name": f"br-ent-{suffix}",
            },
        )
        db.execute(
            text(
                """
                INSERT INTO access_profiles (id, tenant_id, name, display_name, description, is_default, is_system)
                VALUES (:id, :tenant_id, :name, :display_name, 'br profile', false, false)
                """
            ),
            {
                "id": str(profile_id),
                "tenant_id": tenant_id,
                "name": f"br-prof-{suffix}",
                "display_name": f"br-prof-{suffix}",
            },
        )
        db.execute(
            text(
                """
                INSERT INTO access_profile_entitlements (access_profile_id, entitlement_id)
                VALUES (:profile_id, :entitlement_id)
                """
            ),
            {"profile_id": str(profile_id), "entitlement_id": str(entitlement_id)},
        )
        db.commit()

        # Create birthright rule
        rule_resp = requests.post(
            f"{iam_base}/api/iam-portal/birthright-rules",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "attribute_key": "department",
                "match_value": "engineering",
                "access_profile_id": str(profile_id),
            },
            timeout=20,
        )
        rule_resp.raise_for_status()

        # Create Keycloak user directly (admin API)
        kc_admin_token = _get_admin_token()
        kc_url = os.getenv("KEYCLOAK_URL", "https://localhost:8443").rstrip("/")
        create_resp = requests.post(
            f"{kc_url}/admin/realms/{realm}/users",
            headers={"Authorization": f"Bearer {kc_admin_token}", "Content-Type": "application/json"},
            json={
                "username": user_username,
                "email": user_email,
                "enabled": True,
                "attributes": {
                    "tenant_id": [str(tenant_id)],
                    "department": ["sales"],
                    "team": [],
                },
            },
            timeout=20,
            verify=False,
        )
        if create_resp.status_code not in (201, 204):
            create_resp.raise_for_status()

        # Lookup user_id
        lookup = requests.get(
            f"{kc_url}/admin/realms/{realm}/users",
            headers={"Authorization": f"Bearer {kc_admin_token}"},
            params={"username": user_username, "exact": "true"},
            timeout=15,
            verify=False,
        )
        lookup.raise_for_status()
        items = lookup.json()
        assert items, "Expected created user to be found"
        user_id = items[0]["id"]

        # Update department to trigger rule
        update_resp = requests.patch(
            f"{iam_base}/api/iam-portal/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"department": "engineering"},
            timeout=20,
        )
        update_resp.raise_for_status()

        # Verify entitlement assigned
        count = db.execute(
            text(
                """
                SELECT COUNT(*) FROM user_entitlements
                WHERE tenant_id = :tenant_id AND user_id = :user_id AND entitlement_id = :entitlement_id AND status = 'active'
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id, "entitlement_id": str(entitlement_id)},
        ).scalar()
        assert count and int(count) == 1, "Expected birthright entitlement to be assigned"
    finally:
        try:
            _delete_keycloak_user(user_username, realm)
        except Exception:
            pass
        # Cleanup DB rows
        try:
            db.execute(
                text(
                    "DELETE FROM user_entitlements WHERE tenant_id = :tenant_id AND entitlement_id = :entitlement_id"
                ),
                {"tenant_id": tenant_id, "entitlement_id": str(entitlement_id)},
            )
            db.execute(
                text("DELETE FROM birthright_rules WHERE tenant_id = :tenant_id AND access_profile_id = :pid"),
                {"tenant_id": tenant_id, "pid": str(profile_id)},
            )
            db.execute(
                text("DELETE FROM access_profile_entitlements WHERE access_profile_id = :pid"),
                {"pid": str(profile_id)},
            )
            db.execute(
                text("DELETE FROM access_profiles WHERE id = :pid"),
                {"pid": str(profile_id)},
            )
            db.execute(
                text("DELETE FROM entitlements WHERE id = :eid"),
                {"eid": str(entitlement_id)},
            )
            db.execute(text("DELETE FROM apps WHERE id = :aid"), {"aid": str(app_id)})
            db.commit()
        except Exception:
            pass
        db.close()
