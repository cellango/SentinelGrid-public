#!/usr/bin/env python3
"""
Validate the alarm catalog against naming/severity conventions.
No external deps required (uses stdlib only).
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "alarms" / "catalog.json"

ALLOWED_SEVERITIES = {"CRIT", "HIGH", "MED", "LOW"}
ALLOWED_TYPES = {"detection", "health", "coverage"}
ALLOWED_CATEGORIES = {"auth", "endpoint", "network", "data", "application", "service"}
ID_PATTERN = re.compile(r"^ALM-[A-Z]+-[A-Za-z0-9]+$")


def load_catalog() -> list[dict]:
    if not CATALOG_PATH.exists():
        raise SystemExit(f"Catalog not found: {CATALOG_PATH}")
    with CATALOG_PATH.open() as f:
        return json.load(f)


def validate_entry(entry: dict) -> list[str]:
    errors = []
    alarm_id = entry.get("alarm_id", "")
    if not ID_PATTERN.match(alarm_id):
        errors.append(f"{alarm_id or '<missing>'}: invalid alarm_id format (expected ALM-XXX-Name)")
    if entry.get("severity") not in ALLOWED_SEVERITIES:
        errors.append(f"{alarm_id}: invalid severity {entry.get('severity')}")
    if entry.get("type") not in ALLOWED_TYPES:
        errors.append(f"{alarm_id}: invalid type {entry.get('type')}")
    if entry.get("category") not in ALLOWED_CATEGORIES:
        errors.append(f"{alarm_id}: invalid category {entry.get('category')}")
    for req in ("title", "source", "entity"):
        if not entry.get(req):
            errors.append(f"{alarm_id}: missing required field {req}")
    return errors


def validate_catalog(catalog: list[dict]) -> list[str]:
    errors: list[str] = []
    seen_ids = set()
    for entry in catalog:
        errors.extend(validate_entry(entry))
        alarm_id = entry.get("alarm_id")
        if alarm_id in seen_ids:
            errors.append(f"{alarm_id}: duplicate alarm_id")
        seen_ids.add(alarm_id)
    return errors


def main() -> int:
    try:
        catalog = load_catalog()
    except Exception as exc:
        print(f"Error reading catalog: {exc}", file=sys.stderr)
        return 1

    errs = validate_catalog(catalog)
    if errs:
        for err in errs:
            print(f"[ERROR] {err}", file=sys.stderr)
        return 1

    print(f"Catalog OK: {len(catalog)} alarms validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
