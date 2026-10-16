"""Shared helpers for service readiness and dependency health contracts."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Iterable, Mapping

import httpx
from sqlalchemy import text
from sqlalchemy.engine import Engine


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_dependency_status(
    name: str,
    *,
    status: str,
    critical: bool,
    detail: str | None = None,
    url: str | None = None,
    latency_ms: float | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status,
        "critical": critical,
        "checked_at": _utcnow_iso(),
    }
    if detail:
        payload["detail"] = detail
    if url:
        payload["url"] = url
    if latency_ms is not None:
        payload["latency_ms"] = round(latency_ms, 2)
    if extra:
        payload.update(dict(extra))
    return {name: payload}


async def probe_http_dependency(
    name: str,
    url: str,
    *,
    verify_tls: bool,
    critical: bool,
    timeout: float = 5.0,
    headers: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    started = perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=verify_tls) as client:
            response = await client.get(url, headers=dict(headers or {}))
        latency_ms = (perf_counter() - started) * 1000

        payload: dict[str, Any] | None = None
        try:
            candidate = response.json()
            if isinstance(candidate, dict):
                payload = candidate
        except Exception:
            payload = None

        upstream_status = str(payload.get("status", "")).lower() if payload else ""
        if response.status_code != 200 or upstream_status in {"unhealthy", "unready"}:
            status = "unhealthy"
        elif upstream_status == "degraded":
            status = "degraded"
        else:
            status = "healthy"

        detail = payload.get("detail") if payload else None
        if not detail:
            detail = upstream_status or f"HTTP {response.status_code}"

        extra = {"http_status": response.status_code}
        if upstream_status:
            extra["upstream_status"] = upstream_status
        return build_dependency_status(
            name,
            status=status,
            critical=critical,
            detail=detail,
            url=url,
            latency_ms=latency_ms,
            extra=extra,
        )
    except Exception as exc:
        latency_ms = (perf_counter() - started) * 1000
        return build_dependency_status(
            name,
            status="unhealthy",
            critical=critical,
            detail=str(exc),
            url=url,
            latency_ms=latency_ms,
        )


def probe_database_engine(
    name: str,
    engine: Engine,
    *,
    critical: bool,
) -> dict[str, Any]:
    started = perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        latency_ms = (perf_counter() - started) * 1000
        return build_dependency_status(
            name,
            status="healthy",
            critical=critical,
            detail="query_ok",
            latency_ms=latency_ms,
        )
    except Exception as exc:
        latency_ms = (perf_counter() - started) * 1000
        return build_dependency_status(
            name,
            status="unhealthy",
            critical=critical,
            detail=str(exc),
            latency_ms=latency_ms,
        )


async def probe_database_engine_async(
    name: str,
    engine: Engine,
    *,
    critical: bool,
) -> dict[str, Any]:
    return await asyncio.to_thread(probe_database_engine, name, engine, critical=critical)


def summarize_service_health(
    service: str,
    version: str,
    dependencies: Iterable[Mapping[str, Any]],
    *,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    dependency_map: dict[str, Any] = {}
    for item in dependencies:
        dependency_map.update(dict(item))

    statuses = [dep.get("status", "unknown") for dep in dependency_map.values()]
    critical_unhealthy = sum(
        1
        for dep in dependency_map.values()
        if dep.get("critical") and dep.get("status") == "unhealthy"
    )
    degraded_count = sum(1 for status in statuses if status != "healthy")

    if critical_unhealthy:
        overall_status = "unhealthy"
    elif degraded_count:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    payload: dict[str, Any] = {
        "status": overall_status,
        "ready": critical_unhealthy == 0,
        "service": service,
        "version": version,
        "checked_at": _utcnow_iso(),
        "dependencies": dependency_map,
        "dependency_summary": {
            "total": len(dependency_map),
            "degraded": degraded_count,
            "critical_unhealthy": critical_unhealthy,
        },
    }
    if extra:
        payload.update(dict(extra))
    return payload
