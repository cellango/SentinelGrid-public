#!/usr/bin/env python3
"""Run the Phase 8.1 compliance migration/backfill.

Dry-run is the default. Pass --apply to write framework selections and legacy
report metadata markers. This script never creates evidence items.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
COMPLIANCE_ROOT = BACKEND_ROOT / "services" / "compliance_service"

for path in (COMPLIANCE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

from app.services.phase8_backfill import phase8_backfill_service  # noqa: E402
from sg_core.db import SessionLocal  # noqa: E402
from sqlalchemy import text  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill Phase 8 compliance framework/report metadata state.")
    parser.add_argument("--tenant-id", help="Optional tenant UUID to backfill. Defaults to all tenants.")
    parser.add_argument("--apply", action="store_true", help="Write changes. Without this flag the script dry-runs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_superadmin = 'true'"))
        result = phase8_backfill_service.run(db, tenant_id=args.tenant_id, dry_run=not args.apply)
        if args.apply:
            db.commit()
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
