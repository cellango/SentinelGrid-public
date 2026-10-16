"""Load and compile Playbook IR objects for SOC planning."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .playbook_catalog import default_catalog_path, load_playbook_catalog
from .playbook_ir_compiler import compile_playbook_irs
from .playbook_ir_models import PlaybookCrosswalkEntry, PlaybookIR


def default_crosswalk_path() -> Path:
    return Path(__file__).resolve().parents[3] / "cfg" / "playbooks" / "crosswalk.yaml"


def default_executor_aliases_path() -> Path:
    return Path(__file__).resolve().parents[3] / "cfg" / "playbooks" / "executor_aliases.yaml"


def default_ootb_playbooks_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "backend"
        / "agents"
        / "soar_agent"
        / "app"
        / "data"
        / "ootb_playbooks.yaml"
    )


def _load_yaml_list(path: Path, top_level_key: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    values = data.get(top_level_key) or []
    return [value for value in values if isinstance(value, dict)]


@lru_cache(maxsize=1)
def load_crosswalk_entries(path: str | None = None) -> list[PlaybookCrosswalkEntry]:
    yaml_path = Path(path) if path else default_crosswalk_path()
    raw_entries = _load_yaml_list(yaml_path, "mappings")
    return [PlaybookCrosswalkEntry.model_validate(entry) for entry in raw_entries]


@lru_cache(maxsize=1)
def load_executor_aliases(path: str | None = None) -> dict[str, dict[str, Any]]:
    yaml_path = Path(path) if path else default_executor_aliases_path()
    raw_entries = _load_yaml_list(yaml_path, "aliases")
    aliases: dict[str, dict[str, Any]] = {}
    for entry in raw_entries:
        action_ref = str(entry.get("action_ref") or "").strip()
        if action_ref:
            aliases[action_ref] = dict(entry)
    return aliases


@lru_cache(maxsize=1)
def load_ootb_playbooks(path: str | None = None) -> list[dict[str, Any]]:
    yaml_path = Path(path) if path else default_ootb_playbooks_path()
    return _load_yaml_list(yaml_path, "playbooks")


@lru_cache(maxsize=1)
def load_compiled_playbook_irs(
    *,
    catalog_path: str | None = None,
    crosswalk_path: str | None = None,
    ootb_path: str | None = None,
    executor_aliases_path: str | None = None,
) -> list[PlaybookIR]:
    return compile_playbook_irs(
        catalog_playbooks=load_playbook_catalog(catalog_path),
        ootb_playbooks=load_ootb_playbooks(ootb_path),
        crosswalk_entries=load_crosswalk_entries(crosswalk_path),
        executor_aliases=load_executor_aliases(executor_aliases_path),
    )


def playbook_ir_to_planner_dict(playbook: PlaybookIR) -> dict[str, Any]:
    """Project compiled IR back into the planner's current dict shape."""
    return {
        "id": playbook.playbook_id,
        "playbook_key": playbook.playbook_key,
        "key": playbook.playbook_key.lower().replace("_", "-"),
        "name": playbook.name,
        "category": " ".join(
            token
            for token in [playbook.owner_domain or "", *playbook.incident_families]
            if token
        ),
        "tags": list(playbook.tags),
        "mitre_tactics": list(playbook.framework_mappings.mitre_tactics),
        "mitre_techniques": list(playbook.framework_mappings.mitre_techniques),
        "nist_controls": list(playbook.framework_mappings.nist_controls),
        "automation_default": playbook.automation_mode,
        "compiled_ir": playbook,
    }


@lru_cache(maxsize=1)
def load_planner_playbooks() -> list[dict[str, Any]]:
    """Return compiled planner playbooks with raw-catalog fallback for unmapped entries."""
    compiled_irs = load_compiled_playbook_irs()
    compiled_catalog_ids = {playbook.playbook_id for playbook in compiled_irs}
    planner_playbooks = [playbook_ir_to_planner_dict(playbook) for playbook in compiled_irs]
    for catalog_playbook in load_playbook_catalog():
        if str(catalog_playbook.get("id")) in compiled_catalog_ids:
            continue
        planner_playbooks.append(catalog_playbook)
    return planner_playbooks

