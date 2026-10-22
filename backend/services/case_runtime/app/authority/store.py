"""Transactional proposal/approval reservations. This does not execute providers.

PostgreSQL owns application records. No in-memory authority, scheduler, fake
provider success or automatic retry after a potentially consumed reservation.
"""

from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import hashlib
import hmac
import json
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select, func, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.authority.contracts import canonical, digest, proposal_payload, canonical_uuid
from sg_core.action_identity import require_actor
from app.authority.models import (
    Case,
    CaseAccessGrant,
    ActionProposal,
    ApprovalRequest,
    ApprovalDecision,
    PolicyDecision,
    ActionClaim,
    ResourceFence,
    ActionAttempt,
    OutboxEvent,
)


class ActionAuthority:
    def __init__(self, engine, *, policy_version="action-policy-v1", enabled=False):
        self.engine = engine
        self.policy_version = policy_version
        self.enabled = enabled

    @contextmanager
    def transaction(self, request):
        actor = require_actor(request)
        if not self.enabled:
            raise HTTPException(503, "Action authority is unavailable")
        try:
            with (
                Session(self.engine, expire_on_commit=False) as session,
                session.begin(),
            ):
                role = session.execute(
                    text(
                        "SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user"
                    )
                ).one()
                if role.rolsuper or role.rolbypassrls:
                    raise HTTPException(503, "Action database role is unsafe")
                session.execute(
                    text("SELECT set_config('app.current_tenant_id',:tenant,true)"),
                    {"tenant": actor.tenant_id},
                )
                history = session.execute(
                    text(
                        "SELECT EXISTS(SELECT 1 FROM public.flyway_schema_history WHERE version IN ('018','18') AND script='V018__case_runtime_action_authority.sql' AND success)"
                    )
                ).scalar_one()
                if not history:
                    raise HTTPException(503, "Action schema migration unavailable")
                yield session, actor
        except HTTPException:
            raise
        except SQLAlchemyError:
            raise HTTPException(503, "Durable action authority unavailable") from None

    def now(self, session, actor):
        now = session.execute(select(func.clock_timestamp())).scalar_one()
        if actor.payload()["exp"] <= now.timestamp():
            raise HTTPException(401, "Identity expired before action admission")
        return now

    def case(self, s, actor, case_id, permission):
        row = s.execute(
            select(Case)
            .where(
                Case.tenant_id == UUID(actor.tenant_id),
                Case.id == UUID(canonical_uuid(case_id)),
            )
            .with_for_update()
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(404, "Case not found")
        now = self.now(s, actor)
        current_grant = self.grant(
            s, actor.tenant_id, case_id, actor.user_id, permission, now
        )
        now = self.now(s, actor)
        if current_grant.expires_at <= now:
            raise HTTPException(403, "Case action permission expired during admission")
        if row.status != "open" or row.policy_version != self.policy_version:
            raise HTTPException(409, "Case or policy revision is not active")
        return row, now

    def grant(self, s, tenant, case_id, subject, permission, now):
        value = s.execute(
            select(CaseAccessGrant)
            .where(
                CaseAccessGrant.tenant_id == UUID(tenant),
                CaseAccessGrant.case_id == UUID(case_id),
                CaseAccessGrant.subject_id == UUID(subject),
                CaseAccessGrant.permission == permission,
                CaseAccessGrant.expires_at > now,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if value is None:
            raise HTTPException(403, "Case action permission denied")
        return value

    def event(self, s, tenant, aggregate, kind, **payload):
        s.add(
            OutboxEvent(
                id=uuid4(),
                tenant_id=UUID(tenant),
                aggregate_id=aggregate,
                event_type=kind,
                payload=payload,
            )
        )

    def view(self, p, *, status="pending_approval"):
        return {
            "action_id": str(p.action_id),
            "proposal_id": str(p.id),
            "proposal_hash": p.proposal_hash,
            "proposal_revision": p.proposal_revision,
            "status": status,
            "execution_available": False,
        }

    def submit(self, request, case_id, body, request_key):
        canonical_uuid(request_key)
        # A known typed proposal contract is distinct from enabling its provider.
        # Other required tool bindings remain explicit restoration work.
        if (
            body.tool_id != "identity.lock_account"
            or body.tool_version != "source-preview-v1"
        ):
            raise HTTPException(503, "Typed action proposal contract is unavailable")
        if (
            len(body.targets) != 1
            or body.targets[0].kind != "identity.user"
            or set(body.parameters) != {"reason"}
            or not isinstance(body.parameters["reason"], str)
            or not 1 <= len(body.parameters["reason"]) <= 2048
        ):
            raise HTTPException(
                422, "Invalid identity lock proposal parameters or target"
            )
        with self.transaction(request) as (s, actor):
            case, now = self.case(s, actor, case_id, "propose")
            request_hash = digest(
                {
                    "body": body.model_dump(),
                    "case_id": case_id,
                    "proposed_by": actor.user_id,
                }
            )
            prior = s.execute(
                select(ActionProposal).where(
                    ActionProposal.tenant_id == UUID(actor.tenant_id),
                    ActionProposal.case_id == case.id,
                    ActionProposal.request_key == UUID(request_key),
                )
            ).scalar_one_or_none()
            if prior:
                if not hmac.compare_digest(prior.request_hash, request_hash):
                    raise HTTPException(
                        409, "Idempotency key already binds different content"
                    )
                return self.view(prior, status=self.status(s, prior, now, case))
            if not now.timestamp() < body.expires_at <= now.timestamp() + 3600:
                raise HTTPException(
                    422, "Proposal expiry must be current and at most one hour"
                )
            action_id, proposal_id = uuid4(), uuid4()
            try:
                payload = proposal_payload(
                    body,
                    tenant_id=actor.tenant_id,
                    case_id=case_id,
                    case_revision=case.revision,
                    plan_revision=case.plan_revision,
                    policy_version=self.policy_version,
                    action_id=str(action_id),
                    proposal_id=str(proposal_id),
                    actor_id=actor.user_id,
                )
            except ValueError:
                raise HTTPException(
                    422, "Bound proposal exceeds canonical limits"
                ) from None
            proposal_hash = digest(payload)
            p = ActionProposal(
                id=proposal_id,
                tenant_id=UUID(actor.tenant_id),
                case_id=case.id,
                action_id=action_id,
                proposal_revision=1,
                case_revision=case.revision,
                plan_revision=case.plan_revision,
                policy_version=self.policy_version,
                tool_id=body.tool_id,
                tool_version=body.tool_version,
                proposed_by=UUID(actor.user_id),
                request_key=UUID(request_key),
                request_hash=request_hash,
                proposal_hash=proposal_hash,
                canonical_payload=canonical(payload).decode(),
                expires_at=datetime.fromtimestamp(body.expires_at, timezone.utc),
            )
            s.add(p)
            s.flush()
            s.add(
                ApprovalRequest(
                    id=uuid4(),
                    tenant_id=p.tenant_id,
                    proposal_id=p.id,
                    proposal_hash=proposal_hash,
                )
            )
            s.add(
                PolicyDecision(
                    id=uuid4(),
                    tenant_id=p.tenant_id,
                    proposal_id=p.id,
                    actor_id=UUID(actor.user_id),
                    policy_version=self.policy_version,
                    proposal_hash=proposal_hash,
                    decision="approval_required",
                )
            )
            self.event(
                s,
                actor.tenant_id,
                proposal_id,
                "action.proposed",
                proposal_hash=proposal_hash,
            )
            return self.view(p)

    def live(self, s, actor, proposal_id, permission):
        p = s.execute(
            select(ActionProposal).where(
                ActionProposal.tenant_id == UUID(actor.tenant_id),
                ActionProposal.id == UUID(canonical_uuid(proposal_id)),
            )
        ).scalar_one_or_none()
        if p is None:
            raise HTTPException(404, "Proposal not found")
        case, now = self.case(s, actor, str(p.case_id), permission)
        if p.expires_at <= now:
            raise HTTPException(410, "Proposal expired")
        if (p.case_revision, p.plan_revision, p.policy_version) != (
            case.revision,
            case.plan_revision,
            case.policy_version,
        ):
            raise HTTPException(409, "Proposal revision is stale")
        try:
            payload = json.loads(p.canonical_payload)
            if (
                canonical(payload).decode() != p.canonical_payload
                or not hmac.compare_digest(digest(payload), p.proposal_hash)
                or payload["tenant_id"] != str(p.tenant_id)
                or payload["case_id"] != str(p.case_id)
                or payload["proposal_id"] != str(p.id)
                or payload["action_id"] != str(p.action_id)
                or payload["proposed_by"] != str(p.proposed_by)
                or payload["case_revision"] != p.case_revision
                or payload["plan_revision"] != p.plan_revision
                or payload["policy_version"] != p.policy_version
                or payload["tool_id"] != p.tool_id
                or payload["tool_version"] != p.tool_version
                or payload["expires_at"] != int(p.expires_at.timestamp())
            ):
                raise HTTPException(503, "Stored proposal integrity unavailable")
        except (ValueError, TypeError, KeyError, OverflowError):
            raise HTTPException(503, "Stored proposal integrity unavailable") from None
        return p, payload, now

    def latest_decision(self, s, p):
        return s.execute(
            select(ApprovalDecision)
            .where(
                ApprovalDecision.tenant_id == p.tenant_id,
                ApprovalDecision.proposal_id == p.id,
            )
            .order_by(ApprovalDecision.sequence.desc())
            .limit(1)
        ).scalar_one_or_none()

    def status(self, s, p, now, case=None):
        if p.expires_at <= now:
            return "expired"
        if case is not None and (
            p.case_revision,
            p.plan_revision,
            p.policy_version,
        ) != (case.revision, case.plan_revision, case.policy_version):
            return "stale"
        latest = self.latest_decision(s, p)
        if latest is None:
            return "pending_approval"
        if latest.decision != "approve":
            return {"reject": "rejected", "revoke": "revoked"}[latest.decision]
        if latest.expires_at <= now:
            return "approval_expired"
        grant = s.execute(
            select(CaseAccessGrant.id).where(
                CaseAccessGrant.tenant_id == p.tenant_id,
                CaseAccessGrant.case_id == p.case_id,
                CaseAccessGrant.subject_id == latest.decided_by,
                CaseAccessGrant.permission == "approve",
                CaseAccessGrant.expires_at > now,
            )
        ).first()
        return "approved" if grant else "approval_authority_revoked"

    def decide(self, request, proposal_id, body, *, case_id=None):
        with self.transaction(request) as (s, actor):
            p, payload, now = self.live(s, actor, proposal_id, "approve")
            if case_id is not None and str(p.case_id) != case_id:
                raise HTTPException(404, "Proposal not found")
            if str(p.proposed_by) == actor.user_id:
                raise HTTPException(403, "Separate approver required")
            if not hmac.compare_digest(body.proposal_hash, p.proposal_hash):
                raise HTTPException(409, "Approval proposal hash mismatch")
            prior = self.latest_decision(s, p)
            if (
                prior is not None
                and prior.decision == body.decision
                and prior.decided_by == UUID(actor.user_id)
                and prior.reason == body.reason
            ):
                return {
                    **self.view(p, status=self.status(s, p, now)),
                    "decision_id": str(prior.id),
                    "decision_sequence": prior.sequence,
                }
            if prior is not None and prior.decision in {"reject", "revoke"}:
                raise HTTPException(
                    409, "A rejected or revoked proposal requires a new proposal"
                )
            if body.decision == "revoke" and (
                prior is None or prior.decision != "approve"
            ):
                raise HTTPException(409, "Only an approval can be revoked")
            if prior is not None and body.decision != "revoke":
                raise HTTPException(
                    409, "Existing approval must be revoked before another decision"
                )
            if s.execute(
                select(ActionClaim.id).where(
                    ActionClaim.tenant_id == p.tenant_id,
                    ActionClaim.proposal_id == p.id,
                )
            ).first():
                raise HTTPException(
                    409,
                    "Reserved action requires reconciliation; approval cannot imply cancellation",
                )
            grant = self.grant(
                s, actor.tenant_id, str(p.case_id), actor.user_id, "approve", now
            )
            row = ApprovalDecision(
                id=uuid4(),
                tenant_id=p.tenant_id,
                proposal_id=p.id,
                proposal_hash=p.proposal_hash,
                sequence=1 if prior is None else prior.sequence + 1,
                decided_by=UUID(actor.user_id),
                decision=body.decision,
                reason=body.reason,
                expires_at=min(p.expires_at, grant.expires_at),
            )
            s.add(row)
            self.event(
                s,
                actor.tenant_id,
                p.id,
                "action.approval_decided",
                decision_id=str(row.id),
                proposal_hash=p.proposal_hash,
                decision=body.decision,
                sequence=row.sequence,
            )
            return {
                **self.view(
                    p,
                    status={
                        "approve": "approved",
                        "reject": "rejected",
                        "revoke": "revoked",
                    }[body.decision],
                ),
                "decision_id": str(row.id),
                "decision_sequence": row.sequence,
            }

    def inspect(self, request, proposal_id, *, case_id=None):
        with self.transaction(request) as (s, actor):
            p, payload, now = self.live(s, actor, proposal_id, "read")
            if case_id is not None and str(p.case_id) != case_id:
                raise HTTPException(404, "Proposal not found")
            status = self.status(s, p, now)
            return {**self.view(p, status=status), "proposal": payload}

    def reserve(self, request, proposal_id):
        """Internal durable reservation only; no API/provider execution is enabled.

        Domain ownership/provider admission must run again before any dispatcher
        can consume this reservation. A reservation is never an execution receipt.
        """
        with self.transaction(request) as (s, actor):
            p, payload, now = self.live(s, actor, proposal_id, "execute")
            decision = self.latest_decision(s, p)
            if (
                decision is None
                or decision.decision != "approve"
                or decision.expires_at <= now
            ):
                raise HTTPException(403, "Current exact approval required")
            if str(decision.decided_by) == actor.user_id:
                raise HTTPException(403, "Separate executor required")
            approver_grant = self.grant(
                s,
                actor.tenant_id,
                str(p.case_id),
                str(decision.decided_by),
                "approve",
                now,
            )
            if decision.proposal_hash != p.proposal_hash:
                raise HTTPException(409, "Approval binding mismatch")
            prior = s.execute(
                select(ActionClaim).where(
                    ActionClaim.tenant_id == p.tenant_id,
                    ActionClaim.action_id == p.action_id,
                )
            ).scalar_one_or_none()
            if prior:
                raise HTTPException(
                    409, "Existing action reservation requires reconciliation"
                )
            fences = {}
            for target in payload["targets"]:
                key = target["kind"] + ":" + target["resource_id"]
                s.execute(
                    insert(ResourceFence)
                    .values(tenant_id=p.tenant_id, resource_key=key, generation=1)
                    .on_conflict_do_nothing()
                )
                fence = s.execute(
                    select(ResourceFence)
                    .where(
                        ResourceFence.tenant_id == p.tenant_id,
                        ResourceFence.resource_key == key,
                    )
                    .with_for_update()
                ).scalar_one()
                prior_resource = s.execute(
                    select(ActionClaim.id).where(
                        ActionClaim.tenant_id == p.tenant_id,
                        ActionClaim.resource_fences.has_key(key),
                    )
                ).first()
                if prior_resource:
                    raise HTTPException(
                        409,
                        "Resource requires authoritative reconciliation before another action",
                    )
                fences[key] = fence.generation
            now = self.now(s, actor)
            self.grant(
                s, actor.tenant_id, str(p.case_id), actor.user_id, "execute", now
            )
            if (
                p.expires_at <= now
                or decision.expires_at <= now
                or approver_grant.expires_at <= now
            ):
                raise HTTPException(403, "Approval expired during resource admission")
            lease = min(
                p.expires_at,
                decision.expires_at,
                now + timedelta(seconds=30),
                datetime.fromtimestamp(actor.payload()["exp"], timezone.utc),
            )
            if lease <= now + timedelta(seconds=1):
                raise HTTPException(401, "Insufficient current authorization lifetime")
            claim = ActionClaim(
                id=uuid4(),
                tenant_id=p.tenant_id,
                proposal_id=p.id,
                action_id=p.action_id,
                actor_id=UUID(actor.user_id),
                approval_id=decision.id,
                proposal_hash=p.proposal_hash,
                idempotency_key=hashlib.sha256(
                    (actor.tenant_id + ":" + str(p.action_id)).encode()
                ).hexdigest(),
                resource_fences=fences,
                expires_at=lease,
            )
            s.add(claim)
            s.flush()
            s.add(
                ActionAttempt(
                    id=uuid4(),
                    tenant_id=p.tenant_id,
                    claim_id=claim.id,
                    attempt_number=1,
                )
            )
            self.event(
                s,
                actor.tenant_id,
                p.id,
                "action.reserved",
                claim_id=str(claim.id),
                proposal_hash=p.proposal_hash,
            )
            return {
                "claim_id": str(claim.id),
                "action_id": str(p.action_id),
                "idempotency_key": claim.idempotency_key,
                "status": "reserved",
                "execution_available": False,
                "resource_fences": fences,
            }
