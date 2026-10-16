from __future__ import annotations

import json
import os
import socket
import time
from datetime import timezone

import requests

from app.services.siem_export_interface import DeliveryResult, NormalizedSiemEvent, SiemDestinationConfig, SiemExporter


class SplunkHecExporter(SiemExporter):
    @property
    def adapter_type(self) -> str:
        return "splunk_hec"

    def __init__(self, session: requests.Session | None = None):
        self._session = session or requests.Session()

    def validate_config(self, config: SiemDestinationConfig) -> None:
        if config.transport != "http_json":
            raise ValueError("Splunk HEC destinations must use the http_json transport")
        if config.auth.get("type") != "bearer":
            raise ValueError("Splunk HEC destinations must use bearer auth")
        if not config.auth.get("token_env"):
            raise ValueError("Splunk HEC destinations must define auth.token_env")

    def serialize_event(self, event: NormalizedSiemEvent, config: SiemDestinationConfig) -> dict[str, object]:
        routing = config.routing or {}
        return {
            "time": event.occurred_at.timestamp(),
            "host": routing.get("host") or socket.gethostname(),
            "source": routing.get("source", "sentinelgrid_ai_shield"),
            "sourcetype": routing.get("sourcetype", "sentinelgrid:ai:event"),
            "index": routing.get("index", "main"),
            "event": _normalized_event_payload(event),
        }

    def send_batch(
        self,
        events: list[NormalizedSiemEvent],
        config: SiemDestinationConfig,
    ) -> DeliveryResult:
        if not events:
            return DeliveryResult(
                destination_name=config.name,
                success=True,
                message="No events matched destination filters",
            )

        self.validate_config(config)

        token_env = str(config.auth["token_env"])
        token = os.getenv(token_env)
        if not token:
            return DeliveryResult(
                destination_name=config.name,
                success=False,
                message=f"Environment variable {token_env} is not set",
            )

        headers = {
            "Authorization": f"Splunk {token}",
            "Content-Type": "application/json",
        }
        timeout_seconds = int(config.delivery.get("timeout_seconds", 10))
        retry_max = int(config.delivery.get("retry_max", 0))
        payload = "\n".join(
            json.dumps(self.serialize_event(event, config), separators=(",", ":"), sort_keys=True)
            for event in events
        )

        last_status_code: int | None = None
        last_message = "Splunk HEC delivery failed"
        for attempt in range(retry_max + 1):
            try:
                response = self._session.post(
                    config.endpoint,
                    headers=headers,
                    data=payload.encode("utf-8"),
                    timeout=timeout_seconds,
                )
                last_status_code = response.status_code
                if 200 <= response.status_code < 300:
                    return DeliveryResult(
                        destination_name=config.name,
                        success=True,
                        status_code=response.status_code,
                        message=f"Delivered {len(events)} event(s) to Splunk HEC",
                    )

                response_text = response.text.strip()
                last_message = response_text[:500] or f"Splunk HEC returned HTTP {response.status_code}"
                if response.status_code < 500 and response.status_code != 429:
                    break
            except requests.RequestException as exc:
                last_message = str(exc)

            if attempt < retry_max:
                time.sleep(min(0.5 * (2**attempt), 4.0))

        return DeliveryResult(
            destination_name=config.name,
            success=False,
            status_code=last_status_code,
            message=last_message,
        )


def _normalized_event_payload(event: NormalizedSiemEvent) -> dict[str, object]:
    occurred_at = event.occurred_at
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)

    payload = {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "occurred_at": occurred_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tenant_id": event.tenant_id,
        "severity": event.severity,
        "risk_flags": event.risk_flags,
        "metrics": event.metrics,
        "previews": event.previews,
        "labels": event.labels,
        "raw": event.raw,
    }
    optional_fields = {
        "realm": event.realm,
        "ai_app_id": event.ai_app_id,
        "user_id": event.user_id,
        "provider": event.provider,
        "model": event.model,
        "policy_decision": event.policy_decision,
    }
    for key, value in optional_fields.items():
        if value is not None:
            payload[key] = value
    return payload
