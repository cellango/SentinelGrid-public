from __future__ import annotations

"""Detection rule persistence and cloning for the no-code alarm editor."""

import logging
import json
from typing import List, Optional, Tuple, TYPE_CHECKING
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.opensearch import OpenSearchClient
from app.services.monitor_manager import MonitorManager
from datetime import datetime, timedelta
import httpx
from app.core.config import settings

if TYPE_CHECKING:
    # Imported only for type checking to avoid circular imports at runtime
    from app.api.detection_rules import (
        DetectionRuleCreate,
        DetectionRuleVersion,
        DetectionRuleResponse,
        CloneRequest,
        PreviewRequest,
        PreviewResponse,
        DeploymentStatus,
        PlaybookMapping,
    )

ALLOWED_SEVERITIES = {"critical", "high", "medium", "low", "informational"}


def _schemas():
    """Lazy import to avoid circular dependency with app.api.detection_rules."""
    from app.api import detection_rules as dr

    return dr


def _map_severity_to_level(severity: str) -> str:
    """Map severity to OpenSearch level (1-5)."""
    severity_map = {
        "critical": "1",
        "high": "2",
        "medium": "3",
        "low": "4",
        "informational": "5",
        "info": "5",
    }
    return severity_map.get((severity or "").lower(), "3")

logger = logging.getLogger(__name__)


def _row_to_version(row) -> DetectionRuleVersion:
    dr = _schemas()
    return dr.DetectionRuleVersion(
        id=row["id"],
        version=row["version"],
        index_pattern=row["index_pattern"],
        query=row.get("query") or {},
        trigger_condition=row.get("trigger_condition") or {},
        severity=row["severity"],
        action_config=row["action_config"] or {},
        metadata=row["metadata"] or {},
        is_active=row["is_active"],
        is_template=row["is_template"],
        graph_json=row["graph_json"],
    )


def _assemble_rule(
    rule_row,
    version_rows,
    deployment: Optional["DeploymentStatus"] = None,
    mapping: Optional["PlaybookMapping"] = None,
) -> DetectionRuleResponse:
    dr = _schemas()
    versions = [_row_to_version(vr) for vr in version_rows]
    return dr.DetectionRuleResponse(
        id=rule_row["id"],
        rule_key=rule_row["rule_key"],
        name=rule_row["name"],
        description=rule_row["description"],
        category=rule_row["category"],
        current_version=rule_row["current_version"],
        approval_required=rule_row.get("approval_required", False),
        versions=versions,
        deployment=deployment,
        mapping=mapping,
    )


def _metadata_to_mapping(version_rows) -> Optional["PlaybookMapping"]:
    dr = _schemas()
    if not version_rows:
        return None
    meta = version_rows[0].get("metadata") or {}
    alert_type = meta.get("alert_type")
    playbook_key = meta.get("playbook_id") or meta.get("playbook_key")
    if not alert_type and not playbook_key:
        return None
    return dr.PlaybookMapping(
        alert_type=alert_type,
        playbook_key=playbook_key,
        auto_execute=False,
        requires_approval=True,
    )


def create_rule(db: Session, payload: "DetectionRuleCreate", created_by: str) -> "DetectionRuleResponse":
    """Create detection rule and initial version."""
    dr = _schemas()
    rule_sql = text(
        """
        INSERT INTO security_ops.detection_rules (rule_key, name, description, category, current_version, is_builtin, created_by, tenant_id, approval_required)
        VALUES (:rule_key, :name, :description, :category, :current_version, false, :created_by, :tenant_id, :approval_required)
        RETURNING id, rule_key, name, description, category, current_version, approval_required, tenant_id, is_builtin
        """
    )
    version_sql = text(
        """
        INSERT INTO security_ops.detection_rule_versions (
            rule_id, version, index_pattern, query, trigger_condition, severity,
            action_config, metadata, changelog, is_active, is_template, graph_json, created_by
        )
        VALUES (
            :rule_id, :version, :index_pattern, :query, :trigger_condition, :severity,
            :action_config, :metadata, :changelog, :is_active, :is_template, :graph_json, :created_by
        )
        RETURNING *
        """
    )
    with db.begin():
        rule_row = db.execute(
            rule_sql,
            {
                "rule_key": payload.rule_key,
                "name": payload.name,
                "description": payload.description,
                "category": payload.category,
                "current_version": payload.version.version,
                "created_by": created_by,
                # Caller must set tenant_id via created_by when invoked by tenant APIs;
                # system seeding should pass the system tenant explicitly.
                "tenant_id": payload.tenant_id if hasattr(payload, "tenant_id") else created_by,
                "approval_required": payload.approval_required,
            },
        ).mappings().first()

        ver = payload.version
        version_row = db.execute(
            version_sql,
            {
                "rule_id": rule_row["id"],
                "version": ver.version,
                "index_pattern": ver.index_pattern,
                "query": json.dumps(ver.query),
                "trigger_condition": json.dumps(ver.trigger_condition),
                "severity": ver.severity,
                "action_config": json.dumps(ver.action_config or {}),
                "metadata": json.dumps(ver.metadata or {}),
                "changelog": "Initial version",
                "is_active": ver.is_active,
                "is_template": ver.is_template,
                "graph_json": json.dumps(ver.graph_json) if ver.graph_json is not None else None,
                "created_by": created_by,
            },
        ).mappings().first()

    return _assemble_rule(rule_row, [version_row])


def _get_deployment(db: Session, tenant_id: Optional[str], rule_id: UUID) -> Optional["DeploymentStatus"]:
    dr = _schemas()
    if not tenant_id:
        return None
    try:
        dep_row = db.execute(
            text(
                "SELECT opensearch_monitor_id, opensearch_destination_id, is_enabled, approval_status, rule_version "
                "FROM security_ops.tenant_detection_monitors WHERE tenant_id = CAST(:tenant_id AS uuid) AND rule_id = CAST(:rule_id AS uuid)"
            ),
            {"tenant_id": tenant_id, "rule_id": str(rule_id)},
        ).mappings().first()
    except Exception as exc:  # table may not exist in fresh demos
        logger.warning("tenant_detection_monitors unavailable: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return None
    if not dep_row:
        return None
    return dr.DeploymentStatus(
        monitor_id=dep_row.get("opensearch_monitor_id"),
        destination_id=dep_row.get("opensearch_destination_id"),
        is_enabled=dep_row.get("is_enabled"),
        approval_status=dep_row.get("approval_status"),
        rule_version=dep_row.get("rule_version"),
    )


def _get_mapping(db: Session, tenant_id: Optional[str], rule_id: UUID) -> Optional["PlaybookMapping"]:
    dr = _schemas()
    if not tenant_id:
        return None
    row = db.execute(
        text(
            "SELECT alert_type, playbook_key, auto_execute, requires_approval "
            "FROM security_ops.detection_playbook_mappings WHERE tenant_id = CAST(:tenant_id AS uuid) AND rule_id = CAST(:rule_id AS uuid)"
        ),
        {"tenant_id": tenant_id, "rule_id": str(rule_id)},
    ).mappings().first()
    if not row:
        return None
    return dr.PlaybookMapping(
        alert_type=row.get("alert_type"),
        playbook_key=row.get("playbook_key"),
        auto_execute=row.get("auto_execute", False),
        requires_approval=row.get("requires_approval", False),
    )


def get_rule(db: Session, rule_id: UUID, tenant_id: Optional[str] = None) -> Optional[DetectionRuleResponse]:
    filters = "id = :rule_id"
    params = {"rule_id": rule_id}
    if tenant_id:
        params["tenant_id"] = tenant_id
        params["system_tenant_id"] = settings.SYSTEM_TENANT_ID
        if tenant_id == settings.SYSTEM_TENANT_ID:
            filters += " AND tenant_id = :tenant_id"
        else:
            filters += " AND ((tenant_id = :tenant_id AND COALESCE(is_builtin, false) = false) OR (tenant_id = :system_tenant_id AND is_builtin = true))"

    rule_row = db.execute(
        text(
            f"SELECT id, rule_key, name, description, category, current_version, approval_required, created_by, is_builtin "
            f"FROM security_ops.detection_rules WHERE {filters}"
        ),
        params,
    ).mappings().first()
    if not rule_row:
        return None

    version_rows = db.execute(
        text(
            "SELECT id, version, index_pattern, query, trigger_condition, severity, action_config, "
            "metadata, is_active, is_template, graph_json "
            "FROM security_ops.detection_rule_versions WHERE rule_id = :rule_id ORDER BY created_at DESC"
        ),
        {"rule_id": rule_id},
    ).mappings().all()
    deployment = _get_deployment(db, tenant_id, rule_row["id"])
    mapping = _get_mapping(db, tenant_id, rule_row["id"])
    if not mapping:
        mapping = _metadata_to_mapping(version_rows)
    return _assemble_rule(rule_row, version_rows, deployment, mapping)


def list_rules(db: Session, tenant_id: str) -> List[DetectionRuleResponse]:
    params = {"tenant_id": tenant_id, "system_tenant_id": settings.SYSTEM_TENANT_ID}
    if tenant_id == settings.SYSTEM_TENANT_ID:
        query = (
            "SELECT id, rule_key, name, description, category, current_version, approval_required, created_by, is_builtin "
            "FROM security_ops.detection_rules WHERE tenant_id = :tenant_id ORDER BY rule_key"
        )
    else:
        query = (
            "SELECT id, rule_key, name, description, category, current_version, approval_required, created_by, is_builtin "
            "FROM security_ops.detection_rules "
            "WHERE (tenant_id = :tenant_id AND COALESCE(is_builtin, false) = false) "
            "   OR (tenant_id = :system_tenant_id AND is_builtin = true) "
            "ORDER BY rule_key"
        )

    rule_rows = db.execute(text(query), params).mappings().all()
    if not rule_rows:
        return []

    results: List[DetectionRuleResponse] = []
    for rr in rule_rows:
        version_rows = db.execute(
            text(
                "SELECT id, version, index_pattern, query, trigger_condition, severity, action_config, "
                "metadata, is_active, is_template, graph_json "
                "FROM security_ops.detection_rule_versions WHERE rule_id = :rule_id ORDER BY created_at DESC"
            ),
            {"rule_id": rr["id"]},
        ).mappings().all()
        deployment = _get_deployment(db, tenant_id, rr["id"])
        mapping = _get_mapping(db, tenant_id, rr["id"]) or _metadata_to_mapping(version_rows)
        results.append(_assemble_rule(rr, version_rows, deployment, mapping))
    return results


def clone_rule(db: Session, rule_id: UUID, payload: CloneRequest, created_by: str, tenant_id: str) -> DetectionRuleResponse:
    """Clone a rule/template into a new draft rule."""
    source_rule = get_rule(db, rule_id, tenant_id=tenant_id)
    if not source_rule:
        raise ValueError("Rule not found")
    if not source_rule.versions:
        raise ValueError("Source rule has no versions")

    latest_ver = source_rule.versions[0]
    clone_payload = DetectionRuleCreate(
        rule_key=payload.rule_key,
        name=payload.name,
        description=payload.description or source_rule.description,
        category=source_rule.category,
        version=DetectionRuleVersion(
            version=latest_ver.version,
            index_pattern=latest_ver.index_pattern,
            query=latest_ver.query,
            trigger_condition=latest_ver.trigger_condition,
            severity=latest_ver.severity,
            action_config=latest_ver.action_config,
            metadata=latest_ver.metadata,
            is_active=False,  # Start as draft
            is_template=False,
            graph_json=latest_ver.graph_json,
        ),
        approval_required=source_rule.approval_required,
    )
    new_rule = create_rule(db, clone_payload, created_by)

    # Preserve playbook mapping hints on clone so downstream automation stays linked
    mapping = getattr(source_rule, "mapping", None)
    meta = latest_ver.metadata or {}
    playbook_key = (
        getattr(mapping, "playbook_key", None)
        or meta.get("playbook_key")
        or meta.get("playbook_id")
    )
    alert_type = getattr(mapping, "alert_type", None) or meta.get("alert_type")
    if playbook_key:
        upsert_playbook_mapping(
            db=db,
            tenant_id=tenant_id,
            rule_id=new_rule.id,
            alert_type=alert_type,
            playbook_key=playbook_key,
            auto_execute=getattr(mapping, "auto_execute", False),
            requires_approval=getattr(mapping, "requires_approval", False),
        )

    return new_rule


def deploy_rule(
    db: Session,
    rule_id: UUID,
    tenant_id: str,
    destination_id: str,
    auto_execute: bool = False,
    schedule_minutes: int = 5,
    message_template: Optional[dict] = None,
    severity_override: Optional[str] = None,
) -> tuple[str, Optional[str]]:
    """Deploy or update an OpenSearch monitor for this rule."""
    if not destination_id or not destination_id.strip():
        raise ValueError("destination_id is required")
    if schedule_minutes is not None and schedule_minutes < 1:
        raise ValueError("schedule_minutes must be >= 1")
    if severity_override and severity_override not in ALLOWED_SEVERITIES:
        raise ValueError(f"severity must be one of {', '.join(sorted(ALLOWED_SEVERITIES))}")
    rule = get_rule(db, rule_id, tenant_id=tenant_id)
    if not rule:
        raise ValueError("Rule not found")
    if not destination_id:
        raise ValueError("destination_id is required")

    # Use latest version (assume first in list is latest)
    if not rule.versions:
        raise ValueError("Rule has no versions")
    ver = rule.versions[0]

    # Approval gating: if approval_required and existing record is pending/rejected
    status_row = db.execute(
        text(
            "SELECT approval_status FROM tenant_detection_monitors WHERE tenant_id = :tenant_id::uuid AND rule_id = :rule_id::uuid"
        ),
        {"tenant_id": tenant_id, "rule_id": str(rule_id)},
    ).mappings().first()
    existing_status = status_row.get("approval_status") if status_row else "pending"
    if rule.approval_required and existing_status != "approved":
        raise ValueError("Rule requires approval before deployment")

    # Build monitor payload from version data
    severity_value = severity_override if severity_override in ALLOWED_SEVERITIES else ver.severity
    severity_level = _map_severity_to_level(severity_value)
    interval = max(1, schedule_minutes or 5)
    msg_template = message_template or {"source": "{}"}
    monitor_payload = {
        "type": "monitor",
        "name": f"{rule.rule_key} - Tenant {tenant_id[:8]}",
        "enabled": True,
        "schedule": {
            "period": {"interval": interval, "unit": "MINUTES"}
        },
        "inputs": [
            {
                "search": {
                    "indices": [ver.index_pattern.replace("{tenant_id}", tenant_id)],
                    "query": ver.query
                }
            }
        ],
        "triggers": [
            {
                "name": f"{rule.rule_key}_trigger",
                "severity": severity_level,
                "condition": ver.trigger_condition,
                "actions": [
                    {
                        "name": "webhook_to_soar",
                        "destination_id": destination_id,
                        "message_template": msg_template,
                        "throttle_enabled": True,
                        "throttle": {"value": 5, "unit": "MINUTES"}
                    }
                ]
            }
        ]
    }

    manager = MonitorManager()
    # create monitor asynchronously helper; reusing pattern but synchronous call here
    try:
        # using httpx sync call for simplicity here
        resp = httpx.post(
            f"{manager.opensearch_url}/_plugins/_alerting/monitors",
            json=monitor_payload,
            auth=manager.auth,
            verify=settings.OPENSEARCH_VERIFY_CERTS,
            timeout=30.0,
        )
        resp.raise_for_status()
        monitor_id = resp.json().get("_id")
    except Exception as e:
        logger.error("Failed to create monitor: %s", e)
        raise

    # Track deployment in tenant_detection_monitors
    upsert_sql = text(
        """
        INSERT INTO tenant_detection_monitors (
            tenant_id, rule_id, rule_version, opensearch_monitor_id, opensearch_destination_id,
            is_enabled, custom_config, deployed_at, last_updated, approval_status
        ) VALUES (
            :tenant_id::uuid, :rule_id::uuid, :rule_version, :monitor_id, :destination_id,
            true, :custom_config, NOW(), NOW(), :approval_status
        )
        ON CONFLICT (tenant_id, rule_id) DO UPDATE SET
            rule_version = EXCLUDED.rule_version,
            opensearch_monitor_id = EXCLUDED.opensearch_monitor_id,
            opensearch_destination_id = EXCLUDED.opensearch_destination_id,
            is_enabled = true,
            custom_config = EXCLUDED.custom_config,
            approval_status = EXCLUDED.approval_status,
            last_updated = NOW()
        """
    )
    db.execute(
        upsert_sql,
        {
            "tenant_id": tenant_id,
            "rule_id": str(rule_id),
            "rule_version": ver.version,
            "monitor_id": monitor_id,
            "destination_id": destination_id,
            "custom_config": {"auto_execute": auto_execute},
            "approval_status": "approved",
        },
    )
    db.commit()

    # Upsert playbook mapping if metadata provides hint
    meta = ver.metadata or {}
    upsert_playbook_mapping(
        db=db,
        tenant_id=tenant_id,
        rule_id=rule_id,
        alert_type=meta.get("alert_type"),
        playbook_key=meta.get("playbook_key") or meta.get("playbook_id"),
        auto_execute=auto_execute,
    )

    return monitor_id, destination_id, "approved"


def disable_rule(
    db: Session,
    rule_id: UUID,
    tenant_id: str,
) -> bool:
    """Disable (delete) a deployed monitor for a tenant/rule."""
    row = db.execute(
        text(
            "SELECT opensearch_monitor_id FROM tenant_detection_monitors "
            "WHERE tenant_id = :tenant_id::uuid AND rule_id = :rule_id::uuid"
        ),
        {"tenant_id": tenant_id, "rule_id": str(rule_id)},
    ).mappings().first()
    monitor_id = row.get("opensearch_monitor_id") if row else None

    if monitor_id:
        try:
            # Delete monitor
            httpx.delete(
                f"{MonitorManager().opensearch_url}/_plugins/_alerting/monitors/{monitor_id}",
                auth=MonitorManager().auth,
                verify=settings.OPENSEARCH_VERIFY_CERTS,
                timeout=30.0,
            )
        except Exception as e:
            logger.warning("Failed to delete monitor %s: %s", monitor_id, e)

    db.execute(
        text(
            "UPDATE tenant_detection_monitors SET is_enabled = false, last_updated = NOW() "
            "WHERE tenant_id = :tenant_id::uuid AND rule_id = :rule_id::uuid"
        ),
        {"tenant_id": tenant_id, "rule_id": str(rule_id)},
    )
    db.commit()
    return True


def upsert_playbook_mapping(
    db: Session,
    tenant_id: str,
    rule_id: UUID,
    alert_type: Optional[str],
    playbook_key: Optional[str],
    auto_execute: bool,
    requires_approval: bool = False,
) -> None:
    """Upsert detection to playbook mapping based on rule metadata."""
    if not alert_type or not playbook_key:
        return
    sql = text(
        """
        INSERT INTO detection_playbook_mappings (
            tenant_id, rule_id, alert_type, playbook_key, auto_execute, requires_approval
        ) VALUES (
            :tenant_id::uuid, :rule_id::uuid, :alert_type, :playbook_key, :auto_execute, :requires_approval
        )
        ON CONFLICT (tenant_id, alert_type) DO UPDATE SET
            playbook_key = EXCLUDED.playbook_key,
            auto_execute = EXCLUDED.auto_execute,
            requires_approval = EXCLUDED.requires_approval,
            updated_at = NOW()
        """
    )
    db.execute(
        sql,
        {
            "tenant_id": tenant_id,
            "rule_id": str(rule_id),
            "alert_type": alert_type,
            "playbook_key": playbook_key,
            "auto_execute": auto_execute,
            "requires_approval": requires_approval,
        },
    )
    db.commit()


def set_rule_approval_status(
    db: Session,
    rule_id: UUID,
    tenant_id: str,
    approval_status: str,
) -> str:
    """Approve or reject a rule deployment for a tenant."""
    if approval_status not in ("approved", "rejected", "pending"):
        raise ValueError("Invalid approval status")

    # Ensure rule exists
    rule = get_rule(db, rule_id, tenant_id=tenant_id)
    if not rule:
        raise ValueError("Rule not found")

    # Upsert monitor record with status only
    sql = text(
        """
        INSERT INTO tenant_detection_monitors (tenant_id, rule_id, rule_version, opensearch_monitor_id,
                                               opensearch_destination_id, is_enabled, custom_config,
                                               deployed_at, last_updated, approval_status)
        VALUES (:tenant_id::uuid, :rule_id::uuid, :rule_version, NULL, NULL, false, '{}', NOW(), NOW(), :approval_status)
        ON CONFLICT (tenant_id, rule_id) DO UPDATE SET
            approval_status = EXCLUDED.approval_status,
            last_updated = NOW()
        """
    )
    db.execute(
        sql,
        {
            "tenant_id": tenant_id,
            "rule_id": str(rule_id),
            "rule_version": rule.versions[0].version if rule.versions else "1.0.0",
            "approval_status": approval_status,
        },
    )
    db.commit()
    return approval_status


def preview_rule(
    tenant_id: str,
    realm: str,
    req: PreviewRequest,
    sample_size: int = 5,
) -> PreviewResponse:
    """Run a preview search against detection events for this tenant."""
    client = OpenSearchClient()

    # Normalize index pattern with tenant_id placeholder
    index_pattern = req.index_pattern.replace("{tenant_id}", tenant_id).replace("{tenant}", tenant_id)

    # Inject tenant filter into query
    base_query = req.query or {}
    if not base_query or not base_query.get("query") or base_query.get("query") == {"match_all": {}}:
        raise ValueError("Preview requires a non-empty query; match_all is not allowed.")
    tenant_filter = {"term": {"sg.tenant_id": tenant_id}}

    # Wrap into bool filter if needed
    if "bool" in base_query.get("query", {}):
        filters = base_query["query"]["bool"].get("filter", [])
        filters.append(tenant_filter)
        base_query["query"]["bool"]["filter"] = filters
    else:
        base_query = {
            "query": {
                "bool": {
                    "filter": [
                        base_query.get("query", {"match_all": {}}),
                        tenant_filter,
                    ]
                }
            }
        }

    # Time range filter
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=req.time_range_minutes)
    time_filter = {"range": {"@timestamp": {"gte": start_time.isoformat(), "lte": end_time.isoformat()}}}
    base_query["query"]["bool"]["filter"].append(time_filter)

    # Limit sample size
    base_query["size"] = sample_size
    base_query["sort"] = [{"@timestamp": {"order": "desc"}}]

    try:
        resp = client.client.search(index=index_pattern, body=base_query)
        hits = resp.get("hits", {})
        total = hits.get("total", {}).get("value", 0)
        sample = [h.get("_source", {}) for h in hits.get("hits", [])]
        aggs = resp.get("aggregations")
        return PreviewResponse(hits=total, sample=sample, aggregations=aggs)
    except Exception as e:
        logger.error("Preview search failed: %s", e)
        raise
