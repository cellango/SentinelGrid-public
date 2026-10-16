"""Helpers for loading the shared SentinelGrid playbook catalog."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


def default_catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "cfg" / "playbooks" / "catalog.yaml"


@lru_cache(maxsize=1)
def load_playbook_catalog(path: str | None = None) -> list[dict[str, Any]]:
    """Load the shared playbook catalog from YAML."""
    catalog_path = Path(path) if path else default_catalog_path()
    with catalog_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    playbooks = data.get("playbooks") or []
    return [playbook for playbook in playbooks if isinstance(playbook, dict)]
