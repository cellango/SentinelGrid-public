"""Redis caching service for entitlements and evaluation results."""

import json
import logging
from typing import Optional, Any
import redis
from functools import wraps

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache client for entitlements and evaluation results."""
    
    def __init__(self):
        """Initialize Redis connection."""
        try:
            self.client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.client.ping()
            logger.info(f"Redis cache connected: {settings.REDIS_URL}")
            self.enabled = True
        except Exception as e:
            logger.warning(f"Redis cache unavailable: {e}. Caching disabled.")
            self.client = None
            self.enabled = False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled:
            return None
        
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        if not self.enabled:
            return False
        
        try:
            ttl = ttl or settings.REDIS_CACHE_TTL
            serialized = json.dumps(value, default=str)
            return self.client.setex(key, ttl, serialized)
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.enabled:
            return False
        
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self.enabled:
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis delete_pattern error for pattern {pattern}: {e}")
            return 0
    
    def invalidate_entitlement(self, entitlement_id: str, tenant_id: str):
        """Invalidate cache for a specific entitlement."""
        self.delete(f"entitlement:{entitlement_id}")
        self.delete_pattern(f"entitlements:tenant:{tenant_id}:*")
        self.delete_pattern(f"evaluation:*:tenant:{tenant_id}:*")
    
    def invalidate_tenant_entitlements(self, tenant_id: str):
        """Invalidate all entitlements for a tenant."""
        self.delete_pattern(f"entitlements:tenant:{tenant_id}:*")
        self.delete_pattern(f"evaluation:*:tenant:{tenant_id}:*")


# Global cache instance
cache = RedisCache()


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cache miss: {cache_key}")
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cache miss: {cache_key}")
            
            return result
        
        # Return appropriate wrapper based on whether function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator

