"""Batch processing service for events."""

import logging
import asyncio
import json
import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from collections import defaultdict
from app.models.event import IngestEvent
from app.core.config import settings
import hashlib
from sg_core.service_metrics import get_service_metrics

logger = logging.getLogger(__name__)
runtime_metrics = get_service_metrics(settings.SERVICE_NAME)


class BatchProcessor:
    """Service for batch processing events to OpenSearch."""
    
    def __init__(self):
        """Initialize batch processor."""
        self.batches: Dict[str, List[IngestEvent]] = defaultdict(list)
        self.batch_timers: Dict[str, asyncio.Task] = {}
        self.opensearch_url = settings.OPENSEARCH_URL
        self.os_auth = None
        if settings.OPENSEARCH_USERNAME and settings.OPENSEARCH_PASSWORD:
            self.os_auth = (settings.OPENSEARCH_USERNAME, settings.OPENSEARCH_PASSWORD)
        self.batch_size = settings.BATCH_SIZE
        self.batch_timeout = settings.BATCH_TIMEOUT_SECONDS
        self.model_gateway_url = settings.MODEL_GATEWAY_URL
        self.enable_embeddings = settings.ENABLE_EMBEDDINGS
        self.embeddings_cap = settings.EMBEDDINGS_MAX_PER_TENANT_PER_DAY
        self._embeddings_count: Dict[str, int] = defaultdict(int)
        self._embeddings_attempts: Dict[str, int] = defaultdict(int)
        self._embeddings_success: Dict[str, int] = defaultdict(int)
        self._embeddings_fail: Dict[str, int] = defaultdict(int)
        # In-memory de-dupe of recent summaries per tenant to avoid double embedding
        self._embedding_seen: Dict[str, set] = defaultdict(set)
        self._embedding_seen_cap = 5000  # per-tenant rolling cap to bound memory
        self._max_summary_len = 600
        self._record_runtime_snapshot()

    async def add_event(self, tenant_id: str, event: IngestEvent) -> None:
        """
        Add event to batch queue.
        
        Args:
            tenant_id: Tenant ID
            event: Normalized event
        """
        # Add to batch
        self.batches[tenant_id].append(event)
        runtime_metrics.increment_counter("ingestion_events_total", outcome="accepted")
        self._record_runtime_snapshot()
        
        # Check if batch is full
        if len(self.batches[tenant_id]) >= self.batch_size:
            await self._flush_batch(tenant_id, trigger="batch_size")
            return
        
        # Start or reset timer for this tenant
        if tenant_id in self.batch_timers:
            self.batch_timers[tenant_id].cancel()
        
        self.batch_timers[tenant_id] = asyncio.create_task(
            self._batch_timeout(tenant_id)
        )
        self._record_runtime_snapshot()
    
    async def _batch_timeout(self, tenant_id: str) -> None:
        """Handle batch timeout."""
        await asyncio.sleep(self.batch_timeout)
        await self._flush_batch(tenant_id, trigger="timeout")
    
    async def _flush_batch(self, tenant_id: str, *, trigger: str = "manual") -> None:
        """
        Flush batch for a tenant to OpenSearch.
        
        Args:
            tenant_id: Tenant ID
        """
        if tenant_id not in self.batches or not self.batches[tenant_id]:
            self._record_runtime_snapshot()
            return
        
        # Get batch
        batch = self.batches[tenant_id]
        self.batches[tenant_id] = []
        
        # Cancel timer
        if tenant_id in self.batch_timers:
            self.batch_timers[tenant_id].cancel()
            del self.batch_timers[tenant_id]
        
        # Send to SIEM Agent
        try:
            await self._send_to_opensearch(tenant_id, batch)
            # Optionally send a small, high-value slice to embeddings
            if self.enable_embeddings:
                await self._maybe_send_embeddings(tenant_id, batch)
            runtime_metrics.increment_counter(
                "ingestion_batch_flushes_total",
                outcome="success",
                trigger=trigger,
            )
        except Exception as e:
            runtime_metrics.increment_counter(
                "ingestion_batch_flushes_total",
                outcome="failure",
                trigger=trigger,
            )
            logger.error(f"Failed to send batch to OpenSearch for tenant {tenant_id}: {e}")
            # TODO: Implement dead-letter queue or retry mechanism
        finally:
            self._record_runtime_snapshot()
    
    def _resolve_index_pipeline(self, tenant_id: str, event: IngestEvent) -> Tuple[str, Optional[str]]:
        """
        Resolve index name and optional pipeline based on source/type.
        """
        source_name = ""
        if event.raw_data.get("source"):
            source_name = str(event.raw_data.get("source")).lower()
        elif event.ecs_fields.source.get("name"):
            source_name = str(event.ecs_fields.source.get("name")).lower()
        source_type = str(event.ecs_fields.source.get("type", "")).lower() if isinstance(event.ecs_fields.source, dict) else ""

        def idx(base: str) -> str:
            return f"{tenant_id}-{base}"

        # Simple heuristics for v1 AWS sources
        if "cloudtrail" in source_name or "aws_cloudtrail" in source_name or source_type == "cloud":
            return idx("cloudtrail"), "pipeline-cloudtrail"
        if "vpc" in source_name or "flow" in source_name or "vpc_flow" in source_name:
            return idx("net"), "pipeline-vpcflow"
        if "dns" in source_name or "route53" in source_name:
            return idx("dns"), "pipeline-dns"
        if "waf" in source_name or "alb" in source_name:
            return idx("waf"), "pipeline-waf"
        if "guardduty" in source_name:
            return idx("alerts"), "pipeline-guardduty"

        # Default catch-all
        return idx("logs"), None

    async def _send_to_opensearch(
        self,
        tenant_id: str,
        events: List[IngestEvent]
    ) -> None:
        """
        Send events to OpenSearch via _bulk API with per-source pipeline.
        
        Args:
            tenant_id: Tenant ID
            events: List of normalized events
        """
        if not events:
            return

        bulk_lines: List[str] = []
        for event in events:
            index_name, pipeline = self._resolve_index_pipeline(tenant_id, event)
            action: Dict[str, Any] = {"index": {"_index": index_name}}
            if pipeline:
                action["index"]["pipeline"] = pipeline

            body = event.ecs_fields.model_dump(by_alias=True)
            body["raw_data"] = event.raw_data
            bulk_lines.append(json.dumps(action))
            bulk_lines.append(json.dumps(body, default=str))

        bulk_payload = "\n".join(bulk_lines) + "\n"
        url = f"{self.opensearch_url}/_bulk"

        async with httpx.AsyncClient(timeout=60.0, auth=self.os_auth) as client:
            resp = await client.post(
                url,
                content=bulk_payload,
                headers={"Content-Type": "application/x-ndjson"},
            )
            if resp.status_code >= 300:
                runtime_metrics.increment_counter(
                    "ingestion_opensearch_bulk_requests_total",
                    outcome="http_error",
                )
                logger.error(
                    "OpenSearch bulk ingest failed for tenant %s: status=%s body=%s",
                    tenant_id,
                    resp.status_code,
                    resp.text,
                )
                resp.raise_for_status()

            result = resp.json()
            errors = result.get("errors", False)
            if errors:
                runtime_metrics.increment_counter(
                    "ingestion_opensearch_bulk_requests_total",
                    outcome="partial_error",
                )
                # Log first few item errors for debugging
                item_errors = []
                for item in result.get("items", []):
                    for action, info in item.items():
                        if info.get("error"):
                            item_errors.append(info.get("error"))
                logger.warning(
                    "OpenSearch bulk ingest reported errors for tenant %s: %s",
                    tenant_id,
                    item_errors[:3],
                )
            logger.info(
                "Sent batch of %d events to OpenSearch for tenant %s (errors=%s)",
                len(events),
                tenant_id,
                errors,
            )
            if not errors:
                runtime_metrics.increment_counter(
                    "ingestion_opensearch_bulk_requests_total",
                    outcome="success",
                )

    async def _maybe_send_embeddings(self, tenant_id: str, events: List[IngestEvent]) -> None:
        """
        Send a capped, high-value slice of events to model_gateway embeddings API.
        Rules:
          - Only critical/high alerts/incidents or items tagged with tickets/incidents.
          - Cap per tenant per day (embeddings_cap).
        """
        if self._embeddings_count[tenant_id] >= self.embeddings_cap:
            return

        # Filter: keep only alert/incident-like events with high severity
        selected = []
        for ev in events:
            fields = ev.ecs_fields.model_dump(by_alias=True) if hasattr(ev, "ecs_fields") else {}
            sev = str(fields.get("severity") or (ev.raw_data.get("severity") if hasattr(ev, "raw_data") else "")).lower()
            category = str(fields.get("event", {}).get("kind", "")).lower() if isinstance(fields.get("event"), dict) else ""
            if not category:
                category = str(fields.get("event_type", "")).lower()
            # Heuristic: high-value if severity >= high or category == alert/incident
            if sev in ("critical", "high") or category in ("alert", "incident"):
                selected.append(ev)
            if len(selected) >= 5:  # small slice per flush
                break

        if not selected:
            return

        payload = {"summaries": []}
        for ev in selected:
            if self._embeddings_count[tenant_id] >= self.embeddings_cap:
                break
            summary_text, trimmed_fields, host_id = self._summarize_for_embedding(ev)
            if not summary_text:
                continue
            digest = hashlib.sha256(summary_text.encode("utf-8")).hexdigest()
            if digest in self._embedding_seen[tenant_id]:
                continue
            # Bound the seen set to avoid unbounded growth
            self._embedding_seen[tenant_id].add(digest)
            if len(self._embedding_seen[tenant_id]) > self._embedding_seen_cap:
                # Drop oldest-ish by clearing the set when over cap (simple reset to limit memory)
                self._embedding_seen[tenant_id].clear()
                self._embedding_seen[tenant_id].add(digest)
            payload["summaries"].append(
                {
                    "tenant_id": tenant_id,
                    "source": ev.raw_data.get("source") if hasattr(ev, "raw_data") else "ingestion",
                    "agent_id": ev.raw_data.get("agent_id") if hasattr(ev, "raw_data") else None,
                    "host_id": host_id,
                    "os_id": (ev.raw_data.get("id") or ev.raw_data.get("event_id") or ev.raw_data.get("correlation_id")) if hasattr(ev, "raw_data") else None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "summary": summary_text[: self._max_summary_len],  # avoid huge payloads
                    "fields": trimmed_fields,
                }
            )
            self._embeddings_count[tenant_id] += 1

        if not payload["summaries"]:
            return

        attempt_count = len(payload["summaries"])
        self._embeddings_attempts[tenant_id] += attempt_count
        runtime_metrics.increment_counter(
            "ingestion_embedding_summaries_total",
            amount=attempt_count,
            outcome="attempted",
        )
        self._record_runtime_snapshot()

        async def _post_embeddings():
            try:
                logger.info(
                    "Embedding fan-out: tenant=%s count=%d",
                    tenant_id,
                    len(payload["summaries"]),
                )
                async with httpx.AsyncClient(timeout=3.0) as client:
                    await client.post(f"{self.model_gateway_url}/api/v1/embeddings/security-events", json=payload)
                self._embeddings_success[tenant_id] += attempt_count
                runtime_metrics.increment_counter(
                    "ingestion_embedding_summaries_total",
                    amount=attempt_count,
                    outcome="success",
                )
            except Exception as e:
                self._embeddings_fail[tenant_id] += attempt_count
                runtime_metrics.increment_counter(
                    "ingestion_embedding_summaries_total",
                    amount=attempt_count,
                    outcome="failed",
                )
                logger.debug("Embedding ingest failed (tenant %s): %s", tenant_id, e)
            finally:
                self._record_runtime_snapshot()

        # Fire-and-forget to avoid blocking ingestion
        asyncio.create_task(_post_embeddings())

    def _summarize_for_embedding(self, ev: IngestEvent) -> Tuple[Optional[str], Dict[str, Any], Optional[str]]:
        """
        Build a concise summary and trimmed fields for embedding fan-out.
        Keeps volume low for verbose sources (e.g., flow logs) and avoids leaking full raw payloads.
        """
        fields = ev.ecs_fields.model_dump(by_alias=True) if hasattr(ev, "ecs_fields") else {}
        raw = ev.raw_data if hasattr(ev, "raw_data") else {}

        source_info = fields.get("source", {}) if isinstance(fields.get("source"), dict) else {}
        source_name = str(source_info.get("name") or raw.get("source") or "").lower() or None
        severity = str(
            self._get_nested(raw, "severity")
            or self._get_nested(raw, "event.severity")
            or self._get_nested(fields, "event.severity")
            or ""
        ).lower() or None
        event_kind = str(
            self._get_nested(raw, "event.kind") or self._get_nested(fields, "event.kind") or raw.get("event_type", "")
        ).lower() or None
        action = self._get_nested(raw, "event.action") or self._get_nested(fields, "event.action")
        outcome = self._get_nested(raw, "event.outcome") or self._get_nested(fields, "event.outcome")
        user = self._get_nested(raw, "user.name") or self._get_nested(fields, "user.name")
        rule_name = self._get_nested(raw, "rule.name") or self._get_nested(fields, "rule.name")

        network = fields.get("network", {}) if isinstance(fields.get("network"), dict) else raw.get("network", {}) or {}
        src_ip = self._get_nested(network, "source.ip") or raw.get("srcaddr") or raw.get("source_ip")
        dst_ip = self._get_nested(network, "destination.ip") or raw.get("dstaddr") or raw.get("destination_ip")
        src_port = self._get_nested(network, "source.port") or raw.get("srcport") or raw.get("sport")
        dst_port = self._get_nested(network, "destination.port") or raw.get("dstport") or raw.get("dport")
        direction = self._get_nested(network, "direction") or raw.get("direction")
        bytes_count = self._get_nested(network, "bytes") or raw.get("bytes")
        packets = self._get_nested(network, "packets") or raw.get("packets")

        message = (
            raw.get("message")
            or raw.get("detail")
            or raw.get("description")
            or self._get_nested(raw, "log")
        )
        host_id = self._get_nested(fields, "host.id") or raw.get("host_id")

        flow_summary = None
        if src_ip or dst_ip:
            flow_summary = f"{src_ip or '?'}:{src_port or '-'} -> {dst_ip or '?'}:{dst_port or '-'}"
            if direction:
                flow_summary = f"{direction}:{flow_summary}"

        summary_parts = []
        for part in (source_name, f"kind={event_kind}" if event_kind else None, f"sev={severity}" if severity else None):
            if part:
                summary_parts.append(part)
        for part in (f"action={action}" if action else None, f"outcome={outcome}" if outcome else None):
            if part:
                summary_parts.append(part)
        if rule_name:
            summary_parts.append(f"rule={rule_name}")
        if user:
            summary_parts.append(f"user={user}")
        if flow_summary:
            summary_parts.append(flow_summary)
        if bytes_count or packets:
            summary_parts.append(f"bytes={bytes_count or 0} pkts={packets or 0}")
        if message:
            summary_parts.append(self._truncate(str(message), 180))

        summary_text = " | ".join(summary_parts)
        if not summary_text:
            return None, {}, host_id

        trimmed_fields: Dict[str, Any] = {
            "severity": severity,
            "event_kind": event_kind,
            "action": action,
            "outcome": outcome,
            "user": user,
            "direction": direction,
            "source": {"ip": src_ip, "port": src_port},
            "destination": {"ip": dst_ip, "port": dst_port},
            "network": {k: v for k, v in {"bytes": bytes_count, "packets": packets}.items() if v is not None},
            "rule": rule_name,
            "message": self._truncate(str(message), 256) if message else None,
        }
        # Drop empty entries
        trimmed_fields = {k: v for k, v in trimmed_fields.items() if v not in (None, {}, "")}

        return summary_text, trimmed_fields, host_id

    @staticmethod
    def _get_nested(obj: Any, path: str) -> Optional[Any]:
        """Safely get nested dict keys using dot notation."""
        if not isinstance(obj, dict):
            return None
        current = obj
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _truncate(self, val: str, limit: int) -> str:
        if not val:
            return val
        if len(val) <= limit:
            return val
        return val[:limit] + "..."

    async def flush_all(self) -> None:
        """Flush all pending batches."""
        tenant_ids = list(self.batches.keys())
        for tenant_id in tenant_ids:
            await self._flush_batch(tenant_id, trigger="shutdown")

    def queue_summary(self) -> Dict[str, int]:
        """Return aggregate queue pressure without exposing tenant identifiers."""
        pending_depths = [len(batch) for batch in self.batches.values() if batch]
        return {
            "pending_events": sum(pending_depths),
            "tenants_with_pending_batches": len(pending_depths),
            "active_batch_timers": sum(1 for task in self.batch_timers.values() if not task.done()),
            "max_batch_depth": max(pending_depths, default=0),
        }

    def embedding_metrics(self) -> Dict[str, Dict[str, int]]:
        """Return per-tenant embedding fan-out metrics."""
        tenants = set(
            list(self._embeddings_attempts.keys())
            + list(self._embeddings_success.keys())
            + list(self._embeddings_fail.keys())
        )
        metrics = {}
        for t in tenants:
            metrics[t] = {
                "attempted": self._embeddings_attempts.get(t, 0),
                "success": self._embeddings_success.get(t, 0),
                "failed": self._embeddings_fail.get(t, 0),
                "cap_used": self._embeddings_count.get(t, 0),
                "cap_limit": self.embeddings_cap,
            }
        return metrics

    def embedding_summary(self) -> Dict[str, int]:
        """Return aggregate embedding fan-out metrics without tenant-level leakage."""
        tenants = set(
            list(self._embeddings_attempts.keys())
            + list(self._embeddings_success.keys())
            + list(self._embeddings_fail.keys())
            + list(self._embeddings_count.keys())
        )
        return {
            "tenants_with_activity": len(tenants),
            "attempted_total": sum(self._embeddings_attempts.values()),
            "success_total": sum(self._embeddings_success.values()),
            "failed_total": sum(self._embeddings_fail.values()),
            "cap_used_total": sum(self._embeddings_count.values()),
            "cap_limit_per_tenant": self.embeddings_cap,
        }

    def _record_runtime_snapshot(self) -> None:
        queue = self.queue_summary()
        embeddings = self.embedding_summary()
        runtime_metrics.set_gauge("ingestion_pending_events", float(queue["pending_events"]))
        runtime_metrics.set_gauge(
            "ingestion_pending_tenants",
            float(queue["tenants_with_pending_batches"]),
        )
        runtime_metrics.set_gauge(
            "ingestion_active_batch_timers",
            float(queue["active_batch_timers"]),
        )
        runtime_metrics.set_gauge(
            "ingestion_max_batch_depth",
            float(queue["max_batch_depth"]),
        )
        runtime_metrics.set_gauge(
            "ingestion_embeddings_cap_used_total",
            float(embeddings["cap_used_total"]),
        )
        runtime_metrics.set_gauge(
            "ingestion_embeddings_activity_tenants",
            float(embeddings["tenants_with_activity"]),
        )


# Global batch processor instance
_batch_processor: Optional[BatchProcessor] = None


def get_batch_processor() -> BatchProcessor:
    """Get global batch processor instance."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
    return _batch_processor
