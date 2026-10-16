"""
Integration test: birthright (default access profile) is applied on onboarding.

This validates Phase 1 Step 2 in docs/people_access_employee_lifecycle_plan.md:
newly onboarded users should automatically receive baseline entitlements.
"""

from __future__ import annotations

import base64
import json
import os
import time
import uuid

import pytest
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def _decode_jwt_payload(token: str) -> dict:
    payload_part = token.split(".")[1]
    payload_part += "=" * (-len(payload_part) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_part))


def _get_keycloak_admin_token() -> str:
    keycloak_base = os.getenv("KEYCLOAK_URL", "https://localhost:8443").rstrip("/")
    username = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
    password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")

    resp = requests.post(
        f"{keycloak_base}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": username,
            "password": password,
        },
        timeout=15,
        verify=False,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _get_keycloak_user_id_by_username(realm: str, username: str, admin_token: str) -> str | None:
    keycloak_base = os.getenv("KEYCLOAK_URL", "https://localhost:8443").rstrip("/")
    resp = requests.get(
        f"{keycloak_base}/admin/realms/{realm}/users",
        params={"username": username, "exact": "true"},
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
        verify=False,
    )
    resp.raise_for_status()
    users = resp.json()
    if not users:
        return None
    return users[0].get("id")


def _delete_keycloak_user(realm: str, user_id: str, admin_token: str) -> None:
    keycloak_base = os.getenv("KEYCLOAK_URL", "https://localhost:8443").rstrip("/")
    resp = requests.delete(
        f"{keycloak_base}/admin/realms/{realm}/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
        verify=False,
    )
    # 204 is expected; tolerate 404 to keep test cleanup idempotent
    if resp.status_code not in (204, 404):
        resp.raise_for_status()


@pytest.mark.integration
def test_invite_applies_default_access_profile_birthright():
    """
    Creates a default access profile with 1 entitlement, invites a user, and verifies
    the entitlement is inserted into user_entitlements with birthright notes.
    """
    iam_agent_base = os.getenv("IAM_AGENT_HTTP_URL", "http://localhost:8005").rstrip("/")

    login = requests.post(
        f"{iam_agent_base}/api/v1/auth/login",
        json={"email": "admin@demo.sentinelgrid.ai", "password": "DemoPassword123!"},
        timeout=20,
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    payload = _decode_jwt_payload(token)

    tenant_id = payload.get("tenant_id")
    assert tenant_id, "Expected tenant_id in token payload"

    issuer = payload.get("iss", "")
    realm = issuer.split("/realms/")[-1].rstrip("/") if "/realms/" in issuer else "demo"

    # DB setup
    db_url = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)

    app_id = uuid.uuid4()
    entitlement_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    suffix = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"

    email = f"e2e-birthright-{suffix}@example.com"
    app_name = f"e2e-birthright-app-{suffix}"
    entitlement_name = f"e2e_ent_{suffix}"
    profile_name = f"e2e_birthright_{suffix}"

    db = SessionLocal()
    try:
        db.execute(
            text(
                """
                INSERT INTO apps (id, tenant_id, name, display_name, app_type, is_active)
                VALUES (:id, :tenant_id, :name, :display_name, :app_type, true)
                """
            ),
            {
                "id": str(app_id),
                "tenant_id": tenant_id,
                "name": app_name,
                "display_name": app_name,
                "app_type": "custom",
            },
        )

        db.execute(
            text(
                """
                INSERT INTO entitlements (id, tenant_id, app_id, name, display_name, entitlement_type)
                VALUES (:id, :tenant_id, :app_id, :name, :display_name, 'role')
                """
            ),
            {
                "id": str(entitlement_id),
                "tenant_id": tenant_id,
                "app_id": str(app_id),
                "name": entitlement_name,
                "display_name": entitlement_name,
            },
        )

        db.execute(
            text(
                """
                INSERT INTO access_profiles (id, tenant_id, name, display_name, description, is_default, is_system)
                VALUES (:id, :tenant_id, :name, :display_name, :description, true, false)
                """
            ),
            {
                "id": str(profile_id),
                "tenant_id": tenant_id,
                "name": profile_name,
                "display_name": profile_name,
                "description": "E2E birthright default profile",
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
    finally:
        db.close()

    # Invite user (birthright should apply server-side)
    invite = requests.post(
        f"{iam_agent_base}/api/v1/users/invite",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": email, "send_email": False},
        timeout=30,
    )
    invite.raise_for_status()

    # Lookup created user in Keycloak and verify entitlement row exists
    admin_token = _get_keycloak_admin_token()
    user_id = _get_keycloak_user_id_by_username(realm, email, admin_token)
    assert user_id, "Expected invited user to exist in Keycloak"

    try:
        db = SessionLocal()
        try:
            count = db.execute(
                text(
                    """
                    SELECT count(*)
                    FROM user_entitlements
                    WHERE tenant_id = :tenant_id
                      AND user_id = :user_id
                      AND entitlement_id = :entitlement_id
                      AND status = 'active'
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "entitlement_id": str(entitlement_id),
                },
            ).scalar()
            assert int(count or 0) == 1

            notes = db.execute(
                text(
                    """
                    SELECT notes
                    FROM user_entitlements
                    WHERE tenant_id = :tenant_id
                      AND user_id = :user_id
                      AND entitlement_id = :entitlement_id
                      AND status = 'active'
                    LIMIT 1
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "entitlement_id": str(entitlement_id),
                },
            ).scalar()
            assert notes and "birthright:default_access_profile" in notes
        finally:
            db.close()
    finally:
        # Cleanup: delete user and DB fixtures (best-effort)
        try:
            _delete_keycloak_user(realm, user_id, admin_token)
        except Exception:
            pass

        db = SessionLocal()
        try:
            db.execute(text("DELETE FROM access_profile_entitlements WHERE access_profile_id = :id"), {"id": str(profile_id)})
            db.execute(text("DELETE FROM access_profiles WHERE id = :id"), {"id": str(profile_id)})
            db.execute(text("DELETE FROM entitlements WHERE id = :id"), {"id": str(entitlement_id)})
            db.execute(text("DELETE FROM apps WHERE id = :id"), {"id": str(app_id)})
            db.commit()
        finally:
            db.close()

