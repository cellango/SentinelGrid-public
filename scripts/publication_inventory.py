#!/usr/bin/env python3
"""Check the selected source paths, or refresh them after reviewing the diff."""

import argparse
import json
import sys

from public_preview import (
    PUBLICATION_INVENTORY, ROOT, private_file_reason,
    publication_inventory_failures, source_files,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true",
                        help="Record current candidate paths after content review")
    args = parser.parse_args()
    files = source_files()
    if not args.refresh:
        failures = publication_inventory_failures(files)
    else:
        failures = []
        for path in files:
            relative = path.relative_to(ROOT)
            reason = private_file_reason(relative)
            if reason or path.is_symlink():
                failures.append(f"{relative}: {reason or 'symlink requires review'}")
        if not failures:
            names = sorted({p.relative_to(ROOT).as_posix() for p in files}
                           | {PUBLICATION_INVENTORY.as_posix()})
            destination = ROOT / PUBLICATION_INVENTORY
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps({"format_version": 1, "files": names}, indent=2) + "\n")
            print(f"Recorded {len(names)} selected paths. Review the inventory diff before publication.")
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    if not failures and not args.refresh:
        print(f"Publication path selection matches {len(files)} candidate files.")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
