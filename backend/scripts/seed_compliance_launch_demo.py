#!/usr/bin/env python3
"""Seed Phase 8 Compliance launch demo data.

Dry-run is the default. Pass --apply to write deterministic, idempotent demo
framework selections, evidence objects, reports, and agent recommendations.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import text


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
COMPLIANCE_ROOT = BACKEND_ROOT / "services" / "compliance_service"

for path in (COMPLIANCE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

from app.services.launch_demo_seed import launch_demo_seed_service  # noqa: E402
from sg_core.db import SessionLocal  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Compliance launch demo tenant data.")
    parser.add_argument("--tenant-id", help="Demo tenant UUID. Overrides --tenant-slug when provided.")
    parser.add_argument("--tenant-slug", default="demo", help="Demo tenant slug. Defaults to demo.")
    parser.add_argument("--apply", action="store_true", help="Write changes. Without this flag the script dry-runs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_superadmin = 'true'"))
        result = launch_demo_seed_service.run(
            db,
            tenant_id=args.tenant_id,
            tenant_slug=args.tenant_slug,
            dry_run=not args.apply,
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
