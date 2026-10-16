"""Lightweight in-process service metrics for operational snapshots."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from sg_core.request_tracing import get_service_name


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _label_key(labels: dict[str, Any]) -> str:
    if not labels:
        return "__base__"
    return ",".join(f"{key}={labels[key]}" for key in sorted(labels))


def _parse_label_key(key: str) -> dict[str, str]:
    if not key or key == "__base__":
        return {}

    parsed: dict[str, str] = {}
    for pair in key.split(","):
        if "=" not in pair:
            continue
        label_name, label_value = pair.split("=", 1)
        parsed[label_name] = label_value
    return parsed


def _prometheus_metric_name(metric: str) -> str:
    safe_chars = []
    for char in metric:
        if char.isalnum() or char in ("_", ":"):
            safe_chars.append(char)
        else:
            safe_chars.append("_")
    name = "".join(safe_chars)
    if name and name[0].isdigit():
        name = f"metric_{name}"
    return name


def _escape_label_value(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format_prometheus_sample(metric: str, value: float, labels: dict[str, Any] | None = None) -> str:
    rendered_labels = ""
    if labels:
        label_parts = [f'{key}="{_escape_label_value(labels[key])}"' for key in sorted(labels)]
        rendered_labels = "{" + ",".join(label_parts) + "}"
    return f"{metric}{rendered_labels} {value}"


class ServiceMetrics:
    """Thread-safe counter/gauge store keyed by service name."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self._lock = Lock()
        self._counters: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._gauges: dict[str, dict[str, float]] = defaultdict(dict)
        self._last_readiness: dict[str, Any] | None = None

    def increment_counter(self, metric: str, amount: float = 1, **labels: Any) -> None:
        key = _label_key(labels)
        with self._lock:
            self._counters[metric][key] += amount

    def set_gauge(self, metric: str, value: float, **labels: Any) -> None:
        key = _label_key(labels)
        with self._lock:
            self._gauges[metric][key] = value

    def record_readiness(self, payload: dict[str, Any]) -> None:
        ready = bool(payload.get("ready"))
        dependencies = payload.get("dependencies", {})
        summary = payload.get("dependency_summary", {})

        self.increment_counter("readiness_checks_total", outcome="ready" if ready else "unready")
        self.set_gauge("service_ready", 1 if ready else 0)
        self.set_gauge("dependency_total", float(summary.get("total", len(dependencies))))
        self.set_gauge("dependency_degraded", float(summary.get("degraded", 0)))
        self.set_gauge("dependency_critical_unhealthy", float(summary.get("critical_unhealthy", 0)))

        for dependency_name, dependency_payload in dependencies.items():
            status = str(dependency_payload.get("status", "unknown"))
            self.set_gauge(
                "dependency_status",
                1.0 if status == "healthy" else 0.0,
                dependency=dependency_name,
                status=status,
            )

        with self._lock:
            self._last_readiness = {
                "status": payload.get("status"),
                "ready": ready,
                "checked_at": payload.get("checked_at") or _utcnow_iso(),
                "dependency_summary": summary,
            }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = {
                metric: {
                    "total": sum(values.values()),
                    "series": dict(values),
                }
                for metric, values in self._counters.items()
            }
            gauges = {
                metric: dict(values)
                for metric, values in self._gauges.items()
            }
            last_readiness = dict(self._last_readiness or {})

        return {
            "service": self.service_name,
            "generated_at": _utcnow_iso(),
            "counters": counters,
            "gauges": gauges,
            "last_readiness": last_readiness,
        }

    def prometheus_text(self, *, include_service_label: bool = True) -> str:
        with self._lock:
            counters = {
                metric: dict(values)
                for metric, values in self._counters.items()
            }
            gauges = {
                metric: dict(values)
                for metric, values in self._gauges.items()
            }
            last_readiness = dict(self._last_readiness or {})

        lines: list[str] = []
        service_labels = {"service": self.service_name} if include_service_label else {}

        for metric, values in sorted(counters.items()):
            metric_name = _prometheus_metric_name(metric)
            lines.append(f"# TYPE {metric_name} counter")
            for label_key, value in sorted(values.items()):
                labels = {**service_labels, **_parse_label_key(label_key)}
                lines.append(_format_prometheus_sample(metric_name, value, labels))

        for metric, values in sorted(gauges.items()):
            metric_name = _prometheus_metric_name(metric)
            lines.append(f"# TYPE {metric_name} gauge")
            for label_key, value in sorted(values.items()):
                labels = {**service_labels, **_parse_label_key(label_key)}
                lines.append(_format_prometheus_sample(metric_name, value, labels))

        checked_at = last_readiness.get("checked_at")
        if checked_at:
            try:
                timestamp = datetime.fromisoformat(str(checked_at)).timestamp()
            except ValueError:
                timestamp = None
            if timestamp is not None:
                lines.append("# TYPE last_readiness_checked_timestamp_seconds gauge")
                lines.append(
                    _format_prometheus_sample(
                        "last_readiness_checked_timestamp_seconds",
                        timestamp,
                        service_labels,
                    )
                )

        status = last_readiness.get("status")
        if status:
            lines.append("# TYPE last_readiness_status gauge")
            lines.append(
                _format_prometheus_sample(
                    "last_readiness_status",
                    1,
                    {**service_labels, "status": status},
                )
            )

        return "\n".join(lines) + ("\n" if lines else "")

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._last_readiness = None


_registry_lock = Lock()
_registry: dict[str, ServiceMetrics] = {}


def get_service_metrics(service_name: str | None = None) -> ServiceMetrics:
    resolved_name = service_name or get_service_name("unknown-service") or "unknown-service"
    with _registry_lock:
        metrics = _registry.get(resolved_name)
        if metrics is None:
            metrics = ServiceMetrics(resolved_name)
            _registry[resolved_name] = metrics
        return metrics


def reset_service_metrics(service_name: str | None = None) -> None:
    if service_name:
        with _registry_lock:
            metrics = _registry.get(service_name)
        if metrics is not None:
            metrics.reset()
        return

    with _registry_lock:
        metrics_objects = list(_registry.values())
    for metrics in metrics_objects:
        metrics.reset()
