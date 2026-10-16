"""
LLM response caching, token usage tracking, and spending controls.

Caches LLM responses in Redis to avoid redundant API calls.
Tracks token usage per tenant for billing and cost visibility.
Enforces spending caps to prevent cost overruns.
"""

import hashlib
import json
import logging
import os
import time
from typing import Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


class LLMCache:
    """Redis-backed LLM response cache.

    Cache key: hash of (model, messages, temperature, tools).
    TTL: configurable per cache entry, default 1 hour.
    """

    def __init__(self, redis_url: str = None, default_ttl: int = 3600):
        import redis
        self._redis = redis.from_url(redis_url or REDIS_URL, decode_responses=True)
        self._default_ttl = default_ttl

    def _cache_key(self, model: str, messages: list[dict], temperature: float, tools: list[dict] | None = None) -> str:
        """Generate deterministic cache key from request params."""
        key_data = json.dumps({
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "tools": tools or [],
        }, sort_keys=True)
        return f"sg:llm_cache:{hashlib.sha256(key_data.encode()).hexdigest()}"

    def get(self, model: str, messages: list[dict], temperature: float, tools: list[dict] | None = None) -> dict | None:
        """Check cache for a matching response."""
        key = self._cache_key(model, messages, temperature, tools)
        cached = self._redis.get(key)
        if cached:
            logger.debug(f"LLM cache hit: {key[:40]}")
            return json.loads(cached)
        return None

    def set(self, model: str, messages: list[dict], temperature: float, response: dict, tools: list[dict] | None = None, ttl: int | None = None):
        """Cache an LLM response."""
        key = self._cache_key(model, messages, temperature, tools)
        self._redis.setex(key, ttl or self._default_ttl, json.dumps(response))

    def invalidate_all(self):
        """Clear all cached LLM responses."""
        cursor = 0
        while True:
            cursor, keys = self._redis.scan(cursor, match="sg:llm_cache:*", count=100)
            if keys:
                self._redis.delete(*keys)
            if cursor == 0:
                break


class TokenUsageTracker:
    """Tracks LLM token usage per tenant for billing and cost visibility.

    Redis keys:
    - sg:llm_usage:{tenant_id}:daily:{YYYY-MM-DD} -- daily usage hash
    - sg:llm_usage:{tenant_id}:monthly:{YYYY-MM} -- monthly usage hash

    Each hash contains:
    - prompt_tokens: int
    - completion_tokens: int
    - total_tokens: int
    - request_count: int
    - estimated_cost_usd: float (as string)
    - models:{model_name}:tokens -- per-model tracking
    """

    # Approximate cost per 1M tokens (input/output) for common models
    COST_PER_1M_TOKENS = {
        "qwen2.5-coder-7b": {"input": 0.0, "output": 0.0},  # Self-hosted, no API cost
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-4o": {"input": 2.50, "output": 10.0},
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    }

    def __init__(self, redis_url: str = None):
        import redis
        self._redis = redis.from_url(redis_url or REDIS_URL, decode_responses=True)

    def record(self, tenant_id: str, model: str, prompt_tokens: int, completion_tokens: int):
        """Record token usage for a tenant."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        month = datetime.utcnow().strftime("%Y-%m")
        total = prompt_tokens + completion_tokens

        # Calculate estimated cost
        costs = self.COST_PER_1M_TOKENS.get(model, {"input": 5.0, "output": 15.0})
        cost = (prompt_tokens * costs["input"] + completion_tokens * costs["output"]) / 1_000_000

        pipe = self._redis.pipeline()
        for period_key in [f"sg:llm_usage:{tenant_id}:daily:{today}", f"sg:llm_usage:{tenant_id}:monthly:{month}"]:
            pipe.hincrby(period_key, "prompt_tokens", prompt_tokens)
            pipe.hincrby(period_key, "completion_tokens", completion_tokens)
            pipe.hincrby(period_key, "total_tokens", total)
            pipe.hincrby(period_key, "request_count", 1)
            pipe.hincrbyfloat(period_key, "estimated_cost_usd", cost)
            pipe.hincrby(period_key, f"models:{model}:tokens", total)

        # Set TTL: daily keys expire after 90 days, monthly after 2 years
        pipe.expire(f"sg:llm_usage:{tenant_id}:daily:{today}", 90 * 86400)
        pipe.expire(f"sg:llm_usage:{tenant_id}:monthly:{month}", 730 * 86400)
        pipe.execute()

    def get_daily_usage(self, tenant_id: str, date: str = None) -> dict:
        """Get usage for a specific day."""
        date = date or datetime.utcnow().strftime("%Y-%m-%d")
        key = f"sg:llm_usage:{tenant_id}:daily:{date}"
        data = self._redis.hgetall(key)
        return self._parse_usage(data)

    def get_monthly_usage(self, tenant_id: str, month: str = None) -> dict:
        """Get usage for a specific month."""
        month = month or datetime.utcnow().strftime("%Y-%m")
        key = f"sg:llm_usage:{tenant_id}:monthly:{month}"
        data = self._redis.hgetall(key)
        return self._parse_usage(data)

    def _parse_usage(self, data: dict) -> dict:
        if not data:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "request_count": 0, "estimated_cost_usd": 0.0}
        return {
            "prompt_tokens": int(data.get("prompt_tokens", 0)),
            "completion_tokens": int(data.get("completion_tokens", 0)),
            "total_tokens": int(data.get("total_tokens", 0)),
            "request_count": int(data.get("request_count", 0)),
            "estimated_cost_usd": float(data.get("estimated_cost_usd", 0.0)),
        }


class SpendingGuard:
    """Enforces spending caps per tenant.

    Redis key: sg:llm_caps:{tenant_id} -- hash with:
    - daily_cap_usd: float
    - monthly_cap_usd: float
    - alert_threshold_pct: int (e.g. 80 = alert at 80% of cap)
    """

    DEFAULT_DAILY_CAP = 50.0   # $50/day default
    DEFAULT_MONTHLY_CAP = 500.0  # $500/month default

    def __init__(self, tracker: TokenUsageTracker, redis_url: str = None):
        import redis
        self._redis = redis.from_url(redis_url or REDIS_URL, decode_responses=True)
        self._tracker = tracker

    def set_caps(self, tenant_id: str, daily_cap_usd: float = None, monthly_cap_usd: float = None, alert_threshold_pct: int = 80):
        """Set spending caps for a tenant."""
        key = f"sg:llm_caps:{tenant_id}"
        caps = {}
        if daily_cap_usd is not None:
            caps["daily_cap_usd"] = str(daily_cap_usd)
        if monthly_cap_usd is not None:
            caps["monthly_cap_usd"] = str(monthly_cap_usd)
        caps["alert_threshold_pct"] = str(alert_threshold_pct)
        self._redis.hset(key, mapping=caps)

    def check(self, tenant_id: str) -> dict:
        """Check if tenant is within spending limits.

        Returns: {"allowed": bool, "daily_usage_usd": float, "daily_cap_usd": float,
                  "monthly_usage_usd": float, "monthly_cap_usd": float, "warning": str|None}
        """
        caps = self._redis.hgetall(f"sg:llm_caps:{tenant_id}")
        daily_cap = float(caps.get("daily_cap_usd", self.DEFAULT_DAILY_CAP))
        monthly_cap = float(caps.get("monthly_cap_usd", self.DEFAULT_MONTHLY_CAP))
        threshold = int(caps.get("alert_threshold_pct", 80))

        daily = self._tracker.get_daily_usage(tenant_id)
        monthly = self._tracker.get_monthly_usage(tenant_id)

        daily_cost = daily["estimated_cost_usd"]
        monthly_cost = monthly["estimated_cost_usd"]

        allowed = daily_cost < daily_cap and monthly_cost < monthly_cap
        warning = None

        if not allowed:
            warning = f"Spending cap exceeded. Daily: ${daily_cost:.2f}/${daily_cap:.2f}, Monthly: ${monthly_cost:.2f}/${monthly_cap:.2f}"
        elif daily_cost >= daily_cap * threshold / 100 or monthly_cost >= monthly_cap * threshold / 100:
            warning = f"Approaching spending cap ({threshold}%). Daily: ${daily_cost:.2f}/${daily_cap:.2f}, Monthly: ${monthly_cost:.2f}/${monthly_cap:.2f}"

        return {
            "allowed": allowed,
            "daily_usage_usd": daily_cost,
            "daily_cap_usd": daily_cap,
            "monthly_usage_usd": monthly_cost,
            "monthly_cap_usd": monthly_cap,
            "warning": warning,
        }
