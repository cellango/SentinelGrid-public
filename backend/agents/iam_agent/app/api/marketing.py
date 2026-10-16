"""Marketing analytics endpoints for funnel tracking and internal reporting."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.security import SecurityService
from sg_core.service_security import verify_internal_service_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/marketing", tags=["marketing"])
internal_router = APIRouter(prefix="/internal/iam/marketing", tags=["marketing-internal"])

TRACKED_FUNNEL_EVENTS = {
    "marketing_cta_click",
    "marketing_nav_click",
    "marketing_pricing_click",
    "marketing_demo_submit",
    "signup_started",
    "signup_lead_created",
    "signup_payment_viewed",
    "signup_payment_started",
    "signup_payment_succeeded",
    "onboarding_started",
    "onboarding_step_viewed",
    "onboarding_step_completed",
    "onboarding_step_skipped",
    "onboarding_core_connectors_ready",
    "onboarding_first_value_ready",
    "onboarding_completed",
    "onboarding_cta_click",
    "onboarding_banner_dismissed",
}


def verify_internal_token(
    authorization: Optional[str] = Header(None),
    x_internal_service_token: Optional[str] = Header(None, alias="X-Internal-Service-Token"),
) -> bool:
    """Verify the internal service token for service-to-service analytics access."""
    verify_internal_service_token(
        settings.INTERNAL_SERVICE_TOKEN,
        authorization=authorization,
        x_internal_service_token=x_internal_service_token,
        missing_detail="Missing authorization header",
        invalid_detail="Invalid internal service token",
    )
    return True


class MarketingEventRequest(BaseModel):
    """Analytics event payload persisted for funnel reporting."""

    event: str
    properties: dict[str, Any] = Field(default_factory=dict)
    page_path: Optional[str] = None
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    occurred_at: Optional[datetime] = None
    anonymous_id: Optional[str] = None
    session_id: Optional[str] = None
    lead_id: Optional[str] = None

    @field_validator("event")
    @classmethod
    def validate_event(cls, value: str) -> str:
        event_name = value.strip()
        if not event_name:
            raise ValueError("Event is required")
        if len(event_name) > 100:
            raise ValueError("Event is too long")
        return event_name


def _coerce_marketing_event_time(occurred_at: Optional[datetime]) -> datetime:
    if occurred_at is None:
        return datetime.now(timezone.utc)
    if occurred_at.tzinfo is None:
        return occurred_at.replace(tzinfo=timezone.utc)
    return occurred_at.astimezone(timezone.utc)


def _safe_text(value: Any, max_length: int = 255) -> Optional[str]:
    if value is None:
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    return SecurityService.sanitize_input(text_value)[:max_length]


def _extract_plan_tier(properties: dict[str, Any]) -> Optional[str]:
    for key in ("plan_tier", "planTier", "plan"):
        value = properties.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_demo_recommended_path(properties: dict[str, Any]) -> str:
    for key in ("recommended_path", "recommendedPath"):
        value = properties.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "unknown"


def _extract_demo_guided_review_reasons(properties: dict[str, Any]) -> list[str]:
    for key in ("guided_review_reasons", "guidedReviewReasons"):
        value = properties.get(key)
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
    return []


def _build_demo_qualification_payload(rows: list[Any]) -> dict[str, Any]:
    summary = {
        "total_demo_requests": 0,
        "standard_launch_path": 0,
        "guided_review": 0,
        "partner_motion": 0,
        "unknown": 0,
    }
    guided_review_reason_counts: dict[str, int] = {}
    recent_demo_requests: list[dict[str, Any]] = []

    for row in rows:
        properties = row[4] if isinstance(row[4], dict) else {}
        recommended_path = _extract_demo_recommended_path(properties)
        motion = properties.get("motion") if isinstance(properties.get("motion"), str) else "unknown"
        guided_review_reasons = _extract_demo_guided_review_reasons(properties)

        summary["total_demo_requests"] += 1
        if recommended_path == "standard_launch_path":
            summary["standard_launch_path"] += 1
        elif recommended_path == "guided_review":
            summary["guided_review"] += 1
        else:
            summary["unknown"] += 1

        if motion == "partner":
            summary["partner_motion"] += 1

        for reason in guided_review_reasons:
            guided_review_reason_counts[reason] = guided_review_reason_counts.get(reason, 0) + 1

        recent_demo_requests.append(
            {
                "source": row[0],
                "lead_id": row[1],
                "plan_tier": row[2],
                "occurred_at": row[3].isoformat() if hasattr(row[3], "isoformat") else str(row[3]),
                "recommended_path": recommended_path,
                "motion": motion,
                "guided_review_reasons": guided_review_reasons,
            }
        )

    top_guided_review_reasons = [
        {"reason": reason, "count": count}
        for reason, count in sorted(
            guided_review_reason_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:6]
    ]

    return {
        "summary": summary,
        "top_guided_review_reasons": top_guided_review_reasons,
        "recent_demo_requests": recent_demo_requests,
    }


def _calculate_conversion_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


def _round_optional(value: Any, digits: int = 1) -> Optional[float]:
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _ensure_marketing_event_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS marketing_event_log (
                id UUID PRIMARY KEY,
                event_name VARCHAR(100) NOT NULL,
                event_source VARCHAR(255),
                session_id VARCHAR(100),
                anonymous_id VARCHAR(100),
                lead_id VARCHAR(64),
                plan_tier VARCHAR(64),
                page_path TEXT,
                referrer TEXT,
                user_agent TEXT,
                event_properties JSONB,
                occurred_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_marketing_event_log_occurred_at "
            "ON marketing_event_log (occurred_at)"
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_marketing_event_log_event_name "
            "ON marketing_event_log (event_name)"
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_marketing_event_log_source "
            "ON marketing_event_log (event_source)"
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_marketing_event_log_plan_tier "
            "ON marketing_event_log (plan_tier)"
        )
    )


def _build_activation_cohort_payload(rows: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "segment": row[0] or "unknown",
            "onboarding_started": row[1] or 0,
            "core_connectors_ready": row[2] or 0,
            "first_value_ready": row[3] or 0,
            "onboarding_completed": row[4] or 0,
            "start_to_core_rate": _calculate_conversion_rate(row[2] or 0, row[1] or 0),
            "start_to_first_value_rate": _calculate_conversion_rate(row[3] or 0, row[1] or 0),
            "start_to_complete_rate": _calculate_conversion_rate(row[4] or 0, row[1] or 0),
            "avg_hours_to_core": _round_optional(row[5]),
            "avg_hours_to_first_value": _round_optional(row[6]),
            "avg_hours_to_completion": _round_optional(row[7]),
        }
        for row in rows
    ]


def _build_funnel_summary_payload(
    *,
    counts_row: Any,
    daily_rows: list[Any],
    source_rows: list[Any],
    recent_rows: list[Any],
    demo_request_rows: list[Any],
    activation_counts_row: Any,
    activation_daily_rows: list[Any],
    activation_step_rows: list[Any],
    activation_recent_rows: list[Any],
    activation_plan_rows: list[Any],
    activation_identity_rows: list[Any],
    activation_trust_rows: list[Any],
    activation_billing_rows: list[Any],
    days: int,
) -> dict[str, Any]:
    cta_clicks = counts_row[0] or 0
    signup_started = counts_row[1] or 0
    leads_created = counts_row[2] or 0
    payment_started = counts_row[3] or 0
    payment_succeeded = counts_row[4] or 0
    demo_requests = counts_row[5] or 0
    onboarding_started = counts_row[6] or 0
    onboarding_completed = counts_row[7] or 0

    activation_started = activation_counts_row[0] or 0
    core_connectors_ready = activation_counts_row[1] or 0
    first_value_ready = activation_counts_row[2] or 0
    activation_completed = activation_counts_row[3] or 0
    avg_hours_to_core_connectors = _round_optional(activation_counts_row[4])
    avg_hours_to_first_value = _round_optional(activation_counts_row[5])
    avg_hours_to_completion = _round_optional(activation_counts_row[6])

    return {
        "window_days": days,
        "summary": {
            "cta_clicks": cta_clicks,
            "signup_started": signup_started,
            "leads_created": leads_created,
            "payment_started": payment_started,
            "payment_succeeded": payment_succeeded,
            "demo_requests": demo_requests,
            "onboarding_started": onboarding_started,
            "onboarding_completed": onboarding_completed,
        },
        "conversion_rates": {
            "cta_to_signup": _calculate_conversion_rate(signup_started, cta_clicks),
            "signup_to_lead": _calculate_conversion_rate(leads_created, signup_started),
            "lead_to_payment": _calculate_conversion_rate(payment_started, leads_created),
            "payment_to_success": _calculate_conversion_rate(payment_succeeded, payment_started),
            "onboarding_start_to_complete": _calculate_conversion_rate(
                onboarding_completed,
                onboarding_started,
            ),
        },
        "daily_series": [
            {
                "day": row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0]),
                "cta_clicks": row[1] or 0,
                "signup_started": row[2] or 0,
                "leads_created": row[3] or 0,
                "payment_started": row[4] or 0,
                "payment_succeeded": row[5] or 0,
                "demo_requests": row[6] or 0,
            }
            for row in daily_rows
        ],
        "top_sources": [
            {
                "source": row[0] or "unknown",
                "count": row[1] or 0,
            }
            for row in source_rows
        ],
        "recent_events": [
            {
                "event": row[0],
                "source": row[1],
                "lead_id": row[2],
                "plan_tier": row[3],
                "page_path": row[4],
                "occurred_at": row[5].isoformat() if hasattr(row[5], "isoformat") else str(row[5]),
                "properties": row[6] if isinstance(row[6], dict) else {},
            }
            for row in recent_rows
        ],
        "demo_qualification": _build_demo_qualification_payload(demo_request_rows),
        "activation": {
            "summary": {
                "onboarding_started": activation_started,
                "core_connectors_ready": core_connectors_ready,
                "first_value_ready": first_value_ready,
                "onboarding_completed": activation_completed,
            },
            "conversion_rates": {
                "start_to_core_connectors": _calculate_conversion_rate(
                    core_connectors_ready,
                    activation_started,
                ),
                "start_to_first_value": _calculate_conversion_rate(
                    first_value_ready,
                    activation_started,
                ),
                "first_value_to_complete": _calculate_conversion_rate(
                    activation_completed,
                    first_value_ready,
                ),
                "start_to_complete": _calculate_conversion_rate(
                    activation_completed,
                    activation_started,
                ),
            },
            "timings_hours": {
                "avg_to_core_connectors": avg_hours_to_core_connectors,
                "avg_to_first_value": avg_hours_to_first_value,
                "avg_to_completion": avg_hours_to_completion,
            },
            "daily_series": [
                {
                    "day": row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0]),
                    "onboarding_started": row[1] or 0,
                    "core_connectors_ready": row[2] or 0,
                    "first_value_ready": row[3] or 0,
                    "onboarding_completed": row[4] or 0,
                }
                for row in activation_daily_rows
            ],
            "step_breakdown": [
                {
                    "step_id": row[0] or "unknown",
                    "viewed": row[1] or 0,
                    "completed": row[2] or 0,
                    "skipped": row[3] or 0,
                    "completion_rate": _calculate_conversion_rate(row[2] or 0, row[1] or 0),
                    "skip_rate": _calculate_conversion_rate(row[3] or 0, row[1] or 0),
                }
                for row in activation_step_rows
            ],
            "recent_events": [
                {
                    "event": row[0],
                    "step_id": row[1],
                    "source": row[2],
                    "plan_tier": row[3],
                    "occurred_at": row[4].isoformat() if hasattr(row[4], "isoformat") else str(row[4]),
                    "properties": row[5] if isinstance(row[5], dict) else {},
                }
                for row in activation_recent_rows
            ],
            "cohorts": {
                "plan_tiers": _build_activation_cohort_payload(activation_plan_rows),
                "identity_providers": _build_activation_cohort_payload(activation_identity_rows),
                "trust_motions": _build_activation_cohort_payload(activation_trust_rows),
                "billing_periods": _build_activation_cohort_payload(activation_billing_rows),
            },
        },
    }


@router.post("/events")
async def ingest_marketing_event(request: MarketingEventRequest, http_request: Request):
    """Persist marketing and activation analytics events for internal reporting."""
    if request.event not in TRACKED_FUNNEL_EVENTS:
        return {"success": True, "ignored": True}

    if not settings.DB_URL:
        raise HTTPException(status_code=500, detail="Database not configured")

    occurred_at = _coerce_marketing_event_time(request.occurred_at)
    event_properties = dict(request.properties or {})
    event_source = _safe_text(event_properties.get("source"), max_length=255)
    plan_tier = _extract_plan_tier(event_properties)
    lead_id = request.lead_id or _safe_text(event_properties.get("lead_id"), max_length=64)
    page_path = _safe_text(request.page_path, max_length=1000)
    referrer = _safe_text(request.referrer, max_length=1000)
    user_agent = _safe_text(request.user_agent or http_request.headers.get("user-agent"), max_length=1000)

    engine = create_engine(settings.DB_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        _ensure_marketing_event_table(db)
        db.execute(
            text(
                """
                INSERT INTO marketing_event_log (
                    id, event_name, event_source, session_id, anonymous_id, lead_id,
                    plan_tier, page_path, referrer, user_agent, event_properties, occurred_at
                )
                VALUES (
                    :id, :event_name, :event_source, :session_id, :anonymous_id, :lead_id,
                    :plan_tier, :page_path, :referrer, :user_agent, CAST(:event_properties AS jsonb), :occurred_at
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "event_name": request.event,
                "event_source": event_source,
                "session_id": _safe_text(request.session_id, max_length=100),
                "anonymous_id": _safe_text(request.anonymous_id, max_length=100),
                "lead_id": lead_id,
                "plan_tier": _safe_text(plan_tier, max_length=64),
                "page_path": page_path,
                "referrer": referrer,
                "user_agent": user_agent,
                "event_properties": json.dumps(event_properties),
                "occurred_at": occurred_at,
            },
        )
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.error("Error ingesting marketing event: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to persist marketing event")
    finally:
        db.close()


@internal_router.get("/funnel/summary")
async def get_marketing_funnel_summary(
    days: int = Query(30, ge=1, le=90),
    _verified: bool = Depends(verify_internal_token),
):
    """Return a compact internal marketing and signup funnel summary."""
    _ = _verified
    if not settings.DB_URL:
        raise HTTPException(status_code=500, detail="Database not configured")

    since = datetime.now(timezone.utc) - timedelta(days=days)
    engine = create_engine(settings.DB_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        _ensure_marketing_event_table(db)

        counts_row = db.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE event_name = 'marketing_cta_click') AS cta_clicks,
                    COUNT(*) FILTER (WHERE event_name = 'signup_started') AS signup_started,
                    COUNT(*) FILTER (WHERE event_name = 'signup_lead_created') AS leads_created,
                    COUNT(*) FILTER (WHERE event_name = 'signup_payment_started') AS payment_started,
                    COUNT(*) FILTER (WHERE event_name = 'signup_payment_succeeded') AS payment_succeeded,
                    COUNT(*) FILTER (
                        WHERE event_name = 'marketing_demo_submit'
                          AND COALESCE(event_properties->>'result', 'success') = 'success'
                    ) AS demo_requests,
                    COUNT(*) FILTER (WHERE event_name = 'onboarding_started') AS onboarding_started,
                    COUNT(*) FILTER (WHERE event_name = 'onboarding_completed') AS onboarding_completed
                FROM marketing_event_log
                WHERE occurred_at >= :since
                """
            ),
            {"since": since},
        ).fetchone()

        daily_rows = db.execute(
            text(
                """
                SELECT
                    DATE(occurred_at) AS day,
                    COUNT(*) FILTER (WHERE event_name = 'marketing_cta_click') AS cta_clicks,
                    COUNT(*) FILTER (WHERE event_name = 'signup_started') AS signup_started,
                    COUNT(*) FILTER (WHERE event_name = 'signup_lead_created') AS leads_created,
                    COUNT(*) FILTER (WHERE event_name = 'signup_payment_started') AS payment_started,
                    COUNT(*) FILTER (WHERE event_name = 'signup_payment_succeeded') AS payment_succeeded,
                    COUNT(*) FILTER (
                        WHERE event_name = 'marketing_demo_submit'
                          AND COALESCE(event_properties->>'result', 'success') = 'success'
                    ) AS demo_requests
                FROM marketing_event_log
                WHERE occurred_at >= :since
                GROUP BY DATE(occurred_at)
                ORDER BY day ASC
                """
            ),
            {"since": since},
        ).fetchall()

        source_rows = db.execute(
            text(
                """
                SELECT COALESCE(event_source, 'unknown') AS source, COUNT(*) AS count
                FROM marketing_event_log
                WHERE occurred_at >= :since
                  AND event_name IN (
                    'marketing_cta_click',
                    'marketing_pricing_click',
                    'marketing_demo_submit',
                    'signup_started',
                    'signup_lead_created',
                    'signup_payment_started',
                    'signup_payment_succeeded'
                  )
                GROUP BY COALESCE(event_source, 'unknown')
                ORDER BY count DESC
                LIMIT 8
                """
            ),
            {"since": since},
        ).fetchall()

        recent_rows = db.execute(
            text(
                """
                SELECT
                    event_name,
                    event_source,
                    lead_id,
                    plan_tier,
                    page_path,
                    occurred_at,
                    event_properties
                FROM marketing_event_log
                WHERE occurred_at >= :since
                ORDER BY occurred_at DESC
                LIMIT 20
                """
            ),
            {"since": since},
        ).fetchall()

        demo_request_rows = db.execute(
            text(
                """
                SELECT
                    event_source,
                    lead_id,
                    plan_tier,
                    occurred_at,
                    event_properties
                FROM marketing_event_log
                WHERE occurred_at >= :since
                  AND event_name = 'marketing_demo_submit'
                  AND COALESCE(event_properties->>'result', 'success') = 'success'
                ORDER BY occurred_at DESC
                LIMIT 50
                """
            ),
            {"since": since},
        ).fetchall()

        activation_counts_row = db.execute(
            text(
                """
                WITH activation_sessions AS (
                    SELECT
                        COALESCE(
                            NULLIF(lead_id, ''),
                            NULLIF(event_properties->>'tenant_id', ''),
                            NULLIF(session_id, ''),
                            NULLIF(anonymous_id, ''),
                            CAST(id AS TEXT)
                        ) AS activation_key,
                        MIN(occurred_at) FILTER (WHERE event_name = 'onboarding_started') AS onboarding_started_at,
                        MIN(occurred_at) FILTER (
                            WHERE event_name = 'onboarding_core_connectors_ready'
                        ) AS core_connectors_ready_at,
                        MIN(occurred_at) FILTER (
                            WHERE event_name = 'onboarding_first_value_ready'
                        ) AS first_value_ready_at,
                        MIN(occurred_at) FILTER (WHERE event_name = 'onboarding_completed') AS onboarding_completed_at
                    FROM marketing_event_log
                    WHERE occurred_at >= :since
                      AND event_name IN (
                        'onboarding_started',
                        'onboarding_core_connectors_ready',
                        'onboarding_first_value_ready',
                        'onboarding_completed'
                      )
                    GROUP BY 1
                )
                SELECT
                    COUNT(*) FILTER (WHERE onboarding_started_at IS NOT NULL) AS onboarding_started,
                    COUNT(*) FILTER (
                        WHERE onboarding_started_at IS NOT NULL
                          AND core_connectors_ready_at IS NOT NULL
                    ) AS core_connectors_ready,
                    COUNT(*) FILTER (
                        WHERE onboarding_started_at IS NOT NULL
                          AND first_value_ready_at IS NOT NULL
                    ) AS first_value_ready,
                    COUNT(*) FILTER (
                        WHERE onboarding_started_at IS NOT NULL
                          AND onboarding_completed_at IS NOT NULL
                    ) AS onboarding_completed,
                    AVG(EXTRACT(EPOCH FROM (core_connectors_ready_at - onboarding_started_at)) / 3600.0)
                        FILTER (
                            WHERE onboarding_started_at IS NOT NULL
                              AND core_connectors_ready_at IS NOT NULL
                        ) AS avg_hours_to_core_connectors,
                    AVG(EXTRACT(EPOCH FROM (first_value_ready_at - onboarding_started_at)) / 3600.0)
                        FILTER (
                            WHERE onboarding_started_at IS NOT NULL
                              AND first_value_ready_at IS NOT NULL
                        ) AS avg_hours_to_first_value,
                    AVG(EXTRACT(EPOCH FROM (onboarding_completed_at - onboarding_started_at)) / 3600.0)
                        FILTER (
                            WHERE onboarding_started_at IS NOT NULL
                              AND onboarding_completed_at IS NOT NULL
                        ) AS avg_hours_to_completion
                FROM activation_sessions
                """
            ),
            {"since": since},
        ).fetchone()

        activation_daily_rows = db.execute(
            text(
                """
                SELECT
                    DATE(occurred_at) AS day,
                    COUNT(*) FILTER (WHERE event_name = 'onboarding_started') AS onboarding_started,
                    COUNT(*) FILTER (
                        WHERE event_name = 'onboarding_core_connectors_ready'
                    ) AS core_connectors_ready,
                    COUNT(*) FILTER (
                        WHERE event_name = 'onboarding_first_value_ready'
                    ) AS first_value_ready,
                    COUNT(*) FILTER (WHERE event_name = 'onboarding_completed') AS onboarding_completed
                FROM marketing_event_log
                WHERE occurred_at >= :since
                  AND event_name IN (
                    'onboarding_started',
                    'onboarding_core_connectors_ready',
                    'onboarding_first_value_ready',
                    'onboarding_completed'
                  )
                GROUP BY DATE(occurred_at)
                ORDER BY day ASC
                """
            ),
            {"since": since},
        ).fetchall()

        activation_step_rows = db.execute(
            text(
                """
                SELECT
                    COALESCE(event_properties->>'step_id', 'unknown') AS step_id,
                    COUNT(*) FILTER (WHERE event_name = 'onboarding_step_viewed') AS viewed,
                    COUNT(*) FILTER (WHERE event_name = 'onboarding_step_completed') AS completed,
                    COUNT(*) FILTER (WHERE event_name = 'onboarding_step_skipped') AS skipped
                FROM marketing_event_log
                WHERE occurred_at >= :since
                  AND event_name IN (
                    'onboarding_step_viewed',
                    'onboarding_step_completed',
                    'onboarding_step_skipped'
                  )
                GROUP BY COALESCE(event_properties->>'step_id', 'unknown')
                ORDER BY completed DESC, viewed DESC, step_id ASC
                """
            ),
            {"since": since},
        ).fetchall()

        activation_recent_rows = db.execute(
            text(
                """
                SELECT
                    event_name,
                    event_properties->>'step_id' AS step_id,
                    event_source,
                    plan_tier,
                    occurred_at,
                    event_properties
                FROM marketing_event_log
                WHERE occurred_at >= :since
                  AND event_name LIKE 'onboarding_%'
                ORDER BY occurred_at DESC
                LIMIT 20
                """
            ),
            {"since": since},
        ).fetchall()

        activation_plan_rows = db.execute(
            text(
                """
                WITH activation_sessions AS (
                    SELECT
                        COALESCE(
                            NULLIF(lead_id, ''),
                            NULLIF(event_properties->>'tenant_id', ''),
                            NULLIF(session_id, ''),
                            NULLIF(anonymous_id, ''),
                            CAST(id AS TEXT)
                        ) AS activation_key,
                        MAX(NULLIF(plan_tier, '')) AS plan_tier,
                        MIN(occurred_at) FILTER (WHERE event_name = 'onboarding_started') AS onboarding_started_at,
                        MIN(occurred_at) FILTER (
                            WHERE event_name = 'onboarding_core_connectors_ready'
                        ) AS core_connectors_ready_at,
                        MIN(occurred_at) FILTER (
                            WHERE event_name = 'onboarding_first_value_ready'
                        ) AS first_value_ready_at,
                        MIN(occurred_at) FILTER (WHERE event_name = 'onboarding_completed') AS onboarding_completed_at
                    FROM marketing_event_log
                    WHERE occurred_at >= :since
                      AND event_name IN (
                        'signup_started',
                        'signup_lead_created',
                        'signup_payment_started',
                        'signup_payment_succeeded',
                        'onboarding_started',
                        'onboarding_core_connectors_ready',
                        'onboarding_first_value_ready',
                        'onboarding_completed'
                      )
                    GROUP BY 1
                )
                SELECT
                    COALESCE(plan_tier, 'unknown') AS segment,
                    COUNT(*) FILTER (WHERE onboarding_started_at IS NOT NULL) AS onboarding_started,
                    COUNT(*) FILTER (
                        WHERE onboarding_started_at IS NOT NULL
                          AND core_connectors_ready_at IS NOT NULL
                    ) AS core_connectors_ready,
                    COUNT(*) FILTER (
                        WHERE onboarding_started_at IS NOT NULL
                          AND first_value_ready_at IS NOT NULL
                    ) AS first_value_ready,
                    COUNT(*) FILTER (
                        WHERE onboarding_started_at IS NOT NULL
                          AND onboarding_completed_at IS NOT NULL
                    ) AS onboarding_completed,
                    AVG(EXTRACT(EPOCH FROM (core_connectors_ready_at - onboarding_started_at)) / 3600.0)
                        FILTER (
                            WHERE onboarding_started_at IS NOT NULL
                              AND core_connectors_ready_at IS NOT NULL
                        ) AS avg_hours_to_core,
                    AVG(EXTRACT(EPOCH FROM (first_value_ready_at - onboarding_started_at)) / 3600.0)
                        FILTER (
                            WHERE onboarding_started_at IS NOT NULL
                              AND first_value_ready_at IS NOT NULL
                        ) AS avg_hours_to_first_value,
                    AVG(EXTRACT(EPOCH FROM (onboarding_completed_at - onboarding_started_at)) / 3600.0)
                        FILTER (
                            WHERE onboarding_started_at IS NOT NULL
                              AND onboarding_completed_at IS NOT NULL
                        ) AS avg_hours_to_completion
                FROM activation_sessions
                GROUP BY COALESCE(plan_tier, 'unknown')
                ORDER BY onboarding_started DESC, segment ASC
                LIMIT 8
                """
            ),
            {"since": since},
        ).fetchall()

        activation_identity_rows = db.execute(
            text(
                """
                WITH activation_sessions AS (
                    SELECT
                        COALESCE(
                            NULLIF(lead_id, ''),
                            NULLIF(event_properties->>'tenant_id', ''),
                            NULLIF(session_id, ''),
                            NULLIF(anonymous_id, ''),
                            CAST(id AS TEXT)
                        ) AS activation_key,
                        MAX(NULLIF(event_properties->>'idp_provider', '')) AS idp_provider,
                        MIN(occurred_at) FILTER (WHERE event_name = 'onboarding_started') AS onboarding_started_at,
                        MIN(occurred_at) FILTER (
                            WHERE event_name = 'onboarding_core_connectors_ready'
                        ) AS core_connectors_ready_at,
                        MIN(occurred_at) FILTER (
                            WHERE event_name = 'onboarding_first_value_ready'
                        ) AS first_value_ready_at,
                        MIN(occurred_at) FILTER (WHERE event_name = 'onboarding_completed') AS onboarding_completed_at
                    FROM marketing_event_log
                    WHERE occurred_at >= :since
                      AND event_name IN (
                        'onboarding_started',
                        'onboarding_core_connectors_ready',
                        'onboarding_first_value_ready',
                        'onboarding_completed',
                        'onboarding_step_viewed',
                        'onboarding_step_completed',
                        'onboarding_step_skipped'
                      )
                    GROUP BY 1
                )
                SELECT
                    COALESCE(idp_provider, 'unknown') AS segment,
                    COUNT(*) FILTER (WHERE onboarding_started_at IS NOT NULL) AS onboarding_started,
                    COUNT(*) FILTER (
                        WHERE onboarding_started_at IS NOT NULL
                          AND core_connectors_ready_at IS NOT NULL
                    ) AS core_connectors_ready,
                    COUNT(*) FILTER (
                        WHERE onboarding_started_at IS NOT NULL
                          AND first_value_ready_at IS NOT NULL
                    ) AS first_value_ready,
                    COUNT(*) FILTER (
                        WHERE onboarding_started_at IS NOT NULL
                          AND onboarding_completed_at IS NOT NULL
                    ) AS onboarding_completed,
                    AVG(EXTRACT(EPOCH FROM (core_connectors_ready_at - onboarding_started_at)) / 3600.0)
                        FILTER (
                            WHERE onboarding_started_at IS NOT NULL
                              AND core_connectors_ready_at IS NOT NULL
                        ) AS avg_hours_to_core,
                    AVG(EXTRACT(EPOCH FROM (first_value_ready_at - onboarding_started_at)) / 3600.0)
                        FILTER (
                            WHERE onboarding_started_at IS NOT NULL
                              AND first_value_ready_at IS NOT NULL
                        ) AS avg_hours_to_first_value,
                    AVG(EXTRACT(EPOCH FROM (onboarding_completed_at - onboarding_started_at)) / 3600.0)
                        FILTER (
                            WHERE onboarding_started_at IS NOT NULL
                              AND onboarding_completed_at IS NOT NULL
                        ) AS avg_hours_to_completion
                FROM activation_sessions
                GROUP BY COALESCE(idp_provider, 'unknown')
                ORDER BY onboarding_started DESC, segment ASC
                LIMIT 8
                """
            ),
            {"since": since},
        ).fetchall()

        activation_trust_rows = db.execute(
            text(
                """
                WITH activation_sessions AS (
                    SELECT
                        COALESCE(
                            NULLIF(lead_id, ''),
                            NULLIF(event_properties->>'tenant_id', ''),
                            NULLIF(session_id, ''),
                            NULLIF(anonymous_id, ''),
                            CAST(id AS TEXT)
                        ) AS activation_key,
                        BOOL_OR(COALESCE((event_properties->>'trust_enabled')::boolean, false)) AS trust_enabled,
                        MIN(occurred_at) FILTER (WHERE event_name = 'onboarding_started') AS onboarding_started_at,
                        MIN(occurred_at) FILTER (
                            WHERE event_name = 'onboarding_core_connectors_ready'
                        ) AS core_connectors_ready_at,
                        MIN(occurred_at) FILTER (
                            WHERE event_name = 'onboarding_first_value_ready'
                        ) AS first_value_ready_at,
                        MIN(occurred_at) FILTER (WHERE event_name = 'onboarding_completed') AS onboarding_completed_at
                    FROM marketing_event_log
                    WHERE occurred_at >= :since
                      AND event_name IN (
                        'signup_started',
                        'signup_lead_created',
                        'onboarding_started',
                        'onboarding_core_connectors_ready',
                        'onboarding_first_value_ready',
                        'onboarding_completed'
                      )
                    GROUP BY 1
                )
                SELECT
                    CASE
                        WHEN trust_enabled THEN 'trust_enabled'
                        ELSE 'standard'
                    END AS segment,
                    COUNT(*) FILTER (WHERE onboarding_started_at IS NOT NULL) AS onboarding_started,
                    COUNT(*) FILTER (
                        WHERE onboarding_started_at IS NOT NULL
                          AND core_connectors_ready_at IS NOT NULL
                    ) AS core_connectors_ready,
                    COUNT(*) FILTER (
                        WHERE onboarding_started_at IS NOT NULL
                          AND first_value_ready_at IS NOT NULL
                    ) AS first_value_ready,
                    COUNT(*) FILTER (
                        WHERE onboarding_started_at IS NOT NULL
                          AND onboarding_completed_at IS NOT NULL
                    ) AS onboarding_completed,
                    AVG(EXTRACT(EPOCH FROM (core_connectors_ready_at - onboarding_started_at)) / 3600.0)
                        FILTER (
                            WHERE onboarding_started_at IS NOT NULL
                              AND core_connectors_ready_at IS NOT NULL
                        ) AS avg_hours_to_core,
                    AVG(EXTRACT(EPOCH FROM (first_value_ready_at - onboarding_started_at)) / 3600.0)
                        FILTER (
                            WHERE onboarding_started_at IS NOT NULL
                              AND first_value_ready_at IS NOT NULL
                        ) AS avg_hours_to_first_value,
                    AVG(EXTRACT(EPOCH FROM (onboarding_completed_at - onboarding_started_at)) / 3600.0)
                        FILTER (
                            WHERE onboarding_started_at IS NOT NULL
                              AND onboarding_completed_at IS NOT NULL
                        ) AS avg_hours_to_completion
                FROM activation_sessions
                GROUP BY CASE
                    WHEN trust_enabled THEN 'trust_enabled'
                    ELSE 'standard'
                END
                ORDER BY onboarding_started DESC, segment ASC
                LIMIT 8
                """
            ),
            {"since": since},
        ).fetchall()

        activation_billing_rows = db.execute(
            text(
                """
                WITH activation_sessions AS (
                    SELECT
                        COALESCE(
                            NULLIF(lead_id, ''),
                            NULLIF(event_properties->>'tenant_id', ''),
                            NULLIF(session_id, ''),
                            NULLIF(anonymous_id, ''),
                            CAST(id AS TEXT)
                        ) AS activation_key,
                        MAX(NULLIF(event_properties->>'billing_period', '')) AS billing_period,
                        MIN(occurred_at) FILTER (WHERE event_name = 'onboarding_started') AS onboarding_started_at,
                        MIN(occurred_at) FILTER (
                            WHERE event_name = 'onboarding_core_connectors_ready'
                        ) AS core_connectors_ready_at,
                        MIN(occurred_at) FILTER (
                            WHERE event_name = 'onboarding_first_value_ready'
                        ) AS first_value_ready_at,
                        MIN(occurred_at) FILTER (WHERE event_name = 'onboarding_completed') AS onboarding_completed_at
                    FROM marketing_event_log
                    WHERE occurred_at >= :since
                      AND event_name IN (
                        'signup_payment_started',
                        'signup_payment_succeeded',
                        'onboarding_started',
                        'onboarding_core_connectors_ready',
                        'onboarding_first_value_ready',
                        'onboarding_completed'
                      )
                    GROUP BY 1
                )
                SELECT
                    COALESCE(billing_period, 'unknown') AS segment,
                    COUNT(*) FILTER (WHERE onboarding_started_at IS NOT NULL) AS onboarding_started,
                    COUNT(*) FILTER (
                        WHERE onboarding_started_at IS NOT NULL
                          AND core_connectors_ready_at IS NOT NULL
                    ) AS core_connectors_ready,
                    COUNT(*) FILTER (
                        WHERE onboarding_started_at IS NOT NULL
                          AND first_value_ready_at IS NOT NULL
                    ) AS first_value_ready,
                    COUNT(*) FILTER (
                        WHERE onboarding_started_at IS NOT NULL
                          AND onboarding_completed_at IS NOT NULL
                    ) AS onboarding_completed,
                    AVG(EXTRACT(EPOCH FROM (core_connectors_ready_at - onboarding_started_at)) / 3600.0)
                        FILTER (
                            WHERE onboarding_started_at IS NOT NULL
                              AND core_connectors_ready_at IS NOT NULL
                        ) AS avg_hours_to_core,
                    AVG(EXTRACT(EPOCH FROM (first_value_ready_at - onboarding_started_at)) / 3600.0)
                        FILTER (
                            WHERE onboarding_started_at IS NOT NULL
                              AND first_value_ready_at IS NOT NULL
                        ) AS avg_hours_to_first_value,
                    AVG(EXTRACT(EPOCH FROM (onboarding_completed_at - onboarding_started_at)) / 3600.0)
                        FILTER (
                            WHERE onboarding_started_at IS NOT NULL
                              AND onboarding_completed_at IS NOT NULL
                        ) AS avg_hours_to_completion
                FROM activation_sessions
                GROUP BY COALESCE(billing_period, 'unknown')
                ORDER BY onboarding_started DESC, segment ASC
                LIMIT 8
                """
            ),
            {"since": since},
        ).fetchall()

        return _build_funnel_summary_payload(
            counts_row=counts_row or (0, 0, 0, 0, 0, 0, 0, 0),
            daily_rows=list(daily_rows or []),
            source_rows=list(source_rows or []),
            recent_rows=list(recent_rows or []),
            demo_request_rows=list(demo_request_rows or []),
            activation_counts_row=activation_counts_row or (0, 0, 0, 0, None, None, None),
            activation_daily_rows=list(activation_daily_rows or []),
            activation_step_rows=list(activation_step_rows or []),
            activation_recent_rows=list(activation_recent_rows or []),
            activation_plan_rows=list(activation_plan_rows or []),
            activation_identity_rows=list(activation_identity_rows or []),
            activation_trust_rows=list(activation_trust_rows or []),
            activation_billing_rows=list(activation_billing_rows or []),
            days=days,
        )
    finally:
        db.close()
