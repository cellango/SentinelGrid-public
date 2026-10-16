"""Alert service for SIEM Agent."""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
from opensearchpy import Search
from fastapi import HTTPException
from opensearchpy.exceptions import NotFoundError, OpenSearchException
from app.core.opensearch import OpenSearchClient
from app.models.alert import Alert, AlertCreate, AlertListResponse
from app.core.config import settings

logger = logging.getLogger(__name__)


class AlertService:
    """Service for alert retrieval and management."""
    
    def __init__(self, opensearch: OpenSearchClient, db=None):
        self.opensearch = opensearch
        self.db = db  # For future PostgreSQL metadata storage if needed
    
    def list_alerts(
        self,
        tenant_id: str,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
        sort: str = "timestamp:desc"
    ) -> AlertListResponse:
        """
        List alerts with filtering and pagination.
        
        Args:
            tenant_id: Tenant ID (required for isolation)
            severity: Filter by severity (low, medium, high, critical)
            status: Filter by status (open, acknowledged, resolved, false_positive)
            start_time: Start of time range
            end_time: End of time range
            limit: Results per page (max 1000)
            offset: Pagination offset
            sort: Sort field and direction (e.g., "timestamp:desc")
        
        Returns:
            AlertListResponse with alerts and pagination info
        """
        # Validate and sanitize inputs
        limit = min(limit, 1000)  # Enforce max limit
        offset = max(offset, 0)  # Ensure non-negative
        
        # Default time range: last 30 days
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(days=30)
        if end_time is None:
            end_time = datetime.utcnow()
        
        # Get indices for time range
        indices = self.opensearch.search_indices(
            tenant_id, "alerts", start_time, end_time
        )
        
        if not indices:
            # Return empty result if no indices
            return AlertListResponse(alerts=[], total=0, limit=limit, offset=offset)
        
        try:
            # Build OpenSearch query
            s = Search(using=self.opensearch.client, index=indices)
            
            # CRITICAL: Always filter by tenant_id for security
            s = s.filter("term", tenant_id=tenant_id)
            
            # Apply filters
            if severity:
                s = s.filter("term", severity=severity)
            if status:
                s = s.filter("term", status=status)
            if start_time:
                s = s.filter("range", timestamp={"gte": start_time.isoformat()})
            if end_time:
                s = s.filter("range", timestamp={"lte": end_time.isoformat()})
            
            # Parse sort
            sort_field, sort_order = sort.split(":") if ":" in sort else (sort, "desc")
            s = s.sort({sort_field: {"order": sort_order}})
            
            # Pagination
            s = s[offset:offset + limit]
            
            # Execute query
            response = s.execute()
            
            # Convert to Alert models
            alerts = []
            for hit in response:
                alert_dict = hit.to_dict()
                alert_dict["id"] = hit.meta.id
                alerts.append(Alert(**alert_dict))
            
            return AlertListResponse(
                alerts=alerts,
                total=response.hits.total.value,
                limit=limit,
                offset=offset
            )
            
        except OpenSearchException as e:
            logger.error(f"OpenSearch query failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to query alerts: {str(e)}"
            )
    
    def get_alert(self, tenant_id: str, alert_id: str) -> Optional[Alert]:
        """
        Get alert by ID with tenant isolation.
        
        Args:
            tenant_id: Tenant ID (required for isolation)
            alert_id: Alert document ID
        
        Returns:
            Alert if found, None otherwise
        """
        # Search in recent indices (last 30 days)
        indices = self.opensearch.search_indices(
            tenant_id, "alerts",
            datetime.utcnow() - timedelta(days=30),
            datetime.utcnow()
        )
        
        try:
            for index_name in indices:
                try:
                    response = self.opensearch.client.get(
                        index=index_name,
                        id=alert_id
                    )
                    
                    source = response["_source"]
                    
                    # CRITICAL: Verify tenant_id matches (security check)
                    if source.get("tenant_id") != tenant_id:
                        logger.warning(
                            f"Alert {alert_id} found but tenant_id mismatch. "
                            f"Expected: {tenant_id}, Found: {source.get('tenant_id')}"
                        )
                        return None
                    
                    source["id"] = response["_id"]
                    # Handle missing optional fields
                    if "events" not in source:
                        source["events"] = []
                    return Alert(**source)
                    
                except NotFoundError:
                    continue  # Try next index
            
            return None  # Alert not found in any index
            
        except OpenSearchException as e:
            logger.error(f"Failed to get alert {alert_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve alert: {str(e)}"
            )
    
    def update_alert(
        self,
        tenant_id: str,
        alert_id: str,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        comments: Optional[str] = None
    ) -> Optional[Alert]:
        """
        Update alert with tenant isolation.
        
        Args:
            tenant_id: Tenant ID
            alert_id: Alert ID
            status: New status
            assigned_to: Assignee user ID
            comments: Comments/notes
        
        Returns:
            Updated Alert if found, None otherwise
        """
        # First, get the alert to verify it exists and belongs to tenant
        alert = self.get_alert(tenant_id, alert_id)
        if not alert:
            return None
        
        # Find which index contains this alert
        indices = self.opensearch.search_indices(
            tenant_id, "alerts",
            datetime.utcnow() - timedelta(days=30),
            datetime.utcnow()
        )
        
        update_body = {
            "doc": {
                "updated_at": datetime.utcnow().isoformat()
            }
        }
        
        if status:
            update_body["doc"]["status"] = status
        if assigned_to:
            update_body["doc"]["assigned_to"] = assigned_to
        if comments:
            update_body["doc"]["comments"] = comments
        
        try:
            for index_name in indices:
                try:
                    self.opensearch.client.update(
                        index=index_name,
                        id=alert_id,
                        body=update_body
                    )
                    # Refresh to make update visible immediately
                    self.opensearch.client.indices.refresh(index=index_name)
                    break
                except NotFoundError:
                    continue
            
            # Return updated alert
            return self.get_alert(tenant_id, alert_id)
            
        except OpenSearchException as e:
            logger.error(f"Failed to update alert {alert_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update alert: {str(e)}"
            )
    
    def add_events_to_alert(
        self,
        tenant_id: str,
        alert_id: str,
        event_ids: List[str]
    ) -> Optional[Alert]:
        """
        Add events to an existing alert (alert enrichment).
        
        Args:
            tenant_id: Tenant ID
            alert_id: Alert ID
            event_ids: List of event document IDs to link to alert
        
        Returns:
            Updated Alert if found, None otherwise
        """
        from uuid import UUID
        
        # Convert alert_id to UUID if it's a string
        try:
            alert_uuid = UUID(alert_id) if isinstance(alert_id, str) else alert_id
        except ValueError:
            return None
        
        # First, verify alert exists and belongs to tenant
        alert = self.get_alert(tenant_id, alert_uuid)
        if not alert:
            return None
        
        # Find which index contains this alert
        indices = self.opensearch.search_indices(
            tenant_id, "alerts",
            datetime.utcnow() - timedelta(days=30),
            datetime.utcnow()
        )
        
        # Get current events list or create new one
        current_events = alert.events if hasattr(alert, 'events') and alert.events else []
        if not isinstance(current_events, list):
            current_events = []
        
        # Add new event IDs (avoid duplicates)
        updated_events = list(set(current_events + event_ids))
        
        update_body = {
            "doc": {
                "events": updated_events,
                "updated_at": datetime.utcnow().isoformat()
            }
        }
        
        try:
            for index_name in indices:
                try:
                    self.opensearch.client.update(
                        index=index_name,
                        id=str(alert_uuid),
                        body=update_body
                    )
                    self.opensearch.client.indices.refresh(index=index_name)
                    break
                except NotFoundError:
                    continue
            
            # Return updated alert
            return self.get_alert(tenant_id, alert_uuid)
            
        except OpenSearchException as e:
            logger.error(f"Failed to add events to alert {alert_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to enrich alert: {str(e)}"
            )
    
    def create_alert(
        self,
        tenant_id: str,
        alert_data: AlertCreate
    ) -> Alert:
        """
        Create a new alert.
        
        Args:
            tenant_id: Tenant UUID (as string)
            alert_data: Alert creation data
        
        Returns:
            Created Alert
        """
        from uuid import uuid4
        
        alert_id = str(uuid4())
        timestamp = alert_data.timestamp or datetime.utcnow()
        first_seen = alert_data.first_seen or timestamp
        last_seen = alert_data.last_seen or timestamp
        
        # Prepare alert document for OpenSearch
        alert_doc = {
            "id": alert_id,
            "tenant_id": str(tenant_id),
            "severity": alert_data.severity,
            "status": alert_data.status,
            "title": alert_data.title,
            "description": alert_data.description,
            "timestamp": timestamp.isoformat(),
            "source": alert_data.source,
            "detection_rule_id": alert_data.detection_rule_id,
            "user_id": alert_data.user_id,
            "source_ip": alert_data.source_ip,
            "tags": alert_data.tags or [],
            "count": alert_data.count,
            "first_seen": first_seen.isoformat(),
            "last_seen": last_seen.isoformat(),
            "assigned_to": alert_data.assigned_to,
            "comments": alert_data.comments,
            "events": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Get index name for today
        index_name = self.opensearch.get_index_name(str(tenant_id), "alerts", timestamp)
        
        try:
            # Ensure index exists
            if not self.opensearch.client.indices.exists(index=index_name):
                # Create index with template
                self.opensearch.client.indices.create(index=index_name)
            
            # Index alert
            self.opensearch.client.index(
                index=index_name,
                id=alert_id,
                body=alert_doc
            )
            
            # Refresh index
            self.opensearch.client.indices.refresh(index=index_name)
            
            logger.info(f"Alert {alert_id} created in index {index_name}")
            
            # Return Alert model
            return Alert(**alert_doc)
            
        except OpenSearchException as e:
            logger.error(f"Failed to create alert: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create alert: {str(e)}"
            )

