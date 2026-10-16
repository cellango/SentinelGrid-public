"""Tenant-scoped durable evidence repository service."""

from __future__ import annotations

import json
import hashlib
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


DEFAULT_LIMIT = 50
MAX_LIMIT = 200


class EvidenceRepositoryError(ValueError):
    """Raised when evidence repository input cannot be persisted."""


class EvidenceNotFoundError(LookupError):
    """Raised when a tenant-scoped evidence object is not found."""


def _is_uuid(value: str | None) -> bool:
    if not value:
        return False
    try:
        UUID(str(value))
    except (TypeError, ValueError):
        return False
    return True


def _json(value: Any) -> str:
    return json.dumps(value or {}, default=str)


def _json_array(value: Any) -> str:
    return json.dumps(value or [], default=str)


def _row_mapping(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    if isinstance(row, dict):
        return dict(row)
    return {}


def _first_mapping(result: Any) -> dict[str, Any]:
    if hasattr(result, "mappings"):
        mapped = result.mappings()
        if hasattr(mapped, "first"):
            return _row_mapping(mapped.first())
    if hasattr(result, "first"):
        return _row_mapping(result.first())
    return {}


def _all_mappings(result: Any) -> list[dict[str, Any]]:
    if hasattr(result, "mappings"):
        mapped = result.mappings()
        if hasattr(mapped, "all"):
            return [_row_mapping(row) for row in mapped.all()]
    if hasattr(result, "all"):
        return [_row_mapping(row) for row in result.all()]
    return []


def _iso(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _is_expired(value: Any, now: datetime | None = None) -> bool:
    parsed = _parse_datetime(value)
    if not parsed:
        return False
    return parsed <= (now or datetime.now(timezone.utc))


def _hash_json(value: Any) -> str:
    canonical = json.dumps(value or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _actor(actor_id: str | None, fallback: str = "authenticated_user") -> str:
    return (actor_id or fallback).strip() or fallback


def _status_for_review_decision(review_status: str) -> str:
    if review_status == "needs_changes":
        return "needs_changes"
    return review_status


def _serialize_evidence_item(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id")),
        "tenant_id": str(row.get("tenant_id")),
        "realm_name": row.get("realm_name"),
        "package_id": str(row["package_id"]) if row.get("package_id") else None,
        "control_id": str(row["control_id"]) if row.get("control_id") else None,
        "evidence_type": row.get("evidence_type"),
        "title": row.get("evidence_title") or row.get("title"),
        "description": row.get("evidence_description") or row.get("description"),
        "source_system": row.get("source_system"),
        "source_resource_id": row.get("source_resource_id"),
        "collector": row.get("collector") or row.get("collected_by"),
        "collection_method": row.get("collection_method"),
        "collected_at": _iso(row.get("collected_at")),
        "valid_from": _iso(row.get("valid_from")),
        "valid_until": _iso(row.get("valid_until")),
        "hash_sha256": row.get("hash_sha256") or row.get("file_hash"),
        "storage_uri": row.get("storage_uri") or row.get("file_path"),
        "summary": row.get("summary"),
        "sensitivity": row.get("sensitivity"),
        "review_status": row.get("review_status"),
        "metadata": _json_object(row.get("metadata")),
        "provenance": _json_object(row.get("provenance")),
        "integrity_metadata": _json_object(row.get("integrity_metadata")),
        "retention_until": _iso(row.get("retention_until")),
        "created_by": row.get("created_by"),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
        "deleted_at": _iso(row.get("deleted_at")),
        "idempotency_key": row.get("idempotency_key"),
    }


def _serialize_control_link(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id")),
        "tenant_id": str(row.get("tenant_id")),
        "evidence_item_id": str(row.get("evidence_item_id")),
        "control_id": str(row.get("control_id")),
        "control_ref": row.get("control_ref"),
        "control_name": row.get("control_name"),
        "framework_id": str(row["framework_id"]) if row.get("framework_id") else None,
        "framework_code": row.get("framework_code"),
        "framework_name": row.get("framework_name"),
        "evidence_requirement_id": str(row["evidence_requirement_id"]) if row.get("evidence_requirement_id") else None,
        "package_id": str(row["package_id"]) if row.get("package_id") else None,
        "link_type": row.get("link_type"),
        "status": row.get("status"),
        "rationale": row.get("rationale"),
        "linked_by": row.get("linked_by"),
        "linked_at": _iso(row.get("linked_at")),
        "metadata": _json_object(row.get("metadata")),
    }


def _serialize_review(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id")),
        "tenant_id": str(row.get("tenant_id")),
        "evidence_item_id": str(row["evidence_item_id"]) if row.get("evidence_item_id") else None,
        "package_id": str(row["package_id"]) if row.get("package_id") else None,
        "control_link_id": str(row["control_link_id"]) if row.get("control_link_id") else None,
        "review_status": row.get("review_status"),
        "reviewer": row.get("reviewer"),
        "reviewed_at": _iso(row.get("reviewed_at")),
        "review_notes": row.get("review_notes"),
        "rejection_reason": row.get("rejection_reason"),
        "expires_at": _iso(row.get("expires_at")),
        "created_by": row.get("created_by"),
        "created_at": _iso(row.get("created_at")),
        "metadata": _json_object(row.get("metadata")),
    }


def _serialize_package(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id")),
        "tenant_id": str(row.get("tenant_id")),
        "realm_name": row.get("realm_name"),
        "package_name": row.get("package_name"),
        "package_type": row.get("package_type"),
        "framework_id": str(row["framework_id"]) if row.get("framework_id") else None,
        "report_period_start": _iso(row.get("report_period_start")),
        "report_period_end": _iso(row.get("report_period_end")),
        "created_by": row.get("created_by"),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
        "status": row.get("status"),
        "review_status": row.get("review_status"),
        "export_format": row.get("export_format"),
        "storage_uri": row.get("storage_uri") or row.get("file_path"),
        "hash_sha256": row.get("hash_sha256"),
        "file_size_bytes": row.get("file_size_bytes"),
        "description": row.get("description"),
        "summary": row.get("summary"),
        "sensitivity": row.get("sensitivity"),
        "metadata": _json_object(row.get("metadata")),
        "manifest": _json_object(row.get("manifest")),
        "coverage_snapshot": _json_object(row.get("coverage_snapshot")),
        "retention_until": _iso(row.get("retention_until")),
        "deleted_at": _iso(row.get("deleted_at")),
    }


def _serialize_export(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id")),
        "tenant_id": str(row.get("tenant_id")),
        "package_id": str(row.get("package_id")),
        "export_format": row.get("export_format"),
        "status": row.get("status"),
        "requested_by": row.get("requested_by"),
        "requested_at": _iso(row.get("requested_at")),
        "completed_at": _iso(row.get("completed_at")),
        "storage_uri": row.get("storage_uri"),
        "hash_sha256": row.get("hash_sha256"),
        "file_size_bytes": row.get("file_size_bytes"),
        "include_sensitive": row.get("include_sensitive"),
        "manifest": _json_object(row.get("manifest")),
        "expires_at": _iso(row.get("expires_at")),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
        "retention_until": _iso(row.get("retention_until")),
        "metadata": _json_object(row.get("metadata")),
    }


def _serialize_collection_task(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id")),
        "tenant_id": str(row.get("tenant_id")),
        "realm_name": row.get("realm_name"),
        "package_id": str(row["package_id"]) if row.get("package_id") else None,
        "task_name": row.get("task_name"),
        "task_type": row.get("task_type"),
        "status": row.get("status"),
        "source_system": row.get("source_system"),
        "source_resource_id": row.get("source_resource_id"),
        "collector": row.get("collector"),
        "collection_method": row.get("collection_method"),
        "requested_by": row.get("requested_by"),
        "scheduled_for": _iso(row.get("scheduled_for")),
        "due_at": _iso(row.get("due_at")),
        "started_at": _iso(row.get("started_at")),
        "completed_at": _iso(row.get("completed_at")),
        "last_attempt_at": _iso(row.get("last_attempt_at")),
        "retry_count": row.get("retry_count"),
        "evidence_items_created": _json_list(row.get("evidence_items_created")),
        "error_message": row.get("error_message"),
        "metadata": _json_object(row.get("metadata")),
        "retention_until": _iso(row.get("retention_until")),
        "created_by": row.get("created_by"),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
        "idempotency_key": row.get("idempotency_key"),
    }


def _serialize_integrity_verification(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id")),
        "tenant_id": str(row.get("tenant_id")),
        "evidence_item_id": str(row.get("evidence_item_id")),
        "verification_status": row.get("verification_status"),
        "verification_method": row.get("verification_method"),
        "expected_hash_sha256": row.get("expected_hash_sha256"),
        "observed_hash_sha256": row.get("observed_hash_sha256"),
        "verified_by": row.get("verified_by"),
        "verified_at": _iso(row.get("verified_at")),
        "metadata": _json_object(row.get("metadata")),
    }


def _serialize_retention_policy(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id")),
        "tenant_id": str(row.get("tenant_id")),
        "framework_id": str(row["framework_id"]) if row.get("framework_id") else None,
        "subject_type": row.get("subject_type"),
        "retention_days": row.get("retention_days"),
        "policy_name": row.get("policy_name"),
        "description": row.get("description"),
        "legal_hold": bool(row.get("legal_hold")),
        "created_by": row.get("created_by"),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
        "metadata": _json_object(row.get("metadata")),
    }


class EvidenceRepository:
    """Read/write service for tenant-scoped compliance evidence."""

    def list_evidence(
        self,
        db: Session,
        tenant_id: str,
        filters: dict[str, Any],
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = min(max(limit, 1), MAX_LIMIT)
        offset = max(offset, 0)
        where, params = self._evidence_filter_clause(tenant_id, filters)
        params.update({"limit": limit, "offset": offset})

        rows = _all_mappings(
            db.execute(
                text(
                    f"""
                    SELECT ei.*
                    FROM evidence_items ei
                    WHERE {' AND '.join(where)}
                    ORDER BY ei.collected_at DESC, ei.created_at DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            )
        )
        count_row = _first_mapping(
            db.execute(
                text(
                    f"""
                    SELECT COUNT(*) AS count
                    FROM evidence_items ei
                    WHERE {' AND '.join(where)}
                    """
                ),
                params,
            )
        )
        items = []
        for row in rows:
            payload = _serialize_evidence_item(row)
            payload["control_links"] = self.list_control_links(db, tenant_id, evidence_id=str(row["id"]))
            items.append(payload)
        return {
            "tenant_id": tenant_id,
            "items": items,
            "count": int(count_row.get("count") or len(items)),
            "limit": limit,
            "offset": offset,
            "filters": {key: value for key, value in filters.items() if value is not None},
            "source": "evidence_items",
        }

    def count_stale_evidence(self, db: Session, tenant_id: str) -> int:
        """Count accepted evidence that is expired and must not support audit-ready controls."""
        row = _first_mapping(
            db.execute(
                text(
                    """
                    SELECT COUNT(*) AS count
                    FROM evidence_items
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND deleted_at IS NULL
                      AND review_status = 'accepted'
                      AND valid_until <= NOW()
                    """
                ),
                {"tenant_id": tenant_id},
            )
        )
        return int(row.get("count") or 0)

    def create_evidence_item(
        self,
        db: Session,
        tenant_id: str,
        request: dict[str, Any],
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        created_by = _actor(request.get("created_by") or actor_id)
        collected_at = request.get("collected_at") or datetime.now(timezone.utc)
        metadata = dict(request.get("metadata") or {})
        storage_uri = request["storage_uri"]
        hash_sha256 = str(request["hash_sha256"]).lower()
        control_links = list(request.get("control_links") or [])
        primary_control_uuid = self._first_resolved_control_id(db, control_links)
        primary_framework_uuid = self._first_resolved_framework_id(db, control_links)
        idempotency_key = request.get("idempotency_key")
        retention_until = self._retention_until_for_subject(
            db,
            tenant_id,
            "evidence_item",
            framework_id=primary_framework_uuid,
            base_time=request["valid_until"],
        )

        if idempotency_key:
            existing = self._get_evidence_by_idempotency_key(db, tenant_id, idempotency_key)
            if existing:
                payload = _serialize_evidence_item(existing)
                payload["control_links"] = self.list_control_links(db, tenant_id, evidence_id=str(existing["id"]))
                payload["idempotent_replay"] = True
                return payload

        params = {
            "tenant_id": tenant_id,
            "realm_name": request.get("realm_name") or "default",
            "package_id": request.get("package_id") if _is_uuid(request.get("package_id")) else None,
            "control_id": primary_control_uuid,
            "evidence_type": request["evidence_type"],
            "evidence_title": request["title"],
            "evidence_description": request.get("description"),
            "file_path": storage_uri,
            "file_format": metadata.get("file_format"),
            "file_size_bytes": metadata.get("file_size_bytes"),
            "file_hash": hash_sha256,
            "source_system": request["source_system"],
            "source_reference": request["source_resource_id"],
            "source_resource_id": request["source_resource_id"],
            "collected_at": collected_at,
            "collected_by": request["collector"],
            "collector": request["collector"],
            "collection_method": request["collection_method"],
            "valid_from": request["valid_from"],
            "valid_until": request["valid_until"],
            "hash_sha256": hash_sha256,
            "storage_uri": storage_uri,
            "summary": request["summary"],
            "sensitivity": request.get("sensitivity") or "internal",
            "review_status": request.get("review_status") or "pending",
            "created_by": created_by,
            "retention_until": retention_until,
            "metadata": _json(metadata),
            "idempotency_key": idempotency_key,
            "provenance": _json(request.get("provenance")),
            "integrity_metadata": _json(
                {
                    "hash_algorithm": "sha256",
                    "hash_sha256": hash_sha256,
                    **(request.get("integrity_metadata") or {}),
                }
            ),
            "chain_of_custody": _json_array(
                [
                    {
                        "action": "created",
                        "actor": created_by,
                        "timestamp": collected_at.isoformat() if hasattr(collected_at, "isoformat") else str(collected_at),
                    }
                ]
            ),
        }

        try:
            row = _first_mapping(
                db.execute(
                    text(
                        """
                        INSERT INTO evidence_items (
                            tenant_id, realm_name, package_id, control_id,
                            evidence_type, evidence_title, evidence_description,
                            file_path, file_format, file_size_bytes, file_hash,
                            source_system, source_reference, source_resource_id,
                            collected_at, collected_by, collector, collection_method,
                            valid_from, valid_until, hash_sha256, storage_uri, summary,
                            sensitivity, review_status, created_by, retention_until, metadata,
                            idempotency_key, provenance, integrity_metadata, chain_of_custody
                        )
                        VALUES (
                            CAST(:tenant_id AS uuid), :realm_name, CAST(:package_id AS uuid),
                            CAST(:control_id AS uuid), :evidence_type, :evidence_title,
                            :evidence_description, :file_path, :file_format,
                            :file_size_bytes, :file_hash, :source_system,
                            :source_reference, :source_resource_id, :collected_at,
                            :collected_by, :collector, :collection_method, :valid_from,
                            :valid_until, :hash_sha256, :storage_uri, :summary,
                            :sensitivity, :review_status, :created_by, :retention_until,
                            CAST(:metadata AS jsonb), :idempotency_key, CAST(:provenance AS jsonb),
                            CAST(:integrity_metadata AS jsonb), CAST(:chain_of_custody AS jsonb)
                        )
                        RETURNING *
                        """
                    ),
                    params,
                )
            )
        except IntegrityError as exc:
            if idempotency_key:
                existing = self._get_evidence_by_idempotency_key(db, tenant_id, idempotency_key)
                if existing:
                    payload = _serialize_evidence_item(existing)
                    payload["control_links"] = self.list_control_links(db, tenant_id, evidence_id=str(existing["id"]))
                    payload["idempotent_replay"] = True
                    return payload
            raise EvidenceRepositoryError("Evidence item violates repository constraints") from exc

        evidence_id = str(row["id"])
        links = []
        unresolved_links = []
        for link in control_links:
            try:
                links.append(self.link_evidence_to_control(db, tenant_id, evidence_id, link, actor_id=created_by))
            except EvidenceRepositoryError as exc:
                unresolved_links.append({"link": link, "error": str(exc)})
        payload = _serialize_evidence_item(row)
        payload["control_links"] = links
        if unresolved_links:
            payload["unresolved_control_links"] = unresolved_links
        return payload

    def get_evidence_item(self, db: Session, tenant_id: str, evidence_id: str) -> dict[str, Any]:
        row = _first_mapping(
            db.execute(
                text(
                    """
                    SELECT *
                    FROM evidence_items
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND id = CAST(:evidence_id AS uuid)
                      AND deleted_at IS NULL
                    """
                ),
                {"tenant_id": tenant_id, "evidence_id": evidence_id},
            )
        )
        if not row:
            raise EvidenceNotFoundError("Evidence item not found")

        payload = _serialize_evidence_item(row)
        payload["control_links"] = self.list_control_links(db, tenant_id, evidence_id=evidence_id)
        payload["reviews"] = self.list_reviews(db, tenant_id, evidence_id=evidence_id)
        return payload

    def review_evidence_item(
        self,
        db: Session,
        tenant_id: str,
        evidence_id: str,
        request: dict[str, Any],
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        self._assert_evidence_exists(db, tenant_id, evidence_id)
        reviewer = _actor(request.get("reviewer") or actor_id)
        review_status = request["review_status"]
        item_status = _status_for_review_decision(review_status)

        review_row = _first_mapping(
            db.execute(
                text(
                    """
                    INSERT INTO evidence_reviews (
                        tenant_id, evidence_item_id, review_status, reviewer,
                        review_notes, rejection_reason, expires_at, created_by, metadata
                    )
                    VALUES (
                        CAST(:tenant_id AS uuid), CAST(:evidence_id AS uuid),
                        :review_status, :reviewer, :review_notes, :rejection_reason,
                        :expires_at, :created_by, CAST(:metadata AS jsonb)
                    )
                    RETURNING *
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "evidence_id": evidence_id,
                    "review_status": review_status,
                    "reviewer": reviewer,
                    "review_notes": request.get("review_notes"),
                    "rejection_reason": request.get("rejection_reason"),
                    "expires_at": request.get("expires_at"),
                    "created_by": reviewer,
                    "metadata": _json(request.get("metadata")),
                },
            )
        )
        item_row = _first_mapping(
            db.execute(
                text(
                    """
                    UPDATE evidence_items
                    SET review_status = :review_status,
                        updated_by = :updated_by
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND id = CAST(:evidence_id AS uuid)
                      AND deleted_at IS NULL
                    RETURNING *
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "evidence_id": evidence_id,
                    "review_status": item_status,
                    "updated_by": reviewer,
                },
            )
        )
        return {
            "evidence": _serialize_evidence_item(item_row),
            "review": _serialize_review(review_row),
            "source": "evidence_reviews",
        }

    def create_package(
        self,
        db: Session,
        tenant_id: str,
        request: dict[str, Any],
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        created_by = _actor(request.get("created_by") or actor_id)
        framework_uuid = self._resolve_framework_id(db, request.get("framework_id"))
        metadata = dict(request.get("metadata") or {})
        if request.get("framework_id") and not framework_uuid:
            metadata["requested_framework_id"] = request.get("framework_id")
        retention_until = self._retention_until_for_subject(
            db,
            tenant_id,
            "evidence_package",
            framework_id=framework_uuid,
            base_time=request["report_period_end"],
        )

        row = _first_mapping(
            db.execute(
                text(
                    """
                    INSERT INTO evidence_packages (
                        tenant_id, realm_name, package_name, framework_id,
                        report_period_start, report_period_end, created_by,
                        status, package_type, summary, description, sensitivity,
                        review_status, retention_until, metadata
                    )
                    VALUES (
                        CAST(:tenant_id AS uuid), :realm_name, :package_name,
                        CAST(:framework_id AS uuid), CAST(:report_period_start AS date),
                        CAST(:report_period_end AS date), :created_by, 'collecting',
                        :package_type, :summary, :description, :sensitivity, 'pending',
                        :retention_until, CAST(:metadata AS jsonb)
                    )
                    RETURNING *
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "realm_name": request.get("realm_name") or "default",
                    "package_name": request["package_name"],
                    "framework_id": framework_uuid,
                    "report_period_start": request["report_period_start"],
                    "report_period_end": request["report_period_end"],
                    "created_by": created_by,
                    "package_type": request.get("package_type") or "audit_package",
                    "summary": request.get("summary"),
                    "description": request.get("description"),
                    "sensitivity": request.get("sensitivity") or "internal",
                    "retention_until": retention_until,
                    "metadata": _json(metadata),
                },
            )
        )
        package_id = str(row["id"])
        evidence_item_ids = [item for item in request.get("evidence_item_ids") or [] if _is_uuid(item)]
        for evidence_item_id in evidence_item_ids:
            db.execute(
                text(
                    """
                    UPDATE evidence_items
                    SET package_id = CAST(:package_id AS uuid),
                        updated_by = :updated_by
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND id = CAST(:evidence_item_id AS uuid)
                      AND deleted_at IS NULL
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "package_id": package_id,
                    "evidence_item_id": evidence_item_id,
                    "updated_by": created_by,
                },
            )

        payload = _serialize_package(row)
        payload["evidence_item_count"] = len(evidence_item_ids)
        return payload

    def list_packages(
        self,
        db: Session,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        filters = filters or {}
        limit = min(max(limit, 1), MAX_LIMIT)
        offset = max(offset, 0)
        where = ["ep.tenant_id = CAST(:tenant_id AS uuid)", "ep.deleted_at IS NULL"]
        params: dict[str, Any] = {"tenant_id": tenant_id, "limit": limit, "offset": offset}

        if filters.get("status"):
            where.append("ep.status = :status")
            params["status"] = filters["status"]
        if filters.get("review_status"):
            where.append("ep.review_status = :review_status")
            params["review_status"] = filters["review_status"]

        framework_filter = filters.get("framework_id")
        if framework_filter:
            framework_uuid = self._resolve_framework_id(db, framework_filter)
            if framework_uuid:
                where.append("ep.framework_id = CAST(:framework_uuid AS uuid)")
                params["framework_uuid"] = framework_uuid
            else:
                where.append("lower(ep.metadata->>'requested_framework_id') = lower(:framework_ref)")
                params["framework_ref"] = framework_filter

        where_clause = " AND ".join(where)
        rows = _all_mappings(
            db.execute(
                text(
                    f"""
                    SELECT ep.*,
                           (
                               SELECT COUNT(*)
                               FROM evidence_items ei
                               WHERE ei.tenant_id = ep.tenant_id
                                 AND ei.package_id = ep.id
                                 AND ei.deleted_at IS NULL
                           ) AS evidence_item_count
                    FROM evidence_packages ep
                    WHERE {where_clause}
                    ORDER BY ep.created_at DESC, ep.package_name ASC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            )
        )
        count_row = _first_mapping(
            db.execute(
                text(
                    f"""
                    SELECT COUNT(*) AS count
                    FROM evidence_packages ep
                    WHERE {where_clause}
                    """
                ),
                params,
            )
        )
        items = []
        for row in rows:
            payload = _serialize_package(row)
            payload["evidence_item_count"] = int(row.get("evidence_item_count") or 0)
            items.append(payload)

        return {
            "tenant_id": tenant_id,
            "items": items,
            "count": int(count_row.get("count") or 0),
            "limit": limit,
            "offset": offset,
            "filters": filters,
            "source": "evidence_packages",
        }

    def get_package(self, db: Session, tenant_id: str, package_id: str) -> dict[str, Any]:
        row = _first_mapping(
            db.execute(
                text(
                    """
                    SELECT *
                    FROM evidence_packages
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND id = CAST(:package_id AS uuid)
                      AND deleted_at IS NULL
                    """
                ),
                {"tenant_id": tenant_id, "package_id": package_id},
            )
        )
        if not row:
            raise EvidenceNotFoundError("Evidence package not found")

        exports = _all_mappings(
            db.execute(
                text(
                    """
                    SELECT *
                    FROM evidence_exports
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND package_id = CAST(:package_id AS uuid)
                      AND deleted_at IS NULL
                    ORDER BY requested_at DESC
                    """
                ),
                {"tenant_id": tenant_id, "package_id": package_id},
            )
        )
        payload = _serialize_package(row)
        payload["items"] = self._package_items_with_links(db, tenant_id, package_id)
        payload["exports"] = [_serialize_export(item) for item in exports]
        payload["evidence_item_count"] = len(payload["items"])
        return payload

    def create_export(
        self,
        db: Session,
        tenant_id: str,
        package_id: str,
        request: dict[str, Any],
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        package = self._get_package_row(db, tenant_id, package_id)
        if not package:
            raise EvidenceNotFoundError("Evidence package not found")
        requested_by = _actor(request.get("requested_by") or actor_id)
        manifest = self._build_package_export_manifest(db, tenant_id, package_id, request)
        manifest["manifest_hash_sha256"] = _hash_json(manifest)
        retention_until = self._retention_until_for_subject(
            db,
            tenant_id,
            "evidence_export",
            framework_id=str(package["framework_id"]) if package.get("framework_id") else None,
            base_time=datetime.now(timezone.utc),
        )
        row = _first_mapping(
            db.execute(
                text(
                    """
                    INSERT INTO evidence_exports (
                        tenant_id, package_id, export_format, status,
                        requested_by, include_sensitive, manifest, retention_until, metadata
                    )
                    VALUES (
                        CAST(:tenant_id AS uuid), CAST(:package_id AS uuid),
                        :export_format, 'requested', :requested_by,
                        :include_sensitive, CAST(:manifest AS jsonb), :retention_until,
                        CAST(:metadata AS jsonb)
                    )
                    RETURNING *
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "package_id": package_id,
                    "export_format": request["export_format"],
                    "requested_by": requested_by,
                    "include_sensitive": bool(request.get("include_sensitive")),
                    "manifest": _json(manifest),
                    "retention_until": retention_until,
                    "metadata": _json(request.get("metadata")),
                },
            )
        )
        db.execute(
            text(
                """
                UPDATE evidence_packages
                SET status = 'exported',
                    export_format = :export_format,
                    exported_at = NOW(),
                    exported_by = :exported_by
                WHERE tenant_id = CAST(:tenant_id AS uuid)
                  AND id = CAST(:package_id AS uuid)
                  AND deleted_at IS NULL
                """
            ),
            {
                "tenant_id": tenant_id,
                "package_id": package_id,
                "export_format": request["export_format"],
                "exported_by": requested_by,
            },
        )
        return _serialize_export(row)

    def complete_export(
        self,
        db: Session,
        tenant_id: str,
        package_id: str,
        export_id: str,
        request: dict[str, Any],
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        existing = self._get_export_row(db, tenant_id, package_id, export_id)
        if not existing:
            raise EvidenceNotFoundError("Evidence export not found")
        if existing.get("status") == "completed" and existing.get("immutable_after"):
            raise EvidenceRepositoryError("Evidence export is immutable once completed")

        status = request["status"]
        completed_at = request.get("completed_at") or datetime.now(timezone.utc)
        metadata = _json_object(existing.get("metadata"))
        metadata.update(request.get("metadata") or {})
        metadata["finalized_by"] = _actor(actor_id)
        update_values: dict[str, Any] = {
            "tenant_id": tenant_id,
            "package_id": package_id,
            "export_id": export_id,
            "status": status,
            "completed_at": completed_at if status == "completed" else None,
            "storage_uri": request.get("storage_uri"),
            "hash_sha256": str(request["hash_sha256"]).lower() if request.get("hash_sha256") else None,
            "file_size_bytes": request.get("file_size_bytes"),
            "immutable_after": completed_at if status == "completed" else None,
            "updated_by": _actor(actor_id),
            "metadata": _json(metadata),
        }
        row = _first_mapping(
            db.execute(
                text(
                    """
                    UPDATE evidence_exports
                    SET status = :status,
                        completed_at = :completed_at,
                        storage_uri = COALESCE(:storage_uri, storage_uri),
                        hash_sha256 = COALESCE(:hash_sha256, hash_sha256),
                        file_size_bytes = COALESCE(:file_size_bytes, file_size_bytes),
                        immutable_after = COALESCE(:immutable_after, immutable_after),
                        updated_by = :updated_by,
                        metadata = CAST(:metadata AS jsonb)
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND package_id = CAST(:package_id AS uuid)
                      AND id = CAST(:export_id AS uuid)
                      AND deleted_at IS NULL
                    RETURNING *
                    """
                ),
                update_values,
            )
        )
        return _serialize_export(row)

    def verify_evidence_item(
        self,
        db: Session,
        tenant_id: str,
        evidence_id: str,
        request: dict[str, Any],
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        evidence = self._get_evidence_row(db, tenant_id, evidence_id)
        if not evidence:
            raise EvidenceNotFoundError("Evidence item not found")

        expected_hash = str(evidence.get("hash_sha256") or evidence.get("file_hash") or "").lower()
        observed_hash = str(request.get("observed_hash_sha256") or "").lower() or None
        if not observed_hash:
            verification_status = "missing_observed_hash"
        elif observed_hash == expected_hash:
            verification_status = "verified"
        else:
            verification_status = "mismatch"

        verified_by = _actor(request.get("verified_by") or actor_id)
        verification_row = _first_mapping(
            db.execute(
                text(
                    """
                    INSERT INTO evidence_integrity_verifications (
                        tenant_id, evidence_item_id, verification_status,
                        verification_method, expected_hash_sha256, observed_hash_sha256,
                        verified_by, metadata
                    )
                    VALUES (
                        CAST(:tenant_id AS uuid), CAST(:evidence_id AS uuid),
                        :verification_status, :verification_method,
                        :expected_hash_sha256, :observed_hash_sha256, :verified_by,
                        CAST(:metadata AS jsonb)
                    )
                    RETURNING *
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "evidence_id": evidence_id,
                    "verification_status": verification_status,
                    "verification_method": request.get("verification_method") or "hash_compare",
                    "expected_hash_sha256": expected_hash,
                    "observed_hash_sha256": observed_hash,
                    "verified_by": verified_by,
                    "metadata": _json(request.get("metadata")),
                },
            )
        )

        integrity_metadata = _json_object(evidence.get("integrity_metadata"))
        integrity_metadata["last_verification"] = {
            "verification_status": verification_status,
            "verification_method": request.get("verification_method") or "hash_compare",
            "expected_hash_sha256": expected_hash,
            "observed_hash_sha256": observed_hash,
            "verified_by": verified_by,
            "verified_at": _iso(verification_row.get("verified_at")),
        }
        item_row = _first_mapping(
            db.execute(
                text(
                    """
                    UPDATE evidence_items
                    SET integrity_metadata = CAST(:integrity_metadata AS jsonb),
                        updated_by = :updated_by
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND id = CAST(:evidence_id AS uuid)
                      AND deleted_at IS NULL
                    RETURNING *
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "evidence_id": evidence_id,
                    "updated_by": verified_by,
                    "integrity_metadata": _json(integrity_metadata),
                },
            )
        )

        return {
            "evidence": _serialize_evidence_item(item_row),
            "verification": _serialize_integrity_verification(verification_row),
            "source": "evidence_integrity_verifications",
        }

    def list_retention_policies(
        self,
        db: Session,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        filters = filters or {}
        where = ["erp.tenant_id = CAST(:tenant_id AS uuid)", "erp.deleted_at IS NULL"]
        params: dict[str, Any] = {"tenant_id": tenant_id}
        if filters.get("subject_type"):
            where.append("erp.subject_type = :subject_type")
            params["subject_type"] = filters["subject_type"]
        if filters.get("framework_id"):
            framework_uuid = self._resolve_framework_id(db, filters.get("framework_id"))
            if framework_uuid:
                where.append("erp.framework_id = CAST(:framework_id AS uuid)")
                params["framework_id"] = framework_uuid
            else:
                where.append("lower(erp.metadata->>'requested_framework_id') = lower(:requested_framework_id)")
                params["requested_framework_id"] = filters["framework_id"]

        rows = _all_mappings(
            db.execute(
                text(
                    f"""
                    SELECT erp.*
                    FROM evidence_retention_policies erp
                    WHERE {' AND '.join(where)}
                    ORDER BY erp.subject_type ASC, erp.framework_id NULLS FIRST, erp.created_at DESC
                    """
                ),
                params,
            )
        )
        return {
            "tenant_id": tenant_id,
            "items": [_serialize_retention_policy(row) for row in rows],
            "count": len(rows),
            "filters": filters,
            "source": "evidence_retention_policies",
        }

    def upsert_retention_policy(
        self,
        db: Session,
        tenant_id: str,
        request: dict[str, Any],
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        framework_uuid = self._resolve_framework_id(db, request.get("framework_id"))
        metadata = dict(request.get("metadata") or {})
        if request.get("framework_id") and not framework_uuid:
            metadata["requested_framework_id"] = request.get("framework_id")
        actor = _actor(actor_id)
        existing = self._retention_policy_row(
            db,
            tenant_id,
            request["subject_type"],
            framework_uuid,
            include_default=False,
        )
        params = {
            "tenant_id": tenant_id,
            "framework_id": framework_uuid,
            "subject_type": request["subject_type"],
            "retention_days": request["retention_days"],
            "policy_name": request.get("policy_name") or self._default_retention_policy_name(request["subject_type"], framework_uuid),
            "description": request.get("description"),
            "legal_hold": bool(request.get("legal_hold")),
            "created_by": actor,
            "updated_by": actor,
            "metadata": _json(metadata),
        }
        if existing:
            row = _first_mapping(
                db.execute(
                    text(
                        """
                        UPDATE evidence_retention_policies
                        SET retention_days = :retention_days,
                            policy_name = :policy_name,
                            description = :description,
                            legal_hold = :legal_hold,
                            updated_by = :updated_by,
                            metadata = CAST(:metadata AS jsonb)
                        WHERE tenant_id = CAST(:tenant_id AS uuid)
                          AND id = CAST(:policy_id AS uuid)
                          AND deleted_at IS NULL
                        RETURNING *
                        """
                    ),
                    {**params, "policy_id": existing["id"]},
                )
            )
        else:
            row = _first_mapping(
                db.execute(
                    text(
                        """
                        INSERT INTO evidence_retention_policies (
                            tenant_id, framework_id, subject_type, retention_days,
                            policy_name, description, legal_hold, created_by, updated_by, metadata
                        )
                        VALUES (
                            CAST(:tenant_id AS uuid), CAST(:framework_id AS uuid),
                            :subject_type, :retention_days, :policy_name, :description,
                            :legal_hold, :created_by, :updated_by, CAST(:metadata AS jsonb)
                        )
                        RETURNING *
                        """
                    ),
                    params,
                )
            )
        return _serialize_retention_policy(row)

    def schedule_recollection_task(
        self,
        db: Session,
        tenant_id: str,
        evidence_id: str,
        request: dict[str, Any],
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        evidence = self.get_evidence_item(db, tenant_id, evidence_id)
        reason = request.get("reason") or "manual_refresh"
        metadata = {
            "source_evidence_id": evidence_id,
            "source_hash_sha256": evidence.get("hash_sha256"),
            "source_valid_until": evidence.get("valid_until"),
            "reason": reason,
            **(request.get("metadata") or {}),
        }
        task_request = {
            "realm_name": evidence.get("realm_name") or "default",
            "package_id": evidence.get("package_id"),
            "task_name": f"Recollect evidence: {evidence.get('title') or evidence_id}",
            "task_type": "evidence_recollection",
            "status": request.get("task_status") or "pending",
            "source_system": evidence.get("source_system"),
            "source_resource_id": evidence.get("source_resource_id"),
            "collector": evidence.get("collector"),
            "collection_method": evidence.get("collection_method"),
            "requested_by": request.get("requested_by") or actor_id,
            "due_at": request.get("due_at"),
            "metadata": metadata,
            "idempotency_key": f"recollect:{tenant_id}:{evidence_id}:{reason}",
        }
        return self.create_collection_task(db, tenant_id, task_request, actor_id=actor_id)

    def retire_evidence_item(
        self,
        db: Session,
        tenant_id: str,
        evidence_id: str,
        actor_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        actor = _actor(actor_id)
        row = _first_mapping(
            db.execute(
                text(
                    """
                    UPDATE evidence_items
                    SET review_status = 'retired',
                        updated_by = :updated_by,
                        metadata = COALESCE(metadata, '{}'::jsonb) || CAST(:metadata AS jsonb)
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND id = CAST(:evidence_id AS uuid)
                      AND deleted_at IS NULL
                    RETURNING *
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "evidence_id": evidence_id,
                    "updated_by": actor,
                    "metadata": _json({"retired_by": actor, **(metadata or {})}),
                },
            )
        )
        if not row:
            raise EvidenceNotFoundError("Evidence item not found")
        return _serialize_evidence_item(row)

    def delete_evidence_item(
        self,
        db: Session,
        tenant_id: str,
        evidence_id: str,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        actor = _actor(actor_id)
        row = _first_mapping(
            db.execute(
                text(
                    """
                    UPDATE evidence_items
                    SET deleted_at = NOW(),
                        deleted_by = :deleted_by,
                        review_status = 'retired',
                        updated_by = :deleted_by
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND id = CAST(:evidence_id AS uuid)
                      AND deleted_at IS NULL
                    RETURNING *
                    """
                ),
                {"tenant_id": tenant_id, "evidence_id": evidence_id, "deleted_by": actor},
            )
        )
        if not row:
            raise EvidenceNotFoundError("Evidence item not found")
        return _serialize_evidence_item(row)

    def _package_items_with_links(
        self,
        db: Session,
        tenant_id: str,
        package_id: str,
    ) -> list[dict[str, Any]]:
        items = _all_mappings(
            db.execute(
                text(
                    """
                    SELECT *
                    FROM evidence_items
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND package_id = CAST(:package_id AS uuid)
                      AND deleted_at IS NULL
                    ORDER BY collected_at DESC, created_at DESC
                    """
                ),
                {"tenant_id": tenant_id, "package_id": package_id},
            )
        )
        payloads = []
        for item in items:
            payload = _serialize_evidence_item(item)
            payload["control_links"] = self.list_control_links(db, tenant_id, evidence_id=str(item["id"]))
            payloads.append(payload)
        return payloads

    def _build_package_export_manifest(
        self,
        db: Session,
        tenant_id: str,
        package_id: str,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        export_format = request["export_format"]
        include_sensitive = bool(request.get("include_sensitive"))
        items = self._package_items_with_links(db, tenant_id, package_id)
        exportable_items = self._exportable_items(items, include_sensitive)
        excluded_sensitive_items = 0 if include_sensitive else sum(
            1
            for item in items
            if (item.get("sensitivity") or "internal") in {"confidential", "restricted"}
        )
        requested_manifest = dict(request.get("manifest") or {})
        generated_at = datetime.now(timezone.utc).isoformat()

        files = [
            {
                "evidence_item_id": item.get("id"),
                "title": item.get("title"),
                "storage_uri": item.get("storage_uri"),
                "hash_sha256": item.get("hash_sha256"),
                "file_size_bytes": (item.get("metadata") or {}).get("file_size_bytes"),
                "sensitivity": item.get("sensitivity"),
                "valid_until": item.get("valid_until"),
                "review_status": item.get("review_status"),
                "audit_support_status": self._audit_support_status(item),
            }
            for item in exportable_items
        ]
        storage_supported = bool(files) and all(file.get("storage_uri") for file in files)
        expired_item_count = sum(1 for item in items if _is_expired(item.get("valid_until")))
        non_supporting_item_count = sum(1 for item in items if self._audit_support_status(item) != "supporting")

        manifest = {
            "manifest_version": "2026-04-27.phase4.2",
            "tenant_id": tenant_id,
            "package_id": package_id,
            "export_format": export_format,
            "artifact_kind": self._export_artifact_kind(export_format),
            "generated_at": generated_at,
            "include_sensitive": include_sensitive,
            "evidence_item_count": len(items),
            "exported_evidence_item_count": len(exportable_items),
            "excluded_sensitive_item_count": excluded_sensitive_items,
            "excluded_expired_item_count": expired_item_count,
            "excluded_non_supporting_item_count": non_supporting_item_count,
            "storage_supported": storage_supported,
            "storage_state": "ready_for_worker" if storage_supported else "manifest_only",
            "files": files,
            "requested_manifest": requested_manifest,
        }

        if export_format == "csv":
            manifest["csv_columns"] = [
                "framework_id",
                "framework_name",
                "control_id",
                "control_name",
                "evidence_item_id",
                "evidence_title",
                "evidence_type",
                "review_status",
                "valid_until",
                "storage_uri",
                "hash_sha256",
                "audit_support_status",
            ]
            manifest["control_evidence_mapping"] = self._package_control_evidence_mapping(exportable_items)

        return manifest

    def _exportable_items(
        self,
        items: list[dict[str, Any]],
        include_sensitive: bool,
    ) -> list[dict[str, Any]]:
        if include_sensitive:
            candidates = items
        else:
            candidates = [
                item
                for item in items
                if (item.get("sensitivity") or "internal") not in {"confidential", "restricted"}
            ]
        return [
            item
            for item in candidates
            if self._audit_support_status(item) == "supporting"
        ]

    def _audit_support_status(self, item: dict[str, Any]) -> str:
        status = str(item.get("review_status") or "").strip().lower()
        if status != "accepted":
            return f"not_supporting:{status or 'unknown_review_status'}"
        if _is_expired(item.get("valid_until")):
            return "not_supporting:expired"
        return "supporting"

    def _export_artifact_kind(self, export_format: str) -> str:
        if export_format == "zip":
            return "evidence_package_zip"
        if export_format == "csv":
            return "control_evidence_mapping_csv"
        return "evidence_package_pdf"

    def _package_control_evidence_mapping(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in items:
            links = item.get("control_links") or []
            if not links:
                rows.append(self._package_mapping_row(item, {}))
                continue
            for link in links:
                rows.append(self._package_mapping_row(item, link))
        return rows

    def _package_mapping_row(
        self,
        item: dict[str, Any],
        link: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "framework_id": link.get("framework_code") or link.get("framework_id"),
            "framework_name": link.get("framework_name"),
            "control_id": link.get("control_ref") or link.get("control_id") or item.get("control_id"),
            "control_name": link.get("control_name"),
            "link_type": link.get("link_type"),
            "link_status": link.get("status"),
            "evidence_item_id": item.get("id"),
            "evidence_title": item.get("title"),
            "evidence_type": item.get("evidence_type"),
            "review_status": item.get("review_status"),
            "valid_until": item.get("valid_until"),
            "storage_uri": item.get("storage_uri"),
            "hash_sha256": item.get("hash_sha256"),
            "audit_support_status": self._audit_support_status(item),
        }

    def list_collection_tasks(
        self,
        db: Session,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        filters = filters or {}
        limit = min(max(limit, 1), MAX_LIMIT)
        offset = max(offset, 0)
        where = ["ect.tenant_id = CAST(:tenant_id AS uuid)", "ect.deleted_at IS NULL"]
        params: dict[str, Any] = {"tenant_id": tenant_id, "limit": limit, "offset": offset}

        if filters.get("status"):
            where.append("ect.status = :status")
            params["status"] = filters["status"]
        if filters.get("task_type"):
            where.append("ect.task_type = :task_type")
            params["task_type"] = filters["task_type"]
        if filters.get("source_system"):
            where.append("ect.source_system = :source_system")
            params["source_system"] = filters["source_system"]
        if filters.get("package_id") and _is_uuid(filters.get("package_id")):
            where.append("ect.package_id = CAST(:package_id AS uuid)")
            params["package_id"] = filters["package_id"]
        if filters.get("due_before"):
            where.append("ect.due_at <= :due_before")
            params["due_before"] = filters["due_before"]
        if filters.get("due_after"):
            where.append("ect.due_at >= :due_after")
            params["due_after"] = filters["due_after"]

        where_clause = " AND ".join(where)
        rows = _all_mappings(
            db.execute(
                text(
                    f"""
                    SELECT *
                    FROM evidence_collection_tasks ect
                    WHERE {where_clause}
                    ORDER BY
                        CASE WHEN ect.due_at IS NULL THEN 1 ELSE 0 END,
                        ect.due_at ASC,
                        ect.created_at DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            )
        )
        count_row = _first_mapping(
            db.execute(
                text(
                    f"""
                    SELECT COUNT(*) AS count
                    FROM evidence_collection_tasks ect
                    WHERE {where_clause}
                    """
                ),
                params,
            )
        )
        return {
            "tenant_id": tenant_id,
            "items": [_serialize_collection_task(row) for row in rows],
            "count": int(count_row.get("count") or 0),
            "limit": limit,
            "offset": offset,
            "filters": filters,
            "source": "evidence_collection_tasks",
        }

    def create_collection_task(
        self,
        db: Session,
        tenant_id: str,
        request: dict[str, Any],
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        created_by = _actor(request.get("requested_by") or actor_id)
        idempotency_key = request.get("idempotency_key")
        metadata = dict(request.get("metadata") or {})
        retention_until = self._retention_until_for_subject(
            db,
            tenant_id,
            "collection_task",
            framework_id=None,
            base_time=request.get("due_at") or datetime.now(timezone.utc),
        )

        if idempotency_key:
            existing = self._get_task_by_idempotency_key(db, tenant_id, idempotency_key)
            if existing:
                payload = _serialize_collection_task(existing)
                payload["idempotent_replay"] = True
                return payload

        try:
            row = _first_mapping(
                db.execute(
                    text(
                        """
                        INSERT INTO evidence_collection_tasks (
                            tenant_id, realm_name, package_id, task_name, task_type,
                            control_ids, status, error_message, metadata,
                            evidence_requirement_id, source_system, source_resource_id,
                            collector, collection_method, requested_by, due_at,
                            retry_count, created_by, retention_until, idempotency_key
                        )
                        VALUES (
                            CAST(:tenant_id AS uuid), :realm_name, CAST(:package_id AS uuid),
                            :task_name, :task_type, NULL, :status, :error_message,
                            CAST(:metadata AS jsonb), CAST(:evidence_requirement_id AS uuid),
                            :source_system, :source_resource_id, :collector,
                            :collection_method, :requested_by, :due_at, 0,
                            :created_by, :retention_until, :idempotency_key
                        )
                        RETURNING *
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "realm_name": request.get("realm_name") or "default",
                        "package_id": request.get("package_id") if _is_uuid(request.get("package_id")) else None,
                        "task_name": request["task_name"],
                        "task_type": request["task_type"],
                        "status": request.get("status") or "pending",
                        "error_message": request.get("error_message"),
                        "metadata": _json(metadata),
                        "evidence_requirement_id": request.get("evidence_requirement_id")
                        if _is_uuid(request.get("evidence_requirement_id"))
                        else None,
                        "source_system": request.get("source_system"),
                        "source_resource_id": request.get("source_resource_id"),
                        "collector": request.get("collector"),
                        "collection_method": request.get("collection_method"),
                        "requested_by": created_by,
                        "due_at": request.get("due_at"),
                        "created_by": created_by,
                        "retention_until": retention_until,
                        "idempotency_key": idempotency_key,
                    },
                )
            )
        except IntegrityError as exc:
            if idempotency_key:
                existing = self._get_task_by_idempotency_key(db, tenant_id, idempotency_key)
                if existing:
                    payload = _serialize_collection_task(existing)
                    payload["idempotent_replay"] = True
                    return payload
            raise EvidenceRepositoryError("Evidence collection task violates repository constraints") from exc

        return _serialize_collection_task(row)

    def link_evidence_to_control(
        self,
        db: Session,
        tenant_id: str,
        evidence_id: str,
        link: dict[str, Any],
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        control_uuid = self._resolve_control_id(db, link.get("control_id"), link.get("framework_id"))
        if not control_uuid:
            raise EvidenceRepositoryError(f"Compliance control not found: {link.get('control_id')}")

        framework_uuid = self._resolve_framework_id(db, link.get("framework_id"))
        package_id = link.get("package_id") if _is_uuid(link.get("package_id")) else None
        requirement_id = link.get("evidence_requirement_id") if _is_uuid(link.get("evidence_requirement_id")) else None
        linked_by = _actor(actor_id)

        row = _first_mapping(
            db.execute(
                text(
                    """
                    INSERT INTO evidence_control_links (
                        tenant_id, evidence_item_id, control_id, evidence_requirement_id,
                        framework_id, package_id, link_type, status, linked_by,
                        rationale, created_by, metadata
                    )
                    VALUES (
                        CAST(:tenant_id AS uuid), CAST(:evidence_item_id AS uuid),
                        CAST(:control_id AS uuid), CAST(:evidence_requirement_id AS uuid),
                        CAST(:framework_id AS uuid), CAST(:package_id AS uuid),
                        :link_type, 'active', :linked_by, :rationale,
                        :created_by, CAST(:metadata AS jsonb)
                    )
                    ON CONFLICT DO NOTHING
                    RETURNING *
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "evidence_item_id": evidence_id,
                    "control_id": control_uuid,
                    "evidence_requirement_id": requirement_id,
                    "framework_id": framework_uuid,
                    "package_id": package_id,
                    "link_type": link.get("link_type") or "supports",
                    "linked_by": linked_by,
                    "rationale": link.get("rationale"),
                    "created_by": linked_by,
                    "metadata": _json(link.get("metadata")),
                },
            )
        )
        if row:
            return _serialize_control_link(row)
        return {
            "tenant_id": tenant_id,
            "evidence_item_id": evidence_id,
            "control_id": control_uuid,
            "framework_id": framework_uuid,
            "evidence_requirement_id": requirement_id,
            "link_type": link.get("link_type") or "supports",
            "status": "active",
            "linked_by": linked_by,
            "metadata": link.get("metadata") or {},
        }

    def list_control_links(
        self,
        db: Session,
        tenant_id: str,
        evidence_id: str,
    ) -> list[dict[str, Any]]:
        rows = _all_mappings(
            db.execute(
                text(
                    """
                    SELECT ecl.*, cc.control_id AS control_ref, cc.control_name,
                           cf.framework_code, cf.framework_name
                    FROM evidence_control_links ecl
                    LEFT JOIN compliance_controls cc ON cc.id = ecl.control_id
                    LEFT JOIN compliance_frameworks cf ON cf.id = ecl.framework_id
                    WHERE ecl.tenant_id = CAST(:tenant_id AS uuid)
                      AND ecl.evidence_item_id = CAST(:evidence_id AS uuid)
                      AND ecl.deleted_at IS NULL
                    ORDER BY ecl.linked_at DESC
                    """
                ),
                {"tenant_id": tenant_id, "evidence_id": evidence_id},
            )
        )
        return [_serialize_control_link(row) for row in rows]

    def list_reviews(
        self,
        db: Session,
        tenant_id: str,
        evidence_id: str,
    ) -> list[dict[str, Any]]:
        rows = _all_mappings(
            db.execute(
                text(
                    """
                    SELECT *
                    FROM evidence_reviews
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND evidence_item_id = CAST(:evidence_id AS uuid)
                      AND deleted_at IS NULL
                    ORDER BY reviewed_at DESC
                    """
                ),
                {"tenant_id": tenant_id, "evidence_id": evidence_id},
            )
        )
        return [_serialize_review(row) for row in rows]

    def _evidence_filter_clause(
        self,
        tenant_id: str,
        filters: dict[str, Any],
    ) -> tuple[list[str], dict[str, Any]]:
        where = ["ei.tenant_id = CAST(:tenant_id AS uuid)", "ei.deleted_at IS NULL"]
        params: dict[str, Any] = {"tenant_id": tenant_id}

        if filters.get("package_id"):
            where.append("ei.package_id = CAST(:package_id AS uuid)")
            params["package_id"] = filters["package_id"]
        if filters.get("source_system"):
            where.append("ei.source_system = :source_system")
            params["source_system"] = filters["source_system"]
        if filters.get("review_status"):
            where.append("ei.review_status = :review_status")
            params["review_status"] = filters["review_status"]
        if filters.get("expires_before"):
            where.append("ei.valid_until <= :expires_before")
            params["expires_before"] = filters["expires_before"]
        if filters.get("expires_after"):
            where.append("ei.valid_until >= :expires_after")
            params["expires_after"] = filters["expires_after"]

        control_filter = filters.get("control_id")
        if control_filter:
            if _is_uuid(control_filter):
                where.append(
                    """
                    (
                        ei.control_id = CAST(:control_uuid AS uuid)
                        OR EXISTS (
                            SELECT 1 FROM evidence_control_links ecl
                            WHERE ecl.evidence_item_id = ei.id
                              AND ecl.tenant_id = ei.tenant_id
                              AND ecl.control_id = CAST(:control_uuid AS uuid)
                              AND ecl.deleted_at IS NULL
                        )
                    )
                    """
                )
                params["control_uuid"] = control_filter
            else:
                where.append(
                    """
                    EXISTS (
                        SELECT 1
                        FROM evidence_control_links ecl
                        JOIN compliance_controls cc ON cc.id = ecl.control_id
                        WHERE ecl.evidence_item_id = ei.id
                          AND ecl.tenant_id = ei.tenant_id
                          AND lower(cc.control_id) = lower(:control_ref)
                          AND ecl.deleted_at IS NULL
                    )
                    """
                )
                params["control_ref"] = control_filter

        framework_filter = filters.get("framework_id")
        if framework_filter:
            if _is_uuid(framework_filter):
                where.append(
                    """
                    EXISTS (
                        SELECT 1 FROM evidence_control_links ecl
                        WHERE ecl.evidence_item_id = ei.id
                          AND ecl.tenant_id = ei.tenant_id
                          AND ecl.framework_id = CAST(:framework_uuid AS uuid)
                          AND ecl.deleted_at IS NULL
                    )
                    """
                )
                params["framework_uuid"] = framework_filter
            else:
                where.append(
                    """
                    EXISTS (
                        SELECT 1
                        FROM evidence_control_links ecl
                        JOIN compliance_frameworks cf ON cf.id = ecl.framework_id
                        WHERE ecl.evidence_item_id = ei.id
                          AND ecl.tenant_id = ei.tenant_id
                          AND (
                              lower(cf.framework_code) = lower(:framework_ref)
                              OR lower(replace(cf.framework_code, '_', '')) = lower(replace(:framework_ref, '_', ''))
                          )
                          AND ecl.deleted_at IS NULL
                    )
                    """
                )
                params["framework_ref"] = framework_filter

        return where, params

    def _resolve_framework_id(self, db: Session, framework_id: str | None) -> str | None:
        if not framework_id:
            return None
        if _is_uuid(framework_id):
            return str(framework_id)
        row = _first_mapping(
            db.execute(
                text(
                    """
                    SELECT id
                    FROM compliance_frameworks
                    WHERE lower(framework_code) = lower(:framework_id)
                       OR lower(replace(framework_code, '_', '')) = lower(replace(:framework_id, '_', ''))
                    LIMIT 1
                    """
                ),
                {"framework_id": framework_id},
            )
        )
        return str(row["id"]) if row.get("id") else None

    def _resolve_control_id(self, db: Session, control_id: str | None, framework_id: str | None = None) -> str | None:
        if not control_id:
            return None
        if _is_uuid(control_id):
            return str(control_id)
        params = {"control_id": control_id, "framework_id": framework_id}
        framework_clause = ""
        if framework_id:
            framework_clause = """
                AND (
                    lower(cf.framework_code) = lower(:framework_id)
                    OR lower(replace(cf.framework_code, '_', '')) = lower(replace(:framework_id, '_', ''))
                )
            """
        row = _first_mapping(
            db.execute(
                text(
                    f"""
                    SELECT cc.id
                    FROM compliance_controls cc
                    JOIN compliance_frameworks cf ON cf.id = cc.framework_id
                    WHERE lower(cc.control_id) = lower(:control_id)
                    {framework_clause}
                    ORDER BY cc.control_id
                    LIMIT 1
                    """
                ),
                params,
            )
        )
        return str(row["id"]) if row.get("id") else None

    def _first_resolved_control_id(self, db: Session, control_links: list[dict[str, Any]]) -> str | None:
        for link in control_links:
            control_uuid = self._resolve_control_id(db, link.get("control_id"), link.get("framework_id"))
            if control_uuid:
                return control_uuid
        return None

    def _first_resolved_framework_id(self, db: Session, control_links: list[dict[str, Any]]) -> str | None:
        for link in control_links:
            framework_uuid = self._resolve_framework_id(db, link.get("framework_id"))
            if framework_uuid:
                return framework_uuid
        return None

    def _default_retention_policy_name(self, subject_type: str, framework_id: str | None) -> str:
        scope = framework_id or "default"
        return f"{subject_type}:{scope}"

    def _retention_policy_row(
        self,
        db: Session,
        tenant_id: str,
        subject_type: str,
        framework_id: str | None,
        *,
        include_default: bool = True,
    ) -> dict[str, Any]:
        if framework_id and include_default:
            clause = "(framework_id = CAST(:framework_id AS uuid) OR framework_id IS NULL)"
            order_clause = "framework_id NULLS LAST"
        elif framework_id:
            clause = "framework_id = CAST(:framework_id AS uuid)"
            order_clause = "created_at DESC"
        else:
            clause = "framework_id IS NULL"
            order_clause = "created_at DESC"
        return _first_mapping(
            db.execute(
                text(
                    f"""
                    SELECT *
                    FROM evidence_retention_policies
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND subject_type = :subject_type
                      AND deleted_at IS NULL
                      AND {clause}
                    ORDER BY {order_clause}
                    LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id, "subject_type": subject_type, "framework_id": framework_id},
            )
        )

    def _retention_until_for_subject(
        self,
        db: Session,
        tenant_id: str,
        subject_type: str,
        *,
        framework_id: str | None,
        base_time: Any,
    ) -> datetime | None:
        policy = self._retention_policy_row(db, tenant_id, subject_type, framework_id)
        if not policy or policy.get("legal_hold"):
            return None
        base = _parse_datetime(base_time) or datetime.now(timezone.utc)
        try:
            retention_days = int(policy.get("retention_days") or 0)
        except (TypeError, ValueError):
            return None
        if retention_days <= 0:
            return None
        from datetime import timedelta

        return base + timedelta(days=retention_days)

    def _get_evidence_row(self, db: Session, tenant_id: str, evidence_id: str) -> dict[str, Any]:
        return _first_mapping(
            db.execute(
                text(
                    """
                    SELECT *
                    FROM evidence_items
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND id = CAST(:evidence_id AS uuid)
                      AND deleted_at IS NULL
                    """
                ),
                {"tenant_id": tenant_id, "evidence_id": evidence_id},
            )
        )

    def _get_package_row(self, db: Session, tenant_id: str, package_id: str) -> dict[str, Any]:
        return _first_mapping(
            db.execute(
                text(
                    """
                    SELECT *
                    FROM evidence_packages
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND id = CAST(:package_id AS uuid)
                      AND deleted_at IS NULL
                    """
                ),
                {"tenant_id": tenant_id, "package_id": package_id},
            )
        )

    def _get_export_row(
        self,
        db: Session,
        tenant_id: str,
        package_id: str,
        export_id: str,
    ) -> dict[str, Any]:
        return _first_mapping(
            db.execute(
                text(
                    """
                    SELECT *
                    FROM evidence_exports
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND package_id = CAST(:package_id AS uuid)
                      AND id = CAST(:export_id AS uuid)
                      AND deleted_at IS NULL
                    """
                ),
                {"tenant_id": tenant_id, "package_id": package_id, "export_id": export_id},
            )
        )

    def _get_evidence_by_idempotency_key(
        self,
        db: Session,
        tenant_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return _first_mapping(
            db.execute(
                text(
                    """
                    SELECT *
                    FROM evidence_items
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND idempotency_key = :idempotency_key
                      AND deleted_at IS NULL
                    LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id, "idempotency_key": idempotency_key},
            )
        )

    def _get_task_by_idempotency_key(
        self,
        db: Session,
        tenant_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return _first_mapping(
            db.execute(
                text(
                    """
                    SELECT *
                    FROM evidence_collection_tasks
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND idempotency_key = :idempotency_key
                      AND deleted_at IS NULL
                    LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id, "idempotency_key": idempotency_key},
            )
        )

    def _assert_evidence_exists(self, db: Session, tenant_id: str, evidence_id: str) -> None:
        row = _first_mapping(
            db.execute(
                text(
                    """
                    SELECT id
                    FROM evidence_items
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND id = CAST(:evidence_id AS uuid)
                      AND deleted_at IS NULL
                    """
                ),
                {"tenant_id": tenant_id, "evidence_id": evidence_id},
            )
        )
        if not row:
            raise EvidenceNotFoundError("Evidence item not found")

    def _assert_package_exists(self, db: Session, tenant_id: str, package_id: str) -> None:
        row = _first_mapping(
            db.execute(
                text(
                    """
                    SELECT id
                    FROM evidence_packages
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND id = CAST(:package_id AS uuid)
                      AND deleted_at IS NULL
                    """
                ),
                {"tenant_id": tenant_id, "package_id": package_id},
            )
        )
        if not row:
            raise EvidenceNotFoundError("Evidence package not found")


evidence_repository = EvidenceRepository()
