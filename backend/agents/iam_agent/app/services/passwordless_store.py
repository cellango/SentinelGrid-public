"""
Shared store for passwordless tokens (magic links and OTP).

Uses Redis when available; falls back to in-memory with TTL + single-use semantics.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from app.services.redis_cache import cache

logger = logging.getLogger(__name__)


class PasswordlessStore:
    """Small helper to persist passwordless artifacts with TTL and single-use."""

    def __init__(self, prefix: str = "passwordless"):
        self.prefix = prefix
        self.memory_store: Dict[str, Dict[str, Any]] = {}
        self.use_redis = cache.enabled

    def _key(self, token_hash: str) -> str:
        return f"{self.prefix}:{token_hash}"

    @staticmethod
    def _is_expired(record: Dict[str, Any]) -> bool:
        expires_at = record.get("expires_at")
        if not expires_at:
            return False
        try:
            return datetime.utcnow() > datetime.fromisoformat(expires_at)
        except Exception:
            return False

    def save(self, token_hash: str, data: Dict[str, Any], ttl_seconds: int) -> bool:
        """Persist a token record with TTL."""
        data = dict(data)
        if "expires_at" not in data:
            data["expires_at"] = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
        key = self._key(token_hash)
        if self.use_redis:
            return bool(cache.set(key, data, ttl_seconds))
        self.memory_store[token_hash] = data
        return True

    def get(self, token_hash: str) -> Optional[Dict[str, Any]]:
        """Fetch a token record without consuming it."""
        key = self._key(token_hash)
        record: Optional[Dict[str, Any]]
        if self.use_redis:
            record = cache.get(key)
        else:
            record = self.memory_store.get(token_hash)

        if not record:
            return None

        if self._is_expired(record):
            self.delete(token_hash)
            return None

        return record

    def delete(self, token_hash: str) -> bool:
        """Delete a token record."""
        key = self._key(token_hash)
        if self.use_redis:
            return bool(cache.delete(key))
        return self.memory_store.pop(token_hash, None) is not None

    def consume(self, token_hash: str) -> Optional[Dict[str, Any]]:
        """Fetch and delete a token record (single-use)."""
        record = self.get(token_hash)
        if record:
            self.delete(token_hash)
        return record
