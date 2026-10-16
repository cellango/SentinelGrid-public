"""Unit tests for marketing analytics persistence and funnel summaries."""

from datetime import date, datetime, timezone
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import marketing


class _FakeResult:
    def __init__(self, one=None, many=None):
        self._one = one
        self._many = many or []

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._many


class _FakeDB:
    def __init__(self):
        self.statements = []
        self.insert_params = None
        self.committed = False

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params))

        if "INSERT INTO marketing_event_log" in sql:
            self.insert_params = params
            return _FakeResult()

        if "AS avg_hours_to_core_connectors" in sql:
            return _FakeResult((4, 3, 2, 1, 5.5, 18.0, 30.0))

        if (
            "GROUP BY DATE(occurred_at)" in sql
            and "onboarding_core_connectors_ready" in sql
            and "onboarding_first_value_ready" in sql
        ):
            return _FakeResult(
                many=[
                    (date(2026, 3, 25), 2, 1, 1, 0),
                    (date(2026, 3, 26), 2, 2, 1, 1),
                ]
            )

        if "COALESCE(event_properties->>'step_id', 'unknown')" in sql:
            return _FakeResult(
                many=[
                    ("idp", 4, 3, 0),
                    ("cloud", 4, 2, 1),
                    ("ticketing", 3, 1, 1),
                ]
            )

        if "event_name LIKE 'onboarding_%'" in sql:
            return _FakeResult(
                many=[
                    (
                        "onboarding_first_value_ready",
                        None,
                        "welcome_dashboard",
                        "protect_defend",
                        datetime(2026, 3, 26, 14, 15, tzinfo=timezone.utc),
                        {"source": "welcome_dashboard", "incidents": 2},
                    ),
                    (
                        "onboarding_step_completed",
                        "cloud",
                        "onboarding_wizard",
                        "protect_defend",
                        datetime(2026, 3, 26, 13, 0, tzinfo=timezone.utc),
                        {"step_id": "cloud"},
                    ),
                ]
            )

        if "GROUP BY COALESCE(plan_tier, 'unknown')" in sql:
            return _FakeResult(
                many=[
                    ("protect_defend", 4, 3, 2, 1, 6.0, 18.0, 28.0),
                    ("protect_defend_comply", 2, 1, 1, 1, 8.5, 20.0, 32.0),
                ]
            )

        if "GROUP BY COALESCE(idp_provider, 'unknown')" in sql:
            return _FakeResult(
                many=[
                    ("microsoft_entra", 3, 2, 2, 1, 5.0, 12.0, 24.0),
                    ("google_workspace", 2, 1, 1, 1, 7.0, 16.0, 26.0),
                ]
            )

        if "WHEN trust_enabled THEN 'trust_enabled'" in sql:
            return _FakeResult(
                many=[
                    ("trust_enabled", 2, 1, 1, 1, 8.0, 22.0, 34.0),
                    ("standard", 4, 3, 2, 1, 5.0, 16.0, 27.0),
                ]
            )

        if "GROUP BY COALESCE(billing_period, 'unknown')" in sql:
            return _FakeResult(
                many=[
                    ("yearly", 3, 2, 2, 1, 5.5, 14.0, 21.0),
                    ("monthly", 3, 2, 1, 1, 7.0, 20.0, 33.0),
                ]
            )

        if (
            "COUNT(*) FILTER" in sql
            and "signup_started" in sql
            and "signup_payment_succeeded" in sql
        ):
            return _FakeResult((12, 6, 4, 3, 2, 5, 4, 3))

        if "GROUP BY DATE(occurred_at)" in sql:
            return _FakeResult(
                many=[
                    (date(2026, 3, 25), 4, 2, 1, 1, 1, 2),
                    (date(2026, 3, 26), 8, 4, 3, 2, 1, 3),
                ]
            )

        if "GROUP BY COALESCE(event_source, 'unknown')" in sql:
            return _FakeResult(
                many=[
                    ("homepage_hero", 7),
                    ("pricing_page_hero", 3),
                ]
            )

        if (
            "event_name = 'marketing_demo_submit'" in sql
            and "COALESCE(event_properties->>'result', 'success') = 'success'" in sql
            and "LIMIT 50" in sql
        ):
            return _FakeResult(
                many=[
                    (
                        "demo_page",
                        "lead-std",
                        "protect_defend",
                        datetime(2026, 3, 26, 11, 30, tzinfo=timezone.utc),
                        {
                            "recommendedPath": "standard_launch_path",
                            "motion": "standard",
                            "guidedReviewReasons": [],
                        },
                    ),
                    (
                        "walkthrough_page",
                        "lead-guided",
                        "protect_defend",
                        datetime(2026, 3, 26, 10, 15, tzinfo=timezone.utc),
                        {
                            "recommendedPath": "guided_review",
                            "motion": "standard",
                            "guidedReviewReasons": ["multi_environment", "mixed_identity"],
                        },
                    ),
                    (
                        "partner_referral",
                        "lead-partner",
                        "protect_defend_comply",
                        datetime(2026, 3, 26, 9, 0, tzinfo=timezone.utc),
                        {
                            "recommendedPath": "guided_review",
                            "motion": "partner",
                            "guidedReviewReasons": ["partner_motion", "ai_shield_primary"],
                        },
                    ),
                ]
            )

        if "FROM marketing_event_log" in sql and "ORDER BY occurred_at DESC" in sql:
            return _FakeResult(
                many=[
                    (
                        "signup_payment_succeeded",
                        "signup_payment_step",
                        "lead-123",
                        "protect_defend",
                        "/signup/payment-success",
                        datetime(2026, 3, 26, 12, 30, tzinfo=timezone.utc),
                        {"plan": "protect_defend"},
                    )
                ]
            )

        return _FakeResult()

    def commit(self):
        self.committed = True

    def rollback(self):
        return None

    def close(self):
        return None


def _build_client(monkeypatch, fake_db):
    app = FastAPI()
    app.include_router(marketing.router)
    app.include_router(marketing.internal_router)

    monkeypatch.setattr(marketing.settings, "DB_URL", "postgresql://demo:test@localhost:5432/demo")
    monkeypatch.setattr(marketing.settings, "INTERNAL_SERVICE_TOKEN", "internal-token")
    monkeypatch.setattr(marketing, "create_engine", lambda *args, **kwargs: object())
    monkeypatch.setattr(marketing, "sessionmaker", lambda *args, **kwargs: (lambda: fake_db))

    return TestClient(app)


def test_extract_plan_tier_uses_common_property_names():
    assert marketing._extract_plan_tier({"plan": "protect"}) == "protect"
    assert marketing._extract_plan_tier({"planTier": "protect_defend"}) == "protect_defend"
    assert marketing._extract_plan_tier({"plan_tier": "protect_defend_comply"}) == "protect_defend_comply"
    assert marketing._extract_plan_tier({}) is None


def test_build_funnel_summary_payload_calculates_rates():
    payload = marketing._build_funnel_summary_payload(
        counts_row=(20, 10, 5, 4, 2, 3, 6, 3),
        daily_rows=[],
        source_rows=[],
        recent_rows=[],
        demo_request_rows=[
            (
                "demo_page",
                "lead-std",
                "protect_defend",
                datetime(2026, 3, 26, 11, 30, tzinfo=timezone.utc),
                {"recommendedPath": "standard_launch_path", "motion": "standard", "guidedReviewReasons": []},
            )
        ],
        activation_counts_row=(6, 4, 3, 2, 4.5, 10.0, 18.0),
        activation_daily_rows=[],
        activation_step_rows=[],
        activation_recent_rows=[],
        activation_plan_rows=[("protect_defend", 4, 3, 2, 1, 5.0, 16.0, 24.0)],
        activation_identity_rows=[("google_workspace", 2, 1, 1, 1, 6.0, 14.0, 22.0)],
        activation_trust_rows=[("trust_enabled", 2, 1, 1, 1, 8.0, 18.0, 30.0)],
        activation_billing_rows=[("yearly", 3, 2, 2, 1, 4.0, 12.0, 18.0)],
        days=30,
    )

    assert payload["summary"]["cta_clicks"] == 20
    assert payload["conversion_rates"]["cta_to_signup"] == 50.0
    assert payload["conversion_rates"]["signup_to_lead"] == 50.0
    assert payload["conversion_rates"]["lead_to_payment"] == 80.0
    assert payload["conversion_rates"]["payment_to_success"] == 50.0
    assert payload["conversion_rates"]["onboarding_start_to_complete"] == 50.0
    assert payload["demo_qualification"]["summary"]["standard_launch_path"] == 1
    assert payload["activation"]["conversion_rates"]["start_to_core_connectors"] == 66.7
    assert payload["activation"]["timings_hours"]["avg_to_completion"] == 18.0
    assert payload["activation"]["cohorts"]["plan_tiers"][0]["segment"] == "protect_defend"
    assert payload["activation"]["cohorts"]["identity_providers"][0]["start_to_first_value_rate"] == 50.0


def test_build_demo_qualification_payload_summarizes_requests():
    payload = marketing._build_demo_qualification_payload(
        [
            (
                "demo_page",
                "lead-std",
                "protect_defend",
                datetime(2026, 3, 26, 11, 30, tzinfo=timezone.utc),
                {"recommendedPath": "standard_launch_path", "motion": "standard", "guidedReviewReasons": []},
            ),
            (
                "walkthrough_page",
                "lead-guided",
                "protect_defend",
                datetime(2026, 3, 26, 10, 15, tzinfo=timezone.utc),
                {
                    "recommendedPath": "guided_review",
                    "motion": "standard",
                    "guidedReviewReasons": ["multi_environment", "mixed_identity"],
                },
            ),
            (
                "partner_referral",
                "lead-partner",
                "protect_defend_comply",
                datetime(2026, 3, 26, 9, 0, tzinfo=timezone.utc),
                {
                    "recommendedPath": "guided_review",
                    "motion": "partner",
                    "guidedReviewReasons": ["partner_motion", "ai_shield_primary"],
                },
            ),
        ]
    )

    assert payload["summary"]["total_demo_requests"] == 3
    assert payload["summary"]["standard_launch_path"] == 1
    assert payload["summary"]["guided_review"] == 2
    assert payload["summary"]["partner_motion"] == 1
    assert payload["top_guided_review_reasons"][0]["count"] == 1
    assert payload["recent_demo_requests"][0]["lead_id"] == "lead-std"


def test_ingest_marketing_event_persists_event(monkeypatch):
    fake_db = _FakeDB()
    client = _build_client(monkeypatch, fake_db)

    response = client.post(
        "/api/v1/marketing/events",
        json={
            "event": "signup_lead_created",
            "properties": {
                "source": "signup_page",
                "lead_id": "lead-123",
                "plan": "protect_defend",
            },
            "page_path": "/signup",
            "referrer": "https://sentinelgrid.ai/pricing",
            "anonymous_id": "anon-1",
            "session_id": "session-1",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"success": True}
    assert fake_db.committed is True
    assert fake_db.insert_params is not None
    assert fake_db.insert_params["event_name"] == "signup_lead_created"
    assert fake_db.insert_params["event_source"] == "signup_page"
    assert fake_db.insert_params["lead_id"] == "lead-123"
    assert fake_db.insert_params["plan_tier"] == "protect_defend"

    properties = json.loads(fake_db.insert_params["event_properties"])
    assert properties["source"] == "signup_page"


def test_get_marketing_funnel_summary_returns_expected_shape(monkeypatch):
    fake_db = _FakeDB()
    client = _build_client(monkeypatch, fake_db)

    response = client.get(
        "/internal/iam/marketing/funnel/summary?days=30",
        headers={"Authorization": "Bearer internal-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["window_days"] == 30
    assert payload["summary"]["cta_clicks"] == 12
    assert payload["summary"]["demo_requests"] == 5
    assert payload["conversion_rates"]["cta_to_signup"] == 50.0
    assert payload["top_sources"][0]["source"] == "homepage_hero"
    assert payload["recent_events"][0]["event"] == "signup_payment_succeeded"
    assert payload["demo_qualification"]["summary"]["guided_review"] == 2
    assert payload["demo_qualification"]["summary"]["partner_motion"] == 1
    assert payload["demo_qualification"]["top_guided_review_reasons"][0]["reason"] == "ai_shield_primary"
    assert payload["demo_qualification"]["recent_demo_requests"][0]["lead_id"] == "lead-std"
    assert payload["activation"]["summary"]["core_connectors_ready"] == 3
    assert payload["activation"]["timings_hours"]["avg_to_first_value"] == 18.0
    assert payload["activation"]["step_breakdown"][0]["step_id"] == "idp"
    assert payload["activation"]["recent_events"][0]["event"] == "onboarding_first_value_ready"
    assert payload["activation"]["cohorts"]["plan_tiers"][0]["segment"] == "protect_defend"
    assert payload["activation"]["cohorts"]["identity_providers"][0]["segment"] == "microsoft_entra"
    assert payload["activation"]["cohorts"]["trust_motions"][0]["segment"] == "trust_enabled"
    assert payload["activation"]["cohorts"]["billing_periods"][0]["segment"] == "yearly"


def test_get_marketing_funnel_summary_requires_internal_token(monkeypatch):
    fake_db = _FakeDB()
    client = _build_client(monkeypatch, fake_db)

    response = client.get("/internal/iam/marketing/funnel/summary?days=30")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing authorization header"}
