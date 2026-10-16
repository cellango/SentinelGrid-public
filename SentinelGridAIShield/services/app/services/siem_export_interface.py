from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


SUPPORTED_SIEM_TYPES = {
    "ibm_qradar_cef_syslog": "IBM QRadar via CEF over Syslog TLS/TCP",
    "microsoft_sentinel_dcr": "Microsoft Sentinel via Log Ingestion API and DCR",
    "splunk_hec": "Splunk Enterprise or Splunk Cloud via HTTP Event Collector",
}


@dataclass(slots=True)
class NormalizedSiemEvent:
    event_id: str
    event_type: str
    occurred_at: datetime
    tenant_id: str
    realm: str | None = None
    ai_app_id: str | None = None
    user_id: str | None = None
    provider: str | None = None
    model: str | None = None
    policy_decision: str | None = None
    severity: str = "info"
    risk_flags: dict[str, bool] = field(default_factory=dict)
    metrics: dict[str, int | float] = field(default_factory=dict)
    previews: dict[str, str] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SiemDestinationConfig:
    name: str
    type: str
    enabled: bool
    transport: str
    endpoint: str
    auth: dict[str, Any] = field(default_factory=dict)
    routing: dict[str, Any] = field(default_factory=dict)
    filters: dict[str, Any] = field(default_factory=dict)
    format_options: dict[str, Any] = field(default_factory=dict)
    delivery: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DeliveryResult:
    destination_name: str
    success: bool
    status_code: int | None = None
    message: str | None = None


class SiemExporter(ABC):
    """
    Standard adapter contract for external SIEM delivery.

    Adapters should:
    - validate destination configuration
    - format NormalizedSiemEvent instances for the target SIEM
    - deliver a batch and return a DeliveryResult
    """

    @property
    @abstractmethod
    def adapter_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def validate_config(self, config: SiemDestinationConfig) -> None:
        raise NotImplementedError

    @abstractmethod
    def serialize_event(self, event: NormalizedSiemEvent, config: SiemDestinationConfig) -> dict[str, Any] | str:
        raise NotImplementedError

    @abstractmethod
    def send_batch(
        self,
        events: list[NormalizedSiemEvent],
        config: SiemDestinationConfig,
    ) -> DeliveryResult:
        raise NotImplementedError
