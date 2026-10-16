"""
Birthright (baseline access) service.

MVP scope:
- If a tenant has an Access Profile marked `is_default=true`, automatically grant all
  entitlements in that profile to newly onboarded users (invite + bulk upload).

This keeps "day-1 onboarding" frictionless while deferring full birthright rule
evaluation (attribute-based rules) to a later phase.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class BirthrightService:
    """Apply baseline (birthright) access for a tenant."""

    @staticmethod
    def apply_default_access_profile(
        db: Session,
        *,
        tenant_id: str,
        user_id: str,
        granted_by: Optional[str] = None,
    ) -> int:
        """
        Grant entitlements from the tenant's default access profile to the user.

        Returns the number of entitlements inserted (idempotent for active rows).
        """
        profile_row = db.execute(
            text(
                """
                SELECT id
                FROM access_profiles
                WHERE tenant_id = :tenant_id AND is_default = true
                ORDER BY updated_at DESC
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        ).fetchone()

        if not profile_row:
            return 0

        profile_id = str(profile_row[0])
        notes = f"birthright:default_access_profile:{profile_id}"

        result = db.execute(
            text(
                """
                INSERT INTO user_entitlements (tenant_id, user_id, entitlement_id, granted_by, status, notes)
                SELECT :tenant_id, :user_id, ape.entitlement_id, :granted_by, 'active', :notes
                FROM access_profile_entitlements ape
                WHERE ape.access_profile_id = :profile_id
                  AND NOT EXISTS (
                    SELECT 1
                    FROM user_entitlements ue
                    WHERE ue.tenant_id = :tenant_id
                      AND ue.user_id = :user_id
                      AND ue.entitlement_id = ape.entitlement_id
                      AND ue.status = 'active'
                  )
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "profile_id": profile_id,
                "granted_by": granted_by,
                "notes": notes,
            },
        )
        inserted = int(getattr(result, "rowcount", 0) or 0)
        db.commit()

        if inserted:
            logger.info(
                "Applied default access profile birthright: tenant_id=%s user_id=%s profile_id=%s inserted=%s",
                tenant_id,
                user_id,
                profile_id,
                inserted,
            )
        return inserted

    @staticmethod
    def apply_attribute_rules(
        db: Session,
        *,
        tenant_id: str,
        user_id: str,
        attributes: dict,
        granted_by: Optional[str] = None,
        remove_missing: bool = False,
    ) -> dict:
        """
        Apply attribute-based birthright rules for a user (idempotent).

        Supported attribute keys: department, team, location, manager_id, employee_type.
        """
        attr_map = {(k or "").lower(): (v or "").lower().strip() for k, v in (attributes or {}).items()}
        if not attr_map:
            return {"inserted": 0, "revoked": 0}

        rules = db.execute(
            text(
                """
                SELECT id, attribute_key, match_value, access_profile_id
                FROM birthright_rules
                WHERE tenant_id = :tenant_id
                  AND is_active = true
                """
            ),
            {"tenant_id": tenant_id},
        ).fetchall()

        desired_entitlements = set()
        for rule in rules:
            key = (rule.attribute_key or "").lower().strip()
            match_value = (rule.match_value or "").lower().strip()
            if not key or not match_value:
                continue

            current_val = attr_map.get(key)
            if not current_val or current_val != match_value:
                continue

            ent_rows = db.execute(
                text(
                    """
                    SELECT entitlement_id FROM access_profile_entitlements
                    WHERE access_profile_id = :pid
                    """
                ),
                {"pid": str(rule.access_profile_id)},
            ).fetchall()
            for ent_row in ent_rows:
                desired_entitlements.add(str(ent_row.entitlement_id))

        # Current active birthright-rule entitlements
        current_rows = db.execute(
            text(
                """
                SELECT id, entitlement_id
                FROM user_entitlements
                WHERE tenant_id = :tenant_id
                  AND user_id = :user_id
                  AND status = 'active'
                  AND notes LIKE 'birthright:rule:%'
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
        ).fetchall()
        current_entitlements = {str(r.entitlement_id): str(r.id) for r in current_rows}

        to_add = desired_entitlements - set(current_entitlements.keys())
        to_remove = set(current_entitlements.keys()) - desired_entitlements if remove_missing else set()

        inserted_total = 0
        if to_add:
            for ent_id in to_add:
                result = db.execute(
                    text(
                        """
                        INSERT INTO user_entitlements (tenant_id, user_id, entitlement_id, granted_by, status, notes)
                        VALUES (:tenant_id, :user_id, :entitlement_id, :granted_by, 'active', :notes)
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "entitlement_id": ent_id,
                        "granted_by": granted_by,
                        "notes": f"birthright:rule",
                    },
                )
                inserted_total += int(getattr(result, "rowcount", 0) or 0)

        revoked_total = 0
        if to_remove:
            result = db.execute(
                text(
                    """
                    UPDATE user_entitlements
                    SET status = 'revoked', updated_at = now()
                    WHERE tenant_id = :tenant_id
                      AND user_id = :user_id
                      AND entitlement_id = ANY(:ent_ids)
                      AND status = 'active'
                      AND notes LIKE 'birthright:rule:%'
                    """
                ),
                {"tenant_id": tenant_id, "user_id": user_id, "ent_ids": list(to_remove)},
            )
            revoked_total = int(getattr(result, "rowcount", 0) or 0)

        if inserted_total or revoked_total:
            db.commit()
        return {"inserted": inserted_total, "revoked": revoked_total}
