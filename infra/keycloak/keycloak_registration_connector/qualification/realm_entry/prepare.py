#!/usr/bin/env python3
"""Prepare an isolated exact-source realm-denial experiment, never a provider."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ANCHOR = "    private static void resolveRealmAndUpdateSession(KeycloakSession session, String realmName) {\n"
HOOK = "        ai.sentinelgrid.research.RealmEntryProbe.beforeRealmResolution(session, realmName);\n"


def prepare(source, output, mode, shared_root=None):
    fixture = Path(__file__).resolve().parent
    if mode not in {"native", "guarded"} or output.resolve().is_relative_to(source.resolve()):
        raise ValueError("Use a reviewed mode and a separate owned output directory")
    manifest = json.loads((fixture / "native-sources.json").read_text())
    verified = {}
    for row in manifest["files"]:
        unit = source / row["path"]
        raw = unit.read_bytes()
        if unit.is_symlink() or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError("Unreviewed native source bytes")
        relative = row["path"].split("/src/main/java/", 1)[1]
        verified[relative] = raw
    resolver = "org/keycloak/services/resources/RealmsResource.java"
    text = verified[resolver].decode("utf-8")
    if text.count(ANCHOR) != 1 or HOOK in text:
        raise ValueError("Unexpected native realm resolver")
    if mode == "guarded":
        verified[resolver] = text.replace(ANCHOR, ANCHOR + HOOK, 1).encode()
    # Reuse unchanged native authentication controls from the adjacent opt-in lab.
    shared = shared_root if shared_root is not None else fixture.parent / "entry_guard"
    shared_files = ["src/main/java/ai/sentinelgrid/research/EntryGuardProbe.java",
                    "src/test/java/ai/sentinelgrid/research/NativeEntryGuardTest.java"]
    shared_bytes = {name: (shared / name).read_bytes() for name in shared_files}
    reviewed = json.loads((fixture / "shared-controls.json").read_text())
    if {r["path"]: r["sha256"] for r in reviewed["files"]} != {n: hashlib.sha256(b).hexdigest() for n, b in shared_bytes.items()}:
        raise ValueError("Unreviewed shared native authentication controls")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(fixture / "pom.xml", output / "pom.xml")
    shutil.copytree(fixture / "src", output / "src")
    for name, raw in shared_bytes.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    for name, raw in verified.items():
        target = output / "src/main/java" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    record = {"mode": mode, "changed_native_lines": int(mode == "guarded"),
              "source_files": manifest["files"],
              "overlay_sha256": hashlib.sha256(verified[resolver]).hexdigest(),
              "shared_controls_sha256": {n: hashlib.sha256(b).hexdigest() for n, b in shared_bytes.items()},
              "HTTP_or_production_qualification": False}
    (output / "overlay.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("mode", choices=["native", "guarded"])
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output, args.mode), sort_keys=True))
