"""Publication regressions for moves, nested URLs, and private link targets."""

from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_documentation import check_links, documentation_failures, markdown_links


class DocumentationTests(unittest.TestCase):
    def test_classification_rejects_wrong_folder_class_and_unlisted_page(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme = root / 'README.md'
            readme.write_text('# Preview')
            catalog = root / 'publication/documentation.json'
            catalog.parent.mkdir()
            catalog.write_text(json.dumps({'files': [{'path': 'README.md', 'class': 'repository_entrypoint'}]}))
            self.assertEqual(documentation_failures([readme], root), [])
            catalog.write_text(json.dumps({'files': [{'path': 'README.md', 'class': 'historical_reference'}]}))
            self.assertTrue(documentation_failures([readme], root))
            added = root / 'new.md'
            added.write_text('# New')
            self.assertTrue(documentation_failures([readme, added], root))

    def test_balanced_paths_angle_paths_images_and_reference_definitions(self):
        text = ('[route](../app/(group)/page.tsx) ![asset](../icon.svg)\n'
                '[space](<../with space.md>)\n[guide]: ../guide.md "Title"\n')
        self.assertEqual([href for _, _, href in markdown_links(text)],
                         ['../app/(group)/page.tsx', '../icon.svg', '../with space.md', '../guide.md'])

    def test_code_examples_do_not_become_links(self):
        text = '```md\n[example](missing.md)\n```\n`[inline](missing.md)`\n[real](README.md)'
        self.assertEqual([href for _, _, href in markdown_links(text)], ['README.md'])

    def test_moved_page_resolves_from_its_new_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'docs/release/review.md'
            source.parent.mkdir(parents=True)
            source.write_text('[root](../../README.md) [old](README.md)')
            readme = root / 'README.md'
            readme.write_text('# Preview\n')
            self.assertEqual(len(check_links([source, readme], root)), 1)

    def test_existing_ignored_file_cannot_satisfy_a_public_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'README.md'
            source.write_text('[private](artifacts/evidence.md) [outside](../other.md) [file](file:///private/evidence.md)')
            private = root / 'artifacts/evidence.md'
            private.parent.mkdir()
            private.write_text('synthetic private fixture')
            self.assertEqual(len(check_links([source], root)), 3)

    def test_encoded_paths_and_directories_use_selected_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'README.md'
            source.write_text('[space](docs/with%20space.md) [folder](docs/) [root](.) [web](https://example.com)')
            guide = root / 'docs/with space.md'
            guide.parent.mkdir()
            guide.write_text('# Guide')
            self.assertEqual(check_links([source, guide], root), [])


if __name__ == '__main__':
    unittest.main()
