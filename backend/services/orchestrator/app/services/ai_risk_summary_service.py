"""Aggregate platform AI-risk summaries for the core dashboard."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

libs_path = os.path.join(os.path.dirname(__file__), "../../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from sg_core.models import Alert, Incident

from app.core.config import settings


_SEVERITY_WEIGHT = {
    "critical": 400,
    "high": 300,
    "medium": 200,
    "low": 100,
}


def _severity_rank(value: str | None) -> int:
    return _SEVERITY_WEIGHT.get((value or "low").lower(), 0)


def _normalize_alert_status(value: str | None) -> str:
    status = (value or "").lower()
    return status or "open"


def _normalize_incident_status(value: str | None) -> str:
    status = (value or "").lower()
    return status or "open"


def _finding_type(raw_payload: dict) -> str:
    finding = raw_payload.get("finding") if isinstance(raw_payload.get("finding"), dict) else {}
    return str(finding.get("type") or "").lower()


def _ai_payload(raw_payload: dict) -> dict:
    value = raw_payload.get("ai")
    return value if isinstance(value, dict) else {}


class AiRiskSummaryService:
    """Build AI-risk rollups from platform alerts and incidents."""

    def __init__(self) -> None:
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self.db_session_factory = session_local

    def build_summary(self, tenant_id: str, lookback_days: int = 7) -> Dict[str, Any]:
        tenant_uuid = UUID(tenant_id)
        normalized_lookback_days = max(1, min(int(lookback_days or 7), 90))
        lookback = datetime.now(timezone.utc) - timedelta(days=normalized_lookback_days)

        with self.db_session_factory() as db:
            alerts = (
                db.query(Alert)
                .filter(
                    Alert.tenant_id == tenant_uuid,
                    Alert.source == "sentinelgrid_ai_shield",
                    Alert.detection_time >= lookback,
                )
                .order_by(Alert.detection_time.desc(), Alert.updated_at.desc())
                .limit(50)
                .all()
            )
            incidents = (
                db.query(Incident)
                .filter(
                    Incident.tenant_id == tenant_uuid,
                    Incident.source == "sentinelgrid_ai_shield",
                    Incident.created_at >= lookback,
                )
                .order_by(Incident.updated_at.desc(), Incident.created_at.desc())
                .limit(25)
                .all()
            )

        open_alerts = [
            alert for alert in alerts if _normalize_alert_status(alert.status) in {"open", "investigating", "acknowledged"}
        ]
        active_incidents = [
            incident
            for incident in incidents
            if _normalize_incident_status(incident.status) in {"open", "in_progress", "investigating"}
        ]

        affected_users = set()
        app_rollups: Dict[str, Dict[str, Any]] = {}
        severity_breakdown = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        prompt_injection_alerts = 0
        data_exposure_alerts = 0
        policy_violation_alerts = 0

        for alert in alerts:
            raw_payload = alert.raw_payload or {}
            ai = _ai_payload(raw_payload)
            finding_type = _finding_type(raw_payload)
            severity = (alert.raw_severity or "low").lower()
            if severity in severity_breakdown:
                severity_breakdown[severity] += 1

            app_id = str(ai.get("app_id") or alert.asset_id or "unknown-app")
            rollup = app_rollups.setdefault(
                app_id,
                {
                    "app_id": app_id,
                    "label": app_id,
                    "provider": str(ai.get("provider") or "").strip() or None,
                    "model": str(ai.get("model") or "").strip() or None,
                    "open_alerts": 0,
                    "active_incidents": 0,
                    "highest_severity": "low",
                    "prompt_injection_alerts": 0,
                    "data_exposure_alerts": 0,
                    "policy_violations": 0,
                },
            )
            if alert in open_alerts:
                rollup["open_alerts"] += 1
            if _severity_rank(severity) > _severity_rank(rollup["highest_severity"]):
                rollup["highest_severity"] = severity
            if not rollup.get("provider") and ai.get("provider"):
                rollup["provider"] = ai.get("provider")
            if not rollup.get("model") and ai.get("model"):
                rollup["model"] = ai.get("model")

            user_id = str(ai.get("user_id") or alert.user_identifier or "").strip()
            if user_id:
                affected_users.add(user_id)

            if finding_type == "prompt_injection":
                prompt_injection_alerts += 1
                rollup["prompt_injection_alerts"] += 1
            elif finding_type == "sensitive_data_exposure":
                data_exposure_alerts += 1
                rollup["data_exposure_alerts"] += 1
            elif finding_type == "policy_violation":
                policy_violation_alerts += 1
                rollup["policy_violations"] += 1

        for incident in active_incidents:
            raw_payload = incident.raw_payload or {}
            ai = _ai_payload(raw_payload)
            app_id = str(ai.get("app_id") or raw_payload.get("asset_id") or "unknown-app")
            rollup = app_rollups.setdefault(
                app_id,
                {
                    "app_id": app_id,
                    "label": app_id,
                    "provider": str(ai.get("provider") or "").strip() or None,
                    "model": str(ai.get("model") or "").strip() or None,
                    "open_alerts": 0,
                    "active_incidents": 0,
                    "highest_severity": "low",
                    "prompt_injection_alerts": 0,
                    "data_exposure_alerts": 0,
                    "policy_violations": 0,
                },
            )
            rollup["active_incidents"] += 1
            severity = (incident.severity or "low").lower()
            if _severity_rank(severity) > _severity_rank(rollup["highest_severity"]):
                rollup["highest_severity"] = severity
            if not rollup.get("provider") and ai.get("provider"):
                rollup["provider"] = ai.get("provider")
            if not rollup.get("model") and ai.get("model"):
                rollup["model"] = ai.get("model")

            user_id = str(ai.get("user_id") or raw_payload.get("user_identifier") or "").strip()
            if user_id:
                affected_users.add(user_id)

        top_applications = sorted(
            app_rollups.values(),
            key=lambda item: (
                item["active_incidents"],
                item["open_alerts"],
                _severity_rank(item["highest_severity"]),
                item["label"],
            ),
            reverse=True,
        )[:3]

        top_incident = max(
            active_incidents,
            key=lambda item: (_severity_rank(item.severity), item.updated_at or item.created_at or lookback),
            default=None,
        )
        top_alert = max(
            open_alerts,
            key=lambda item: (_severity_rank(item.raw_severity), item.updated_at or item.detection_time or lookback),
            default=None,
        )

        top_risk = None
        if top_incident is not None:
            raw_payload = top_incident.raw_payload or {}
            top_risk = {
                "item_type": "incident",
                "id": str(top_incident.id),
                "title": top_incident.title,
                "severity": top_incident.severity or "high",
                "summary": raw_payload.get("summary") or raw_payload.get("description") or "Active AI incident requiring operator review.",
                "href": f"/dashboard/incidents/{top_incident.id}",
            }
        elif top_alert is not None:
            raw_payload = top_alert.raw_payload or {}
            top_risk = {
                "item_type": "alert",
                "id": str(top_alert.id),
                "title": top_alert.title,
                "severity": top_alert.raw_severity or "medium",
                "summary": top_alert.description or raw_payload.get("summary") or "Open AI finding requiring review.",
                "href": f"/dashboard/alerts/{top_alert.id}",
            }

        if active_incidents or severity_breakdown["critical"] > 0:
            health_status = "critical"
        elif open_alerts:
            health_status = "warning"
        else:
            health_status = "inactive"

        if top_risk:
            summary = (
                f"{len(active_incidents)} active AI incident{'s' if len(active_incidents) != 1 else ''} and "
                f"{len(open_alerts)} open AI alert{'s' if len(open_alerts) != 1 else ''} across "
                f"{len(app_rollups)} app{'s' if len(app_rollups) != 1 else ''}."
            )
        else:
            summary = "No elevated AI risk is currently active in the main operator workflow."

        priority_actions: List[Dict[str, str]] = []
        if top_risk:
            priority_actions.append(
                {
                    "label": "Open top AI case",
                    "href": top_risk["href"],
                }
            )
        priority_actions.append(
            {
                "label": "Review AI activity",
                "href": "/dashboard/compliance/ai-activity",
            }
        )
        priority_actions.append(
            {
                "label": "Open AI playbooks",
                "href": "/dashboard/playbooks",
            }
        )

        return {
            "health_status": health_status,
            "summary": summary,
            "lookback_days": normalized_lookback_days,
            "open_alerts": len(open_alerts),
            "active_incidents": len(active_incidents),
            "affected_apps": len(app_rollups),
            "affected_users": len(affected_users),
            "prompt_injection_alerts": prompt_injection_alerts,
            "data_exposure_alerts": data_exposure_alerts,
            "policy_violation_alerts": policy_violation_alerts,
            "severity_breakdown": severity_breakdown,
            "top_applications": top_applications,
            "top_risk": top_risk,
            "priority_actions": priority_actions,
        }
