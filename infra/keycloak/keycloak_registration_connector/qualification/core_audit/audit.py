#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inventory pinned vendor syntax. Exit 2 means enforcement remains unproved."""
from collections import Counter
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import re
import subprocess
import tarfile
import tempfile

VERSION = "26.8.1"
COMMIT = "24ed1dadf3f246a555adb6d3d4a99e9b3003fb3b"
ARCHIVE_SHA256 = "f67ec723e2eaf46b2d38f167ecb7578964115f1f2ce203f9b6659322223d9874"
CALL_MARKERS = frozenset({"persist", "merge", "remove", "flush", "executeUpdate",
    "executeLargeUpdate", "commit", "rollback", "begin", "runJobInTransaction",
    "runJobInTransactionWithResult", "enableServiceAccount", "removeUser", "removeClient"})
ROUTE_MARKERS = frozenset({"GET", "POST", "PUT", "DELETE", "PATCH", "Path"})


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def eligible(name):
    return ("/src/main/java/" in name and name.endswith(".java")
            or "/src/main/resources/META-INF/services/" in name)


def verify_source(source, archive, expected_hash=ARCHIVE_SHA256, commit=COMMIT):
    """Hash the archive and every selected source; reject extra/missing/symlink inputs."""
    if source.is_symlink() or digest(archive) != expected_hash:
        raise ValueError("Source/archive provenance mismatch")
    manifest = {}
    prefix = "keycloak-" + commit + "/"
    with tarfile.open(archive) as bundle:
        for member in bundle:
            if member.isdir():
                continue
            if not member.name.startswith(prefix):
                raise ValueError("Unexpected archive prefix")
            name = member.name[len(prefix):]
            if not eligible(name):
                continue
            parts = PurePosixPath(name).parts
            if not parts or ".." in parts or PurePosixPath(name).is_absolute():
                raise ValueError("Invalid archive path")
            if not member.isfile() or name in manifest:
                raise ValueError("Unsupported or duplicate source entry")
            actual = source / name
            if any((source.joinpath(*parts[:i])).is_symlink() for i in range(1,len(parts)+1)):
                raise ValueError("Symlinked source input")
            expected = hashlib.sha256(bundle.extractfile(member).read()).hexdigest()
            if not actual.is_file() or digest(actual) != expected:
                raise ValueError("Missing or changed source input")
            manifest[name] = expected
    current = {p.relative_to(source).as_posix() for p in source.rglob("*")
               if eligible(p.relative_to(source).as_posix()) and not p.is_dir()}
    if not manifest or current != set(manifest):
        raise ValueError("Source path selection differs from pinned archive")
    return manifest


def summarize(records):
    kinds = Counter()
    units = set()
    markers = Counter()
    routes = Counter()
    modules = Counter()
    module_markers = {}
    unknown = 0
    for row in records:
        kind = row["kind"]
        kinds[kind] += 1
        if kind == "unit":
            if row["path"] in units:
                raise ValueError("Duplicate parsed unit")
            units.add(row["path"])
            modules[row["path"].split("/src/main/java/",1)[0]] += 1
        if kind == "call" and row["name"] in CALL_MARKERS:
            markers[row["name"]] += 1
            module = row["path"].split("/src/main/java/",1)[0]
            module_markers.setdefault(module,Counter())[row["name"]] += 1
        if kind == "annotation" and row["name"] in ROUTE_MARKERS:
            routes[row["name"]] += 1
        unknown += row["name"] == "<unknown>"
    if unknown:
        raise ValueError("Unknown syntax selector")
    return dict(record_counts=dict(sorted(kinds.items())), parsed_units=sorted(units),
                syntactic_call_markers=dict(sorted(markers.items())),
                route_annotation_markers=dict(sorted(routes.items())),
                module_main_source_file_counts=dict(sorted(modules.items())),
                module_syntactic_call_markers={k:dict(sorted(v.items())) for k,v in sorted(module_markers.items())},
                symbol_resolution_performed=False, transitive_callgraph_proved=False,
                complete_writer_fence_proved=False, R3_R4_GO=False)


def copy_verified(source, manifest, destination):
    """Parse only an owned copy of bytes matching the verified archive manifest."""
    for name, expected in manifest.items():
        data = (source/name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("Source changed before parser snapshot")
        target = destination/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)


def run(source, archive, java_home, output):
    if output.exists():
        raise ValueError("Output already exists")
    manifest = verify_source(source, archive)
    java_files = sorted(n for n in manifest if "/src/main/java/" in n)
    if not java_files:
        raise ValueError("No main-source Java inputs")
    output.mkdir(mode=0o700)
    write = lambda n,v: (output/n).write_text(json.dumps(v,indent=2)+"\n")
    write("source-manifest.private.json", manifest)
    file_list = output/"java-inputs.private.txt"
    file_list.write_text("".join(n+"\n" for n in java_files))
    env = {k:v for k,v in os.environ.items()
           if k not in {"JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS", "CLASSPATH"}}
    with tempfile.TemporaryDirectory(prefix="sg-core-audit-build-") as temporary:
        build = Path(temporary)
        snapshot = build/"verified-source"
        copy_verified(source,manifest,snapshot)
        provider_texts = {name:(snapshot/name).read_text() for name in manifest
                          if "/src/main/resources/META-INF/services/" in name}
        tool_source = Path(__file__).parent/"java/CoreSourceAudit.java"
        commands = [
            [str(java_home/"bin/javac"), "--release", "21", "-proc:none", "-d", str(build), str(tool_source)],
            [str(java_home/"bin/java"), "-Xmx1024m", "-Duser.home="+str(build), "-cp", str(build),
             "CoreSourceAudit", str(snapshot), str(file_list), str(output/"syntax.private.ndjson")],
        ]
        for index, command in enumerate(commands):
            result = subprocess.run(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            (output/f"compiler-{index}.private.log").write_bytes(result.stdout+result.stderr)
            if result.returncode:
                raise RuntimeError("Audit compiler/parser failed; review private diagnostic")
    with (output/"syntax.private.ndjson").open() as stream:
        summary = summarize(json.loads(line) for line in stream)
    if set(summary["parsed_units"]) != set(java_files):
        raise ValueError("Parsed units differ from verified inputs")
    providers = []
    service = "org.keycloak.protocol.oidc.grants.OAuth2GrantTypeFactory"
    for name in sorted(manifest):
        if name.endswith("/"+service):
            for line in provider_texts[name].splitlines():
                value = line.split("#",1)[0].strip()
                if value:
                    if not re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$.]*",value):
                        raise ValueError("Invalid grant service declaration")
                    providers.append(dict(source=name,factory=value))
    summary.update(version=VERSION,commit=COMMIT,archive_sha256=ARCHIVE_SHA256,
        verified_main_source_java_files=len(java_files), verified_source_and_service_files=len(manifest),
        scope="All pinned src/main/java and src/main/resources/META-INF/services files, including testsuite/helper modules with that layout; not an installed runtime graph",
        grant_factory_declarations=providers, compiler_parse_complete=True,
        issuer_server_build_or_runtime_executed=False, no_vendor_source_literals_or_SQL_in_syntax_report=True,
        parser_inputs_copied_and_hash_verified_before_parse=True,
        enforcement_status="NO_GO_complete_entry_writer_storage_transaction_closure_unproved")
    write("summary.private.json",summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--archive",type=Path,required=True)
    parser.add_argument("--java-home",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    try:
        result = run(args.source.resolve(),args.archive.resolve(),args.java_home.resolve(),args.output)
    except (OSError,ValueError,RuntimeError,tarfile.TarError,KeyError,json.JSONDecodeError):
        print("Audit failed; no enforcement evidence accepted.")
        return 1
    print(json.dumps({k:result[k] for k in ["verified_main_source_java_files","compiler_parse_complete",
        "complete_writer_fence_proved","R3_R4_GO","enforcement_status"]}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
