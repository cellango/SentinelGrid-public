"""Synthetic row-transfer safety; explicitly not native DB/evaluator tests."""
from copy import deepcopy
import ast
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from iam_consolidation_rehearsal import ROOT, TABLES, plan, profile_fingerprints, verify_result

A = "11111111-1111-4111-8111-111111111111"
B = "22222222-2222-4222-8222-222222222222"
C = "33333333-3333-4333-8333-333333333333"


def sample():
    tables = {key: [] for key in TABLES}
    tables["catalog.public.policies"] = [{"id": A, "tenant_id": A, "is_template": False,
        "policy_type": "authorization", "policy_data": {"effect": "deny", "unknown_extension": [1]}, "is_active": False}]
    tables["catalog.public.policy_rules"] = [{"id": B, "policy_id": A, "conditions": [], "actions": [{"type": "deny"}]}]
    tables["iam.public.entitlements"] = [{"id": A, "tenant_id": A, "resource_type": "document", "resource_id": "synthetic",
        "action": "read", "granted_to_type": "user", "granted_to_id": B, "status": "revoked", "expires_at": "2020-01-01T00:00:00Z"}]
    tables["catalog.public.entitlements"] = [{"id": A, "tenant_id": A, "name": "catalog permission", "app_id": C}]
    tables["catalog.public.policy_templates"] = [{"id": C, "tenant_id": None, "template_data": {"effect": "allow"}}]
    return {"synthetic": True, "profiles": {"test": "pinned"}, "tables": tables}


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.s = sample()
        self.fp = deepcopy(self.s["profiles"])

    def rejected(self):
        with self.assertRaises((ValueError, KeyError)):
            plan(self.s, self.fp)

    def test_preserves_all_rows_payloads_and_source(self):
        original = deepcopy(self.s)
        result = plan(self.s, self.fp)
        for source, target in TABLES.items():
            self.assertEqual(result["tables"][target], self.s["tables"][source])
        self.assertEqual(self.s, original)
        self.assertFalse(result["executable"])
        verify_result(result, self.s, self.fp)

    def test_catalog_definition_is_not_subject_grant(self):
        self.s["tables"]["iam.public.entitlements"] = self.s["tables"]["catalog.public.entitlements"]
        self.rejected()

    def test_same_uuid_in_independent_stores_is_preserved(self):
        r = plan(self.s, self.fp)["tables"]
        self.assertEqual(r["catalog.permission_definitions"][0]["id"], r["iam.subject_grants"][0]["id"])
        self.assertNotEqual(r["catalog.permission_definitions"], r["iam.subject_grants"])

    def test_profile_drift(self):
        self.s["profiles"]["test"] = "changed"
        self.rejected()

    def test_real_data_envelope_rejected(self):
        self.s["synthetic"] = False
        self.rejected()

    def test_missing_and_unknown_table(self):
        self.s["tables"]["unreviewed"] = []
        self.rejected()
        self.s = sample()
        del self.s["tables"]["catalog.public.policy_rules"]
        self.rejected()

    def test_duplicate_identity(self):
        rows = self.s["tables"]["catalog.public.policies"]
        rows.append(deepcopy(rows[0]))
        self.rejected()

    def test_duplicate_logical_grant(self):
        rows = self.s["tables"]["iam.public.entitlements"]
        rows.append({**rows[0], "id": C})
        self.rejected()

    def test_orphan_rule(self):
        self.s["tables"]["catalog.public.policy_rules"][0]["policy_id"] = C
        self.rejected()

    def test_cross_tenant_rule(self):
        self.s["tables"]["catalog.public.policy_rules"][0]["tenant_id"] = B
        self.rejected()

    def test_slug_rejected(self):
        self.s["tables"]["iam.public.entitlements"][0]["tenant_id"] = "customer-a"
        self.rejected()

    def test_mixed_template_policy_rejected(self):
        self.s["tables"]["catalog.public.policies"][0]["is_template"] = True
        self.rejected()

    def test_unknown_policy_or_status_rejected(self):
        self.s["tables"]["catalog.public.policies"][0]["policy_type"] = "custom"
        self.rejected()
        self.s = sample()
        self.s["tables"]["iam.public.entitlements"][0]["status"] = "custom"
        self.rejected()

    def test_tampered_output_rejected(self):
        r = plan(self.s, self.fp)
        r["tables"]["iam.subject_grants"][0]["status"] = "active"
        with self.assertRaises(ValueError):
            verify_result(r, self.s, self.fp)

    def test_repeat_and_source_order_are_deterministic(self):
        rows = self.s["tables"]["catalog.public.policies"]
        rows.append({**rows[0], "id": C, "tenant_id": B})
        first = plan(self.s, self.fp)
        rows.reverse()
        self.assertEqual(first, plan(self.s, self.fp))

    def test_repository_profile_bytes(self):
        self.assertEqual(len(profile_fingerprints()), 2)

    def test_ledger_references_and_selected_identity_coverage(self):
        ledger = json.loads((ROOT / "publication/domain-store-foundation.json").read_text())
        self.assertFalse(ledger["runtime_enabled"])
        self.assertEqual({row["source"] for row in ledger["owners"]}, set(TABLES))
        for row in ledger["owners"]:
            self.assertTrue((ROOT / row["evidence"]).is_file())
        for queue in ("writer_review_queue", "runner_review_queue"):
            for row in ledger[queue]:
                self.assertTrue((ROOT / row["path"]).is_file())

    def test_all_current_policy_types_preserved_without_evaluating(self):
        source = ROOT / "backend/agents/iam_agent/app/services/policy_service.py"
        tree = ast.parse(source.read_text())
        values = [ast.literal_eval(node.value) for node in ast.walk(tree)
                  if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_POLICY_TYPES" for t in node.targets)]
        self.assertEqual(len(values), 1)
        for policy_type in values[0]:
            self.s["tables"]["catalog.public.policies"][0]["policy_type"] = policy_type
            self.assertEqual(plan(self.s, self.fp)["tables"]["iam.effective_policies"][0]["policy_type"], policy_type)

    def test_changed_migration_bytes_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "publication").mkdir()
            (root / "migration.sql").write_text("changed")
            (root / "publication/application-database-profile.json").write_text(json.dumps({
                "migrations": [{"path": "migration.sql", "sha256": "0" * 64}]}))
            with self.assertRaisesRegex(ValueError, "Migration source drift"):
                profile_fingerprints(root)


if __name__ == "__main__":
    unittest.main()
