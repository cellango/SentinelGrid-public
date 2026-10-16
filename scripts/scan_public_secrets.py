#!/usr/bin/env python3
"""Run pinned Gitleaks locally; never print matches or upload reports."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from public_preview import ROOT, source_files

GITLEAKS_VERSION = "8.30.1"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scope", choices=["snapshot", "history"])
    args = parser.parse_args()
    binary = shutil.which(os.environ.get("GITLEAKS", "gitleaks"))
    if not binary:
        parser.error(f"Install official Gitleaks {GITLEAKS_VERSION} or set GITLEAKS to its path")
    version = subprocess.run([binary, "version"], check=True, capture_output=True,
                             text=True).stdout.strip().removeprefix("v")
    if version != GITLEAKS_VERSION:
        parser.error(f"Expected Gitleaks {GITLEAKS_VERSION}; installed version differs")

    output = ROOT / "artifacts/private-release-review"
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.chmod(0o700)
    report = output / f"{args.scope}-gitleaks.json"
    log = output / f"{args.scope}-gitleaks.log"
    common = ["--redact=100", "--no-banner", "--report-format=json",
              f"--report-path={report}", f"--config={ROOT / '.gitleaks.toml'}"]
    # Reports can expose sensitive paths and context even with secret redaction.
    # Keep both stdout and stderr local; CI receives only a status summary.
    old_umask = os.umask(0o077)
    try:
        with tempfile.TemporaryDirectory(prefix="sentinelgrid-source-") as directory:
            if args.scope == "snapshot":
                target = Path(directory)
                for path in source_files():
                    if path.is_symlink():
                        parser.error("Source snapshot contains a symlink; review it before scanning")
                    dest = target / path.relative_to(ROOT)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, dest)
                command = [binary, "dir", str(target), *common]
            else:
                shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"],
                                         cwd=ROOT, check=True, capture_output=True, text=True)
                if shallow.stdout.strip() != "false":
                    parser.error("History scan requires a full clone (fetch-depth: 0)")
                command = [binary, "git", str(ROOT), "--log-opts=--all", *common]
            with log.open("w") as handle:
                result = subprocess.run(command, cwd=ROOT, stdout=handle, stderr=handle)
        print(f"Gitleaks {GITLEAKS_VERSION}: {args.scope} scan "
              f"{'passed' if result.returncode == 0 else 'requires review or failed'}.")
        print(f"Local redacted evidence: {report.relative_to(ROOT)}")
        return result.returncode
    finally:
        os.umask(old_umask)


if __name__ == "__main__":
    raise SystemExit(main())
