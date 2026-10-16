"""Lightweight async circuit breaker for downstream service protection."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")
_MISSING = object()


class CircuitBreakerOpenError(RuntimeError):
    """Raised when a circuit is open and requests should fail fast."""


@dataclass
class _CircuitState:
    failures: int = 0
    opened_at: float | None = None


class AsyncCircuitBreaker:
    """Track transient downstream failures and short-circuit repeated calls."""

    def __init__(self, *, fail_max: int = 5, reset_timeout: float = 30.0):
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._lock = Lock()
        self._states: dict[str, _CircuitState] = {}

    def _get_state(self, name: str) -> _CircuitState:
        with self._lock:
            return self._states.setdefault(name, _CircuitState())

    def allow_request(self, name: str) -> bool:
        state = self._get_state(name)
        if state.opened_at is None:
            return True

        elapsed = monotonic() - state.opened_at
        if elapsed >= self.reset_timeout:
            with self._lock:
                state.failures = 0
                state.opened_at = None
            return True
        return False

    def record_success(self, name: str) -> None:
        state = self._get_state(name)
        with self._lock:
            state.failures = 0
            state.opened_at = None

    def record_failure(self, name: str) -> None:
        state = self._get_state(name)
        with self._lock:
            state.failures += 1
            if state.failures >= self.fail_max:
                state.opened_at = monotonic()

    async def call(
        self,
        name: str,
        operation: Callable[[], Awaitable[T]],
        *,
        fallback: T | object = _MISSING,
    ) -> T:
        if not self.allow_request(name):
            if fallback is not _MISSING:
                return fallback  # type: ignore[return-value]
            raise CircuitBreakerOpenError(
                f"Circuit '{name}' is open; retry after {self.reset_timeout:.0f}s."
            )

        try:
            result = await operation()
        except Exception:
            self.record_failure(name)
            if fallback is not _MISSING:
                return fallback  # type: ignore[return-value]
            raise

        self.record_success(name)
        return result
