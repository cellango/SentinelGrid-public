"""Cache service for SIEM Agent using Redis."""

import logging
import json
from typing import Optional, Any, List
from datetime import datetime, timedelta
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis caching service for query results and statistics."""
    
    def __init__(self):
        """Initialize Redis client."""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed (caching disabled): {e}")
            self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None
        """
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
        
        return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl_seconds: Time to live in seconds
        """
        if not self.redis_client:
            return
        
        try:
            serialized = json.dumps(value, default=str)
            if ttl_seconds:
                self.redis_client.setex(key, ttl_seconds, serialized)
            else:
                self.redis_client.set(key, serialized)
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
    
    def delete(self, key: str):
        """Delete key from cache."""
        if not self.redis_client:
            return
        
        try:
            self.redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")
    
    def get_stats_cache_key(self, tenant_id: str, metric: str, date: Optional[datetime] = None) -> str:
        """Generate cache key for statistics."""
        date_suffix = date.strftime("%Y-%m-%d") if date else datetime.utcnow().strftime("%Y-%m-%d")
        return f"siem:tenant:{tenant_id}:stats:{metric}:{date_suffix}"
    
    def get_query_cache_key(self, tenant_id: str, query_hash: str) -> str:
        """Generate cache key for query results."""
        return f"siem:tenant:{tenant_id}:query:{query_hash}"
    
    def get_top_entities_cache_key(self, tenant_id: str, entity_type: str, date: Optional[datetime] = None) -> str:
        """Generate cache key for top entities."""
        date_suffix = date.strftime("%Y-%m-%d") if date else datetime.utcnow().strftime("%Y-%m-%d")
        return f"siem:tenant:{tenant_id}:top:{entity_type}:{date_suffix}"
    
    def invalidate_tenant_cache(self, tenant_id: str):
        """Invalidate all cache for a tenant."""
        if not self.redis_client:
            return
        
        try:
            pattern = f"siem:tenant:{tenant_id}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache keys for tenant {tenant_id}")
        except Exception as e:
            logger.warning(f"Cache invalidation failed for tenant {tenant_id}: {e}")

