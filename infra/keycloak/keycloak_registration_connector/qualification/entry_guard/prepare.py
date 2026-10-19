#!/usr/bin/env python3
"""Prepare an opt-in temporary source overlay. Never install into an issuer."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

SOURCE = "services/src/main/java/org/keycloak/protocol/oidc/endpoints/TokenEndpoint.java"
SHA256 = "23c8c74cbaeee855b77ae71c855a0e577b61c14e2c0c0a3ba97f66d0b8103ef7"
ANCHOR = "    public Response processGrantRequest() {\n"
HOOK = "        ai.sentinelgrid.research.EntryGuardProbe.beforeNativeDispatch(realm);\n"


def prepare(source, output, mode):
    if (source / SOURCE).is_symlink() or output.resolve().is_relative_to(source.resolve()):
        raise ValueError("Use owned source bytes and a separate experiment directory")
    original = (source / SOURCE).read_bytes()
    if hashlib.sha256(original).hexdigest() != SHA256:
        raise ValueError("Unreviewed native source bytes")
    text = original.decode("utf-8")
    if text.count(ANCHOR) != 1 or HOOK in text:
        raise ValueError("Unexpected native entry shape")
    if mode not in {"native", "guarded"}:
        raise ValueError("Unknown experiment mode")
    if mode == "guarded":
        text = text.replace(ANCHOR, ANCHOR + HOOK, 1)
    output.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).resolve().parent
    shutil.copyfile(fixture / "pom.xml", output / "pom.xml")
    shutil.copytree(fixture / "src", output / "src")
    target = output / "src/main/java/org/keycloak/protocol/oidc/endpoints/TokenEndpoint.java"
    target.parent.mkdir(parents=True)
    target.write_bytes(text.encode("utf-8"))
    record = {"mode": mode, "source_sha256": SHA256,
              "overlay_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
              "changed_lines": 1 if mode == "guarded" else 0,
              "production_qualification": False}
    (output / "overlay.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("mode", choices=["native", "guarded"])
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output, args.mode), sort_keys=True))
