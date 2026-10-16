"""
Redis Streams-backed event bus for SentinelGrid agent communication.

Uses Redis Streams for durable, distributed pub/sub with consumer groups.
Each agent/service subscribes to topics via consumer groups, ensuring
each event is processed exactly once per consumer group.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Callable, Coroutine
from datetime import datetime

try:
    import redis.asyncio as aioredis
except ImportError:  # pragma: no cover - exercised in minimal local test envs
    aioredis = None

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


class EventBus:
    """Redis Streams event bus for distributed agent communication."""

    def __init__(self, redis_url: str = None, consumer_group: str = "default"):
        self._redis_url = redis_url or REDIS_URL
        self._redis: aioredis.Redis | None = None
        self._consumer_group = consumer_group
        self._consumer_name = f"{consumer_group}-{os.getpid()}-{int(time.time())}"
        self._handlers: dict[str, list[Callable]] = {}
        self._running = False
        self._listen_task: asyncio.Task | None = None

    async def connect(self):
        """Initialize Redis connection."""
        if aioredis is None:
            raise RuntimeError("redis package is required for the async event bus")
        self._redis = aioredis.from_url(self._redis_url, decode_responses=True)

    async def close(self):
        """Shutdown the bus."""
        self._running = False
        if self._listen_task:
            self._listen_task.cancel()
        if self._redis:
            await self._redis.aclose()

    async def publish(self, topic: str, event: dict):
        """Publish an event to a topic (Redis Stream).

        Stream key: sg:events:{topic}
        Event data includes: event_type, tenant_id, payload, source, timestamp
        """
        if not self._redis:
            await self.connect()

        stream_key = f"sg:events:{topic}"
        event_data = {
            "data": json.dumps(event),
            "timestamp": datetime.utcnow().isoformat(),
        }
        msg_id = await self._redis.xadd(stream_key, event_data, maxlen=10000)
        logger.debug(f"Published to {stream_key}: {msg_id}")
        return msg_id

    def subscribe(self, topic: str, handler: Callable):
        """Register a handler for a topic.

        Handler signature: async def handler(event: dict) -> None
        """
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(handler)

    async def start_listening(self):
        """Start consuming events from subscribed topics.

        Creates consumer groups if they don't exist.
        Uses XREADGROUP for exactly-once delivery per consumer group.
        """
        if not self._redis:
            await self.connect()

        # Create consumer groups for each subscribed topic
        for topic in self._handlers:
            stream_key = f"sg:events:{topic}"
            try:
                await self._redis.xgroup_create(stream_key, self._consumer_group, id="0", mkstream=True)
            except aioredis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise  # Group already exists, that's fine

        self._running = True
        self._listen_task = asyncio.create_task(self._consume_loop())

    async def _consume_loop(self):
        """Main consumption loop reading from all subscribed streams."""
        streams = {f"sg:events:{topic}": ">" for topic in self._handlers}

        while self._running:
            try:
                results = await self._redis.xreadgroup(
                    groupname=self._consumer_group,
                    consumername=self._consumer_name,
                    streams=streams,
                    count=10,
                    block=1000,  # 1 second block
                )

                for stream_key, messages in results:
                    topic = stream_key.replace("sg:events:", "")
                    handlers = self._handlers.get(topic, [])

                    for msg_id, msg_data in messages:
                        try:
                            event = json.loads(msg_data.get("data", "{}"))
                            for handler in handlers:
                                if asyncio.iscoroutinefunction(handler):
                                    await handler(event)
                                else:
                                    handler(event)
                            # ACK after successful processing
                            await self._redis.xack(stream_key, self._consumer_group, msg_id)
                        except Exception as e:
                            logger.error(f"Error processing {msg_id} from {stream_key}: {e}")
                            # Don't ACK — message will be re-delivered

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event bus consume error: {e}")
                await asyncio.sleep(1)

    async def replay(self, topic: str, since: str = "0") -> list[dict]:
        """Replay events from a topic since a given message ID.

        Useful for catch-up after restarts.
        """
        if not self._redis:
            await self.connect()
        stream_key = f"sg:events:{topic}"
        results = await self._redis.xrange(stream_key, min=since, count=1000)
        events = []
        for msg_id, msg_data in results:
            event = json.loads(msg_data.get("data", "{}"))
            event["_msg_id"] = msg_id
            events.append(event)
        return events


# Singleton for backward compatibility
_default_bus: EventBus | None = None

async def get_event_bus(consumer_group: str = "default") -> EventBus:
    """Get or create the default event bus instance."""
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus(consumer_group=consumer_group)
        await _default_bus.connect()
    return _default_bus


# Synchronous publish helper for use in non-async contexts (Celery tasks, etc.)
def publish_sync(topic: str, event: dict):
    """Publish an event synchronously (creates a temporary connection)."""
    import redis as sync_redis
    r = sync_redis.from_url(REDIS_URL, decode_responses=True)
    stream_key = f"sg:events:{topic}"
    event_data = {
        "data": json.dumps(event),
        "timestamp": datetime.utcnow().isoformat(),
    }
    r.xadd(stream_key, event_data, maxlen=10000)
    r.close()


class _BestEffortEventBusPublisher:
    """Synchronous compatibility publisher used by workflow helpers."""

    def publish(self, topic: str, event: dict):
        try:
            publish_sync(topic, event)
        except Exception as exc:
            logger.warning("Failed to publish workflow event to %s: %s", topic, exc)
            return None


event_bus = _BestEffortEventBusPublisher()
