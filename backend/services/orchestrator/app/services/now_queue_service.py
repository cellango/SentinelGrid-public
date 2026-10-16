"""Backend service for the Phase 3 cross-domain Now queue."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

libs_path = os.path.join(os.path.dirname(__file__), "../../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from sg_core.entity_model import build_story_context, build_story_summary
from sg_core.models import Alert, Incident
from sg_core.service_metrics import get_service_metrics

from app.core.config import settings
from app.services.welcome_prioritization import build_now_queue, build_recommendations

runtime_metrics = get_service_metrics(settings.SERVICE_NAME)


class NowQueueService:
    """Build the operator-facing Now queue from live backend state."""

    def __init__(self) -> None:
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self.db_session_factory = session_local

    def _incident_story_context(self, incident: Incident) -> tuple[Dict[str, Any], Dict[str, Any]]:
        raw_payload = incident.raw_payload or {}
        related_detections = []
        for item in raw_payload.get("related_alert_ids") or []:
            related_detections.append({"id": str(item)})
        for detection in raw_payload.get("detections") or []:
            if isinstance(detection, dict):
                related_detections.append(
                    {
                        "id": str(
                            detection.get("id")
                            or detection.get("alert_id")
                            or detection.get("title")
                            or "alert"
                        ),
                        "title": detection.get("title"),
                        "severity": detection.get("severity"),
                    }
                )
            else:
                related_detections.append({"id": str(detection)})
        story = build_story_context(
            raw_payload=raw_payload,
            asset_id=raw_payload.get("asset_id"),
            user_identifier=raw_payload.get("user_identifier"),
            detection_rule_id=raw_payload.get("detection_rule_id"),
            detection_rule_version_id=raw_payload.get("detection_rule_version_id"),
            playbook_id=raw_payload.get("playbook_id") or (raw_payload.get("sg") or {}).get("playbook_id"),
            playbook_version_id=raw_payload.get("playbook_version_id"),
            related_detections=related_detections,
            ticket_id=str(incident.ticket_id) if incident.ticket_id else None,
            external_ticket_id=incident.external_ticket_id,
            external_ticket_provider=incident.external_ticket_provider,
            cve_ids=incident.cve_ids,
        )
        return story, build_story_summary(story_context=story)

    def list_open_incidents(self, tenant_id: str, *, limit: int = 10) -> List[Dict[str, Any]]:
        tenant_uuid = UUID(tenant_id)
        with self.db_session_factory() as db:
            incidents = (
                db.query(Incident)
                .filter(
                    Incident.tenant_id == tenant_uuid,
                    Incident.status.in_(["open", "in_progress", "investigating"]),
                )
                .order_by(Incident.updated_at.desc(), Incident.created_at.desc())
                .limit(limit)
                .all()
            )

        items: List[Dict[str, Any]] = []
        for incident in incidents:
            raw_payload = incident.raw_payload or {}
            story, story_summary = self._incident_story_context(incident)
            items.append(
                {
                    "id": str(incident.id),
                    "title": incident.title,
                    "severity": (incident.severity or "medium").lower(),
                    "risk_level": incident.severity or "medium",
                    "affected_count": max(story_summary["entity_count"], 1),
                    "description": raw_payload.get("description") or raw_payload.get("summary") or story_summary["detail"],
                    "ai_summary": raw_payload.get("ai_summary"),
                    "ai_proposed_fixes": raw_payload.get("ai_proposed_fixes") or [],
                    "quick_actions": [],
                    "created_at": incident.created_at.isoformat() if incident.created_at else None,
                    "story_domains": story["story_domains"],
                    "story_summary": story_summary,
                    "entities": story["entities"],
                    "evidence": story["evidence"],
                }
            )
        runtime_metrics.set_gauge("now_queue_open_incidents_last", float(len(items)))
        return items

    def _incident_candidates(self, tenant_id: str) -> List[Dict[str, Any]]:
        tenant_uuid = UUID(tenant_id)
        with self.db_session_factory() as db:
            incidents = (
                db.query(Incident)
                .filter(
                    Incident.tenant_id == tenant_uuid,
                    Incident.status.in_(["open", "in_progress", "investigating"]),
                )
                .order_by(Incident.updated_at.desc(), Incident.created_at.desc())
                .limit(8)
                .all()
            )

        items: List[Dict[str, Any]] = []
        for incident in incidents:
            raw_payload = incident.raw_payload or {}
            story, story_summary = self._incident_story_context(incident)
            domains = story["story_domains"] or ["security"]
            domain_phrase = ", ".join(domain.title() for domain in domains[:3])
            evidence_count = len(story["evidence"])
            source_label = (
                raw_payload.get("source_label")
                or ("AI Incident" if "ai" in domains or incident.source == "sentinelgrid_ai_shield" else "Incident")
            )
            items.append(
                {
                    "id": f"incident:{incident.id}",
                    "item_type": "incident",
                    "priority": (incident.severity or "medium").lower(),
                    "title": incident.title,
                    "summary": incident.description or raw_payload.get("summary") or "Open incident requiring operator attention.",
                    "why_now": (
                        f"Open incident spanning {domain_phrase}. "
                        f"{evidence_count} linked evidence item{'s' if evidence_count != 1 else ''} already point at the active story."
                    ),
                    "status": incident.status,
                    "owner": incident.assigned_to,
                    "source_label": source_label,
                    "href": f"/dashboard/incidents/{incident.id}",
                    "action_label": "Review AI incident" if source_label == "AI Incident" else "Open incident",
                    "action_href": f"/dashboard/incidents/{incident.id}",
                    "updated_at": incident.updated_at.isoformat() if incident.updated_at else None,
                    "domains": domains,
                    "entities": story["entities"],
                    "evidence": story["evidence"],
                    "story_summary": story_summary,
                    "sla": raw_payload.get("sla") or raw_payload.get("sla_minutes"),
                }
            )
        return items

    def _alert_candidates(self, tenant_id: str) -> List[Dict[str, Any]]:
        tenant_uuid = UUID(tenant_id)
        with self.db_session_factory() as db:
            alerts = (
                db.query(Alert)
                .filter(
                    Alert.tenant_id == tenant_uuid,
                    Alert.status.in_(["open", "investigating", "acknowledged"]),
                )
                .order_by(Alert.detection_time.desc(), Alert.updated_at.desc())
                .limit(12)
                .all()
            )

        items: List[Dict[str, Any]] = []
        for alert in alerts:
            raw_payload = alert.raw_payload or {}
            if raw_payload.get("incident_id") or raw_payload.get("incident_ids") or raw_payload.get("incidents"):
                continue
            related_detections = []
            for detection in raw_payload.get("detections") or []:
                if isinstance(detection, dict):
                    related_detections.append(
                        {
                            "id": str(detection.get("id") or detection.get("alert_id") or detection.get("title") or "alert"),
                            "title": detection.get("title"),
                            "severity": detection.get("severity"),
                        }
                    )
                else:
                    related_detections.append({"id": str(detection)})
            detection_rule_id = raw_payload.get("detection_rule_id") or (raw_payload.get("sg") or {}).get("detection_rule_id")
            detection_rule_version_id = raw_payload.get("detection_rule_version_id") or (raw_payload.get("sg") or {}).get("detection_rule_version_id")
            playbook_version_id = raw_payload.get("playbook_version_id") or (raw_payload.get("sg") or {}).get("playbook_version_id")
            playbook_id = (
                raw_payload.get("recommended_playbook")
                or raw_payload.get("recommended_playbook_id")
                or raw_payload.get("playbook_id")
                or (raw_payload.get("sg") or {}).get("playbook_id")
            )
            story = build_story_context(
                raw_payload=raw_payload,
                asset_id=alert.asset_id,
                user_identifier=alert.user_identifier,
                detection_rule_id=detection_rule_id,
                detection_rule_version_id=detection_rule_version_id,
                playbook_id=playbook_id,
                playbook_version_id=playbook_version_id,
                related_detections=related_detections,
                cve_ids=alert.cve_ids,
            )
            story_summary = build_story_summary(story_context=story)
            domains = story["story_domains"] or ["security"]
            entities = story["entities"]
            primary_entity = entities[0]["label"] if entities else "the affected entity"
            source_label = (
                raw_payload.get("source_label")
                or ("AI Shield" if "ai" in domains or alert.source == "sentinelgrid_ai_shield" else "Alert")
            )
            items.append(
                {
                    "id": f"alert:{alert.id}",
                    "item_type": "alert",
                    "priority": (getattr(alert, "raw_severity", None) or getattr(alert, "severity", None) or "medium").lower(),
                    "title": alert.title,
                    "summary": alert.description or "Open detection requiring triage.",
                    "why_now": f"High-signal detection still open for {primary_entity}. Triage it before it becomes a larger incident.",
                    "status": alert.status,
                    "owner": raw_payload.get("assigned_to"),
                    "source_label": source_label,
                    "href": f"/dashboard/alerts/{alert.id}",
                    "action_label": "Review AI alert" if source_label == "AI Shield" else "Investigate alert",
                    "action_href": f"/dashboard/alerts/{alert.id}",
                    "updated_at": alert.updated_at.isoformat() if alert.updated_at else None,
                    "domains": domains,
                    "entities": entities,
                    "evidence": story["evidence"],
                    "story_summary": story_summary,
                }
            )
        return items

    def build_queue(
        self,
        tenant_id: str,
        posture_score: Dict[str, Any],
        people_access: Dict[str, Any],
        onboarding_status: Dict[str, Any],
        *,
        limit: int = 8,
    ) -> Dict[str, Any]:
        recommendations = build_recommendations(posture_score, people_access, onboarding_status)
        incidents = self._incident_candidates(tenant_id)
        alerts = self._alert_candidates(tenant_id)
        queue = build_now_queue(incidents, alerts, recommendations, limit=limit)
        queue["generated_at"] = datetime.now(timezone.utc).isoformat()
        queue["tenant_id"] = tenant_id
        summary = queue.get("summary", {})
        runtime_metrics.increment_counter("now_queue_builds_total")
        runtime_metrics.set_gauge("now_queue_items_last", float(summary.get("total_items", 0)))
        runtime_metrics.set_gauge("now_queue_urgent_items_last", float(summary.get("urgent_items", 0)))
        runtime_metrics.set_gauge("now_queue_items_by_type_last", float(summary.get("incidents", 0)), item_type="incident")
        runtime_metrics.set_gauge("now_queue_items_by_type_last", float(summary.get("alerts", 0)), item_type="alert")
        runtime_metrics.set_gauge(
            "now_queue_items_by_type_last",
            float(summary.get("recommendations", 0)),
            item_type="recommendation",
        )
        return queue
