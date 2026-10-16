"""Read-only compliance framework catalog loaded from bundled framework data."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


FRAMEWORK_FILES = {
    "soc2": "soc2_controls.json",
    "hipaa": "hipaa_security_rule.json",
    "pci_dss": "pci_dss_requirements.json",
    "nist_800_171": "nist_800_171_controls.json",
}


FRAMEWORK_METADATA = {
    "soc2": {
        "framework_code": "SOC2",
        "framework_name": "SOC 2 Trust Services Criteria",
        "description": "AICPA Trust Services Criteria currently used by SentinelGrid readiness reporting.",
        "runtime_support": "readiness",
    },
    "hipaa": {
        "framework_code": "HIPAA",
        "framework_name": "HIPAA Security Rule",
        "description": "HIPAA Security Rule catalog data available for upcoming framework selection.",
        "runtime_support": "catalog",
    },
    "pci_dss": {
        "framework_code": "PCI_DSS",
        "framework_name": "PCI DSS",
        "description": "PCI DSS catalog data available for upcoming framework selection.",
        "runtime_support": "catalog",
    },
    "nist_800_171": {
        "framework_code": "NIST_800_171",
        "framework_name": "NIST SP 800-171",
        "description": "NIST SP 800-171 catalog data with CMMC Level 2 relationship metadata.",
        "runtime_support": "catalog",
    },
}


ALIASES = {
    "soc2": "soc2",
    "soc_2": "soc2",
    "soc-2": "soc2",
    "hipaa": "hipaa",
    "pci": "pci_dss",
    "pci_dss": "pci_dss",
    "pci-dss": "pci_dss",
    "nist": "nist_800_171",
    "nist_800_171": "nist_800_171",
    "nist-800-171": "nist_800_171",
    "iso": "iso27001",
    "iso27001": "iso27001",
    "iso_27001": "iso27001",
    "customer_questionnaire": "customer_questionnaires",
    "customer_questionnaires": "customer_questionnaires",
}


def normalize_framework_id(value: str) -> str:
    """Normalize URL/framework tokens to canonical catalog keys."""
    token = (value or "").strip().lower().replace(" ", "_")
    return ALIASES.get(token, token)


def _load_json(filename: str) -> dict[str, Any]:
    with (DATA_DIR / filename).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _category_summary(category: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": category["code"],
        "name": category["name"],
        "description": category.get("description"),
        "control_count": len(category.get("controls", [])),
    }


def _control_payload(framework_id: str, category: dict[str, Any], control: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": control["control_id"],
        "framework_id": framework_id,
        "control_id": control["control_id"],
        "title": control["control_name"],
        "description": control.get("description"),
        "category": {
            "code": category["code"],
            "name": category["name"],
        },
        "priority": control.get("priority"),
        "coverage_level": control.get("coverage_level"),
        "sentinelgrid_features": control.get("sentinelgrid_features", []),
        "implementation_specs": control.get("implementation_specs", []),
        "evidence_requirements": [],
    }


def _flatten_controls(framework_id: str, raw: dict[str, Any]) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    for category in raw.get("categories", []):
        controls.extend(
            _control_payload(framework_id, category, control)
            for control in category.get("controls", [])
        )
    return controls


def _framework_summary(framework_id: str, raw: dict[str, Any]) -> dict[str, Any]:
    metadata = FRAMEWORK_METADATA[framework_id]
    categories = raw.get("categories", [])
    controls = _flatten_controls(framework_id, raw)

    return {
        "id": framework_id,
        "framework_id": framework_id,
        "framework_code": metadata["framework_code"],
        "framework_name": metadata["framework_name"],
        "version": raw.get("version"),
        "description": metadata["description"],
        "runtime_support": metadata["runtime_support"],
        "source": "bundled_json",
        "category_count": len(categories),
        "control_count": len(controls),
        "related_framework": raw.get("related_framework"),
        "additional_features": raw.get("additional_features", {}),
    }


@lru_cache(maxsize=1)
def load_framework_catalog() -> dict[str, dict[str, Any]]:
    """Load and normalize bundled framework JSON data."""
    catalog: dict[str, dict[str, Any]] = {}

    for framework_id, filename in FRAMEWORK_FILES.items():
        raw = _load_json(filename)
        summary = _framework_summary(framework_id, raw)
        catalog[framework_id] = {
            **summary,
            "categories": [_category_summary(category) for category in raw.get("categories", [])],
            "controls": _flatten_controls(framework_id, raw),
        }

    return catalog


class FrameworkCatalog:
    """Framework catalog read model for API endpoints."""

    def list_frameworks(self) -> dict[str, Any]:
        items = [
            {
                key: value
                for key, value in framework.items()
                if key not in {"categories", "controls", "additional_features"}
            }
            for framework in load_framework_catalog().values()
        ]
        return {
            "items": items,
            "count": len(items),
            "source": "bundled_json",
            "schema_tables": [
                "compliance_frameworks",
                "compliance_controls",
                "control_mappings",
                "control_evidence_requirements",
                "evidence_packages",
                "evidence_items",
                "evidence_control_links",
                "evidence_collection_tasks",
                "evidence_reviews",
                "evidence_exports",
            ],
        }

    def get_framework(self, framework_id: str) -> dict[str, Any] | None:
        normalized = normalize_framework_id(framework_id)
        framework = load_framework_catalog().get(normalized)
        if not framework:
            return None
        return {key: value for key, value in framework.items() if key != "controls"}

    def list_controls(self, framework_id: str) -> dict[str, Any] | None:
        normalized = normalize_framework_id(framework_id)
        framework = load_framework_catalog().get(normalized)
        if not framework:
            return None
        return {
            "framework_id": normalized,
            "framework_code": framework["framework_code"],
            "framework_name": framework["framework_name"],
            "items": framework["controls"],
            "count": len(framework["controls"]),
            "source": "bundled_json",
        }


framework_catalog = FrameworkCatalog()
