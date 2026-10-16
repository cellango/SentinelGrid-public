import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.welcome_prioritization import (
    build_now_queue,
    build_dashboard_health,
    build_first_value_findings,
    build_recommendations,
)


def test_build_first_value_findings_prioritizes_real_backend_signals():
    posture_score = {
        "top_risks": [
            {
                "id": "risk-1",
                "title": "Public storage bucket with restricted data",
                "severity": "critical",
                "domain": "cloud",
                "exposed": True,
                "criticality": "critical",
                "data_classification": "restricted",
            },
            {
                "id": "risk-2",
                "title": "Dormant repository with leaked token",
                "severity": "high",
                "domain": "app",
                "exposed": False,
            },
        ]
    }
    people_access = {
        "mfa_missing_count": 5,
        "users_admins": 2,
        "anomalies_critical": 0,
    }

    findings = build_first_value_findings("tenant-1", posture_score, people_access)

    assert findings[0]["title"] == "Public storage bucket with restricted data"
    assert findings[0]["href"] == "/dashboard/compliance"
    assert any(item["id"] == "identity-mfa-gap" for item in findings)


def test_build_recommendations_frontload_activation_before_lower_signal_work():
    posture_score = {
        "domain_scores": {"cloud": {"counts": {"critical": 1}, "open": 2}},
        "coverage_details": {"endpoint": {"scanned": 1, "total": 4}, "cloud": {"scanned": 0, "total": 0}},
        "top_risks": [
            {
                "id": "risk-1",
                "title": "Public storage bucket with restricted data",
                "severity": "critical",
                "domain": "cloud",
            }
        ],
    }
    people_access = {
        "mfa_missing_count": 3,
        "users_admins": 1,
    }
    onboarding_status = {
        "idp_connected": False,
        "cloud_connected": False,
        "endpoint_deployed": False,
        "git_connected": False,
        "appsec_connected": False,
        "ai_connected": False,
        "services_selected": {
            "cloud": True,
            "git": True,
            "appsec": True,
            "aiShield": "hosted",
            "socManaged": False,
        },
        "ticketing_health": {"status": "degraded"},
    }

    recommendations = build_recommendations(posture_score, people_access, onboarding_status)
    recommendation_ids = [item["id"] for item in recommendations]
    first_recommendation = recommendations[0]
    cloud_recommendation = next(item for item in recommendations if item["id"] == "cloud-critical-misconfig")

    assert recommendation_ids[:2] == ["activation-idp", "activation-cloud"]
    assert "identity-mfa-enforcement" in recommendation_ids
    assert "ticketing-handoff" in recommendation_ids
    assert first_recommendation["finding_class"] == "activation.identity_connection"
    assert len(first_recommendation["remediation"]["steps"]) == 3
    assert first_recommendation["remediation"]["owner"] == "Security admin"
    assert cloud_recommendation["finding_class"] == "cloud.critical_exposure"
    assert any(action.get("playbook_id") == "CLOUD-PUBLIC-STORAGE" for action in cloud_recommendation["actions"])


def test_build_dashboard_health_reflects_connected_integrations_and_coverage():
    onboarding_status = {
        "idp_connected": True,
        "cloud_connected": True,
        "endpoint_deployed": True,
        "cloud_health": {"status": "healthy"},
    }
    posture_score = {
        "coverage_details": {
            "endpoint": {"scanned": 7, "total": 10},
        }
    }

    health = build_dashboard_health(onboarding_status, posture_score)

    assert health["integrations"]["aws"] == "connected"
    assert health["integrations"]["idp"] == "connected"
    assert health["integrations"]["endpoint"] == "partial"
    assert health["agents"]["percentage_online"] == 70


def test_build_now_queue_prioritizes_incidents_then_alerts_then_recommendations():
    incidents = [
        {
            "id": "incident:1",
            "item_type": "incident",
            "priority": "critical",
            "title": "Open incident",
            "summary": "Critical incident",
            "why_now": "Immediate response needed",
            "domains": ["identity", "cloud"],
            "entities": [],
            "evidence": [],
        }
    ]
    alerts = [
        {
            "id": "alert:1",
            "item_type": "alert",
            "priority": "high",
            "title": "Untriaged alert",
            "summary": "Alert still open",
            "why_now": "Needs triage",
            "domains": ["endpoint"],
            "entities": [],
            "evidence": [],
        }
    ]
    recommendations = [
        {
            "id": "activation-idp",
            "priority": "high",
            "title": "Connect Microsoft 365 / Entra first",
            "description": "Identity data unlocks early findings.",
            "category": "activation",
            "estimated_time_minutes": 10,
            "remediation": {"owner": "Security admin", "why_now": "Identity data is still missing."},
            "actions": [{"label": "Open onboarding", "type": "view_details", "endpoint": "/onboarding"}],
        }
    ]

    queue = build_now_queue(incidents, alerts, recommendations, limit=6)

    assert [item["item_type"] for item in queue["items"][:3]] == ["incident", "alert", "recommendation"]
    assert queue["summary"]["urgent_items"] == 3
    assert queue["summary"]["incidents"] == 1
    assert queue["summary"]["alerts"] == 1
    assert queue["summary"]["recommendations"] == 1
    assert queue["items"][2]["action_href"] == "/onboarding"
