"""Keep the public task inventory and omitted-pilot evidence honest."""
import csv
from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseDocsTest(unittest.TestCase):
    def test_every_builtin_has_source_and_license_in_public_docs(self):
        readme = (ROOT / 'README.md').read_text()
        notices = (ROOT / 'THIRD_PARTY_NOTICES.md').read_text()
        for path in sorted((ROOT / 'tasks').glob('*/task.toml')):
            meta = tomllib.loads(path.read_text())
            task_id = meta['id']
            self.assertIn(task_id, readme)
            self.assertIn('## ' + task_id + '\n', notices)
            section = notices.split('## ' + task_id + '\n', 1)[1].split('\n## ', 1)[0]
            self.assertIn('https://', section)
            self.assertIn('LICENSE-SOURCE', section)
            self.assertTrue((path.parent / 'LICENSE-SOURCE').is_file())
        self.assertTrue(readme.split('\n\n')[1].startswith('**Privacy first.**'))
        for limit in ('n=1', 'short tasks', 'not container-isolated', 'secondary', 'native Windows use WSL'):
            self.assertIn(limit, readme)

    def test_removed_pilot_rows_keep_measurements_and_explain_removal(self):
        with (ROOT / 'evidence/results.csv').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 81)
        removed = [row for row in rows if row['task'] == 'removed-pilot-task']
        self.assertTrue(removed)
        for row in removed:
            self.assertIn('removed to keep the licence trail clean', row['notes'])
            self.assertTrue(row['result'] and row['wall_s'] and row['usd_equivalent'])
