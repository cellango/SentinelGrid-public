from __future__ import annotations

import logging

from app.core.config import settings
from app.schemas import TelemetryEventCreate
from app.services.siem_event_normalizer import normalize_ai_event
from app.services.siem_export_config import SiemExportConfigLoader
from app.services.siem_export_interface import DeliveryResult, NormalizedSiemEvent, SiemExporter
from app.services.splunk_hec_exporter import SplunkHecExporter


logger = logging.getLogger(__name__)

_SEVERITY_RANK = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

_siem_export_manager: "SiemExportManager | None" = None


class SiemExportManager:
    def __init__(
        self,
        loader: SiemExportConfigLoader | None = None,
        exporters: dict[str, SiemExporter] | None = None,
    ):
        self._loader = loader or SiemExportConfigLoader()
        self._exporters = exporters or {
            "splunk_hec": SplunkHecExporter(),
        }

    def export_ai_event(self, event: TelemetryEventCreate) -> list[DeliveryResult]:
        normalized_event = normalize_ai_event(event)
        return self.export_normalized_events([normalized_event])

    def export_normalized_events(self, events: list[NormalizedSiemEvent]) -> list[DeliveryResult]:
        if not settings.SIEM_EXPORT_ENABLED or not events:
            return []

        try:
            export_config = self._loader.load()
        except FileNotFoundError:
            logger.warning("SIEM export is enabled but the config file is missing: %s", self._loader.config_path)
            return []
        except Exception:
            logger.exception("Failed to load SIEM export configuration")
            return []

        results: list[DeliveryResult] = []
        for destination in export_config.destinations:
            if not destination.enabled:
                continue

            matched_events = [event for event in events if _matches_filters(event, destination.filters)]
            if not matched_events:
                continue

            exporter = self._exporters.get(destination.type)
            if exporter is None:
                logger.warning(
                    "Skipping enabled SIEM destination %s with unsupported type %s",
                    destination.name,
                    destination.type,
                )
                results.append(
                    DeliveryResult(
                        destination_name=destination.name,
                        success=False,
                        message=f"Unsupported SIEM adapter type: {destination.type}",
                    )
                )
                continue

            try:
                exporter.validate_config(destination)
                result = exporter.send_batch(matched_events, destination)
            except Exception:
                logger.exception("SIEM export failed for destination %s", destination.name)
                result = DeliveryResult(
                    destination_name=destination.name,
                    success=False,
                    message="Unhandled SIEM exporter exception",
                )
            results.append(result)

        return results


def get_siem_export_manager() -> SiemExportManager:
    global _siem_export_manager
    if _siem_export_manager is None:
        _siem_export_manager = SiemExportManager()
    return _siem_export_manager


def _matches_filters(event: NormalizedSiemEvent, filters: dict[str, object]) -> bool:
    include_event_types = {value for value in filters.get("include_event_types", []) if isinstance(value, str)}
    if include_event_types and event.event_type not in include_event_types:
        return False

    exclude_event_types = {value for value in filters.get("exclude_event_types", []) if isinstance(value, str)}
    if event.event_type in exclude_event_types:
        return False

    minimum_severity = filters.get("minimum_severity")
    if isinstance(minimum_severity, str):
        if _severity_rank(event.severity) < _severity_rank(minimum_severity):
            return False

    include_tenants = {str(value) for value in filters.get("include_tenants", [])}
    if include_tenants and event.tenant_id not in include_tenants:
        return False

    exclude_tenants = {str(value) for value in filters.get("exclude_tenants", [])}
    if event.tenant_id in exclude_tenants:
        return False

    if filters.get("only_blocked") and event.policy_decision != "blocked":
        return False

    return True


def _severity_rank(severity: str) -> int:
    return _SEVERITY_RANK.get(severity, -1)
