"""Offline bundle selection and fail-closed interpretation of native results."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bundle = load("prepare_iam_flyway")
with patch.dict("sys.modules", {"prepare_iam_flyway": bundle}):
    gate = load("qualify_application_database")


class ApplicationProfileTests(unittest.TestCase):
    def test_full_shared_lineage_excludes_iam_local_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            self.assertEqual(bundle.prepare(output, profile=gate.PROFILE), 18)
            copied = sorted((output / "sql").glob("V*.sql"))
            self.assertEqual(
                [int(p.name.split("__")[0][1:]) for p in copied], list(range(1, 19))
            )
            for entry in json.loads(gate.PROFILE.read_text())["migrations"]:
                source = ROOT / entry["path"]
                self.assertEqual(
                    source.read_bytes(), (output / "sql" / source.name).read_bytes()
                )
            config = (output / "flyway.conf").read_text()
            for line in (
                "validateOnMigrate=true",
                "baselineOnMigrate=false",
                "cleanDisabled=true",
                "createSchemas=false",
            ):
                self.assertIn("flyway." + line, config)

    def test_shared_drift_is_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            profile = json.loads(gate.PROFILE.read_text())
            profile["migrations"][-1]["sha256"] = "0" * 64
            file = directory / "profile.json"
            file.write_text(json.dumps(profile))
            with self.assertRaisesRegex(ValueError, "checksum"):
                bundle.prepare(directory / "output", profile=file)
            self.assertFalse((directory / "output").exists())

    def test_json_failure_cannot_be_accepted_on_exit_zero(self):
        for result in (
            {},
            None,
            [],
            {"validationSuccessful": False},
            {"success": False},
            {"success": True, "exception": "failed"},
            {"validationSuccessful": True, "invalidMigrations": ["missing"]},
            {"success": True, "error": "failed"},
            {"validationSuccessful": True, "errorDetails": "failed"},
            {"success": True, "validationSuccessful": False},
        ):
            with self.subTest(result=result):
                self.assertFalse(gate.successful(0, result))

    def test_success_requires_an_explicit_success_flag_and_exit_zero(self):
        for result in (
            {"success": True},
            {"validationSuccessful": True, "invalidMigrations": []},
        ):
            self.assertTrue(gate.successful(0, result))
            self.assertFalse(gate.successful(1, result))

    def test_missing_native_tools_fail_without_a_database_fallback(self):
        with patch.dict(
            "os.environ",
            {"SG_TEST_PG_BINDIR": "/missing", "SG_TEST_FLYWAY": "/missing"},
        ):
            with self.assertRaisesRegex(ValueError, "native PostgreSQL"):
                gate.qualify()


class ProvenanceProfileTests(unittest.TestCase):
    def test_extension_preserves_baseline_and_covers_global_lineage(self):
        profile = ROOT / "publication/case-provenance-profile.json"
        extended = json.loads(profile.read_text())
        baseline = json.loads(gate.PROFILE.read_text())
        self.assertEqual(extended["migrations"][:-1], baseline["migrations"])
        self.assertEqual(
            {entry["path"] for entry in extended["migrations"]},
            {
                str(p.relative_to(ROOT))
                for p in (ROOT / "backend/migrations_consolidated").glob("V*.sql")
            },
        )
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                bundle.prepare(Path(directory) / "bundle", profile=profile), 19
            )

    def test_extension_checksum_drift_fails_before_bundle_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            data = json.loads(
                (ROOT / "publication/case-provenance-profile.json").read_text()
            )
            data["migrations"][-1]["sha256"] = "0" * 64
            profile = directory / "profile.json"
            profile.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "checksum"):
                bundle.prepare(directory / "bundle", profile=profile)
            self.assertFalse((directory / "bundle").exists())
