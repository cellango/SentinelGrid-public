"""Compliance report snapshot data provider.

This provider captures the evidence and coverage inputs that make a generated
compliance report reproducible after live posture changes.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _review_status_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        status = str(item.get("review_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _is_expired(item: dict[str, Any], now: datetime) -> bool:
    valid_until = item.get("valid_until")
    if not valid_until:
        return False
    try:
        parsed = datetime.fromisoformat(str(valid_until).replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed < now


def _control_gaps_from_coverage(coverage_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for framework in coverage_payloads:
        framework_id = framework.get("framework_id")
        for control in framework.get("controls") or []:
            control_gaps = control.get("gaps") or []
            if control_gaps or control.get("status") in {"not_started", "needs_evidence", "partial", "non_compliant"}:
                gaps.append(
                    {
                        "framework_id": framework_id,
                        "control_id": control.get("control_id") or control.get("id"),
                        "title": control.get("title"),
                        "status": control.get("status"),
                        "gaps": control_gaps,
                    }
                )
    return gaps


class ComplianceReportDataProvider:
    """Fetches tenant-scoped compliance evidence and coverage snapshots."""

    def __init__(
        self,
        compliance_service_url: str | None = None,
        internal_token: str | None = None,
    ) -> None:
        self.compliance_service_url = (compliance_service_url or settings.COMPLIANCE_SERVICE_URL).rstrip("/")
        self.internal_token = internal_token or settings.INTERNAL_SERVICE_TOKEN

    async def build_snapshot(
        self,
        *,
        tenant_id: str,
        date_range: dict[str, str] | None = None,
        report_parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a reproducible evidence-backed compliance report snapshot."""
        report_parameters = report_parameters or {}
        framework_ids = _as_list(report_parameters.get("framework_ids"))
        control_ids = _as_list(report_parameters.get("control_ids"))
        evidence_package_ids = _as_list(report_parameters.get("evidence_package_ids"))
        include_gaps = bool(report_parameters.get("include_gaps", True))
        include_expired = bool(report_parameters.get("include_expired_evidence", False))

        snapshot: dict[str, Any] = {
            "snapshot_version": "2026-04-27.phase4.1",
            "tenant_id": tenant_id,
            "generated_at": _now_iso(),
            "inputs": {
                "framework_ids": framework_ids,
                "control_ids": control_ids,
                "evidence_package_ids": evidence_package_ids,
                "date_range": date_range or {},
                "include_gaps": include_gaps,
                "include_expired_evidence": include_expired,
            },
            "selected_frameworks": None,
            "coverage_snapshots": [],
            "control_status": [],
            "evidence_packages": [],
            "evidence_inventory": None,
            "evidence_summary": {},
            "control_gaps": [],
            "errors": [],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            snapshot["selected_frameworks"] = await self._get(
                client,
                tenant_id,
                "/api/v1/compliance/framework-selections",
                params={},
                errors=snapshot["errors"],
            )
            snapshot["coverage_snapshots"] = await self._coverage_snapshots(
                client,
                tenant_id,
                framework_ids,
                errors=snapshot["errors"],
            )
            snapshot["control_status"] = await self._control_statuses(
                client,
                tenant_id,
                control_ids,
                framework_ids,
                errors=snapshot["errors"],
            )
            snapshot["evidence_packages"] = await self._evidence_packages(
                client,
                tenant_id,
                framework_ids,
                evidence_package_ids,
                errors=snapshot["errors"],
            )
            snapshot["evidence_inventory"] = await self._evidence_inventory(
                client,
                tenant_id,
                framework_ids,
                control_ids,
                include_expired,
                errors=snapshot["errors"],
            )

        snapshot["control_gaps"] = _control_gaps_from_coverage(snapshot["coverage_snapshots"]) if include_gaps else []
        snapshot["evidence_summary"] = self._evidence_summary(snapshot, include_expired)
        snapshot["snapshot_hash_sha256"] = hashlib.sha256(_canonical_json(snapshot).encode("utf-8")).hexdigest()
        snapshot["source"] = "compliance_report_data_provider"
        return snapshot

    async def _get(
        self,
        client: httpx.AsyncClient,
        tenant_id: str,
        path: str,
        *,
        params: dict[str, Any] | None,
        errors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        try:
            response = await client.get(
                f"{self.compliance_service_url}{path}",
                headers={
                    "Authorization": f"Bearer {self.internal_token}",
                    "X-Tenant-ID": tenant_id,
                },
                params={key: value for key, value in (params or {}).items() if value not in (None, "", [])},
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.warning("Failed to fetch compliance report data from %s: %s", path, exc)
            errors.append({"path": path, "error": str(exc)})
            return {"error": str(exc), "path": path}

    async def _coverage_snapshots(
        self,
        client: httpx.AsyncClient,
        tenant_id: str,
        framework_ids: list[str],
        *,
        errors: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if framework_ids:
            return [
                await self._get(
                    client,
                    tenant_id,
                    f"/api/v1/compliance/frameworks/{framework_id}/coverage",
                    params={"limit": 500},
                    errors=errors,
                )
                for framework_id in framework_ids
            ]

        payload = await self._get(
            client,
            tenant_id,
            "/api/v1/compliance/coverage",
            params={"limit": 500},
            errors=errors,
        )
        return payload.get("items", []) if isinstance(payload.get("items"), list) else [payload]

    async def _control_statuses(
        self,
        client: httpx.AsyncClient,
        tenant_id: str,
        control_ids: list[str],
        framework_ids: list[str],
        *,
        errors: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        statuses: list[dict[str, Any]] = []
        framework_id = framework_ids[0] if len(framework_ids) == 1 else None
        for control_id in control_ids:
            statuses.append(
                await self._get(
                    client,
                    tenant_id,
                    f"/api/v1/compliance/controls/{control_id}/status",
                    params={"framework_id": framework_id},
                    errors=errors,
                )
            )
        return statuses

    async def _evidence_packages(
        self,
        client: httpx.AsyncClient,
        tenant_id: str,
        framework_ids: list[str],
        evidence_package_ids: list[str],
        *,
        errors: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if evidence_package_ids:
            return [
                await self._get(
                    client,
                    tenant_id,
                    f"/api/v1/compliance/evidence/packages/{package_id}",
                    params={},
                    errors=errors,
                )
                for package_id in evidence_package_ids
            ]

        packages: list[dict[str, Any]] = []
        for framework_id in framework_ids or [None]:
            payload = await self._get(
                client,
                tenant_id,
                "/api/v1/compliance/evidence/packages",
                params={"framework_id": framework_id, "limit": 50},
                errors=errors,
            )
            packages.extend(payload.get("items", []) if isinstance(payload.get("items"), list) else [])
        return packages

    async def _evidence_inventory(
        self,
        client: httpx.AsyncClient,
        tenant_id: str,
        framework_ids: list[str],
        control_ids: list[str],
        include_expired: bool,
        *,
        errors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": 200}
        if not include_expired:
            params["expires_after"] = _now_iso()
        if len(framework_ids) == 1:
            params["framework_id"] = framework_ids[0]
        if len(control_ids) == 1:
            params["control_id"] = control_ids[0]
        return await self._get(
            client,
            tenant_id,
            "/api/v1/compliance/evidence",
            params=params,
            errors=errors,
        )

    def _evidence_summary(self, snapshot: dict[str, Any], include_expired: bool) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        package_items: list[dict[str, Any]] = []
        package_ids: list[str] = []
        for package in snapshot.get("evidence_packages") or []:
            if package.get("id"):
                package_ids.append(str(package["id"]))
            package_items.extend(package.get("items") or [])

        inventory_items = (snapshot.get("evidence_inventory") or {}).get("items") or []
        all_items = package_items or inventory_items
        non_expired_items = [item for item in all_items if include_expired or not _is_expired(item, now)]
        review_counts = _review_status_counts(non_expired_items)

        return {
            "evidence_package_ids": package_ids,
            "evidence_package_count": len(package_ids),
            "evidence_item_count": len(non_expired_items),
            "accepted_evidence_item_count": review_counts.get("accepted", 0),
            "pending_review_item_count": review_counts.get("pending", 0) + review_counts.get("ready_for_review", 0),
            "expired_evidence_item_count": sum(1 for item in all_items if _is_expired(item, now)),
            "review_status_counts": review_counts,
            "source": "durable_evidence_repository",
        }
