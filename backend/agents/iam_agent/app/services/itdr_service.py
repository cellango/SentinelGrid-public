"""Audited ITDR proposals. This service has no provider-effect executor."""

from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException
from app.api.request_context import (
    ensure_request_has_any_role,
    ensure_request_tenant_matches,
)
from app.core.config import settings
from app.schemas.itdr import ThreatSignalBatch, EnforcementResponse, ActionOutcome
from app.services.audit_logger import AuditLogger
from app.services.itdr_response_map import (
    ResponseAction,
    get_response_for_threat,
    get_advisory_actions,
    get_enforcement_actions,
)
from app.services.role_directory_service import RoleDirectoryService, RoleSnapshot


def require_itdr_admin(context):
    try:
        actor = UUID(str(context.user_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="A verified user UUID is required")
    ensure_request_has_any_role(context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN")
    return actor


def block_legacy_response():
    raise HTTPException(
        status_code=503,
        detail="Identity response execution is unavailable; submit an audited ITDR proposal",
    )


class ITDRService:
    def __init__(self, db, *, directory=None):
        self.db = db
        self.directory = directory if directory is not None else RoleDirectoryService()

    def _fresh(self, snapshot, tenant, user):
        valid = (
            isinstance(snapshot, RoleSnapshot)
            and snapshot.tenant_id == tenant
            and snapshot.user_id == user
            and snapshot.directory_realm
            == settings.IAM_ROLE_SYNC_REALMS.get(str(tenant))
            and bool(snapshot.directory_realm)
            and snapshot.observed_at.tzinfo is not None
            and 0
            <= (datetime.now(timezone.utc) - snapshot.observed_at).total_seconds()
            <= 30
        )
        if not valid:
            raise HTTPException(
                status_code=503, detail="ITDR subject membership is unverified"
            )

    def _commit(self, write):
        try:
            result = write()
            self.db.commit()
            return result
        except Exception as error:
            try:
                self.db.rollback()
            except Exception:
                pass  # Preserve the unavailable outcome if the connection is lost.
            raise HTTPException(
                status_code=503,
                detail="ITDR audit could not be confirmed; inspect audit state before retry",
            ) from error

    async def propose(self, signals, context):
        actor = require_itdr_admin(context)
        signals = ThreatSignalBatch(signals=signals).signals
        tenant = context.tenant_id
        # Reject every tenant/realm mismatch before any provider observation/write.
        for signal in signals:
            ensure_request_tenant_matches(tenant, signal.tenant_id)
            if (
                signal.realm is not None
                and signal.realm != settings.IAM_ROLE_SYNC_REALMS.get(str(tenant))
            ):
                raise HTTPException(status_code=403, detail="ITDR realm mismatch")
        observations = []
        try:
            for signal in signals:
                rows = await self.directory.observe(tenant, signal.user_id)
                if not isinstance(rows, list) or len(rows) != 1:
                    raise HTTPException(
                        status_code=503, detail="ITDR subject membership is unverified"
                    )
                self._fresh(rows[0], tenant, signal.user_id)
                observations.append(rows[0])
            for signal, snapshot in zip(signals, observations):
                self._fresh(snapshot, tenant, signal.user_id)
        except Exception as error:
            # No proposal subset is committed. Provider details/credentials never
            # enter the response or audit; rejection is separately durable.
            def reject():
                for signal in signals:
                    AuditLogger(self.db).log_entitlement_event(
                        "itdr_rejected",
                        None,
                        tenant,
                        actor,
                        subject_id=signal.user_id,
                        decision="deny",
                        reason="Subject directory verification failed",
                        changes={
                            "threat_type": signal.threat_type.value,
                            "effects_executed": [],
                        },
                    )

            self._commit(reject)
            code = (
                403
                if isinstance(error, HTTPException) and error.status_code == 403
                else 503
            )
            raise HTTPException(
                status_code=code, detail="ITDR subject membership is unverified"
            ) from error

        def record():
            results = []
            for signal, snapshot in zip(signals, observations):
                definition = get_response_for_threat(signal.threat_type)

                def outcome(action):
                    recorded = action == ResponseAction.LOG_ALERT
                    return ActionOutcome(
                        action=action.value,
                        status="recorded" if recorded else "blocked",
                        reason="Audit record only"
                        if recorded
                        else "Qualified action authorization, provider and effect verification unavailable",
                    )

                advisory = [outcome(a) for a in get_advisory_actions(definition)]
                enforcement = [outcome(a) for a in get_enforcement_actions(definition)]
                skipped = [
                    a.action for a in advisory + enforcement if a.status == "blocked"
                ]
                row = AuditLogger(self.db).log_entitlement_event(
                    "itdr_proposed",
                    None,
                    tenant,
                    actor,
                    subject_id=signal.user_id,
                    reason="Unverified threat assertion; response effects blocked",
                    changes={
                        "threat_type": signal.threat_type.value,
                        "severity": definition.severity.value,
                        "advisory_actions": [a.model_dump() for a in advisory],
                        "enforcement_actions": [a.model_dump() for a in enforcement],
                        "effects_executed": [],
                        "requires_human_approval": definition.requires_human_approval,
                    },
                    metadata={
                        "context": signal.context,
                        "signal_trust": "caller_assertion",
                        "directory_realm": snapshot.directory_realm,
                        "membership_observed_at": snapshot.observed_at,
                        "response_map_version": "itdr_proposal_v1",
                    },
                )
                results.append(
                    EnforcementResponse(
                        proposal_id=row.id,
                        tenant_id=tenant,
                        user_id=signal.user_id,
                        threat_type=signal.threat_type,
                        severity=definition.severity.value,
                        advisory_actions=advisory,
                        enforcement_actions=enforcement,
                        actions_recorded=["log_alert"],
                        actions_skipped=skipped,
                    )
                )
            for signal, snapshot in zip(signals, observations):
                self._fresh(snapshot, tenant, signal.user_id)
            return results

        return self._commit(record)
