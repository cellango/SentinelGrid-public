import os
import sys
from datetime import datetime, timezone

import pytest

SERVICE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIBS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs"))

for path in (SERVICE_ROOT, LIBS_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.services.ai_governance_reporting import AiGovernanceReportingService


@pytest.mark.asyncio
async def test_ai_governance_summary_aggregates_activity_and_risk(monkeypatch):
    service = AiGovernanceReportingService()

    monkeypatch.setattr(service, "_lookup_realm_name", lambda _tenant_id: "acme")

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 3, 28, 12, 0, 0, tzinfo=tz or timezone.utc)

    monkeypatch.setattr("app.services.ai_governance_reporting.datetime", FrozenDateTime)

    async def fake_activity(*, tenant_id, realm_name, start_date, end_date):
        return [
            {
                "id": "evt-1",
                "timestamp": "2026-03-20T12:00:00Z",
                "action": "unified_chat",
                "user_email": "analyst@acme.com",
                "metadata": {"app_id": "internal-copilot", "model": "gpt-4.1", "module": "assistant"},
            },
            {
                "id": "evt-2",
                "timestamp": "2026-03-21T12:00:00Z",
                "action": "unified_chat",
                "user_email": "analyst@acme.com",
                "metadata": {"app_id": "internal-copilot", "model": "gpt-4.1", "module": "assistant"},
            },
            {
                "id": "evt-3",
                "timestamp": "2026-03-22T12:00:00Z",
                "action": "unified_chat",
                "user_email": "engineer@acme.com",
                "metadata": {"model": "unknown-proxy", "module": "shadow"},
            },
        ]

    async def fake_risk(_tenant_id, lookback_days):
        if lookback_days <= 30:
            return {
                "open_alerts": 2,
                "active_incidents": 1,
                "policy_violation_alerts": 3,
                "prompt_injection_alerts": 2,
                "data_exposure_alerts": 1,
                "severity_breakdown": {"critical": 1, "high": 1, "medium": 1, "low": 0},
                "summary": "1 active AI incident and 2 open AI alerts.",
                "top_risk": {
                    "item_type": "incident",
                    "id": "inc-1",
                    "title": "Secrets exposure through internal-copilot",
                    "severity": "critical",
                    "summary": "Secret material reached an external model path.",
                    "href": "/dashboard/incidents/inc-1",
                },
                "top_applications": [
                    {
                        "app_id": "internal-copilot",
                        "label": "Internal Copilot",
                        "provider": "OpenAI",
                        "model": "gpt-4.1",
                        "open_alerts": 2,
                        "active_incidents": 1,
                        "highest_severity": "critical",
                        "prompt_injection_alerts": 2,
                        "data_exposure_alerts": 1,
                        "policy_violations": 3,
                    }
                ],
            }
        return {
            "open_alerts": 3,
            "active_incidents": 1,
            "policy_violation_alerts": 4,
            "prompt_injection_alerts": 3,
            "data_exposure_alerts": 2,
            "severity_breakdown": {"critical": 1, "high": 2, "medium": 1, "low": 0},
            "summary": "Historical AI summary.",
            "top_risk": None,
            "top_applications": [],
        }

    monkeypatch.setattr(service, "_fetch_ai_activity", fake_activity)
    monkeypatch.setattr(service, "_fetch_ai_risk_summary", fake_risk)

    summary = await service.build_summary("tenant-1", lookback_days=30)

    assert summary["overview"]["active_apps"] == 2
    assert summary["overview"]["active_users"] == 2
    assert summary["overview"]["requests_in_window"] == 3
    assert summary["overview"]["apps_needing_review"] == 1
    assert summary["overview"]["unclassified_apps"] == 1
    assert summary["top_threats"][0]["type"] == "Prompt injection attempts"
    assert summary["top_risk"]["title"] == "Secrets exposure through internal-copilot"
    assert summary["app_inventory"][0]["label"] == "Internal Copilot"
    assert summary["recent_activity"][0]["app_label"] == "unknown-proxy"
