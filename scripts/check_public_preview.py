#!/usr/bin/env python3
"""Check source-preview hygiene without importing applications or contacting services."""

from collections import Counter
from pathlib import Path
import re
import sys

from public_preview import ROOT, private_file_reason, publication_inventory_failures, source_files
from check_documentation import documentation_failures


def main() -> int:
    failures = []
    files = source_files()
    failures.extend(publication_inventory_failures(files))
    failures.extend(documentation_failures(files))
    python_count = 0
    for path in files:
        relative = path.relative_to(ROOT)
        if path.is_symlink():
            failures.append(f"{relative}: symlink requires explicit publication review")
            continue
        reason = private_file_reason(relative)
        if reason:
            failures.append(f"{relative}: {reason}")
        if path.stat().st_size > 5 * 1024 * 1024:
            failures.append(f"{relative}: exceeds the preview's 5 MiB source-file limit")
        if path.suffix == ".py":
            python_count += 1
            try:
                compile(path.read_bytes(), str(relative), "exec", dont_inherit=True)
            except (SyntaxError, ValueError) as exc:
                # Do not echo source lines, which may contain credentials.
                failures.append(f"{relative}:{getattr(exc, 'lineno', '?')}: "
                                f"{getattr(exc, 'msg', type(exc).__name__)}")

    for name in ["README.md", "RELEASE_SCOPE.md", "SECURITY.md", "CONTRIBUTING.md",
                 "LICENSE", "NOTICE", "LICENSING.md", "THIRD_PARTY_NOTICES.md", ".dockerignore"]:
        if not (ROOT / name).is_file():
            failures.append(f"Missing public entry point: {name}")

    for name in ["agents/wazuh/LICENSE_WAZUH.txt",
                 "scripts/rebrand-agents/LICENSE_WAZUH.txt"]:
        text = (ROOT / name).read_text()
        if "placeholder" in text.lower() or "END OF TERMS AND CONDITIONS" not in text:
            failures.append(f"{name}: incomplete upstream license")

    active = {p.name for p in (ROOT / ".github/workflows").iterdir()
              if p.suffix in {".yml", ".yaml"}}
    if active != {"source-preview.yml"}:
        failures.append("Active workflows differ from the reviewed source-preview workflow")

    versions = Counter()
    for path in (ROOT / "backend/migrations_consolidated").glob("V*.sql"):
        match = re.match(r"V(\d{3})__[a-z0-9_]+\.sql$", path.name)
        if not match:
            failures.append(f"Invalid consolidated migration name: {path.name}")
        else:
            versions[match[1]] += 1
    failures.extend(f"Duplicate consolidated Flyway version: V{v}"
                    for v, count in versions.items() if count > 1)

    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    print(f"Reviewed {len(files)} source files; compiled {python_count} Python files; "
          f"{len(failures)} hygiene failures.")
    print("This check does not establish runtime security, secret clearance, or licensing clearance.")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
