"""Prepare a trusted exact-host JDK-only probe; no issuer/admission authority."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform

FIXTURE = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate(tool_root):
    inputs = json.loads((FIXTURE / "inputs.json").read_text())
    if platform.system() != "Darwin" or platform.machine() != "arm64" or platform.mac_ver()[0] != "15.5":
        raise ValueError("Unsupported exact research platform")
    for name, value in inputs["fixture_sha256"].items():
        path = FIXTURE / name
        if path.is_symlink() or digest(path) != value:
            raise ValueError("Fixture drift")
    tool_root = Path(tool_root)
    if not tool_root.is_absolute() or any(p.is_symlink() for p in [tool_root, *tool_root.parents]):
        raise ValueError("Absolute reviewed tool root without symlink parents required")
    tool_root = tool_root.resolve()
    archive = tool_root / inputs["JDK_archive_name"]
    if archive.is_symlink() or digest(archive) != inputs["JDK_archive_sha256"]:
        raise ValueError("JDK archive drift")
    pins = {row["path"]: row["sha256"] for row in inputs["JDK_installed_files"]}
    if len(pins) != len(inputs["JDK_installed_files"]) or len(pins) != 459:
        raise ValueError("Duplicate or incomplete JDK manifest")
    if any(Path(name).is_absolute() or ".." in Path(name).parts or Path(name).parts[0] != inputs["JDK_root_name"] for name in pins):
        raise ValueError("Unowned JDK manifest path")
    jdk = tool_root / inputs["JDK_root_name"]
    if jdk.is_symlink():
        raise ValueError("Unexpected JDK root symlink")
    actual = set()
    for path in jdk.rglob("*"):
        if path.is_symlink():
            raise ValueError("Unexpected JDK symlink")
        if path.is_file():
            actual.add(str(path.relative_to(tool_root)))
    if actual != set(pins):
        raise ValueError("Unexpected or missing JDK installed input")
    for relative, value in pins.items():
        if digest(tool_root / relative) != value:
            raise ValueError("Installed JDK drift")
    for name, value in inputs["OS_input_sha256"].items():
        if digest(Path(name)) != value:
            raise ValueError("OS input drift")
    return inputs, tool_root / inputs["java_relative"], tool_root / inputs["java_home_relative"]

def profile_text(java, java_home, output):
    quote = lambda path: json.dumps(str(path))
    work = output / "work"
    return (
        '(version 1)\n(deny default)\n(import "dyld-support.sb")\n'
        + '(allow process-exec (literal ' + quote(java) + '))\n'
        + '(allow file-read* file-test-existence file-map-executable (subpath ' + quote(java_home) + ') (subpath "/System/Library") (subpath "/usr/lib"))\n'
        + '(allow file-read* file-test-existence file-write* (subpath ' + quote(work) + ') (literal "/dev/null"))\n'
        + '(allow file-read-metadata file-test-existence (path-ancestors ' + quote(java) + ') (path-ancestors ' + quote(work) + '))\n'
        + '(allow signal (target self))\n(allow sysctl-read)\n(deny network*)\n(deny process-fork)\n(deny file-link)\n'
    )

def prepare(tool_root, output):
    inputs, java, java_home = validate(tool_root)
    output = Path(output)
    if not output.is_absolute() or any(p.is_symlink() for p in [output, *output.parents]):
        raise ValueError("New absolute output without symlink parents required")
    output = output.resolve()
    if output == FIXTURE or output.is_relative_to(FIXTURE) or output.is_relative_to(Path(tool_root).resolve()):
        raise ValueError("Output must be outside fixture and tool root")
    output.mkdir(mode=0o700, exist_ok=False)
    work = output / "work"
    work.mkdir(mode=0o700)
    for relative in ["home", "tmp", "classes", "empty"]:
        (work / relative).mkdir(mode=0o700)
    canary = output / "denied-canary.txt"
    canary.write_text("SYNTHETIC_OWNED_JVM_CANARY_NO_SECRET\n")
    (work / "escape-link").symlink_to(canary)
    (work / "JvmBoundaryProbe.java").write_bytes((FIXTURE / "JvmBoundaryProbe.java").read_bytes())
    profile = output / "default-deny.sb"
    profile.write_text(profile_text(java, java_home, output))
    state = dict(root=str(output), tool_root=str(Path(tool_root).resolve()), java=str(java), java_home=str(java_home), profile_sha256=digest(profile), fixture_sha256=inputs["fixture_sha256"], no_Maven_issuer_provider_or_admission_authority=True)
    (output / "state.json").write_text(json.dumps(state, indent=2) + "\n")
    return state

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.tool_root, args.output), indent=2))
