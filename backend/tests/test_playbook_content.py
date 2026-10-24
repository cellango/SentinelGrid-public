"""Content gate tests use synthetic input and never contact services."""
from pathlib import Path
import sys
import json
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from check_playbook_content import ROOT, content_failures, packaging_failures


class PlaybookContentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "source.yaml"
        self.fixture = ROOT / "backend/tests/fixtures/account_compromise.synthetic.yaml"

    def test_missing_source_blocks_without_fallback(self):
        self.assertIn("missing", content_failures(self.source, ["ACCOUNT-COMPROMISE"])[0])

    def test_explicit_synthetic_source_passes_only_selected_key(self):
        self.assertEqual(content_failures(self.fixture, ["ACCOUNT-COMPROMISE"]), [])
        self.assertTrue(content_failures(self.fixture, ["PHISH-USER"]))

    def test_unknown_or_empty_selection_blocks(self):
        for keys in [[], ["invented"]]:
            self.assertTrue(content_failures(self.fixture, keys))

    def test_malformed_empty_and_wrong_structure_block(self):
        for text in ["[", "", "playbooks: []", "playbooks: invalid"]:
            self.source.write_text(text)
            self.assertTrue(content_failures(self.source, ["ACCOUNT-COMPROMISE"]))

    def test_duplicate_definitions_block(self):
        self.source.write_text("playbooks: [{id: same}, {id: same}]")
        self.assertIn("Duplicate", content_failures(self.source, ["ACCOUNT-COMPROMISE"])[0])

    def test_changed_source_is_rechecked(self):
        self.source.write_bytes(self.fixture.read_bytes())
        self.assertEqual(content_failures(self.source, ["ACCOUNT-COMPROMISE"]), [])
        self.source.write_text("playbooks: []")
        self.assertTrue(content_failures(self.source, ["ACCOUNT-COMPROMISE"]))

    def test_fixture_has_no_executor_binding_or_automatic_action(self):
        import yaml
        source = yaml.safe_load(self.fixture.read_text())["playbooks"][0]
        self.assertEqual(source["version"], "synthetic-qualification-1")
        self.assertIn("effect-disabled", source["tags"])
        steps = [step for phase in source["phases"] for step in phase["steps"]]
        self.assertEqual(len(steps), 9)
        self.assertTrue(all(step["type"] == "manual" and "action_ref" not in step for step in steps))

    def test_local_resource_cannot_mask_export_omission(self):
        root = Path(self.temp.name)
        (root / "publication").mkdir()
        manifest = root / "publication/source-files.json"
        self.source.write_bytes(self.fixture.read_bytes())
        manifest.write_text(json.dumps({"files": []}))
        self.assertTrue(packaging_failures(self.source, root))
        manifest.write_text(json.dumps({"files": [self.source.name]}))
        self.assertEqual(packaging_failures(self.source, root), [])
        manifest.write_text("invalid")
        self.assertTrue(packaging_failures(self.source, root))
