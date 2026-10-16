"""
Audit Log Query API endpoints.

Provides search, filter, and export capabilities for audit logs.
All queries enforce strict tenant isolation.

Security: Users can only view audit logs for their own tenant.
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import csv
import io
import json

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/audit-logs", tags=["audit-logs"])


# ============================================================================
# Models
# ============================================================================

class AuditLogEntry(BaseModel):
    """Audit log entry model."""
    id: Optional[str]
    timestamp: datetime
    tenant_id: str
    action: str
    actor_user_id: Optional[str]
    actor_email: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[dict]
    ip_address: Optional[str]
    user_agent: Optional[str]
    result: Optional[str]  # success, failure


class AuditLogListResponse(BaseModel):
    """Paginated audit log response."""
    items: List[AuditLogEntry]
    total: int
    page: int
    limit: int
    pages: int


class AuditStatsResponse(BaseModel):
    """Audit log statistics."""
    tenant_id: str
    total_events: int
    events_by_action: dict
    events_by_user: dict
    events_last_24h: int
    events_last_7d: int
    events_last_30d: int


# ============================================================================
# Helper Functions
# ============================================================================

async def get_token_data(authorization: str) -> dict:
    """Validate token and extract data."""
    from app.services.token_validator import TokenValidator
    from app.services.keycloak_client import KeycloakClient
    
    keycloak_client = KeycloakClient()
    validator = TokenValidator(keycloak_client)
    result = validator.validate_token(authorization)
    
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if not result.get("tenant_id"):
        raise HTTPException(status_code=403, detail="No tenant_id in token")
    
    return result


def get_db_session():
    """Get database session."""
    if not settings.DB_URL:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    engine = create_engine(settings.DB_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


# ============================================================================
# Audit Log Endpoints
# ============================================================================

@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    action: Optional[str] = Query(None, description="Filter by action"),
    user_id: Optional[str] = Query(None, description="Filter by user_id"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    List audit logs with filtering and pagination.
    
    SECURITY: Only returns logs for authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    logger.info(f"Querying audit logs for tenant {tenant_id}")
    
    try:
        db = get_db_session()
        
        try:
            # Build query - CRITICAL: Always filter by tenant_id
            query = """
                SELECT 
                    id, timestamp, tenant_id, action, actor_user_id, actor_email,
                    resource_type, resource_id, details, ip_address, user_agent, result
                FROM audit_logs
                WHERE tenant_id = :tenant_id
            """
            
            params = {"tenant_id": tenant_id}
            
            # Add filters
            if action:
                query += " AND action = :action"
                params["action"] = action
            
            if user_id:
                query += " AND actor_user_id = :user_id"
                params["user_id"] = user_id
            
            if start_date:
                query += " AND timestamp >= :start_date"
                params["start_date"] = start_date
            
            if end_date:
                query += " AND timestamp <= :end_date"
                params["end_date"] = end_date
            
            if resource_type:
                query += " AND resource_type = :resource_type"
                params["resource_type"] = resource_type
            
            # Order by timestamp desc
            query += " ORDER BY timestamp DESC"
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM ({query}) as q"
            total = db.execute(text(count_query), params).scalar()
            
            # Add pagination
            query += " LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = (page - 1) * limit
            
            # Execute query
            result = db.execute(text(query), params)
            rows = result.fetchall()
            
            # Convert to model
            logs = []
            for row in rows:
                logs.append(AuditLogEntry(
                    id=str(row[0]) if row[0] else None,
                    timestamp=row[1],
                    tenant_id=row[2],
                    action=row[3],
                    actor_user_id=row[4],
                    actor_email=row[5],
                    resource_type=row[6],
                    resource_id=row[7],
                    details=row[8],
                    ip_address=row[9],
                    user_agent=row[10],
                    result=row[11]
                ))
            
            pages = (total + limit - 1) // limit
            
            logger.info(f"Returning {len(logs)} audit logs for tenant {tenant_id}")
            
            return AuditLogListResponse(
                items=logs,
                total=total,
                page=page,
                limit=limit,
                pages=pages
            )
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error querying audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to query audit logs")


@router.get("/search")
async def search_audit_logs(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Search audit logs by text.
    
    Searches in action, actor_email, resource_type, and details fields.
    
    SECURITY: Only searches within authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    try:
        db = get_db_session()
        
        try:
            # Search query - CRITICAL: tenant_id filter
            query = """
                SELECT 
                    id, timestamp, tenant_id, action, actor_user_id, actor_email,
                    resource_type, resource_id, details, ip_address, user_agent, result
                FROM audit_logs
                WHERE tenant_id = :tenant_id
                AND (
                    action ILIKE :search
                    OR actor_email ILIKE :search
                    OR resource_type ILIKE :search
                    OR details::text ILIKE :search
                )
                ORDER BY timestamp DESC
                LIMIT :limit OFFSET :offset
            """
            
            search_pattern = f"%{q}%"
            params = {
                "tenant_id": tenant_id,
                "search": search_pattern,
                "limit": limit,
                "offset": (page - 1) * limit
            }
            
            result = db.execute(text(query), params)
            rows = result.fetchall()
            
            # Convert to model
            logs = []
            for row in rows:
                logs.append(AuditLogEntry(
                    id=str(row[0]) if row[0] else None,
                    timestamp=row[1],
                    tenant_id=row[2],
                    action=row[3],
                    actor_user_id=row[4],
                    actor_email=row[5],
                    resource_type=row[6],
                    resource_id=row[7],
                    details=row[8],
                    ip_address=row[9],
                    user_agent=row[10],
                    result=row[11]
                ))
            
            return {"items": logs, "count": len(logs), "query": q}
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error searching audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to search audit logs")


@router.get("/export")
async def export_audit_logs(
    format: str = Query("csv", pattern="^(csv|json)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Export audit logs to CSV or JSON.
    
    SECURITY: Only exports logs for authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    logger.info(f"Exporting audit logs for tenant {tenant_id} in {format} format")
    
    try:
        db = get_db_session()
        
        try:
            # Query - CRITICAL: tenant filter
            query = """
                SELECT 
                    timestamp, action, actor_email, resource_type, resource_id,
                    details, ip_address, result
                FROM audit_logs
                WHERE tenant_id = :tenant_id
            """
            
            params = {"tenant_id": tenant_id}
            
            if start_date:
                query += " AND timestamp >= :start_date"
                params["start_date"] = start_date
            
            if end_date:
                query += " AND timestamp <= :end_date"
                params["end_date"] = end_date
            
            query += " ORDER BY timestamp DESC LIMIT 10000"  # Max export limit
            
            result = db.execute(text(query), params)
            rows = result.fetchall()
            
            if format == "csv":
                # Generate CSV
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Header
                writer.writerow([
                    "Timestamp", "Action", "User", "Resource Type",
                    "Resource ID", "Details", "IP Address", "Result"
                ])
                
                # Data
                for row in rows:
                    writer.writerow([
                        row[0].isoformat() if row[0] else "",
                        row[1] or "",
                        row[2] or "",
                        row[3] or "",
                        row[4] or "",
                        json.dumps(row[5]) if row[5] else "",
                        row[6] or "",
                        row[7] or ""
                    ])
                
                content = output.getvalue()
                media_type = "text/csv"
                filename = f"audit_logs_{tenant_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
            else:  # JSON
                # Generate JSON
                logs = []
                for row in rows:
                    logs.append({
                        "timestamp": row[0].isoformat() if row[0] else None,
                        "action": row[1],
                        "user": row[2],
                        "resource_type": row[3],
                        "resource_id": row[4],
                        "details": row[5],
                        "ip_address": row[6],
                        "result": row[7]
                    })
                
                content = json.dumps(logs, indent=2)
                media_type = "application/json"
                filename = f"audit_logs_{tenant_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            logger.info(f"Exported {len(rows)} audit logs for tenant {tenant_id}")
            
            return Response(
                content=content,
                media_type=media_type,
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error exporting audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to export audit logs")


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Get audit log statistics for the tenant.
    
    SECURITY: Only returns stats for authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    try:
        db = get_db_session()
        
        try:
            # Total events
            total_query = "SELECT COUNT(*) FROM audit_logs WHERE tenant_id = :tenant_id"
            total = db.execute(text(total_query), {"tenant_id": tenant_id}).scalar()
            
            # Events by action
            action_query = """
                SELECT action, COUNT(*) as count
                FROM audit_logs
                WHERE tenant_id = :tenant_id
                GROUP BY action
                ORDER BY count DESC
                LIMIT 10
            """
            action_result = db.execute(text(action_query), {"tenant_id": tenant_id})
            events_by_action = {row[0]: row[1] for row in action_result.fetchall()}
            
            # Events by user
            user_query = """
                SELECT actor_email, COUNT(*) as count
                FROM audit_logs
                WHERE tenant_id = :tenant_id AND actor_email IS NOT NULL
                GROUP BY actor_email
                ORDER BY count DESC
                LIMIT 10
            """
            user_result = db.execute(text(user_query), {"tenant_id": tenant_id})
            events_by_user = {row[0]: row[1] for row in user_result.fetchall()}
            
            # Time-based counts
            now = datetime.utcnow()
            
            count_24h = db.execute(
                text("SELECT COUNT(*) FROM audit_logs WHERE tenant_id = :tenant_id AND timestamp >= :since"),
                {"tenant_id": tenant_id, "since": now - timedelta(hours=24)}
            ).scalar()
            
            count_7d = db.execute(
                text("SELECT COUNT(*) FROM audit_logs WHERE tenant_id = :tenant_id AND timestamp >= :since"),
                {"tenant_id": tenant_id, "since": now - timedelta(days=7)}
            ).scalar()
            
            count_30d = db.execute(
                text("SELECT COUNT(*) FROM audit_logs WHERE tenant_id = :tenant_id AND timestamp >= :since"),
                {"tenant_id": tenant_id, "since": now - timedelta(days=30)}
            ).scalar()
            
            return AuditStatsResponse(
                tenant_id=tenant_id,
                total_events=total or 0,
                events_by_action=events_by_action,
                events_by_user=events_by_user,
                events_last_24h=count_24h or 0,
                events_last_7d=count_7d or 0,
                events_last_30d=count_30d or 0
            )
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error getting audit stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get audit statistics")

