# SPDX-License-Identifier: Apache-2.0
"""Offline provenance/coverage fault controls; no issuer/runtime acceptance."""
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import tarfile
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location("core_source_audit",Path(__file__).with_name("audit.py"))
audit=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(audit)


class ProvenanceControls(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name);self.source=self.root/"source";self.source.mkdir()
        self.name="services/src/main/java/audit/NativeBoundary.java"
        self.code=b"package audit; class NativeBoundary { void entry() {} }"
        path=self.source/self.name;path.parent.mkdir(parents=True);path.write_bytes(self.code)
        self.archive=self.root/"source.tar.gz"
        with tarfile.open(self.archive,"w:gz") as bundle:
            entry=tarfile.TarInfo("keycloak-"+audit.COMMIT+"/"+self.name);entry.size=len(self.code)
            bundle.addfile(entry,io.BytesIO(self.code))
        self.sha=audit.digest(self.archive)

    def verify(self):
        return audit.verify_source(self.source,self.archive,expected_hash=self.sha)

    def test_exact_pinned_inputs(self):
        self.assertEqual(set(self.verify()),{self.name})

    def test_archive_hash_drift(self):
        with self.assertRaises(ValueError):
            audit.verify_source(self.source,self.archive,expected_hash="0"*64)

    def test_changed_native_entry(self):
        (self.source/self.name).write_bytes(self.code+b" // changed")
        with self.assertRaises(ValueError):self.verify()

    def test_missing_native_entry(self):
        (self.source/self.name).unlink()
        with self.assertRaises(ValueError):self.verify()

    def test_additional_ignored_looking_adapter(self):
        (self.source/self.name).with_name("CredentialAdapter.java").write_text("class CredentialAdapter {}")
        with self.assertRaises(ValueError):self.verify()

    def test_symlinked_native_entry(self):
        actual=self.source/self.name;outside=self.root/"outside.java";outside.write_bytes(self.code)
        actual.unlink();actual.symlink_to(outside)
        with self.assertRaises(ValueError):self.verify()

    def test_source_change_before_snapshot_rejected(self):
        manifest=self.verify();(self.source/self.name).write_bytes(self.code+b" // race")
        with self.assertRaises(ValueError):audit.copy_verified(self.source,manifest,self.root/"snapshot")

    def test_parser_snapshot_survives_later_source_edit(self):
        manifest=self.verify();snapshot=self.root/"snapshot"
        audit.copy_verified(self.source,manifest,snapshot)
        (self.source/self.name).write_text("class Changed {}")
        self.assertEqual((snapshot/self.name).read_bytes(),self.code)

    def test_existing_output_preserved(self):
        output=self.root/"report";output.mkdir();canary=output/"keep";canary.write_text("preserve")
        with self.assertRaises(ValueError):audit.run(self.source,self.archive,self.root,output)
        self.assertEqual(canary.read_text(),"preserve")

    def test_unknown_selector_rejected(self):
        with self.assertRaises(ValueError):
            audit.summarize([dict(kind="call",path=self.name,name="<unknown>")])

    def test_duplicate_parsed_unit_rejected(self):
        row=dict(kind="unit",path=self.name,name="")
        with self.assertRaises(ValueError):audit.summarize([row,row])

    def test_syntax_inventory_never_claims_enforcement(self):
        rows=[dict(kind="unit",path=self.name,name=""),
              dict(kind="call",path=self.name,name="commit"),
              dict(kind="call",path=self.name,name="requireCompleteFence")]
        result=audit.summarize(rows)
        self.assertFalse(result["R3_R4_GO"])
        self.assertFalse(result["complete_writer_fence_proved"])
        self.assertFalse(result["symbol_resolution_performed"])

    def test_main_source_test_helpers_remain_distinct_modules(self):
        result=audit.summarize([dict(kind="unit",path="services/src/main/java/Entry.java",name=""),
            dict(kind="unit",path="testsuite/helper/src/main/java/Fixture.java",name="")])
        self.assertEqual(result["module_main_source_file_counts"],{"services":1,"testsuite/helper":1})
        self.assertFalse(result["transitive_callgraph_proved"])


@unittest.skipUnless(os.environ.get("SG_CORE_AUDIT_JAVA_HOME"),"set SG_CORE_AUDIT_JAVA_HOME to an owned JDK21")
class CompilerControls(unittest.TestCase):
    def test_literals_not_emitted_and_nested_paths_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);java=Path(os.environ["SG_CORE_AUDIT_JAVA_HOME"])
            compiler=Path(__file__).parent/"java/CoreSourceAudit.java"
            subprocess.run([str(java/"bin/javac"),"--release","21","-proc:none","-d",str(root),str(compiler)],check=True,capture_output=True)
            name="NativeBoundary.java";literal="synthetic-"+"source-value-"+"canary"
            (root/name).write_text('class NativeBoundary { int count; @Deprecated void entry(){'
                'class Nested { void action(){ target("'+literal+'"); count++; } } } '
                'void target(String value){} }')
            files=root/"inputs";files.write_text(name+"\n");output=root/"syntax"
            subprocess.run([str(java/"bin/java"),"-cp",str(root),"CoreSourceAudit",str(root),str(files),str(output)],check=True,capture_output=True)
            text=output.read_text();self.assertNotIn(literal,text)
            rows=[json.loads(line) for line in text.splitlines()]
            call=next(r for r in rows if r["kind"]=="call" and r["name"]=="target")
            self.assertEqual(call["owner"],"NativeBoundary.Nested");self.assertEqual(call["method"],"action/0")
            self.assertTrue(any(r["kind"]=="assignment" and r["detail"]=="POSTFIX_INCREMENT" for r in rows))

    def test_invalid_java_rejected_without_source_value(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);java=Path(os.environ["SG_CORE_AUDIT_JAVA_HOME"])
            compiler=Path(__file__).parent/"java/CoreSourceAudit.java"
            subprocess.run([str(java/"bin/javac"),"--release","21","-proc:none","-d",str(root),str(compiler)],check=True,capture_output=True)
            (root/"Broken.java").write_text("class Broken { void bad( { }")
            files=root/"inputs";files.write_text("Broken.java\n")
            result=subprocess.run([str(java/"bin/java"),"-cp",str(root),"CoreSourceAudit",str(root),str(files),str(root/"syntax")],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn(b"void bad",result.stdout+result.stderr)


if __name__=="__main__":unittest.main()
