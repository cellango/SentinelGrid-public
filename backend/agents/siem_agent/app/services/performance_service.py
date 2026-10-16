"""Performance optimization service for SIEM Agent."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from opensearchpy import Search
from opensearchpy.exceptions import OpenSearchException
from fastapi import HTTPException
from app.core.opensearch import OpenSearchClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class PerformanceService:
    """Service for performance optimizations and query tuning."""
    
    def __init__(self, opensearch: OpenSearchClient):
        self.opensearch = opensearch
    
    def optimize_query(self, search: Search, tenant_id: str, time_range: Dict[str, datetime]) -> Search:
        """
        Optimize OpenSearch query for performance.
        
        Args:
            search: OpenSearch Search object
            tenant_id: Tenant ID
            time_range: Dict with 'start' and 'end' datetime
        
        Returns:
            Optimized Search object
        """
        # 1. Always filter by tenant_id first (most selective)
        search = search.filter("term", tenant_id=tenant_id)
        
        # 2. Add time range filter early (indexes are time-based)
        if "start" in time_range or "end" in time_range:
            time_filter = {}
            if "start" in time_range:
                time_filter["gte"] = time_range["start"].isoformat()
            if "end" in time_range:
                time_filter["lte"] = time_range["end"].isoformat()
            search = search.filter("range", timestamp=time_filter)
        
        # 3. Use specific indices instead of wildcards when possible
        # (Already handled by search_indices method)
        
        # 4. Limit result size early
        if not hasattr(search, '_extra') or search._extra.get('size') is None:
            search = search[:100]  # Default limit
        
        return search
    
    def get_index_aliases(self, tenant_id: str, index_type: str) -> Dict[str, List[str]]:
        """
        Get index aliases for faster querying.
        
        Args:
            tenant_id: Tenant ID
            index_type: logs, alerts, or events
        
        Returns:
            Dict mapping alias names to index lists
        """
        try:
            pattern = f"sg-{tenant_id}-{index_type}-*"
            aliases = self.opensearch.client.indices.get_alias(pattern)
            
            result = {}
            for index_name, index_data in aliases.items():
                alias_names = list(index_data.get("aliases", {}).keys())
                if alias_names:
                    for alias in alias_names:
                        if alias not in result:
                            result[alias] = []
                        result[alias].append(index_name)
            
            return result
            
        except OpenSearchException as e:
            logger.warning(f"Failed to get index aliases: {e}")
            return {}
    
    def create_index_alias(
        self,
        tenant_id: str,
        index_type: str,
        alias_name: str,
        indices: Optional[List[str]] = None
    ) -> bool:
        """
        Create index alias for faster querying.
        
        Args:
            tenant_id: Tenant ID
            index_type: logs, alerts, or events
            alias_name: Name of the alias
            indices: Optional list of indices (defaults to all matching)
        
        Returns:
            True if successful
        """
        try:
            if indices is None:
                # Get all indices for tenant and type
                indices = self.opensearch.search_indices(
                    tenant_id,
                    index_type,
                    datetime.utcnow() - timedelta(days=settings.INDEX_RETENTION_DAYS),
                    datetime.utcnow()
                )
            
            if not indices:
                return False
            
            actions = []
            for index in indices:
                actions.append({
                    "add": {
                        "index": index,
                        "alias": alias_name
                    }
                })
            
            self.opensearch.client.indices.update_aliases(body={"actions": actions})
            logger.info(f"Created alias {alias_name} for {len(indices)} indices")
            return True
            
        except OpenSearchException as e:
            logger.error(f"Failed to create index alias: {e}")
            return False
    
    def bulk_update_alerts(
        self,
        tenant_id: str,
        updates: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Bulk update multiple alerts for performance.
        
        Args:
            tenant_id: Tenant ID
            updates: List of update dicts with 'alert_id' and 'updates'
        
        Returns:
            Dict with 'success' and 'failed' counts
        """
        from opensearchpy.helpers import bulk
        
        success_count = 0
        failed_count = 0
        
        try:
            # Get indices
            indices = self.opensearch.search_indices(
                tenant_id, "alerts",
                datetime.utcnow() - timedelta(days=30),
                datetime.utcnow()
            )
            
            actions = []
            for update_item in updates:
                alert_id = update_item.get("alert_id")
                updates_dict = update_item.get("updates", {})
                
                if not alert_id:
                    failed_count += 1
                    continue
                
                # Find which index contains this alert
                for index_name in indices:
                    action = {
                        "_op_type": "update",
                        "_index": index_name,
                        "_id": alert_id,
                        "doc": {
                            **updates_dict,
                            "updated_at": datetime.utcnow().isoformat()
                        }
                    }
                    actions.append(action)
            
            # Execute bulk update
            if actions:
                success, failed = bulk(
                    self.opensearch.client,
                    actions,
                    raise_on_error=False
                )
                success_count = len(success)
                failed_count = len(failed)
            
            return {
                "success": success_count,
                "failed": failed_count
            }
            
        except OpenSearchException as e:
            logger.error(f"Bulk update failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Bulk update failed: {str(e)}"
            )

