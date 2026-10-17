"""Verified, bounded, transaction-coupled role reconciliation in the IAM store."""

from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import text
from app.models.entitlement import Entitlement
from app.models.role_entitlement_pattern import RoleEntitlementPattern
from app.models.role_grant_binding import RoleGrantBinding
from app.schemas.role_mappings import parse_pattern, RolePatternResponse
from app.services.audit_logger import AuditLogger
from app.services.governance_service import grant_snapshot
from app.services.redis_cache import cache
from app.services.role_directory_service import RoleDirectoryService, RoleSnapshot

MAX_PATTERNS = 500
MAX_EFFECTS = 500


def admin(context):
    try:
        user = UUID(str(context.user_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="A verified user UUID is required")
    if not {"TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"}.intersection(
        r.upper() for r in context.roles
    ):
        raise HTTPException(status_code=403, detail="Administrator role required")
    return user


@contextmanager
def change(db):
    try:
        yield
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Role change could not be committed; inspect state before retry",
        ) from error


def pattern_change(db, context, data=None, *, identity=None, delete=False):
    actor = admin(context)
    if (
        identity is None
        and data.tenant_id is not None
        and data.tenant_id != context.tenant_id
    ):
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    with change(db):
        if identity is None:
            if (
                db.query(RoleEntitlementPattern)
                .filter(
                    RoleEntitlementPattern.tenant_id == context.tenant_id,
                    RoleEntitlementPattern.role_name == data.role_name,
                    RoleEntitlementPattern.entitlement_pattern
                    == data.entitlement_pattern,
                )
                .first()
                is not None
            ):
                raise HTTPException(
                    status_code=409, detail="Role pattern already exists"
                )
            row = RoleEntitlementPattern(
                role_name=data.role_name,
                tenant_id=context.tenant_id,
                entitlement_pattern=data.entitlement_pattern,
                auto_grant=data.auto_grant,
                created_by=actor,
                enabled=True,
            )
            before = None
            db.add(row)
        else:
            row = (
                db.query(RoleEntitlementPattern)
                .filter(
                    RoleEntitlementPattern.id == identity,
                    RoleEntitlementPattern.tenant_id == context.tenant_id,
                )
                .populate_existing()
                .with_for_update()
                .first()
            )
            if row is None:
                raise HTTPException(status_code=404, detail="Role pattern not found")
            before = RolePatternResponse.model_validate(row).model_dump()
            if delete:
                db.delete(row)
            else:
                for key, value in data.model_dump(exclude_unset=True).items():
                    setattr(row, key, value)
                try:
                    parse_pattern(row.entitlement_pattern)
                except ValueError:
                    raise HTTPException(
                        status_code=409, detail="Legacy pattern requires reconciliation"
                    )
        db.flush()
        after = None if delete else RolePatternResponse.model_validate(row)
        AuditLogger(db).log_entitlement_event(
            "role_pattern_deleted"
            if delete
            else (
                "role_pattern_created" if identity is None else "role_pattern_updated"
            ),
            None,
            context.tenant_id,
            actor,
            changes={
                "pattern_id": str(row.id),
                "before": before,
                "after": after.model_dump() if after else None,
            },
        )
    return after


class RoleSyncService:
    def __init__(self, db, *, directory=None):
        self.db = db
        self.directory = directory or RoleDirectoryService()

    def _check(self, snapshot, tenant):
        if (
            not isinstance(snapshot, RoleSnapshot)
            or snapshot.tenant_id != tenant
            or not isinstance(snapshot.user_id, UUID)
        ):
            raise HTTPException(status_code=503, detail="Unverified directory snapshot")
        age = (datetime.now(timezone.utc) - snapshot.observed_at).total_seconds()
        if not 0 <= age <= 30:
            raise HTTPException(status_code=503, detail="Directory snapshot expired")

    def _apply(self, context, snapshots):
        actor = admin(context)
        changed = []
        if len(snapshots) > 100 or len({s.user_id for s in snapshots}) != len(
            snapshots
        ):
            raise HTTPException(status_code=503, detail="Invalid directory batch")
        result = dict(
            users_processed=0,
            roles_processed=0,
            entitlements_created=0,
            entitlements_existing=0,
            entitlements_revoked=0,
            entitlements_blocked=0,
            errors=[],
        )
        with change(self.db):
            for snapshot in sorted(snapshots, key=lambda s: str(s.user_id)):
                self._check(snapshot, context.tenant_id)
                self.db.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:identity,0))"),
                    {
                        "identity": f"iam-role-sync:{context.tenant_id}:{snapshot.user_id}"
                    },
                )
            patterns = (
                self.db.query(RoleEntitlementPattern)
                .filter(
                    RoleEntitlementPattern.tenant_id == context.tenant_id,
                    RoleEntitlementPattern.enabled.is_(True),
                    RoleEntitlementPattern.auto_grant.is_(True),
                )
                .order_by(RoleEntitlementPattern.id)
                .limit(MAX_PATTERNS + 1)
                .populate_existing()
                .with_for_update(read=True)
                .all()
            )
            if len(patterns) > MAX_PATTERNS:
                raise HTTPException(
                    status_code=409, detail="Role pattern set exceeds bounded operation"
                )
            for snapshot in snapshots:
                self._check(snapshot, context.tenant_id)
                AuditLogger(self.db).log_entitlement_event(
                    "role_sync_observed",
                    None,
                    context.tenant_id,
                    actor,
                    subject_id=snapshot.user_id,
                    metadata={
                        "roles": list(snapshot.roles),
                        "observed_at": snapshot.observed_at,
                        "directory_realm": snapshot.directory_realm,
                    },
                )
                desired = {}
                for pattern in patterns:
                    if pattern.role_name not in snapshot.roles:
                        continue
                    try:
                        target = parse_pattern(pattern.entitlement_pattern)
                    except ValueError:
                        raise HTTPException(
                            status_code=409,
                            detail="Enabled legacy pattern requires reconciliation",
                        )
                    roles, ids = desired.setdefault(target, (set(), set()))
                    roles.add(pattern.role_name)
                    ids.add(str(pattern.id))
                grants = (
                    self.db.query(Entitlement)
                    .filter(
                        Entitlement.tenant_id == context.tenant_id,
                        Entitlement.granted_to_type == "user",
                        Entitlement.granted_to_id == snapshot.user_id,
                    )
                    .order_by(Entitlement.id)
                    .limit(MAX_EFFECTS + 1)
                    .populate_existing()
                    .with_for_update()
                    .all()
                )
                bindings = (
                    self.db.query(RoleGrantBinding)
                    .filter(
                        RoleGrantBinding.tenant_id == context.tenant_id,
                        RoleGrantBinding.subject_id == snapshot.user_id,
                    )
                    .order_by(RoleGrantBinding.id)
                    .populate_existing()
                    .with_for_update()
                    .all()
                )
                if len(grants) > MAX_EFFECTS:
                    raise HTTPException(
                        status_code=409,
                        detail="User grant set exceeds bounded operation",
                    )
                owned = {b.entitlement_id: b for b in bindings}
                for grant in grants:
                    if grant.id in owned and owned[grant.id].target != grant_snapshot(
                        grant
                    ):
                        raise HTTPException(
                            status_code=409,
                            detail="Managed grant target changed; reconcile ownership",
                        )
                existing = {
                    (g.resource_type, g.resource_id, g.action): g for g in grants
                }
                for target, (roles, ids) in desired.items():
                    grant = existing.get(target)
                    if grant is not None:
                        result["entitlements_existing"] += 1
                        if grant.status != "active":
                            result["entitlements_blocked"] += 1
                        if grant.id not in owned:
                            continue  # Manual/legacy metadata cannot establish ownership.
                        binding = owned[grant.id]
                    else:
                        grant = Entitlement(
                            tenant_id=context.tenant_id,
                            resource_type=target[0],
                            resource_id=target[1],
                            action=target[2],
                            granted_to_type="user",
                            granted_to_id=snapshot.user_id,
                            granted_by=actor,
                            status="active",
                            metadata_json={"source": "role_sync"},
                        )
                        self.db.add(grant)
                        self.db.flush()
                        binding = RoleGrantBinding(
                            tenant_id=context.tenant_id,
                            subject_id=snapshot.user_id,
                            entitlement_id=grant.id,
                            target=grant_snapshot(grant),
                            roles=sorted(roles),
                            pattern_ids=sorted(ids),
                            created_by=actor,
                        )
                        self.db.add(binding)
                        AuditLogger(self.db).log_entitlement_created(
                            grant, actor, reason="Verified role reconciliation"
                        )
                        AuditLogger(self.db).log_entitlement_event(
                            "role_grant_bound",
                            grant.id,
                            context.tenant_id,
                            actor,
                            subject_id=snapshot.user_id,
                            changes={
                                "target": binding.target,
                                "roles": binding.roles,
                                "pattern_ids": binding.pattern_ids,
                            },
                        )
                        result["entitlements_created"] += 1
                        changed.append(grant.id)
                    before = {
                        "roles": binding.roles,
                        "pattern_ids": binding.pattern_ids,
                    }
                    if before != {"roles": sorted(roles), "pattern_ids": sorted(ids)}:
                        binding.roles = sorted(roles)
                        binding.pattern_ids = sorted(ids)
                        AuditLogger(self.db).log_entitlement_event(
                            "role_grant_sources_updated",
                            grant.id,
                            context.tenant_id,
                            actor,
                            subject_id=snapshot.user_id,
                            changes={
                                "before": before,
                                "after": {
                                    "roles": binding.roles,
                                    "pattern_ids": binding.pattern_ids,
                                },
                            },
                        )
                for grant in grants:
                    target = (grant.resource_type, grant.resource_id, grant.action)
                    if grant.id in owned and target not in desired:
                        binding = owned[grant.id]
                        if grant.status == "active":
                            grant.status = "revoked"
                            changed.append(grant.id)
                            result["entitlements_revoked"] += 1
                            AuditLogger(self.db).log_entitlement_event(
                                "revoked",
                                grant.id,
                                context.tenant_id,
                                actor,
                                subject_id=snapshot.user_id,
                                changes={
                                    "status": {"old": "active", "new": "revoked"},
                                    "target": grant_snapshot(grant),
                                },
                                reason="Verified role/pattern removal",
                            )
                        if binding.roles or binding.pattern_ids:
                            AuditLogger(self.db).log_entitlement_event(
                                "role_grant_sources_updated",
                                grant.id,
                                context.tenant_id,
                                actor,
                                subject_id=snapshot.user_id,
                                changes={
                                    "before": {
                                        "roles": binding.roles,
                                        "pattern_ids": binding.pattern_ids,
                                    },
                                    "after": {"roles": [], "pattern_ids": []},
                                },
                            )
                        binding.roles = []
                        binding.pattern_ids = []
                result["users_processed"] += 1
                result["roles_processed"] += len(snapshot.roles)
                if (
                    result["entitlements_created"] + result["entitlements_revoked"]
                    > MAX_EFFECTS
                ):
                    raise HTTPException(
                        status_code=409,
                        detail="Role reconciliation exceeds bounded operation",
                    )
            AuditLogger(self.db).log_entitlement_event(
                "role_sync_completed",
                None,
                context.tenant_id,
                actor,
                changes={k: v for k, v in result.items() if k != "errors"},
            )
            for snapshot in snapshots:
                self._check(snapshot, context.tenant_id)
        for identity in changed:
            cache.invalidate_entitlement(str(identity), str(context.tenant_id))
        return result

    async def sync_user_roles_to_entitlements(
        self, user_id, tenant_id, granted_by=None, *, request_context=None
    ):
        if request_context is None:
            raise HTTPException(
                status_code=403, detail="Verified caller context required"
            )
        admin(request_context)
        if UUID(str(tenant_id)) != request_context.tenant_id:
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        identity = UUID(str(user_id))
        snapshots = await self.directory.observe(request_context.tenant_id, identity)
        if len(snapshots) != 1 or snapshots[0].user_id != identity:
            raise HTTPException(status_code=503, detail="Directory subject mismatch")
        return {"user_id": str(identity), **self._apply(request_context, snapshots)}

    async def sync_role_to_all_users(
        self, role_name, tenant_id, granted_by=None, *, request_context=None
    ):
        if request_context is None:
            raise HTTPException(
                status_code=403, detail="Verified caller context required"
            )
        admin(request_context)
        if UUID(str(tenant_id)) != request_context.tenant_id:
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        snapshots = await self.directory.observe(request_context.tenant_id)
        # Include formerly owned members to reconcile loss of the selected role.
        former = (
            self.db.query(RoleGrantBinding)
            .filter(
                RoleGrantBinding.tenant_id == request_context.tenant_id,
                RoleGrantBinding.roles.contains([role_name]),
            )
            .limit(101)
            .all()
        )
        if len(former) > 100:
            self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Former role member set exceeds bounded operation",
            )
        ids = {b.subject_id for b in former}
        available = {s.user_id for s in snapshots}
        if not ids <= available:
            self.db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Former role member is unverified; reconcile before bulk sync",
            )
        return {
            "role_name": role_name,
            **self._apply(
                request_context,
                [s for s in snapshots if role_name in s.roles or s.user_id in ids],
            ),
        }

    async def revoke_user_entitlements_for_role(
        self, user_id, role_name, tenant_id, *, request_context=None
    ):
        if request_context is None:
            raise HTTPException(
                status_code=403, detail="Verified caller context required"
            )
        admin(request_context)
        if UUID(str(tenant_id)) != request_context.tenant_id:
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        snapshots = await self.directory.observe(
            request_context.tenant_id, UUID(str(user_id))
        )
        if len(snapshots) != 1 or snapshots[0].user_id != UUID(str(user_id)):
            raise HTTPException(status_code=503, detail="Directory subject mismatch")
        if role_name in snapshots[0].roles:
            raise HTTPException(
                status_code=409, detail="Directory still reports the role"
            )
        return {
            "user_id": str(user_id),
            "role_name": role_name,
            **self._apply(request_context, snapshots),
        }
