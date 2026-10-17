"""Profile selection cannot mix the shared baseline into the grant database."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "prepare_iam_flyway", ROOT / "scripts/prepare_iam_flyway.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class IAMProfileTests(unittest.TestCase):
    def test_exact_lineage_and_no_automatic_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "bundle"
            self.assertEqual(module.prepare(dest), 8)
            files = {p.name for p in (dest / "sql").iterdir()}
            self.assertIn("V014__public_iam_audit_and_tenant_guards.sql", files)
            self.assertIn("V015__public_governance_contract.sql", files)
            self.assertIn("V016__public_role_grant_provenance.sql", files)
            self.assertIn("V017__public_service_account_registry.sql", files)
            self.assertFalse(any(name.startswith("V001__") for name in files))
            self.assertIn(
                "flyway.baselineOnMigrate=false", (dest / "flyway.conf").read_text()
            )

    def test_drift_is_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            data = json.loads(module.PROFILE.read_text())
            data["migrations"][0]["sha256"] = "0" * 64
            profile = directory / "profile.json"
            profile.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "checksum"):
                module.prepare(directory / "bundle", profile=profile)
            self.assertFalse((directory / "bundle").exists())

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)
            sentinel = dest / "keep"
            sentinel.write_text("synthetic existing content")
            with self.assertRaises(ValueError):
                module.prepare(dest)
            self.assertEqual(sentinel.read_text(), "synthetic existing content")
