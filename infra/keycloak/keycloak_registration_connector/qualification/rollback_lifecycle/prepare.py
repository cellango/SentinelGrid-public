#!/usr/bin/env python3
"""Build isolated native-manager comparison inputs; never install or deploy."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import types

OLD = "                exception = exception != null ? e : exception;"
NEW = """                if (exception == null) {
                    exception = e;
                } else if (exception != e) {
                    exception.addSuppressed(e);
                }"""
OLD_ORACLE = 'assertFalse(denial.cleanupFaultObserved(), "Native close did not propagate the participant failure");'
NEW_ORACLE = 'assertEquals(Boolean.getBoolean("rollback.candidate"), denial.cleanupFaultObserved(), "Compare native versus candidate propagation only; complete cleanup remains unproved");'


def prepare(source, output, mode, qualification_root=None):
    if mode not in {"native", "candidate"} or output.resolve().is_relative_to(source.resolve()):
        raise ValueError("Use reviewed comparison mode and separate owned output")
    fixture = Path(__file__).resolve().parent
    shared = qualification_root if qualification_root is not None else fixture.parent
    inputs = json.loads((fixture / "inputs.json").read_text())
    row = inputs["native_manager"]
    unit = source / row["path"]
    original = unit.read_bytes()
    if unit.is_symlink() or hashlib.sha256(original).hexdigest() != row["sha256"]:
        raise ValueError("Unreviewed native manager bytes")
    for row in inputs["reused_files"]:
        item = shared / row["path"]
        if item.is_symlink() or hashlib.sha256(item.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Unreviewed earlier fixture/control bytes")
    text = original.decode("utf-8")
    if text.count(OLD) != 2 or NEW in text:
        raise ValueError("Unexpected rollback accumulator source")
    oracle_file = "src/test/java/org/keycloak/services/resources/RealmEntryTest.java"
    oracle = (shared / "realm_entry" / oracle_file).read_text()
    if oracle.count(OLD_ORACLE) != 1:
        raise ValueError("Unexpected original negative cleanup oracle")
    # Exact, hash-checked earlier recipe supplies its already-qualified denial overlay.
    recipe = shared / "realm_entry/prepare.py"
    module = types.ModuleType("reviewed_realm_prepare")
    module.__file__ = str(recipe)
    exec(compile(recipe.read_bytes(), str(recipe), "exec"), module.__dict__)
    module.prepare(source, output, "guarded", shared_root=shared / "entry_guard")
    shutil.copyfile(fixture / "pom.xml", output / "pom.xml")
    shutil.copytree(fixture / "src", output / "src", dirs_exist_ok=True)
    (output / oracle_file).write_text(oracle.replace(OLD_ORACLE, NEW_ORACLE, 1))
    patched = text.replace(OLD, NEW) if mode == "candidate" else text
    target = output / "src/main/java/org/keycloak/services/DefaultKeycloakTransactionManager.java"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(patched.encode("utf-8"))
    record = {"mode": mode, "manager_source_sha256": hashlib.sha256(original).hexdigest(),
              "manager_overlay_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
              "manager_replacement_sites": 2 if mode == "candidate" else 0,
              "earlier_realm_denial_overlay_retained": True,
              "prior_negative_oracle_change": "Explicit native/candidate observed-fault comparison; unfinished participant and failed cleanup retained",
              "HTTP_SQL_or_production_qualification": False}
    (output / "rollback-overlay.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("mode", choices=["native", "candidate"])
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output, args.mode), sort_keys=True))
