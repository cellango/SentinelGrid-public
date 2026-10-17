"""Deterministic governance over the explicit IAM store. Models grant no authority."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import and_, or_, true
from app.models.audit_campaign import AuditCampaign
from app.models.certification import Certification
from app.models.certification_history import CertificationHistory
from app.models.entitlement import Entitlement
from app.schemas.governance import (
    CampaignCreate,
    CampaignResponse,
    CertificationResponse,
)
from app.services.audit_logger import AuditLogger
from app.services.redis_cache import cache

CONTRACT = "iam_governance_v1"
ADMIN_ROLES = {"TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"}
MAX_CERTIFICATIONS = 500
WIRE_STATUS = {
    "draft": "pending",
    "active": "in_progress",
    "completed": "completed",
    "cancelled": "cancelled",
}


def fail(code, message):
    raise HTTPException(status_code=code, detail=message)


def actor(context):
    try:
        return UUID(str(context.user_id))
    except (ValueError, TypeError):
        fail(401, "A verified user UUID is required")


def is_admin(context):
    return bool(ADMIN_ROLES.intersection(role.upper() for role in context.roles))


def admin(context):
    user = actor(context)
    if not is_admin(context):
        fail(403, "Governance administrator role required")
    return user


@contextmanager
def change(db):
    try:
        yield
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Governance change could not be committed; inspect state before retry",
        ) from exc


def config(row):
    if (
        row.campaign_type != "on_demand"
        or not isinstance(row.scope, dict)
        or set(row.scope) != {"api_contract", "subject_type", "entitlement_patterns"}
        or row.scope.get("api_contract") != CONTRACT
        or row.scope.get("subject_type") != "user"
        or not isinstance(row.review_config, dict)
        or set(row.review_config) != {"reviewer_type", "auto_revoke_days"}
        or not isinstance(row.schedule, dict)
        or set(row.schedule) != {"start_date", "end_date"}
        or row.status not in WIRE_STATUS
    ):
        fail(409, "Legacy campaign needs explicit contract reconciliation")
    try:
        return CampaignCreate(
            tenant_id=row.tenant_id,
            name=row.name,
            description=row.description,
            **row.schedule,
            **row.review_config,
            entitlement_patterns=row.scope["entitlement_patterns"],
        )
    except (ValidationError, TypeError, ValueError):
        fail(409, "Campaign configuration is invalid or unsupported")


def campaign_response(row):
    data = config(row)
    return CampaignResponse(
        id=row.id,
        **data.model_dump(exclude={"entitlement_patterns"}),
        status=WIRE_STATUS[row.status],
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def locked_campaign(db, identity, tenant):
    row = (
        db.query(AuditCampaign)
        .filter(AuditCampaign.id == identity, AuditCampaign.tenant_id == tenant)
        .populate_existing()
        .with_for_update()
        .first()
    )
    if row is None:
        fail(404, "Campaign not found")
    config(row)
    return row


def write_config(row, data):
    row.name, row.description = data.name, data.description
    row.scope = {
        "api_contract": CONTRACT,
        "subject_type": "user",
        "entitlement_patterns": data.entitlement_patterns,
    }
    row.review_config = {
        "reviewer_type": data.reviewer_type,
        "auto_revoke_days": data.auto_revoke_days,
    }
    row.schedule = {
        "start_date": data.start_date.isoformat(),
        "end_date": data.end_date.isoformat(),
    }


def campaign_event(db, row, user, event, **changes):
    AuditLogger(db).log_entitlement_event(
        event,
        None,
        row.tenant_id,
        user,
        campaign_id=row.id,
        changes={"campaign_id": str(row.id), **changes},
    )


def create_campaign(db, context, data):
    user = admin(context)
    if data.tenant_id != context.tenant_id:
        fail(403, "Access denied: Tenant mismatch")
    with change(db):
        row = AuditCampaign(
            tenant_id=context.tenant_id,
            campaign_type="on_demand",
            status="draft",
            created_by=user,
        )
        write_config(row, data)
        db.add(row)
        db.flush()
        campaign_event(db, row, user, "campaign_created", config=data.model_dump())
        response = campaign_response(row)
    return response


def update_campaign(db, context, identity, update):
    user = admin(context)
    with change(db):
        row = locked_campaign(db, identity, context.tenant_id)
        before = campaign_response(row).model_dump()
        values = update.model_dump(exclude_unset=True)
        desired = values.pop("status", None)
        if row.status not in {"draft", "active"}:
            fail(409, "Campaign is closed")
        if row.status == "active" and (values or desired != "cancelled"):
            fail(
                409,
                "Started campaign configuration is immutable; only cancellation is supported",
            )
        if desired == "cancelled":
            if values:
                fail(409, "Cancellation cannot also change campaign configuration")
            row.status = "cancelled"
            row.completed_at = datetime.now(timezone.utc)
        else:
            data = config(row).model_dump()
            data.update(values)
            try:
                write_config(row, CampaignCreate.model_validate(data))
            except ValidationError:
                fail(422, "Campaign dates or configuration are invalid")
        db.flush()
        response = campaign_response(row)
        campaign_event(
            db,
            row,
            user,
            "campaign_updated",
            before=before,
            after=response.model_dump(),
        )
    return response


def grant_snapshot(row):
    return dict(
        tenant_id=str(row.tenant_id),
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        action=row.action,
        granted_to_type=row.granted_to_type,
        granted_to_id=str(row.granted_to_id),
        granted_by=str(row.granted_by),
        expires_at=row.expires_at.astimezone(timezone.utc).isoformat()
        if row.expires_at
        else None,
    )


def cert_response(cert, grant):
    outcome = cert.status
    if (
        outcome == "approved"
        and (cert.metadata_json or {}).get("review_outcome") == "retained"
    ):
        outcome = "retained"
    return CertificationResponse(
        id=cert.id,
        campaign_id=cert.campaign_id,
        entitlement_id=cert.entitlement_id,
        user_id=grant.granted_to_id,
        reviewer_id=cert.certifier_id,
        review_status=outcome,
        review_date=cert.decision_date,
        comments=cert.justification,
        created_at=cert.created_at,
        updated_at=cert.updated_at,
    )


def start_campaign(db, context, identity):
    user = admin(context)
    with change(db):
        row = locked_campaign(db, identity, context.tenant_id)
        data = config(row)
        now = datetime.now(timezone.utc)
        if row.status != "draft":
            fail(400, f"Cannot start campaign with status '{WIRE_STATUS[row.status]}'")
        if not data.start_date <= now < data.end_date:
            fail(409, "Campaign is outside its start/end window")
        if data.reviewer_type == "manager":
            fail(409, "Verified manager assignment is not configured")
        query = db.query(Entitlement).filter(
            Entitlement.tenant_id == context.tenant_id,
            Entitlement.status == "active",
            Entitlement.granted_to_type == "user",
            or_(Entitlement.expires_at.is_(None), Entitlement.expires_at > now),
        )
        if data.entitlement_patterns:
            clauses = []
            for pattern in data.entitlement_patterns:
                terms = [
                    column == part
                    for column, part in zip(
                        (
                            Entitlement.resource_type,
                            Entitlement.resource_id,
                            Entitlement.action,
                        ),
                        pattern.split(":"),
                    )
                    if part != "*"
                ]
                clauses.append(and_(*terms) if terms else true())
            query = query.filter(or_(*clauses))
        grants = (
            query.order_by(Entitlement.id)
            .limit(MAX_CERTIFICATIONS + 1)
            .populate_existing()
            .with_for_update()
            .all()
        )
        if len(grants) > MAX_CERTIFICATIONS:
            fail(409, "Campaign scope exceeds the bounded review size")
        if data.reviewer_type == "admin" and any(
            g.granted_to_id == user for g in grants
        ):
            fail(
                409,
                "Admin review requires an independent administrator for every selected grant",
            )
        for grant in grants:
            cert = Certification(
                campaign_id=row.id,
                entitlement_id=grant.id,
                certifier_type=data.reviewer_type,
                certifier_id=grant.granted_to_id
                if data.reviewer_type == "self"
                else user,
                status="pending",
                deadline=data.end_date,
                metadata_json={
                    "api_contract": CONTRACT,
                    "grant_snapshot": grant_snapshot(grant),
                },
            )
            db.add(cert)
        row.status = "active"
        row.started_at = now
        row.statistics = {"selected": len(grants)}
        db.flush()
        campaign_event(
            db,
            row,
            user,
            "campaign_started",
            selected_grants=[str(g.id) for g in grants],
            reviewer_type=data.reviewer_type,
        )
        response = campaign_response(row)
    return response


def cert_query(db, tenant):
    return (
        db.query(Certification)
        .join(AuditCampaign, Certification.campaign_id == AuditCampaign.id)
        .join(Entitlement, Certification.entitlement_id == Entitlement.id)
        .filter(AuditCampaign.tenant_id == tenant, Entitlement.tenant_id == tenant)
    )


def locked_grants(db, tenant, certs):
    ids = {c.entitlement_id for c in certs}
    if not ids:
        return {}
    rows = (
        db.query(Entitlement)
        .filter(Entitlement.id.in_(ids), Entitlement.tenant_id == tenant)
        .order_by(Entitlement.id)
        .populate_existing()
        .with_for_update()
        .all()
    )
    if len(rows) != len(ids):
        fail(409, "A certification grant is unavailable")
    return {g.id: g for g in rows}


def validate_target(cert, grant, campaign):
    data = config(campaign)
    meta = cert.metadata_json or {}
    if (
        meta.get("api_contract") != CONTRACT
        or meta.get("grant_snapshot") != grant_snapshot(grant)
        or grant.granted_to_type != "user"
        or cert.certifier_type != data.reviewer_type
    ):
        fail(409, "Certification target or contract changed; reconcile before deciding")
    if cert.certifier_type == "self" and cert.certifier_id != grant.granted_to_id:
        fail(409, "Self reviewer differs from the grant beneficiary")


def validate_cert(cert, grant, campaign, context, *, automatic=False):
    if campaign.status != "active" or cert.status != "pending":
        fail(409, "Certification or campaign is no longer active")
    validate_target(cert, grant, campaign)
    if automatic:
        return
    user = actor(context)
    if cert.certifier_id != user:
        fail(403, "You are not authorized to certify this entitlement")
    if cert.certifier_type == "self":
        if grant.granted_to_id != user:
            fail(403, "Self certification requires the grant beneficiary")
    elif cert.certifier_type == "admin":
        admin(context)
        if grant.granted_to_id == user:
            fail(403, "An independent administrator is required")
    else:
        fail(409, "Reviewer assignment is unsupported")


def decide(db, cert, grant, campaign, user, decision, comments):
    now = datetime.now(timezone.utc)
    if decision != "revoked" and (
        grant.status != "active"
        or (grant.expires_at is not None and grant.expires_at <= now)
        or cert.deadline <= now
    ):
        fail(409, "Inactive, expired or overdue access cannot be retained or approved")
    old = cert.status
    old_grant = grant.status
    cert.status = "revoked" if decision == "revoked" else "approved"
    cert.decision = "revoke" if decision == "revoked" else "approve"
    cert.justification, cert.decision_date = comments, now
    cert.metadata_json = {**cert.metadata_json, "review_outcome": decision}
    if decision == "revoked":
        grant.status = "revoked"
    db.add(
        CertificationHistory(
            certification_id=cert.id,
            entitlement_id=grant.id,
            previous_status=old,
            new_status=cert.status,
            decision=cert.decision,
            changed_by=user,
            reason=comments,
        )
    )
    AuditLogger(db).log_entitlement_event(
        "certified",
        grant.id,
        campaign.tenant_id,
        user,
        subject_id=grant.granted_to_id,
        campaign_id=campaign.id,
        certification_id=cert.id,
        changes={
            "review_status": {"old": old, "new": decision},
            "grant_status": {"old": old_grant, "new": grant.status},
            "target": grant_snapshot(grant),
        },
        reason=comments,
    )
    if old_grant != grant.status:
        AuditLogger(db).log_entitlement_event(
            "revoked",
            grant.id,
            campaign.tenant_id,
            user,
            subject_id=grant.granted_to_id,
            campaign_id=campaign.id,
            certification_id=cert.id,
            changes={
                "status": {"old": old_grant, "new": grant.status},
                "target": grant_snapshot(grant),
            },
            reason=comments,
        )


def certify(db, context, identities, decision, comments, *, bulk=False):
    user = actor(context)
    if decision not in {"approved", "retained", "revoked"}:
        fail(422, "Unsupported certification decision")
    if (
        not identities
        or len(identities) > MAX_CERTIFICATIONS
        or len(set(identities)) != len(identities)
    ):
        fail(422, "Certification IDs must be nonempty, distinct and bounded")
    with change(db):
        query = cert_query(db, context.tenant_id).filter(
            Certification.id.in_(identities)
        )
        if bulk:
            query = query.filter(
                Certification.certifier_id == user, Certification.status == "pending"
            )
        initial = query.all()
        if len(initial) != len(identities):
            fail(
                400 if bulk else 404,
                "Some certifications not found or already completed"
                if bulk
                else "Certification not found",
            )
        # All paths lock campaigns, certifications and grants in that order.
        campaigns = {
            identity: locked_campaign(db, identity, context.tenant_id)
            for identity in sorted({c.campaign_id for c in initial}, key=str)
        }
        certs = (
            query.order_by(Certification.id)
            .populate_existing()
            .with_for_update(of=Certification)
            .all()
        )
        if len(certs) != len(identities):
            fail(400, "Some certifications not found or already completed")
        grants = locked_grants(db, context.tenant_id, certs)
        for cert in certs:
            validate_cert(
                cert, grants[cert.entitlement_id], campaigns[cert.campaign_id], context
            )
        for cert in certs:
            decide(
                db,
                cert,
                grants[cert.entitlement_id],
                campaigns[cert.campaign_id],
                user,
                decision,
                comments,
            )
        db.flush()
        responses = [cert_response(cert, grants[cert.entitlement_id]) for cert in certs]
    if decision == "revoked":
        for response in responses:
            cache.invalidate_entitlement(
                str(response.entitlement_id), str(context.tenant_id)
            )
    return (
        {"certified_count": len(responses), "decision": decision}
        if bulk
        else responses[0]
    )


def complete_campaign(db, context, identity, auto_revoke):
    user = admin(context)
    with change(db):
        row = locked_campaign(db, identity, context.tenant_id)
        data = config(row)
        if row.status != "active":
            fail(
                400, f"Cannot complete campaign with status '{WIRE_STATUS[row.status]}'"
            )
        certs = (
            cert_query(db, context.tenant_id)
            .filter(Certification.campaign_id == row.id)
            .order_by(Certification.id)
            .limit(MAX_CERTIFICATIONS + 1)
            .populate_existing()
            .with_for_update(of=Certification)
            .all()
        )
        if len(certs) > MAX_CERTIFICATIONS or len(certs) != (row.statistics or {}).get(
            "selected"
        ):
            fail(409, "Certification set changed; reconcile before completion")
        grants = locked_grants(db, context.tenant_id, certs)
        for cert in certs:
            validate_target(cert, grants[cert.entitlement_id], row)
            if cert.status not in {"pending", "approved", "revoked"}:
                fail(409, "Unresolved legacy certification status")
        pending = [cert for cert in certs if cert.status == "pending"]
        if pending:
            if not auto_revoke or data.auto_revoke_days is None:
                fail(
                    409,
                    "Pending certifications require review or configured revocation",
                )
            if datetime.now(timezone.utc) < data.end_date + timedelta(
                days=data.auto_revoke_days
            ):
                fail(409, "Automatic revocation grace period has not elapsed")
            for cert in pending:
                validate_cert(
                    cert, grants[cert.entitlement_id], row, context, automatic=True
                )
            for cert in pending:
                decide(
                    db,
                    cert,
                    grants[cert.entitlement_id],
                    row,
                    user,
                    "revoked",
                    "Uncertified after campaign grace period",
                )
        row.status = "completed"
        row.completed_at = datetime.now(timezone.utc)
        row.statistics = {**(row.statistics or {}), "auto_revoked": len(pending)}
        db.flush()
        campaign_event(db, row, user, "campaign_completed", auto_revoked=len(pending))
        response = campaign_response(row)
        revoked_ids = [cert.entitlement_id for cert in pending]
    for identity in revoked_ids:
        cache.invalidate_entitlement(str(identity), str(context.tenant_id))
    return response
