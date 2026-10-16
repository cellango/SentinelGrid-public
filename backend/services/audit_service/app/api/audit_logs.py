"""Audit logs API endpoints."""

import logging
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID
from pydantic import BaseModel
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_current_tenant, get_tenant_session

logger = logging.getLogger(__name__)

router = APIRouter()


def _enforce_same_tenant(requested_tenant_id: UUID, current_tenant_id: UUID) -> None:
    if requested_tenant_id != current_tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Tenant ID mismatch. You can only access your own tenant's data.",
        )


class AuditLogCreate(BaseModel):
    tenant_id: UUID
    realm_name: str
    action: str
    actor_user_id: Optional[str] = None
    actor_email: Optional[str] = None
    actor_roles: Optional[List[str]] = None
    action_category: Optional[str] = "general"
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    before_state: Optional[dict] = None
    after_state: Optional[dict] = None
    changes: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    success: Optional[bool] = True
    error_message: Optional[str] = None
    metadata: Optional[dict] = None


@router.post("/logs", status_code=201)
async def write_audit_log(
    event: AuditLogCreate,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Create a new audit entry in audit.platform_audit_logs.
    Ensures tenant_id and realm_name are always populated; actor_user_id defaults to 'system'.
    """
    _enforce_same_tenant(event.tenant_id, current_tenant_id)
    payload = event.model_dump()
    payload["tenant_id"] = str(current_tenant_id)
    payload["actor_user_id"] = payload.get("actor_user_id") or "system"
    payload["action_category"] = payload.get("action_category") or "general"
    # Normalize JSON/array fields for psycopg2
    payload["actor_roles"] = payload.get("actor_roles") or None
    if isinstance(payload.get("metadata"), dict):
        payload["metadata"] = json.dumps(payload["metadata"])
    if isinstance(payload.get("before_state"), dict):
        payload["before_state"] = json.dumps(payload["before_state"])
    if isinstance(payload.get("after_state"), dict):
        payload["after_state"] = json.dumps(payload["after_state"])
    if isinstance(payload.get("changes"), dict):
        payload["changes"] = json.dumps(payload["changes"])

    insert = text(
        """
        INSERT INTO audit.platform_audit_logs (
            tenant_id, realm_name, actor_user_id, actor_email, actor_roles,
            action, action_category, resource_type, resource_id, resource_name,
            before_state, after_state, changes,
            ip_address, user_agent, request_id, session_id,
            success, error_message, metadata
        )
        VALUES (
            :tenant_id, :realm_name, :actor_user_id, :actor_email, :actor_roles,
            :action, :action_category, :resource_type, :resource_id, :resource_name,
            :before_state, :after_state, :changes,
            :ip_address, :user_agent, :request_id, :session_id,
            :success, :error_message, :metadata
        )
        RETURNING id, timestamp
        """
    )
    result = db.execute(insert, payload).fetchone()
    db.commit()
    return {"id": str(result[0]), "timestamp": result[1].isoformat() if result and result[1] else None}


@router.get("/logs")
async def get_audit_logs(
    tenant_id: UUID,
    realm_name: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    action: Optional[str] = Query(None),
    action_category: Optional[str] = Query(None),
    actor_user_id: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    success: Optional[bool] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Get audit logs for a tenant.
    
    Filters:
    - start_date, end_date: Time range
    - action: Specific action
    - actor_user_id: Filter by user
    - resource_type: Filter by resource type
    - success: Filter by success status
    """
    _enforce_same_tenant(tenant_id, current_tenant_id)
    # Build query
    query = """
        SELECT id, tenant_id, realm_name, timestamp, action, action_category,
               actor_user_id, actor_email, resource_type, resource_id, resource_name,
               success, error_message, ip_address, metadata
        FROM audit.platform_audit_logs
        WHERE tenant_id = :tenant_id AND realm_name = :realm_name
    """
    
    params = {
        "tenant_id": str(tenant_id),
        "realm_name": realm_name,
        "limit": limit,
        "offset": offset
    }
    
    if start_date:
        query += " AND timestamp >= :start_date"
        params["start_date"] = start_date
    
    if end_date:
        query += " AND timestamp <= :end_date"
        params["end_date"] = end_date
    
    if action:
        query += " AND action = :action"
        params["action"] = action

    if action_category:
        query += " AND action_category = :action_category"
        params["action_category"] = action_category
    
    if actor_user_id:
        query += " AND actor_user_id = :actor_user_id"
        params["actor_user_id"] = actor_user_id
    
    if resource_type:
        query += " AND resource_type = :resource_type"
        params["resource_type"] = resource_type
    
    if success is not None:
        query += " AND success = :success"
        params["success"] = success
    
    query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"
    
    # Execute query
    result = db.execute(text(query), params)
    logs = result.fetchall()
    
    # Convert to dict
    logs_list = []
    for log in logs:
        logs_list.append({
            "id": str(log[0]),
            "tenant_id": str(log[1]),
            "realm_name": log[2],
            "timestamp": log[3].isoformat() if log[3] else None,
            "action": log[4],
            "action_category": log[5],
            "actor_user_id": log[6],
            "actor_email": log[7],
            "resource_type": log[8],
            "resource_id": log[9],
            "resource_name": log[10],
            "success": log[11],
            "error_message": log[12],
            "ip_address": str(log[13]) if log[13] else None,
            "metadata": log[14]
        })
    
    return {
        "logs": logs_list,
        "count": len(logs_list),
        "limit": limit,
        "offset": offset
    }


@router.get("/logs/{log_id}")
async def get_audit_log(
    log_id: UUID,
    tenant_id: UUID,
    realm_name: str,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Get a specific audit log entry with full details."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    query = text("""
        SELECT id, tenant_id, realm_name, timestamp, action, action_category,
               actor_user_id, actor_email, actor_roles,
               resource_type, resource_id, resource_name,
               before_state, after_state, changes,
               success, error_message,
               ip_address, user_agent, request_id, session_id,
               metadata
        FROM audit.platform_audit_logs
        WHERE id = :log_id AND tenant_id = :tenant_id AND realm_name = :realm_name
    """)
    
    result = db.execute(query, {
        "log_id": str(log_id),
        "tenant_id": str(tenant_id),
        "realm_name": realm_name
    })
    
    log = result.fetchone()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    return {
        "id": str(log[0]),
        "tenant_id": str(log[1]),
        "realm_name": log[2],
        "timestamp": log[3].isoformat() if log[3] else None,
        "action": log[4],
        "action_category": log[5],
        "actor_user_id": log[6],
        "actor_email": log[7],
        "actor_roles": log[8],
        "resource_type": log[9],
        "resource_id": log[10],
        "resource_name": log[11],
        "before_state": log[12],
        "after_state": log[13],
        "changes": log[14],
        "success": log[15],
        "error_message": log[16],
        "ip_address": str(log[17]) if log[17] else None,
        "user_agent": log[18],
        "request_id": log[19],
        "session_id": log[20],
        "metadata": log[21]
    }


@router.get("/ai-activity")
async def get_ai_activity(
    tenant_id: UUID,
    realm_name: str,
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
):
    """
    Get AI-related audit entries (action_category='ai') for a tenant.
    Supports optional time range filters and returns total count for pagination.
    """
    _enforce_same_tenant(tenant_id, current_tenant_id)
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    base_params = {
        "tenant_id": str(tenant_id),
        "realm_name": realm_name,
        "start_date": start_date,
        "end_date": end_date,
        "limit": limit,
        "offset": offset,
    }

    query = text("""
        SELECT id, tenant_id, realm_name, timestamp, action, actor_user_id, actor_email, metadata
        FROM audit.platform_audit_logs
        WHERE tenant_id = :tenant_id AND realm_name = :realm_name
          AND action_category = 'ai'
          AND timestamp >= :start_date AND timestamp <= :end_date
        ORDER BY timestamp DESC
        LIMIT :limit OFFSET :offset
    """)

    count_query = text("""
        SELECT COUNT(*) 
        FROM audit.platform_audit_logs
        WHERE tenant_id = :tenant_id AND realm_name = :realm_name
          AND action_category = 'ai'
          AND timestamp >= :start_date AND timestamp <= :end_date
    """)

    rows = db.execute(query, base_params).fetchall()
    total = db.execute(count_query, base_params).scalar() or 0

    items = []
    for row in rows:
        items.append({
            "id": str(row[0]),
            "tenant_id": str(row[1]),
            "realm_name": row[2],
            "timestamp": row[3].isoformat() if row[3] else None,
            "action": row[4],
            "user_id": row[5],
            "user_email": row[6],
            "metadata": row[7] or {},
            "query": (row[7] or {}).get("query") if isinstance(row[7], dict) else None,
            "sources": (row[7] or {}).get("sources") if isinstance(row[7], dict) else None,
        })

    return {
        "items": items,
        "count": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/ai-activity", status_code=201)
async def write_ai_activity(
    event: AuditLogCreate,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Convenience endpoint to record AI activity with action_category='ai'.
    """
    _enforce_same_tenant(event.tenant_id, current_tenant_id)
    ai_event = event.model_dump()
    ai_event["tenant_id"] = str(current_tenant_id)
    ai_event["action_category"] = "ai"
    ai_event["action"] = ai_event.get("action") or "ai_activity"
    ai_event["actor_user_id"] = ai_event.get("actor_user_id") or "system"
    if isinstance(ai_event.get("metadata"), dict):
        ai_event["metadata"] = json.dumps(ai_event["metadata"])
    if isinstance(ai_event.get("before_state"), dict):
        ai_event["before_state"] = json.dumps(ai_event["before_state"])
    if isinstance(ai_event.get("after_state"), dict):
        ai_event["after_state"] = json.dumps(ai_event["after_state"])
    if isinstance(ai_event.get("changes"), dict):
        ai_event["changes"] = json.dumps(ai_event["changes"])

    insert = text(
        """
        INSERT INTO audit.platform_audit_logs (
            tenant_id, realm_name, actor_user_id, actor_email, actor_roles,
            action, action_category, resource_type, resource_id, resource_name,
            before_state, after_state, changes,
            ip_address, user_agent, request_id, session_id,
            success, error_message, metadata
        )
        VALUES (
            :tenant_id, :realm_name, :actor_user_id, :actor_email, :actor_roles,
            :action, :action_category, :resource_type, :resource_id, :resource_name,
            :before_state, :after_state, :changes,
            :ip_address, :user_agent, :request_id, :session_id,
            :success, :error_message, :metadata
        )
        RETURNING id, timestamp
        """
    )
    row = db.execute(insert, ai_event).fetchone()
    db.commit()
    return {"id": str(row[0]), "timestamp": row[1].isoformat() if row and row[1] else None}


@router.get("/stats")
async def get_audit_stats(
    tenant_id: UUID,
    realm_name: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Get audit statistics for a tenant."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    query = text("""
        SELECT 
            COUNT(*) as total_events,
            COUNT(*) FILTER (WHERE success = true) as successful_events,
            COUNT(*) FILTER (WHERE success = false) as failed_events,
            COUNT(*) FILTER (WHERE action_category = 'auth') as auth_events,
            COUNT(*) FILTER (WHERE action_category = 'iam') as iam_events,
            COUNT(*) FILTER (WHERE action_category = 'config') as config_events,
            COUNT(*) FILTER (WHERE action_category = 'data') as data_events,
            COUNT(*) FILTER (WHERE action_category = 'compliance') as compliance_events,
            COUNT(DISTINCT actor_user_id) as unique_actors
        FROM audit.platform_audit_logs
        WHERE tenant_id = :tenant_id 
          AND realm_name = :realm_name
          AND timestamp >= :start_date 
          AND timestamp <= :end_date
    """)
    
    result = db.execute(query, {
        "tenant_id": str(tenant_id),
        "realm_name": realm_name,
        "start_date": start_date,
        "end_date": end_date
    })
    
    stats = result.fetchone()
    
    return {
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "total_events": stats[0] or 0,
        "successful_events": stats[1] or 0,
        "failed_events": stats[2] or 0,
        "auth_events": stats[3] or 0,
        "iam_events": stats[4] or 0,
        "config_events": stats[5] or 0,
        "data_events": stats[6] or 0,
        "compliance_events": stats[7] or 0,
        "unique_actors": stats[8] or 0
    }


@router.get("/export")
async def export_audit_logs(
    tenant_id: UUID,
    realm_name: str,
    start_date: datetime,
    end_date: datetime,
    format: str = Query("csv", regex="^(csv|json)$"),
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Export audit logs for compliance reporting.
    
    Formats:
    - csv: CSV format for Excel/auditors
    - json: JSON format for programmatic access
    """
    _enforce_same_tenant(tenant_id, current_tenant_id)
    query = text("""
        SELECT timestamp, action, actor_user_id, actor_email,
               resource_type, resource_id, resource_name,
               success, error_message, ip_address
        FROM audit.platform_audit_logs
        WHERE tenant_id = :tenant_id 
          AND realm_name = :realm_name
          AND timestamp >= :start_date 
          AND timestamp <= :end_date
        ORDER BY timestamp DESC
    """)
    
    result = db.execute(query, {
        "tenant_id": str(tenant_id),
        "realm_name": realm_name,
        "start_date": start_date,
        "end_date": end_date
    })
    
    logs = result.fetchall()
    
    if format == "csv":
        # Convert to CSV
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Timestamp", "Action", "Actor User ID", "Actor Email",
            "Resource Type", "Resource ID", "Resource Name",
            "Success", "Error Message", "IP Address"
        ])
        
        # Data
        for log in logs:
            writer.writerow([
                log[0].isoformat() if log[0] else "",
                log[1] or "",
                log[2] or "",
                log[3] or "",
                log[4] or "",
                log[5] or "",
                log[6] or "",
                log[7] if log[7] is not None else "",
                log[8] or "",
                str(log[9]) if log[9] else ""
            ])
        
        return {
            "format": "csv",
            "data": output.getvalue(),
            "filename": f"audit_logs_{tenant_id}_{start_date.date()}_{end_date.date()}.csv"
        }
    
    else:  # json
        logs_list = []
        for log in logs:
            logs_list.append({
                "timestamp": log[0].isoformat() if log[0] else None,
                "action": log[1],
                "actor_user_id": log[2],
                "actor_email": log[3],
                "resource_type": log[4],
                "resource_id": log[5],
                "resource_name": log[6],
                "success": log[7],
                "error_message": log[8],
                "ip_address": str(log[9]) if log[9] else None
            })
        
        return {
            "format": "json",
            "data": logs_list,
            "filename": f"audit_logs_{tenant_id}_{start_date.date()}_{end_date.date()}.json"
        }
