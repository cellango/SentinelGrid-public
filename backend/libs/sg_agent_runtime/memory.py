"""Redis-backed agent memory store for the SentinelGrid agent runtime."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

try:
    import redis.asyncio as aioredis
except ModuleNotFoundError:  # pragma: no cover - exercised indirectly in lightweight test envs
    aioredis = None  # type: ignore[assignment]

from .models import AgentMemory
from .soc_models import SOCCaseContext, SOCCaseMemory

logger = logging.getLogger(__name__)

_MEM_KEY = "sg:memory:{agent_id}:{tenant_id}:{key}"
_MEM_PREFIX = "sg:memory:{agent_id}:{tenant_id}:"
_CASE_CONTEXT_KEY = "sg:soc:case_context:{tenant_id}:{incident_id}"
_CASE_MEMORY_KEY = "sg:soc:case_memory:{tenant_id}:{incident_id}"


class AgentMemoryStore:
    """Per-agent, per-tenant key-value memory backed by Redis."""

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or os.environ.get("REDIS_URL", "redis://redis:6379")
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        if self._redis is None:
            if aioredis is None:
                raise RuntimeError(
                    "redis.asyncio is not installed; AgentMemoryStore requires the redis package"
                )
            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
            )

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    @property
    def redis(self) -> aioredis.Redis:
        if self._redis is None:
            raise RuntimeError("AgentMemoryStore not connected — call connect() first")
        return self._redis

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def store(
        self,
        agent_id: str,
        tenant_id: str,
        key: str,
        value: dict,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store a memory entry, optionally with a TTL."""
        r = self.redis
        mem_key = _MEM_KEY.format(agent_id=agent_id, tenant_id=tenant_id, key=key)
        mem = AgentMemory(
            agent_id=agent_id,
            tenant_id=tenant_id,
            key=key,
            value=value,
            ttl_seconds=ttl_seconds,
            created_at=datetime.now(timezone.utc),
        )
        payload = mem.model_dump_json()
        if ttl_seconds:
            await r.setex(mem_key, ttl_seconds, payload)
        else:
            await r.set(mem_key, payload)
        logger.debug("Stored memory %s for agent %s", key, agent_id)

    async def recall(self, agent_id: str, tenant_id: str, key: str) -> dict | None:
        """Recall a specific memory's value. Returns None if not found."""
        r = self.redis
        mem_key = _MEM_KEY.format(agent_id=agent_id, tenant_id=tenant_id, key=key)
        raw = await r.get(mem_key)
        if raw is None:
            return None
        mem = AgentMemory.model_validate_json(raw)
        return mem.value

    async def search(
        self,
        agent_id: str,
        tenant_id: str,
        prefix: str = "",
    ) -> list[AgentMemory]:
        """Search memories by key prefix."""
        r = self.redis
        pattern = _MEM_PREFIX.format(agent_id=agent_id, tenant_id=tenant_id) + prefix + "*"
        memories: list[AgentMemory] = []
        async for k in r.scan_iter(match=pattern, count=200):
            raw = await r.get(k)
            if raw:
                memories.append(AgentMemory.model_validate_json(raw))
        memories.sort(key=lambda m: m.created_at)
        return memories

    async def forget(self, agent_id: str, tenant_id: str, key: str) -> None:
        """Delete a memory entry."""
        r = self.redis
        mem_key = _MEM_KEY.format(agent_id=agent_id, tenant_id=tenant_id, key=key)
        await r.delete(mem_key)
        logger.debug("Forgot memory %s for agent %s", key, agent_id)

    async def store_case_context(
        self,
        case_context: SOCCaseContext,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store durable incident-scoped case context."""
        r = self.redis
        key = _CASE_CONTEXT_KEY.format(
            tenant_id=case_context.tenant_id,
            incident_id=case_context.incident_id,
        )
        payload = case_context.model_dump_json()
        if ttl_seconds:
            await r.setex(key, ttl_seconds, payload)
        else:
            await r.set(key, payload)
        logger.debug(
            "Stored SOC case context for tenant=%s incident=%s",
            case_context.tenant_id,
            case_context.incident_id,
        )

    async def recall_case_context(
        self,
        tenant_id: str,
        incident_id: str,
    ) -> SOCCaseContext | None:
        """Recall incident-scoped case context."""
        r = self.redis
        key = _CASE_CONTEXT_KEY.format(tenant_id=tenant_id, incident_id=incident_id)
        raw = await r.get(key)
        if raw is None:
            return None
        return SOCCaseContext.model_validate_json(raw)

    async def store_case_memory(
        self,
        case_memory: SOCCaseMemory,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store durable incident-scoped working memory."""
        r = self.redis
        key = _CASE_MEMORY_KEY.format(
            tenant_id=case_memory.tenant_id,
            incident_id=case_memory.incident_id,
        )
        payload = case_memory.model_dump_json()
        if ttl_seconds:
            await r.setex(key, ttl_seconds, payload)
        else:
            await r.set(key, payload)
        logger.debug(
            "Stored SOC case memory for tenant=%s incident=%s",
            case_memory.tenant_id,
            case_memory.incident_id,
        )

    async def recall_case_memory(
        self,
        tenant_id: str,
        incident_id: str,
    ) -> SOCCaseMemory | None:
        """Recall incident-scoped working memory."""
        r = self.redis
        key = _CASE_MEMORY_KEY.format(tenant_id=tenant_id, incident_id=incident_id)
        raw = await r.get(key)
        if raw is None:
            return None
        return SOCCaseMemory.model_validate_json(raw)
