"""Lightweight in-process metrics for orchestrator operations."""

import time
import threading
from copy import deepcopy
from typing import Dict


class MetricsTracker:
    """Tracks queued/running/completed/failed counts and durations by operation."""

    def _reset_locked(self) -> None:
        self._metrics = {
            "queued": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "last_duration_ms": 0.0,
            "avg_duration_ms": 0.0,
            "total_duration_ms": 0.0,
            "samples": 0,
            "by_type": {},
        }

    def reset(self) -> None:
        with self._lock:
            self._reset_locked()
            self._start_time = time.time()

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset_locked()
        self._start_time = time.time()

    def _ensure_type(self, op_type: str) -> None:
        if op_type not in self._metrics["by_type"]:
            self._metrics["by_type"][op_type] = {
                "queued": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "last_duration_ms": 0.0,
                "avg_duration_ms": 0.0,
                "total_duration_ms": 0.0,
                "samples": 0,
            }

    def mark_queued(self, op_type: str) -> None:
        with self._lock:
            self._ensure_type(op_type)
            self._metrics["queued"] += 1
            self._metrics["by_type"][op_type]["queued"] += 1

    def mark_started(self, op_type: str) -> float:
        """Mark an operation as running; returns start time."""
        with self._lock:
            self._ensure_type(op_type)
            if self._metrics["queued"] > 0:
                self._metrics["queued"] -= 1
            if self._metrics["by_type"][op_type]["queued"] > 0:
                self._metrics["by_type"][op_type]["queued"] -= 1
            self._metrics["running"] += 1
            self._metrics["by_type"][op_type]["running"] += 1
        return time.perf_counter()

    def _record_outcome(self, op_type: str, duration_ms: float, success: bool) -> None:
        with self._lock:
            self._ensure_type(op_type)
            if self._metrics["running"] > 0:
                self._metrics["running"] -= 1
            if self._metrics["by_type"][op_type]["running"] > 0:
                self._metrics["by_type"][op_type]["running"] -= 1

            if success:
                self._metrics["completed"] += 1
                self._metrics["by_type"][op_type]["completed"] += 1
            else:
                self._metrics["failed"] += 1
                self._metrics["by_type"][op_type]["failed"] += 1

            self._metrics["last_duration_ms"] = duration_ms
            self._metrics["total_duration_ms"] += duration_ms
            self._metrics["samples"] += 1
            self._metrics["avg_duration_ms"] = (
                self._metrics["total_duration_ms"] / self._metrics["samples"]
            )

            type_metrics = self._metrics["by_type"][op_type]
            type_metrics["last_duration_ms"] = duration_ms
            type_metrics["total_duration_ms"] += duration_ms
            type_metrics["samples"] += 1
            type_metrics["avg_duration_ms"] = (
                type_metrics["total_duration_ms"] / max(1, type_metrics["samples"])
            )

    def mark_completed(self, op_type: str, duration_ms: float) -> None:
        self._record_outcome(op_type, duration_ms, success=True)

    def mark_failed(self, op_type: str, duration_ms: float) -> None:
        self._record_outcome(op_type, duration_ms, success=False)

    def snapshot(self) -> Dict:
        with self._lock:
            snap = deepcopy(self._metrics)
        snap["uptime_seconds"] = time.time() - self._start_time
        return snap


metrics_tracker = MetricsTracker()
