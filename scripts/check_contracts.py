"""Read-only structural contract traceability; never executes recorded test commands."""
import argparse
import ast
import json
from pathlib import Path
import re
import subprocess

from public_preview import ROOT, source_files

LEDGER = 'publication/contracts.json'


def validate(data, selected, root):
    errors = []
    if not isinstance(data, dict) or data.get('format_version') != 1 or not isinstance(data.get('contracts'), list):
        return ['Invalid contract ledger format']
    rows = data['contracts']
    if not rows:
        return ['Contract ledger must not be empty']
    ids = [r.get('id') for r in rows if isinstance(r, dict)]
    if len(ids) != len(rows) or any(not isinstance(i, str) or not re.fullmatch(r'[A-Z]+-\d{3}', i) for i in ids):
        return ['Contract IDs must be explicit PREFIX-000 strings']
    if len(set(ids)) != len(ids):
        errors.append('Duplicate contract ID')
    by_id = {r['id']: r for r in rows}

    def path_ok(value):
        return (isinstance(value, str) and value in selected
                and not (root / value).is_symlink()
                and (root / value).resolve().is_relative_to(root.resolve()))

    for row in rows:
        label = row['id']
        for field in ('owner', 'reason', 'gap'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f'{label}: missing {field}')
        if row.get('status') not in ('source_present', 'partial', 'target', 'legacy', 'retired'):
            errors.append(f'{label}: invalid status; qualification is not inferred')
        if row.get('disposition') not in ('keep', 'update', 'replace', 'archive'):
            errors.append(f'{label}: invalid disposition')
        if row.get('evidence') != 'not_asserted':
            errors.append(f'{label}: ledger cannot assert passed or unverified execution evidence')
        for field in ('design', 'implementation', 'tests', 'documentation'):
            refs = row.get(field)
            if not isinstance(refs, list) or not refs or not all(isinstance(x, str) for x in refs):
                errors.append(f'{label}: missing {field} references')
                continue
            for ref in refs:
                parts = ref.split('::')
                path = parts[0]
                if not path_ok(path):
                    errors.append(f'{label}: missing or unsafe {field} path: {path}')
                    continue
                if field in {'design', 'documentation'} and path.startswith('docs/archive/'):
                    errors.append(f'{label}: historical document cannot be current authority')
                if len(parts) > 1:
                    if field != 'tests' or not path.endswith('.py'):
                        errors.append(f'{label}: selectors supported only for Python tests')
                        continue
                    try:
                        nodes = ast.parse((root / path).read_text()).body
                        for name in parts[1:]:
                            node = next((n for n in nodes if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name), None)
                            if node is None:
                                raise ValueError('missing selector')
                            nodes = node.body
                    except (SyntaxError, ValueError):
                        errors.append(f'{label}: unresolved test selector: {ref}')
        for field in ('test_profile', 'review_scope'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                errors.append(f'{label}: missing {field}')
        retired = row.get('retired_paths', [])
        if not isinstance(retired, list) or not all(isinstance(p, str) for p in retired):
            errors.append(f'{label}: invalid retired_paths')
            retired = []
        for path in retired:
            if (not path or Path(path).is_absolute() or '..' in Path(path).parts
                    or path in selected or (root / path).exists()):
                errors.append(f'{label}: retired path must be an absent repository-relative path')
        successors = row.get('replacement_ids', [])
        if not isinstance(successors, list) or not all(isinstance(i, str) for i in successors):
            errors.append(f'{label}: invalid replacement_ids')
            continue
        if (row.get('disposition') in ('replace', 'archive') or retired) and not successors:
            errors.append(f'{label}: replacement coverage must be mapped before retirement')
        for successor in successors:
            replacement = by_id.get(successor)
            if successor == label or not replacement or not replacement.get('tests') or replacement.get('status') == 'retired':
                errors.append(f'{label}: invalid replacement coverage: {successor}')
    return errors


def impact(data, changed):
    covered = {ref.split('::')[0] for row in data['contracts']
               for field in ('design', 'implementation', 'tests', 'documentation')
               for ref in row[field]}
    covered.update(path for row in data['contracts'] for path in row.get('retired_paths', []))
    return [f'Unmapped changed path requires contract review: {p}' for p in sorted(set(changed) - covered)]


def changed_paths(root, base):
    sha = subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--verify', '--end-of-options', base + '^{commit}'], text=True).strip()
    result = subprocess.check_output(['git', '-C', str(root), 'diff', '--name-only', '--no-renames', '-z', sha, '--'])
    untracked = subprocess.check_output(['git', '-C', str(root), 'ls-files', '--others', '--exclude-standard', '-z'])
    return set((result + untracked).decode().split('\0')) - {''}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', help='Compare base commit to working tree, including non-ignored untracked paths')
    args = parser.parse_args()
    try:
        data = json.loads((ROOT / LEDGER).read_text())
        selected = {p.relative_to(ROOT).as_posix() for p in source_files()}
        errors = validate(data, selected, ROOT)
        if args.base and not errors:
            errors += impact(data, changed_paths(ROOT, args.base))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f'Contract validation unavailable: {type(exc).__name__}')
        return 1
    for error in errors:
        print(f'FAIL: {error}')
    print(f'Contract structural checks: {len(errors)} failures. No test execution or behavioral qualification claimed.')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
