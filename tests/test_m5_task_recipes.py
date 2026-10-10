"""Task-boundary checks; no downloads or model calls."""
import importlib.util
from pathlib import Path
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'tasks/qcew-county-shift-share'
spec = importlib.util.spec_from_file_location('qcew_checker',DATA/'hidden/check.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class M5TaskRecipes(unittest.TestCase):
    def test_code_recipes_keep_upstream_regressions_hidden(self):
        for task in ['pydantic-namespace-inspection','mypy-paramspec-unpack-crash']:
            root=ROOT/'tasks'/task
            snapshot=tomllib.loads((root/'snapshot.toml').read_text())
            manifest=tomllib.loads((root/'manifest.toml').read_text())
            self.assertGreater(manifest['fix_merged'],'2026-06-30')
            self.assertNotEqual(snapshot['base_commit'],snapshot['fix_commit'])
            self.assertTrue(snapshot['hidden_files'])
            for row in snapshot['hidden_files']:
                self.assertIn(row['from'],snapshot['gold_paths'])
                self.assertFalse((root/'hidden'/row['to']).exists())
            self.assertFalse((root/'repo').exists())
            self.assertEqual(len(manifest['workflow_match']),5)

    def test_data_recipe_has_only_pinned_public_downloads(self):
        recipe=tomllib.loads((DATA/'data_recipe.toml').read_text())
        self.assertGreater(recipe['release_date'],'2026-06-30')
        self.assertEqual(len(recipe['files']),2)
        for row in recipe['files']:
            self.assertTrue(row['url'].startswith('https://data.bls.gov/cew/'))
            self.assertRegex(row['sha256'],r'^[0-9a-f]{64}$')
        self.assertFalse((DATA/'repo').exists())
        self.assertFalse((DATA/'gold').exists())
        self.assertFalse(list(DATA.rglob('*.zip')))

    def test_checker_rejects_nan_duplicates_extra_keys_and_lost_fips(self):
        # Exercise a contract boundary, independent of any answer arithmetic.
        old_file=checker.__file__
        import os
        cwd=Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            work=Path(directory)
            hidden=work/'hidden';hidden.mkdir()
            checker.__file__=str(hidden/'check.py')
            name='result.csv'
            wanted='area_fips,employment_2025\n01001,0.000000\n'
            (hidden/name).write_text(wanted)
            try:
                os.chdir(work)
                for text in ['area_fips,employment_2025\n01001,nan\n',
                             wanted+'01001,0\n',wanted+'01003,0\n',
                             'area_fips,employment_2025\n01001,0,unexpected\n',
                             'area_fips,employment_2025\n1001,0\n']:
                    Path(name).write_text(text)
                    self.assertTrue(checker.check(name))
                Path(name).write_text(wanted)
                self.assertEqual(checker.check(name),[])
            finally:
                os.chdir(cwd)
                checker.__file__=old_file
