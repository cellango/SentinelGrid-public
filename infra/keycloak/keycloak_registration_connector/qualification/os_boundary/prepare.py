"""Prepare an exact macOS-only owned OS probe; grants no issuer authority."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform


FIXTURE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(runtime):
    inputs = json.loads((FIXTURE / "inputs.json").read_text())
    if platform.system() != "Darwin" or platform.machine() != inputs["architecture"] or platform.mac_ver()[0] != inputs["macOS_version"]:
        raise ValueError("Unsupported research platform; do not infer a working sandbox")
    for name, value in inputs["fixture_sha256"].items():
        path = FIXTURE / name
        if path.is_symlink() or digest(path) != value:
            raise ValueError("Fixture drift")
    runtime = Path(runtime)
    if runtime.is_symlink() or not runtime.is_absolute() or digest(runtime) != inputs["runtime_sha256"]:
        raise ValueError("Exact reviewed runtime image required; no launcher or symlink")
    runtime = runtime.resolve()
    runtime_root = runtime.parents[8]
    if str(runtime.relative_to(runtime_root)) != inputs["runtime_relative_path"]:
        raise ValueError("Unsupported runtime layout")
    for relative, value in inputs["runtime_additional_pins"].items():
        if digest(runtime_root / relative) != value:
            raise ValueError("Runtime drift")
    for name, value in inputs["OS_input_sha256"].items():
        if digest(Path(name)) != value:
            raise ValueError("OS input drift")
    return inputs, runtime, runtime_root


def profile_text(runtime, runtime_root, output):
    quote = lambda p: json.dumps(str(p))
    payload = output / "probe.py"
    work = output / "work"
    return (
        '(version 1)\n(deny default)\n(import "dyld-support.sb")\n'
        + '(allow process-exec (literal ' + quote(runtime) + '))\n'
        + '(allow file-read* (subpath ' + quote(runtime_root) + ') (subpath "/usr/lib") (subpath "/System/Library") (literal "/dev/null") (literal ' + quote(payload) + ') (subpath ' + quote(work) + '))\n'
        + '(allow file-write* (subpath ' + quote(work) + ') (literal "/dev/null"))\n'
        + '(allow file-map-executable (subpath ' + quote(runtime_root) + ') (subpath "/usr/lib") (subpath "/System/Library"))\n'
        + '(allow file-test-existence (subpath ' + quote(runtime_root) + ') (subpath "/usr/lib") (subpath "/System/Library") (literal ' + quote(payload) + ') (subpath ' + quote(work) + '))\n'
        + '(allow file-read-metadata file-test-existence (path-ancestors ' + quote(runtime) + ') (path-ancestors ' + quote(payload) + ') (path-ancestors ' + quote(work) + '))\n'
        + '(allow sysctl-read)\n(allow signal (target self))\n(deny network*)\n(deny process-fork)\n(deny file-link)\n'
    )


def prepare(runtime, output):
    inputs, runtime, runtime_root = validate(runtime)
    output = Path(output)
    if not output.is_absolute() or any(p.is_symlink() for p in [output, *output.parents]):
        raise ValueError("New absolute owned output without symlink parents required")
    output = output.resolve()
    if output == FIXTURE or output.is_relative_to(FIXTURE) or output == runtime_root or output.is_relative_to(runtime_root):
        raise ValueError("Output must be outside source/runtime")
    output.mkdir(mode=0o700, exist_ok=False)
    (output / "work").mkdir(mode=0o700)
    (output / "tmp").mkdir(mode=0o700)
    canary = output / "denied-canary.txt"
    canary.write_text("SYNTHETIC_OWNED_CANARY_NO_SECRET\n")
    (output / "work/escape-link").symlink_to(canary)
    payload = output / "probe.py"
    payload.write_bytes((FIXTURE / "probe.py").read_bytes())
    profile = output / "default-deny.sb"
    profile.write_text(profile_text(runtime, runtime_root, output))
    record = dict(root=str(output), work=str(output / "work"), canary=str(canary), payload=str(payload), profile=str(profile), python_executable=str(runtime), python_runtime_root=str(runtime_root), sha256s={str(p): digest(p) for p in [payload, profile, runtime]}, read_only_trusted_runtime_and_OS_paths_are_TCB_not_full_input_closure=True, no_JVM_or_issuer_admission_authority=True)
    (output / "state.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.runtime, args.output), indent=2))
