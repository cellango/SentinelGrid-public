"""Contract drift checks must fail closed without importing product modules."""
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_contracts import changed_paths, impact, validate


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.selected = {'design.md', 'module.py', 'test_module.py', 'guide.md', 'docs/archive/old.md'}
        for path in self.selected:
            p = self.root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('def test_deny():\n    assert True\n' if path.endswith('.py') else '# doc')
        self.row = dict(id='AUTH-001', owner='Security', reason='Preserve deny', gap='Source only', status='partial', disposition='keep', evidence='not_asserted', design=['design.md'], implementation=['module.py'], tests=['test_module.py::test_deny'], documentation=['guide.md'], test_profile='isolated unit', review_scope='deny contract', replacement_ids=[])
        self.data = {'format_version': 1, 'contracts': [self.row]}

    def check(self):
        return validate(self.data, self.selected, self.root)

    def test_valid_mapping_is_structural_only(self):
        self.assertEqual(self.check(), [])

    def test_missing_references_and_owner_are_rejected(self):
        for key in ('design', 'implementation', 'tests', 'documentation', 'owner'):
            with self.subTest(key=key):
                old = self.row.pop(key)
                self.assertTrue(self.check())
                self.row[key] = old

    def test_missing_path_and_stale_test_selector(self):
        self.row['tests'] = ['test_module.py::test_removed']
        self.assertTrue(self.check())
        self.row['tests'] = ['private.py']
        (self.root / 'private.py').write_text('')
        self.assertTrue(self.check())

    def test_selector_lookup_does_not_import_or_execute_test_module(self):
        (self.root / 'test_module.py').write_text(
            "raise RuntimeError('must not execute')\nclass TestBoundary:\n"
            "    async def test_deny(self):\n        pass\n")
        self.row['tests'] = ['test_module.py::TestBoundary::test_deny']
        self.assertEqual(self.check(), [])

    def test_duplicate_id(self):
        self.data['contracts'].append(copy.deepcopy(self.row))
        self.assertTrue(self.check())

    def test_archived_doc_cannot_authorize_current_contract(self):
        self.row['design'] = ['docs/archive/old.md']
        self.assertTrue(self.check())

    def test_replacement_requires_successor_coverage(self):
        self.row['disposition'] = 'replace'
        self.assertTrue(self.check())
        successor = copy.deepcopy(self.row)
        successor.update(id='AUTH-002', disposition='keep')
        self.data['contracts'].append(successor)
        self.row['replacement_ids'] = ['AUTH-002']
        self.assertEqual(self.check(), [])
        successor['tests'] = []
        self.assertTrue(self.check())

    def test_unrun_or_unknown_evidence_cannot_claim_pass(self):
        for evidence in ('passed', 'skipped', 'unknown', {'passed': True}):
            self.row['evidence'] = evidence
            self.assertTrue(self.check())

    def test_unsafe_and_symlink_paths(self):
        for path in ('../outside.py', '/tmp/no.py'):
            self.row['implementation'] = [path]
            self.assertTrue(self.check())
        (self.root / 'link.py').symlink_to(self.root / 'module.py')
        self.selected.add('link.py')
        self.row['implementation'] = ['link.py']
        self.assertTrue(self.check())

    def test_impact_unknown_and_deleted_paths_require_review(self):
        self.assertEqual(impact(self.data, ['module.py']), [])
        self.assertEqual(len(impact(self.data, ['new.py', 'deleted.py'])), 2)

    def test_real_git_impact_includes_staged_unstaged_new_and_both_rename_sides(self):
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.root), *args])
        git('init', '-q')
        git('add', '.')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')
        (self.root / 'module.py').write_text('# staged')
        git('add', 'module.py')
        (self.root / 'guide.md').write_text('# unstaged')
        (self.root / 'new.py').write_text('# new')
        git('mv', 'design.md', 'renamed.md')
        self.assertEqual(changed_paths(self.root, 'HEAD'), {'module.py', 'guide.md', 'new.py', 'design.md', 'renamed.md'})

    def test_deleted_path_requires_explicit_retirement_and_successor(self):
        self.row['retired_paths'] = ['removed.py']
        self.assertTrue(self.check())
        successor = copy.deepcopy(self.row)
        successor.update(id='AUTH-002', retired_paths=[])
        self.data['contracts'].append(successor)
        self.row['replacement_ids'] = ['AUTH-002']
        self.assertEqual(self.check(), [])
        self.assertEqual(impact(self.data, ['removed.py']), [])
        self.row['retired_paths'] = ['module.py']
        self.assertTrue(self.check())

    def test_invalid_status_types_fail_without_crashing(self):
        self.row['status'] = {'passed': True}
        self.row['disposition'] = []
        self.assertTrue(self.check())

    def test_invalid_format(self):
        for data in ([], {}, {'format_version': 1, 'contracts': []}, {'format_version': 1, 'contracts': [None]}):
            self.assertTrue(validate(data, self.selected, self.root))


if __name__ == '__main__':
    unittest.main()
