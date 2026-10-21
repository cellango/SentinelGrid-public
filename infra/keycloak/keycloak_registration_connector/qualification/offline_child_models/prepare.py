"""Prepare owned pinned model inputs without running Maven or resolving artifacts."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import types
import xml.etree.ElementTree as ET

FIXTURE = Path(__file__).resolve().parent
# Reviewed constants are part of the trusted recipe, not caller-supplied state.
EXPECTED_POM_PINS_SHA256 = '69a36fefd87b9d10bd6b31ed490320c820b7ec6383fdd44d3ecea3df5fb07d26'
EXPECTED_TARGETS_SHA256 = '3f05913a4a9b0d2de6588583471314cc917b7d2fd92fb45ba2206f9998024236'
EXPECTED_LIBRARY_PINS_SHA256 = '498bf29c76c74f96a4880556d5bce23f5d9c2016d0da46357a91f121edbe3614'
def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

def validate(tool_root, metadata_root):
    manifest = json.loads((FIXTURE / "inputs.json").read_text())
    for field, expected in [("POM_inputs", EXPECTED_POM_PINS_SHA256), ("selected_model_targets", EXPECTED_TARGETS_SHA256), ("model_libraries", EXPECTED_LIBRARY_PINS_SHA256)]:
        if canonical_digest(manifest[field]) != expected:
            raise ValueError("Reviewed manifest drift: " + field)
    targets = manifest["selected_model_targets"]
    if len(targets) != 265 or targets != sorted(set(targets)) or not set(targets) <= {p["coordinate"] for p in manifest["POM_inputs"]}:
        raise ValueError("Invalid reviewed target set")
    for name, digest in manifest["fixture_sha256"].items():
        if (FIXTURE / name).is_symlink() or sha(FIXTURE / name) != digest:
            raise ValueError("Fixture drift")
    helper = FIXTURE.parent / "jvm_boundary"
    for name, digest in manifest["JDK_helper_sha256"].items():
        if (helper / name).is_symlink() or sha(helper / name) != digest:
            raise ValueError("Reviewed JDK helper drift")
    module = types.ModuleType("trusted_pinned_JDK_inputs")
    module.__file__ = str(helper / "prepare.py")
    exec(compile((helper / "prepare.py").read_bytes(), str(helper / "prepare.py"), "exec"), module.__dict__)
    _, java, java_home = module.validate(Path(tool_root))
    tool_root, metadata_root = Path(tool_root), Path(metadata_root)
    if not metadata_root.is_absolute() or any(p.is_symlink() for p in [metadata_root, *metadata_root.parents]):
        raise ValueError("Absolute owned metadata path without symlink parents required")
    if os.stat(metadata_root).st_uid != os.getuid() or os.stat(metadata_root).st_mode & 0o077:
        raise ValueError("Private owner-controlled metadata required; not an existing Maven repository")
    for pin in manifest["model_libraries"]:
        path = tool_root / pin["path"]
        if path.is_symlink() or sha(path) != pin["sha256"]:
            raise ValueError("Model library drift")
    for pin in manifest["POM_inputs"]:
        path = metadata_root / pin["path"]
        if any(p.is_symlink() for p in [path, *path.parents]) or path.stat().st_nlink != 1 or sha(path) != pin["sha256"]:
            raise ValueError("POM drift or alias")
        data = path.read_bytes()
        xml = data.decode("utf-8")
        if "<!doctype" in xml.lower() or "<!entity" in xml.lower():
            raise ValueError("DTD/entity input forbidden")
        tree = ET.fromstring(data)
        prefix = "{http://maven.apache.org/POM/4.0.0}" if tree.tag.startswith("{") else ""
        if tree.tag != prefix + "project":
            raise ValueError("Unsupported POM namespace")
        text = lambda name: tree.findtext("/".join(prefix + part for part in name.split("/")))
        coordinate = ":".join([text("groupId") or text("parent/groupId"), text("artifactId"), text("version") or text("parent/version")])
        if coordinate != pin["coordinate"]:
            raise ValueError("Foreign POM identity")
    return manifest, java, java_home

def profile_text(java, java_home, root):
    q = lambda path: json.dumps(str(path))
    work, inputs = root / "work", root / "inputs"
    return (
        '(version 1)\n(deny default)\n(import "dyld-support.sb")\n'
        + '(allow process-exec (literal ' + q(java) + '))\n'
        + '(allow file-read* file-test-existence file-map-executable (subpath ' + q(java_home) + ') (subpath "/System/Library") (subpath "/usr/lib") (subpath ' + q(inputs) + '))\n'
        + '(allow file-read* file-test-existence file-write* (subpath ' + q(work) + ') (literal "/dev/null"))\n'
        + '(allow file-read-metadata file-test-existence (path-ancestors ' + q(java) + ') (path-ancestors ' + q(work) + ') (path-ancestors ' + q(inputs) + '))\n'
        + '(allow signal (target self))\n(allow sysctl-read)\n(deny network*)\n(deny process-fork)\n(deny file-link)\n'
    )

def synthetic_POMs():
    start = '<project><modelVersion>4.0.0</modelVersion><groupId>review.fixture</groupId>'
    synthetic = {
        "review.fixture:parent:1": start + '<artifactId>parent</artifactId><version>1</version><packaging>pom</packaging><properties><profile.value>base</profile.value></properties></project>',
        "review.fixture:bom:1": start + '<artifactId>bom</artifactId><version>1</version><packaging>pom</packaging><dependencyManagement><dependencies><dependency><groupId>review.fixture</groupId><artifactId>library</artifactId><version>2</version></dependency></dependencies></dependencyManagement></project>',
        "review.fixture:child:1": '<project><modelVersion>4.0.0</modelVersion><parent><groupId>review.fixture</groupId><artifactId>parent</artifactId><version>1</version><relativePath>/MUST_NOT_BE_READ/pom.xml</relativePath></parent><artifactId>child</artifactId><repositories><repository><id>ignored-review-repository</id><url>https://invalid.example/MUST_NOT_BE_FETCHED</url></repository></repositories><dependencyManagement><dependencies><dependency><groupId>review.fixture</groupId><artifactId>bom</artifactId><version>1</version><type>pom</type><scope>import</scope></dependency></dependencies></dependencyManagement><dependencies><dependency><groupId>review.fixture</groupId><artifactId>library</artifactId></dependency></dependencies><profiles><profile><id>auto-must-stay-off</id><activation><activeByDefault>true</activeByDefault></activation><properties><profile.value>UNREVIEWED_AUTO</profile.value></properties></profile><profile><id>review</id><properties><profile.value>reviewed</profile.value></properties></profile></profiles></project>'
    }
    return synthetic

def expected_input_hashes(manifest):
    result = {"inputs/lib/" + Path(pin["path"]).name: pin["sha256"] for pin in manifest["model_libraries"]}
    pins = []
    for number, pin in enumerate(manifest["POM_inputs"]):
        relative = "poms/" + str(number) + ".pom"
        result["inputs/" + relative] = pin["sha256"]
        pins.append((pin["coordinate"], pin["sha256"], relative))
    for number, (coordinate, xml) in enumerate(synthetic_POMs().items()):
        relative = "poms/fixture-" + str(number) + ".pom"
        digest = hashlib.sha256(xml.encode()).hexdigest()
        result["inputs/" + relative] = digest
        pins.append((coordinate, digest, relative))
    result["inputs/pins.tsv"] = hashlib.sha256("".join("\t".join(row) + "\n" for row in pins).encode()).hexdigest()
    result["inputs/read-only-canary.txt"] = hashlib.sha256(b"OWNED_READ_ONLY_INPUT_NO_SECRET").hexdigest()
    return result

def prepare(tool_root, metadata_root, output):
    manifest, java, java_home = validate(tool_root, metadata_root)
    output = Path(output)
    if not output.is_absolute() or any(p.is_symlink() for p in [output, *output.parents]):
        raise ValueError("New absolute output without symlink parents required")
    output = output.resolve()
    if any(output.is_relative_to(base.resolve()) for base in [FIXTURE, Path(tool_root), Path(metadata_root)]):
        raise ValueError("Output inside source or reviewed inputs")
    output.mkdir(mode=0o700, exist_ok=False)
    work, owned = output / "work", output / "inputs"
    work.mkdir(mode=0o700); owned.mkdir(mode=0o700)
    for name in ["home", "tmp", "classes", "empty"]:
        (work / name).mkdir(mode=0o700)
    (owned / "lib").mkdir(); (owned / "poms").mkdir()
    for pin in manifest["model_libraries"]:
        shutil.copyfile(Path(tool_root) / pin["path"], owned / "lib" / Path(pin["path"]).name)
    pins = []
    for number, pin in enumerate(manifest["POM_inputs"]):
        relative = "poms/" + str(number) + ".pom"
        shutil.copyfile(Path(metadata_root) / pin["path"], owned / relative)
        pins.append((pin["coordinate"], pin["sha256"], relative))
    synthetic = synthetic_POMs()
    for number, (coordinate, xml) in enumerate(synthetic.items()):
        relative = "poms/fixture-" + str(number) + ".pom"
        (owned / relative).write_text(xml)
        pins.append((coordinate, sha(owned / relative), relative))
    (owned / "pins.tsv").write_text("".join("\t".join(row) + "\n" for row in pins))
    (owned / "read-only-canary.txt").write_text("OWNED_READ_ONLY_INPUT_NO_SECRET")
    (output / "outside-canary.txt").write_text("OWNED_OUTSIDE_WORK_NO_SECRET")
    (work / "OfflineModelProbe.java").write_bytes((FIXTURE / "OfflineModelProbe.java").read_bytes())
    (output / "default-deny.sb").write_text(profile_text(java, java_home, output))
    hashes = {str(path.relative_to(output)): sha(path) for path in owned.rglob("*") if path.is_file()}
    if hashes != expected_input_hashes(manifest):
        raise ValueError("Prepared input identity mismatch")
    for path in owned.rglob("*"):
        path.chmod(0o500 if path.is_dir() else 0o400)
    owned.chmod(0o500)
    state = dict(root=str(output), tool_root=str(Path(tool_root).resolve()), metadata_root=str(Path(metadata_root).resolve()), java=str(java), java_home=str(java_home), input_sha256=hashes, policy_sha256=sha(output / "default-deny.sb"), fixture_sha256=manifest["fixture_sha256"], model_source_inputs=456, synthetic_fixture_POMs=3)
    (output / "state.json").write_text(json.dumps(state, indent=2) + "\n")
    return state

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("tool_root", type=Path); p.add_argument("metadata_root", type=Path); p.add_argument("output", type=Path)
    args = p.parse_args(); print(json.dumps(prepare(args.tool_root, args.metadata_root, args.output), indent=2))
