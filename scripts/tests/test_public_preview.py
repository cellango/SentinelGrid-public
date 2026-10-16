"""Regression checks for the inventory used by publication and secret scans."""

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from public_preview import (
    PUBLICATION_INVENTORY, private_file_reason,
    publication_inventory_failures, source_files,
)


class PublicationInventoryTests(unittest.TestCase):
    def test_application_source_survives_model_secret_and_data_ignore_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            policy = Path(__file__).resolve().parents[2] / ".gitignore"
            (root / ".gitignore").write_bytes(policy.read_bytes())
            source = [
                "backend/agents/iam_agent/app/models/auth.py",
                "backend/services/connector_service/app/models/connector.py",
                "SentinelGridPenTestAgent/shared/models/engagement.py",
                "SentinelGridPenTestAgent/scanners/secrets/gitleaks_scanner.py",
                "SentinelGridPostureAgent/analyzers/secrets/gitleaks_analyzer.py",
                "backend/tests/siem/data/generate_test_logs.py",
            ]
            private = [
                "models/downloaded_model.py",
                "backend/agents/iam_agent/app/models/weights.bin",
                "backend/agents/iam_agent/app/models/__pycache__/auth.pyc",
                "SentinelGridPenTestAgent/scanners/secrets/.env",
                "backend/tests/siem/data/telemetry.json",
            ]
            for name in source + private:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# synthetic inventory fixture\n")
            selected = {p.relative_to(root).as_posix() for p in source_files(root)}
            self.assertTrue(set(source) <= selected)
            self.assertFalse(set(private) & selected)

    def test_publication_selection_rejects_added_missing_and_duplicate_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / PUBLICATION_INVENTORY
            manifest.parent.mkdir()
            names = [PUBLICATION_INVENTORY.as_posix(), "review.py"]
            files = [root / name for name in names]
            manifest.write_text(json.dumps({"files": names}))
            self.assertEqual(publication_inventory_failures(files, root), [])
            self.assertTrue(publication_inventory_failures(files + [root / "unreviewed.py"], root))
            self.assertTrue(publication_inventory_failures(files[:-1], root))
            manifest.write_text(json.dumps({"files": names + [names[-1]]}))
            self.assertTrue(publication_inventory_failures(files, root))

    def test_tracked_ignored_secrets_still_get_scanned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".env").write_text("SYNTHETIC_CANARY=example\n")
            (root / "removed.py").write_text("pass\n")
            subprocess.run(["git", "-C", str(root), "add", ".env", "removed.py"], check=True)
            (root / ".gitignore").write_text(".env\nprivate.txt\n")
            (root / "private.txt").write_text("synthetic local-only data\n")
            (root / "new.py").write_text("pass\n")
            (root / "removed.py").unlink()
            names = {p.relative_to(root).as_posix() for p in source_files(root)}
            self.assertIn(".env", names)
            self.assertIn("new.py", names)
            self.assertNotIn("removed.py", names)
            self.assertNotIn("private.txt", names)

    def test_rejects_nested_credentials_and_third_party_installers(self):
        for name in ["backend/.env.production", "nested/private.key", "a/state.tfstate",
                     "agents/wazuh/upstream.deb", "artifacts/report.json",
                     ".claire/state.json", "gitleaks-report.json",
                     "infra/customer/tfplan", "infra/customer/review.tfplan",
                     "infra/customer/terraform.tfstate.backup", "infra/vault/ca.srl",
                     "docs/assets/html/browser_capture.html"]:
            with self.subTest(name=name):
                self.assertIsNotNone(private_file_reason(Path(name)))
        for name in ["SentinelGridAIShield/.env.example", "backend/app.py",
                     "backend/tests/helpers/vault_helper.py"]:
            self.assertIsNone(private_file_reason(Path(name)))

    def test_symlink_is_not_silently_followed_or_dropped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "outside.txt").symlink_to("/nonexistent-outside-target")
            self.assertEqual(source_files(root), [root / "outside.txt"])


if __name__ == "__main__":
    unittest.main()
