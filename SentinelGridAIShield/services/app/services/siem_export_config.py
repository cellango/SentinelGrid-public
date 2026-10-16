from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.core.config import settings
from app.services.siem_export_interface import SiemDestinationConfig


@dataclass(slots=True)
class LoadedSiemExportConfig:
    version: int
    default_delivery: dict[str, Any] = field(default_factory=dict)
    destinations: list[SiemDestinationConfig] = field(default_factory=list)


class SiemExportConfigLoader:
    def __init__(self, config_path: str | Path | None = None):
        self._config_path = Path(config_path or settings.SIEM_EXPORT_CONFIG_FILE)
        self._cached_mtime_ns: int | None = None
        self._cached_config: LoadedSiemExportConfig | None = None

    @property
    def config_path(self) -> Path:
        return self._config_path

    def load(self, force_reload: bool = False) -> LoadedSiemExportConfig:
        if not force_reload and self._cached_config is not None:
            try:
                current_mtime_ns = self._config_path.stat().st_mtime_ns
            except FileNotFoundError:
                self._cached_mtime_ns = None
                self._cached_config = None
                raise
            if current_mtime_ns == self._cached_mtime_ns:
                return self._cached_config

        loaded = self._load_from_disk()
        self._cached_mtime_ns = self._config_path.stat().st_mtime_ns
        self._cached_config = loaded
        return loaded

    def _load_from_disk(self) -> LoadedSiemExportConfig:
        if not self._config_path.exists():
            raise FileNotFoundError(f"SIEM export config file not found: {self._config_path}")

        with self._config_path.open("r", encoding="utf-8") as handle:
            document = yaml.safe_load(handle) or {}

        if not isinstance(document, dict):
            raise ValueError("SIEM export config must be a YAML mapping at the top level")

        version = document.get("version")
        if version != 1:
            raise ValueError("SIEM export config version must be 1")

        default_delivery = self._default_delivery()
        raw_default_delivery = document.get("default_delivery") or {}
        if raw_default_delivery:
            default_delivery.update(_as_dict(raw_default_delivery, "default_delivery"))

        raw_destinations = document.get("destinations") or []
        if not isinstance(raw_destinations, list):
            raise ValueError("SIEM export destinations must be a list")

        destinations: list[SiemDestinationConfig] = []
        for raw_destination in raw_destinations:
            destination = _as_dict(raw_destination, "destinations[]")
            delivery = dict(default_delivery)
            raw_delivery = destination.get("delivery") or {}
            if raw_delivery:
                delivery.update(_as_dict(raw_delivery, f"{destination.get('name', 'destination')}.delivery"))

            siem_destination = SiemDestinationConfig(
                name=str(destination.get("name", "")).strip(),
                type=str(destination.get("type", "")).strip(),
                enabled=bool(destination.get("enabled", False)),
                transport=str(destination.get("transport", "")).strip(),
                endpoint=str(destination.get("endpoint", "")).strip(),
                auth=_as_dict(destination.get("auth"), f"{destination.get('name', 'destination')}.auth"),
                routing=_as_dict(destination.get("routing"), f"{destination.get('name', 'destination')}.routing"),
                filters=_as_dict(destination.get("filters"), f"{destination.get('name', 'destination')}.filters"),
                format_options=_as_dict(
                    destination.get("format_options"),
                    f"{destination.get('name', 'destination')}.format_options",
                ),
                delivery=delivery,
            )

            if not siem_destination.name:
                raise ValueError("Each SIEM destination must define a non-empty name")
            if not siem_destination.type:
                raise ValueError(f"Destination {siem_destination.name} must define a type")
            if not siem_destination.transport:
                raise ValueError(f"Destination {siem_destination.name} must define a transport")
            if not siem_destination.endpoint:
                raise ValueError(f"Destination {siem_destination.name} must define an endpoint")

            destinations.append(siem_destination)

        return LoadedSiemExportConfig(
            version=version,
            default_delivery=default_delivery,
            destinations=destinations,
        )

    def _default_delivery(self) -> dict[str, Any]:
        return {
            "mode": "batch",
            "batch_size": settings.SIEM_EXPORT_BATCH_SIZE,
            "flush_interval_seconds": 5,
            "retry_max": settings.SIEM_EXPORT_RETRY_MAX,
            "timeout_seconds": settings.SIEM_EXPORT_TIMEOUT_SECONDS,
        }


def _as_dict(value: Any, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping")
    return dict(value)
