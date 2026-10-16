#!/usr/bin/env python3
"""Assemble a checksum-verified IAM-only Flyway location; never access a database."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "publication/iam-database-profile.json"


def prepare(output: Path, *, root=ROOT, profile=PROFILE):
    manifest = json.loads(profile.read_text())
    selected = []
    versions = set()
    for item in manifest["migrations"]:
        source = root / item["path"]
        if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
            raise ValueError("Migration must be a regular reviewed repository file")
        if hashlib.sha256(source.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Migration checksum changed: {item['path']}")
        version = int(source.name.split("__", 1)[0][1:])
        if version in versions:
            raise ValueError("Duplicate migration version in IAM profile")
        versions.add(version)
        selected.append(source)
    if output.exists() or output.is_symlink():
        raise ValueError("Output must be a new directory")
    output.mkdir(parents=True, mode=0o700)
    location = output / "sql"
    location.mkdir(mode=0o700)
    for source in selected:
        shutil.copyfile(source, location / source.name)
    (output / "flyway.conf").write_text(
        "flyway.locations=filesystem:sql\n"
        "flyway.table=flyway_schema_history\n"
        "flyway.validateOnMigrate=true\n"
        "flyway.validateMigrationNaming=true\n"
        "flyway.baselineOnMigrate=false\n"
        "flyway.cleanDisabled=true\n"
    )
    (output / "reviewed-profile.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return len(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = prepare(args.output)
    print(f"Prepared {count} unchanged reviewed migrations. No database was accessed.")


if __name__ == "__main__":
    main()
