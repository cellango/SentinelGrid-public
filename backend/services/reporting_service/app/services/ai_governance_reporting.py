"""Leadership-facing AI governance reporting service."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


_SEVERITY_RANK = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


def _normalize_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str) and value:
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


def _normalize_activity_metadata(item: dict[str, Any]) -> dict[str, Any]:
    metadata = item.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _app_key_from_label(label: str) -> str:
    normalized = "".join(char.lower() if char.isalnum() else "-" for char in label).strip("-")
    return normalized or "unknown-ai-workflow"


def _resolve_app_identity(item: dict[str, Any]) -> tuple[str, str]:
    metadata = _normalize_activity_metadata(item)
    candidates = [
        metadata.get("app_id"),
        metadata.get("application_id"),
        metadata.get("application_name"),
        item.get("resource_name"),
        metadata.get("model"),
        metadata.get("module"),
        "Unknown AI workflow",
    ]
    label = next((str(value).strip() for value in candidates if value), "Unknown AI workflow")
    app_id = str(metadata.get("app_id") or metadata.get("application_id") or _app_key_from_label(label)).strip()
    return app_id or "unknown-ai-workflow", label


def _trend(current: int, previous: int) -> str:
    if current > previous:
        return "up"
    if current < previous:
        return "down"
    return "flat"


def _risk_rank(value: Optional[str]) -> int:
    return _SEVERITY_RANK.get((value or "low").lower(), 0)


class AiGovernanceReportingService:
    """Build AI usage and governance reporting for leadership surfaces."""

    def __init__(self) -> None:
        self.internal_token = settings.INTERNAL_SERVICE_TOKEN
        self.orchestrator_url = settings.ORCHESTRATOR_URL
        self.audit_service_url = settings.AUDIT_SERVICE_URL
        engine = create_engine(settings.DB_URL, pool_pre_ping=True)
        self.db_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    async def build_summary(self, tenant_id: str, lookback_days: int = 30) -> dict[str, Any]:
        lookback_days = max(7, min(int(lookback_days or 30), 90))
        now = datetime.now(timezone.utc)
        current_window_start = now - timedelta(days=lookback_days)
        previous_window_start = now - timedelta(days=lookback_days * 2)

        realm_name = self._lookup_realm_name(tenant_id) or "sentinelgrid"
        activity_items = await self._fetch_ai_activity(
            tenant_id=tenant_id,
            realm_name=realm_name,
            start_date=previous_window_start,
            end_date=now,
        )
        current_items = [
            item for item in activity_items
            if _normalize_timestamp(item.get("timestamp") or item.get("created_at")) >= current_window_start
        ]
        previous_items = [
            item for item in activity_items
            if previous_window_start <= _normalize_timestamp(item.get("timestamp") or item.get("created_at")) < current_window_start
        ]

        current_risk = await self._fetch_ai_risk_summary(tenant_id, lookback_days)
        previous_risk = await self._fetch_ai_risk_summary(tenant_id, min(lookback_days * 2, 90))

        app_inventory = self._build_app_inventory(current_items, current_risk)
        previous_app_inventory = self._build_app_inventory(previous_items, {"top_applications": []})
        top_threats = self._build_top_threats(current_risk, previous_risk, app_inventory, previous_app_inventory)
        usage_trend = self._build_usage_trend(current_items, lookback_days, now)
        recent_activity = self._build_recent_activity(current_items)

        active_users = {
            str(item.get("user_email") or item.get("user_id") or "").strip()
            for item in current_items
            if item.get("user_email") or item.get("user_id")
        }
        apps_needing_review = sum(1 for item in app_inventory if item["governance_state"] == "needs_review")
        unclassified_apps = sum(1 for item in app_inventory if item["governance_state"] == "unclassified")
        high_risk_apps = sum(1 for item in app_inventory if _risk_rank(item.get("highest_severity")) >= _risk_rank("high"))
        governance_score = max(
            0,
            100
            - (current_risk.get("active_incidents", 0) * 18)
            - (current_risk.get("open_alerts", 0) * 5)
            - (apps_needing_review * 4)
            - (unclassified_apps * 6),
        )

        actions = [
            {
                "label": "Open AI governance view",
                "href": "/dashboard/ai-governance",
            },
            {
                "label": "Review AI activity evidence",
                "href": "/dashboard/compliance/ai-activity",
            },
            {
                "label": "Open AI response packs",
                "href": "/dashboard/playbooks",
            },
        ]

        return {
            "generated_at": now.isoformat(),
            "realm_name": realm_name,
            "lookback_days": lookback_days,
            "overview": {
                "governance_score": governance_score,
                "active_apps": len(app_inventory),
                "active_users": len(active_users),
                "requests_in_window": len(current_items),
                "open_ai_alerts": current_risk.get("open_alerts", 0),
                "active_ai_incidents": current_risk.get("active_incidents", 0),
                "policy_violations": current_risk.get("policy_violation_alerts", 0),
                "prompt_injection_events": current_risk.get("prompt_injection_alerts", 0),
                "sensitive_data_events": current_risk.get("data_exposure_alerts", 0),
                "apps_needing_review": apps_needing_review,
                "unclassified_apps": unclassified_apps,
                "high_risk_apps": high_risk_apps,
            },
            "risk_breakdown": current_risk.get(
                "severity_breakdown",
                {"critical": 0, "high": 0, "medium": 0, "low": 0},
            ),
            "top_threats": top_threats,
            "usage_trend": usage_trend,
            "app_inventory": app_inventory,
            "recent_activity": recent_activity,
            "priority_actions": actions,
            "top_risk": current_risk.get("top_risk"),
            "current_risk_summary": current_risk.get("summary"),
        }

    def _lookup_realm_name(self, tenant_id: str) -> str:
        with self.db_session_factory() as db:
            row = db.execute(
                text(
                    """
                    SELECT COALESCE(realm_name, 'sentinelgrid')
                    FROM tenants
                    WHERE id::text = :tenant_id
                    LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id},
            ).fetchone()
        if not row:
            return "sentinelgrid"
        return str(row[0] or "sentinelgrid")

    async def _fetch_ai_risk_summary(self, tenant_id: str, lookback_days: int) -> dict[str, Any]:
        url = f"{self.orchestrator_url}/api/v1/orchestrator/tenant/{tenant_id}/ai-risk-summary"
        headers = {
            "Authorization": f"Bearer {self.internal_token}",
            "X-Tenant-ID": tenant_id,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, headers=headers, params={"lookback_days": lookback_days})
            response.raise_for_status()
            return response.json()

    async def _fetch_ai_activity(
        self,
        *,
        tenant_id: str,
        realm_name: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        url = f"{self.audit_service_url}/api/v1/audit/ai-activity"
        params = {
            "tenant_id": tenant_id,
            "realm_name": realm_name,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "limit": 200,
            "offset": 0,
        }

        items: list[dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=20.0) as client:
            while True:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
                batch = payload.get("items") or []
                items.extend(batch)
                if len(batch) < params["limit"] or len(items) >= 1000:
                    break
                params["offset"] += params["limit"]

        return items[:1000]

    def _build_app_inventory(
        self,
        activity_items: list[dict[str, Any]],
        risk_summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        apps: dict[str, dict[str, Any]] = {}

        for item in activity_items:
            app_id, label = _resolve_app_identity(item)
            metadata = _normalize_activity_metadata(item)
            entry = apps.setdefault(
                app_id,
                {
                    "app_id": app_id,
                    "label": label,
                    "models": set(),
                    "modules": set(),
                    "users": set(),
                    "requests_in_window": 0,
                    "policy_hits": 0,
                    "prompt_injection_hits": 0,
                    "sensitive_data_hits": 0,
                    "open_alerts": 0,
                    "active_incidents": 0,
                    "highest_severity": "low",
                    "last_activity": None,
                },
            )

            entry["requests_in_window"] += 1
            if metadata.get("model"):
                entry["models"].add(str(metadata["model"]))
            if metadata.get("module"):
                entry["modules"].add(str(metadata["module"]))
            user_key = str(item.get("user_email") or item.get("user_id") or "").strip()
            if user_key:
                entry["users"].add(user_key)
            if metadata.get("policy_decision") == "blocked" or metadata.get("violation_reason"):
                entry["policy_hits"] += 1
            if metadata.get("prompt_injection_suspected"):
                entry["prompt_injection_hits"] += 1
            if metadata.get("has_pii") or metadata.get("has_secrets"):
                entry["sensitive_data_hits"] += 1

            observed_at = _normalize_timestamp(item.get("timestamp") or item.get("created_at"))
            if not entry["last_activity"] or observed_at > entry["last_activity"]:
                entry["last_activity"] = observed_at

        for item in risk_summary.get("top_applications", []) or []:
            app_id = str(item.get("app_id") or item.get("label") or "unknown-app")
            label = str(item.get("label") or app_id)
            entry = apps.setdefault(
                app_id,
                {
                    "app_id": app_id,
                    "label": label,
                    "models": set(),
                    "modules": set(),
                    "users": set(),
                    "requests_in_window": 0,
                    "policy_hits": 0,
                    "prompt_injection_hits": 0,
                    "sensitive_data_hits": 0,
                    "open_alerts": 0,
                    "active_incidents": 0,
                    "highest_severity": "low",
                    "last_activity": None,
                },
            )
            if entry["label"] in {"Unknown AI workflow", app_id} and label:
                entry["label"] = label
            entry["open_alerts"] = max(entry["open_alerts"], int(item.get("open_alerts", 0) or 0))
            entry["active_incidents"] = max(entry["active_incidents"], int(item.get("active_incidents", 0) or 0))
            if _risk_rank(item.get("highest_severity")) > _risk_rank(entry["highest_severity"]):
                entry["highest_severity"] = str(item.get("highest_severity") or "low")
            entry["policy_hits"] += int(item.get("policy_violations", 0) or 0)
            entry["prompt_injection_hits"] += int(item.get("prompt_injection_alerts", 0) or 0)
            entry["sensitive_data_hits"] += int(item.get("data_exposure_alerts", 0) or 0)
            if item.get("model"):
                entry["models"].add(str(item["model"]))
            if item.get("provider"):
                entry["modules"].add(str(item["provider"]))

        inventory = []
        for entry in apps.values():
            label_lower = entry["label"].lower()
            if entry["active_incidents"] > 0 or _risk_rank(entry["highest_severity"]) >= _risk_rank("high"):
                governance_state = "needs_review"
            elif "unknown" in label_lower or label_lower.startswith("shadow") or label_lower.startswith("unclassified"):
                governance_state = "unclassified"
            elif entry["policy_hits"] > 0 or entry["open_alerts"] > 0:
                governance_state = "guardrail_watch"
            else:
                governance_state = "monitored"

            inventory.append(
                {
                    "app_id": entry["app_id"],
                    "label": entry["label"],
                    "requests_in_window": entry["requests_in_window"],
                    "unique_users": len(entry["users"]),
                    "models": sorted(entry["models"]),
                    "modules": sorted(entry["modules"]),
                    "policy_hits": entry["policy_hits"],
                    "prompt_injection_hits": entry["prompt_injection_hits"],
                    "sensitive_data_hits": entry["sensitive_data_hits"],
                    "open_alerts": entry["open_alerts"],
                    "active_incidents": entry["active_incidents"],
                    "highest_severity": entry["highest_severity"],
                    "governance_state": governance_state,
                    "last_activity": entry["last_activity"].isoformat() if entry["last_activity"] else None,
                }
            )

        inventory.sort(
            key=lambda item: (
                item["active_incidents"],
                item["open_alerts"],
                _risk_rank(item["highest_severity"]),
                item["requests_in_window"],
                item["label"],
            ),
            reverse=True,
        )
        return inventory[:12]

    def _build_top_threats(
        self,
        current_risk: dict[str, Any],
        previous_risk: dict[str, Any],
        current_inventory: list[dict[str, Any]],
        previous_inventory: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        def previous_delta(key: str) -> int:
            return max(
                int(previous_risk.get(key, 0) or 0) - int(current_risk.get(key, 0) or 0),
                0,
            )

        previous_unclassified = sum(
            1 for item in previous_inventory if item["governance_state"] == "unclassified"
        )
        current_unclassified = sum(
            1 for item in current_inventory if item["governance_state"] == "unclassified"
        )

        return [
            {
                "type": "Prompt injection attempts",
                "count": int(current_risk.get("prompt_injection_alerts", 0) or 0),
                "trend": _trend(
                    int(current_risk.get("prompt_injection_alerts", 0) or 0),
                    previous_delta("prompt_injection_alerts"),
                ),
            },
            {
                "type": "Sensitive data exposure",
                "count": int(current_risk.get("data_exposure_alerts", 0) or 0),
                "trend": _trend(
                    int(current_risk.get("data_exposure_alerts", 0) or 0),
                    previous_delta("data_exposure_alerts"),
                ),
            },
            {
                "type": "Policy violations",
                "count": int(current_risk.get("policy_violation_alerts", 0) or 0),
                "trend": _trend(
                    int(current_risk.get("policy_violation_alerts", 0) or 0),
                    previous_delta("policy_violation_alerts"),
                ),
            },
            {
                "type": "Unclassified AI usage",
                "count": current_unclassified,
                "trend": _trend(current_unclassified, previous_unclassified),
            },
        ]

    def _build_usage_trend(
        self,
        items: list[dict[str, Any]],
        lookback_days: int,
        now: datetime,
    ) -> list[dict[str, Any]]:
        bucket_days = 7 if lookback_days <= 42 else 14 if lookback_days <= 75 else 30
        bucket_count = max(4, min(6, (lookback_days + bucket_days - 1) // bucket_days))
        buckets = []
        for index in range(bucket_count):
            bucket_end = now - timedelta(days=bucket_days * (bucket_count - index - 1))
            bucket_start = bucket_end - timedelta(days=bucket_days)
            bucket = {
                "label": bucket_start.strftime("%b %d"),
                "requests": 0,
                "unique_users": set(),
                "policy_hits": 0,
                "start": bucket_start,
                "end": bucket_end,
            }
            buckets.append(bucket)

        for item in items:
            observed_at = _normalize_timestamp(item.get("timestamp") or item.get("created_at"))
            for bucket in buckets:
                if bucket["start"] <= observed_at < bucket["end"]:
                    bucket["requests"] += 1
                    user_key = str(item.get("user_email") or item.get("user_id") or "").strip()
                    if user_key:
                        bucket["unique_users"].add(user_key)
                    metadata = _normalize_activity_metadata(item)
                    if metadata.get("policy_decision") == "blocked" or metadata.get("violation_reason"):
                        bucket["policy_hits"] += 1
                    break

        return [
            {
                "label": bucket["label"],
                "requests": bucket["requests"],
                "unique_users": len(bucket["unique_users"]),
                "policy_hits": bucket["policy_hits"],
            }
            for bucket in buckets
        ]

    def _build_recent_activity(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        recent = []
        for item in sorted(
            items,
            key=lambda entry: _normalize_timestamp(entry.get("timestamp") or entry.get("created_at")),
            reverse=True,
        )[:8]:
            metadata = _normalize_activity_metadata(item)
            app_id, label = _resolve_app_identity(item)
            recent.append(
                {
                    "id": item.get("id"),
                    "timestamp": item.get("timestamp") or item.get("created_at"),
                    "action": item.get("action") or "ai_activity",
                    "user_label": item.get("user_email") or item.get("user_id") or "system",
                    "app_label": label,
                    "model": metadata.get("model"),
                    "module": metadata.get("module"),
                }
            )
        return recent
