"""Redis-backed task queue for the SentinelGrid agent runtime."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

try:
    import redis.asyncio as aioredis
except ModuleNotFoundError:  # pragma: no cover - exercised indirectly in lightweight test envs
    aioredis = None  # type: ignore[assignment]

from .models import AgentTask, TaskResult

logger = logging.getLogger(__name__)

# Priority weights — lower score = higher priority in the sorted set.
PRIORITY_SCORES: dict[str, float] = {
    "critical": 0.0,
    "high": 1.0,
    "medium": 2.0,
    "low": 3.0,
}

# Redis key helpers
_TASK_KEY = "sg:task:{task_id}"
_QUEUE_KEY = "sg:queue:{agent_id}"
_TENANT_KEY = "sg:tenant:{tenant_id}:tasks"
_APPROVAL_KEY = "sg:approvals:{tenant_id}"
_CHANNEL_KEY = "sg:channel:{agent_id}"


class TaskQueue:
    """Redis-backed priority task queue with approval workflow support."""

    def __init__(self, redis_url: str | None = None):
        self._redis_url = redis_url or os.environ.get("REDIS_URL", "redis://redis:6379")
        self._redis: aioredis.Redis | None = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        if self._redis is None:
            if aioredis is None:
                raise RuntimeError(
                    "redis.asyncio is not installed; TaskQueue requires the redis package"
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
            raise RuntimeError("TaskQueue not connected — call connect() first")
        return self._redis

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialise(task: AgentTask) -> str:
        return task.model_dump_json()

    @staticmethod
    def _deserialise(raw: str) -> AgentTask:
        return AgentTask.model_validate_json(raw)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def submit(self, task: AgentTask) -> str:
        """Submit a task and return its id."""
        r = self.redis
        score = PRIORITY_SCORES.get(task.priority, 2.0)
        task_key = _TASK_KEY.format(task_id=task.id)
        queue_key = _QUEUE_KEY.format(agent_id=task.agent_id)
        tenant_key = _TENANT_KEY.format(tenant_id=task.tenant_id)
        channel_key = _CHANNEL_KEY.format(agent_id=task.agent_id)

        pipe = r.pipeline(transaction=True)
        pipe.set(task_key, self._serialise(task))
        pipe.zadd(queue_key, {task.id: score})
        pipe.sadd(tenant_key, task.id)
        await pipe.execute()

        # Notify agent channel
        await r.publish(channel_key, task.id)
        logger.info("Submitted task %s to agent %s", task.id, task.agent_id)
        return task.id

    async def claim(self, agent_id: str) -> AgentTask | None:
        """Atomically pop the highest-priority task for *agent_id*."""
        r = self.redis
        queue_key = _QUEUE_KEY.format(agent_id=agent_id)

        # zpopmin returns list of (member, score) tuples
        results = await r.zpopmin(queue_key, count=1)
        if not results:
            return None

        task_id = results[0][0] if isinstance(results[0], (list, tuple)) else results[0]
        task_key = _TASK_KEY.format(task_id=task_id)
        raw = await r.get(task_key)
        if raw is None:
            return None

        task = self._deserialise(raw)
        task.status = "claimed"
        task.claimed_by = agent_id
        task.updated_at = datetime.now(timezone.utc)
        await r.set(task_key, self._serialise(task))
        logger.info("Agent %s claimed task %s", agent_id, task.id)
        return task

    async def complete(self, task_id: str, result: TaskResult) -> None:
        """Mark a task as completed with its result."""
        r = self.redis
        task_key = _TASK_KEY.format(task_id=task_id)
        raw = await r.get(task_key)
        if raw is None:
            raise ValueError(f"Task {task_id} not found")

        task = self._deserialise(raw)
        task.status = "completed"
        task.result = result.result
        task.updated_at = datetime.now(timezone.utc)
        await r.set(task_key, self._serialise(task))

        # Remove from approval set if present
        approval_key = _APPROVAL_KEY.format(tenant_id=task.tenant_id)
        await r.srem(approval_key, task_id)
        logger.info("Task %s completed", task_id)

    async def fail(self, task_id: str, error: str) -> None:
        """Mark a task as failed."""
        r = self.redis
        task_key = _TASK_KEY.format(task_id=task_id)
        raw = await r.get(task_key)
        if raw is None:
            raise ValueError(f"Task {task_id} not found")

        task = self._deserialise(raw)
        task.status = "failed"
        task.error = error
        task.updated_at = datetime.now(timezone.utc)
        await r.set(task_key, self._serialise(task))

        approval_key = _APPROVAL_KEY.format(tenant_id=task.tenant_id)
        await r.srem(approval_key, task_id)
        logger.info("Task %s failed: %s", task_id, error)

    async def request_approval(self, task_id: str, action: dict, reason: str) -> None:
        """Pause a task pending human approval."""
        r = self.redis
        task_key = _TASK_KEY.format(task_id=task_id)
        raw = await r.get(task_key)
        if raw is None:
            raise ValueError(f"Task {task_id} not found")

        task = self._deserialise(raw)
        task.status = "awaiting_approval"
        task.requires_approval = True
        task.approval_status = "pending"
        task.approval_reason = reason
        task.context["pending_action"] = action
        task.updated_at = datetime.now(timezone.utc)

        approval_key = _APPROVAL_KEY.format(tenant_id=task.tenant_id)
        pipe = r.pipeline(transaction=True)
        pipe.set(task_key, self._serialise(task))
        pipe.sadd(approval_key, task_id)
        await pipe.execute()

        # Publish to approval channel
        await r.publish(f"sg:approval_requests:{task.tenant_id}", task_id)
        logger.info("Task %s awaiting approval: %s", task_id, reason)

    async def approve(self, task_id: str, approved_by: str) -> AgentTask:
        """Approve a paused task and return it for resumption."""
        r = self.redis
        task_key = _TASK_KEY.format(task_id=task_id)
        raw = await r.get(task_key)
        if raw is None:
            raise ValueError(f"Task {task_id} not found")

        task = self._deserialise(raw)
        if task.status != "awaiting_approval":
            raise ValueError(f"Task {task_id} is not awaiting approval (status={task.status})")

        task.status = "running"
        task.approval_status = "approved"
        task.updated_at = datetime.now(timezone.utc)
        task.context["approved_by"] = approved_by

        approval_key = _APPROVAL_KEY.format(tenant_id=task.tenant_id)
        pipe = r.pipeline(transaction=True)
        pipe.set(task_key, self._serialise(task))
        pipe.srem(approval_key, task_id)
        await pipe.execute()

        # Re-enqueue so the agent picks it up
        queue_key = _QUEUE_KEY.format(agent_id=task.agent_id)
        score = PRIORITY_SCORES.get(task.priority, 2.0)
        await r.zadd(queue_key, {task.id: score})

        logger.info("Task %s approved by %s", task_id, approved_by)
        return task

    async def reject(self, task_id: str, rejected_by: str, reason: str) -> None:
        """Reject a paused task."""
        r = self.redis
        task_key = _TASK_KEY.format(task_id=task_id)
        raw = await r.get(task_key)
        if raw is None:
            raise ValueError(f"Task {task_id} not found")

        task = self._deserialise(raw)
        task.status = "failed"
        task.approval_status = "rejected"
        task.error = f"Rejected by {rejected_by}: {reason}"
        task.updated_at = datetime.now(timezone.utc)

        approval_key = _APPROVAL_KEY.format(tenant_id=task.tenant_id)
        pipe = r.pipeline(transaction=True)
        pipe.set(task_key, self._serialise(task))
        pipe.srem(approval_key, task_id)
        await pipe.execute()
        logger.info("Task %s rejected by %s: %s", task_id, rejected_by, reason)

    async def get_task(self, task_id: str) -> AgentTask | None:
        """Get a task by ID."""
        raw = await self.redis.get(_TASK_KEY.format(task_id=task_id))
        return self._deserialise(raw) if raw else None

    async def list_tasks(
        self,
        agent_id: str | None = None,
        tenant_id: str | None = None,
        status: str | None = None,
    ) -> list[AgentTask]:
        """List tasks with optional filters."""
        r = self.redis
        task_ids: set[str] = set()

        if tenant_id:
            tenant_key = _TENANT_KEY.format(tenant_id=tenant_id)
            task_ids = await r.smembers(tenant_key)
        elif agent_id:
            queue_key = _QUEUE_KEY.format(agent_id=agent_id)
            # Include queued tasks
            queued = await r.zrange(queue_key, 0, -1)
            task_ids.update(queued)
            # Also scan for claimed/running tasks for this agent
            async for key in r.scan_iter(match="sg:task:*", count=200):
                raw = await r.get(key)
                if raw:
                    task = self._deserialise(raw)
                    if task.agent_id == agent_id:
                        task_ids.add(task.id)
        else:
            # Full scan — use sparingly
            async for key in r.scan_iter(match="sg:task:*", count=200):
                tid = key.split(":")[-1]
                task_ids.add(tid)

        tasks: list[AgentTask] = []
        for tid in task_ids:
            raw = await r.get(_TASK_KEY.format(task_id=tid))
            if raw:
                task = self._deserialise(raw)
                if status and task.status != status:
                    continue
                tasks.append(task)

        tasks.sort(key=lambda t: t.created_at)
        return tasks

    async def get_pending_approvals(self, tenant_id: str) -> list[AgentTask]:
        """Return all tasks awaiting human approval for a tenant."""
        r = self.redis
        approval_key = _APPROVAL_KEY.format(tenant_id=tenant_id)
        task_ids = await r.smembers(approval_key)

        tasks: list[AgentTask] = []
        for tid in task_ids:
            raw = await r.get(_TASK_KEY.format(task_id=tid))
            if raw:
                tasks.append(self._deserialise(raw))
        tasks.sort(key=lambda t: t.created_at)
        return tasks
