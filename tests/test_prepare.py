import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentbench import prepare, tasks
from toyrepo import make_toy, _git


class PrepareTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.upstream = self.root / "source"
        fix = make_toy(self.upstream)
        base = _git(self.upstream, "rev-parse", fix + "^")
        self.template = self.root / "template"
        self.template.mkdir()
        (self.template / "prompt.md").write_text("Fix total(None).\n")
        (self.template / "LICENSE-SOURCE").write_text("Synthetic test scaffold; MIT, TayHCode.\n")
        (self.template / "repo").mkdir()
        (self.template / "repo/LICENSE").write_text("Retained historical notice.\n")
        (self.template / "task.toml").write_text('id="toy"\ntitle="Toy"\nprompt="prompt.md"\ncheck=["python3","-m","unittest","discover","-s","tests"]\n')
        (self.template / "snapshot.toml").write_text(
            'source_repo="example/sample"\nbase_commit=' + json.dumps(base) + '\nfix_commit=' + json.dumps(fix)
            + '\ngold_paths=["cart.py"]\n[[hidden_files]]\nfrom="tests/test_cart.py"\nto="overlay/tests/test_cart.py"\n')

    def fetch_local(self, repo, source, base, fix):
        shutil.copytree(self.upstream / ".git", repo / ".git")
        self.assertEqual(source, "example/sample")
        self.assertEqual(_git(repo, "rev-parse", fix + "^{commit}"), fix)

    def test_prepared_task_uses_upstream_gold_and_hidden_regression(self):
        with patch.object(prepare, "_fetch", self.fetch_local):
            built = prepare.prepare_task(self.template, self.root / "tasks")
        self.assertFalse((built / "repo/.git").exists())
        self.assertFalse((built / "snapshot.toml").exists())
        self.assertTrue((built / "repo/cart.py").is_file())
        self.assertFalse((built / "repo/start").exists())
        self.assertEqual((built / "repo/LICENSE").read_text(), "Retained historical notice.\n")
        self.assertIn("prices or", (built / "gold/cart.py").read_text())
        result = tasks.verify_task(tasks.load_task("toy", self.root / "tasks"), self.root / "verify")
        self.assertTrue(result["start_fails"] and result["gold_passes"])

    def test_existing_task_is_preserved_without_a_network_call(self):
        target = self.root / "tasks/toy"
        target.mkdir(parents=True)
        (target / "keep").write_text("unfamiliar work")
        with patch.object(prepare, "_fetch") as fetch:
            with self.assertRaises(prepare.PrepareError):
                prepare.prepare_task(self.template, target.parent)
            fetch.assert_not_called()
        self.assertEqual((target / "keep").read_text(), "unfamiliar work")

    def test_snapshot_rejects_traversal(self):
        with self.assertRaises(prepare.PrepareError):
            prepare._path("../outside")

    def test_downloaded_commit_mismatch_is_rejected(self):
        with patch.object(prepare, "_git", side_effect=["", "", "c" * 40 + "\n"]):
            with self.assertRaisesRegex(prepare.PrepareError, "commit did not match"):
                prepare._fetch(self.upstream, "example/sample", "a" * 40, "b" * 40)

    def test_unprepared_builtin_has_an_actionable_message(self):
        with self.assertRaisesRegex(ValueError, "agentbench task prepare"):
            tasks.load_task("mypy-deferred-alias-crash")


class DataPrepareTest(unittest.TestCase):
    def setUp(self):
        import csv
        import hashlib
        import io
        import zipfile
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        template = tasks.DEFAULT_TASKS / 'qcew-county-shift-share'
        self.template = self.root / 'template'
        shutil.copytree(template, self.template)
        self.cache = self.root / 'cache'
        recipe = ''
        fields = ['year', 'qtr', 'own_code', 'size_code', 'area_fips', 'agglvl_code',
                  'industry_code', 'disclosure_code', 'month1_emplvl', 'month2_emplvl',
                  'month3_emplvl', 'total_qtrly_wages']
        for year, employment in ((2025, 100), (2026, 110)):
            text = io.StringIO()
            writer = csv.writer(text)
            writer.writerow(fields)
            for area, total_level, sector_level in (('US000', '11', '14'), ('01001', '71', '74')):
                for industry, level in (('10', total_level), ('11', sector_level)):
                    writer.writerow([year, 1, 5, 0, area, level, industry, '',
                                     employment, employment, employment, 130000])
            source = self.root / f'qcew-{year}.zip'
            with zipfile.ZipFile(source, 'w') as archive:
                archive.writestr(f'{year}.csv', text.getvalue())
            recipe += ('\n[[files]]\nname=' + json.dumps(source.name) + '\nurl='
                       + json.dumps(source.as_uri()) + '\nsha256='
                       + json.dumps(hashlib.sha256(source.read_bytes()).hexdigest()) + '\n')
        (self.template / 'data_recipe.toml').write_text(recipe)

    def test_downloads_inputs_and_verifies_real_data_preparer_twice(self):
        built = prepare.prepare_task(self.template, self.root / 'tasks', self.cache)
        self.assertEqual(len(list((built / 'repo/data').glob('*.zip'))), 2)
        self.assertFalse((built / 'repo/sector_shift_share.csv').exists())
        self.assertFalse((built / 'repo/build_reference.py').exists())
        result = tasks.verify_task(tasks.load_task(built.name, built.parent), self.root / 'verify', repeats=2)
        self.assertTrue(result['start_fails'] and result['gold_passes'])
        self.assertFalse(result['flaky'])

        with patch.object(tasks, 'DEFAULT_TASKS', self.template.parent), patch.object(tasks, 'user_tasks_dir', return_value=built.parent):
            self.assertEqual(tasks.find_task_root(built.name), built)

    def test_bad_checksum_rejects_task_and_preserves_download(self):
        recipe = self.template / 'data_recipe.toml'
        import tomllib
        pinned = tomllib.loads(recipe.read_text())['files'][0]['sha256']
        recipe.write_text(recipe.read_text().replace(pinned, '0' * 64))
        with self.assertRaisesRegex(prepare.PrepareError, 'data preparation failed'):
            prepare.prepare_task(self.template, self.root / 'tasks', self.cache)
        self.assertFalse((self.root / 'tasks/qcew-county-shift-share').exists())
        self.assertTrue((self.cache / 'qcew-2025.zip').is_file())

    def test_existing_data_task_never_launches_preparer(self):
        target = self.root / 'tasks/qcew-county-shift-share'
        target.mkdir(parents=True)
        (target / 'keep').write_text('existing work')
        with patch.object(prepare.subprocess, 'run') as launch:
            with self.assertRaises(prepare.PrepareError):
                prepare.prepare_task(self.template, target.parent, self.cache)
            launch.assert_not_called()
        self.assertEqual((target / 'keep').read_text(), 'existing work')

    def test_unprepared_data_recipe_gives_prepare_command(self):
        with self.assertRaisesRegex(ValueError, 'agentbench task prepare qcew-county-shift-share'):
            tasks.load_task('qcew-county-shift-share', tasks.DEFAULT_TASKS)

    def test_cli_data_prepare_prints_a_working_verify_command_with_custom_destination(self):
        import contextlib
        import io
        import shlex
        from agentbench import cli
        template = self.root / 'qcew-county-shift-share'
        self.template.rename(template)
        destination = self.root / 'prepared tasks'
        output = io.StringIO()
        with patch.object(cli, 'DEFAULT_TASKS', self.root), contextlib.redirect_stdout(output):
            code = cli.main(['task', 'prepare', template.name, '--tasks-dir', str(destination),
                             '--cache-dir', str(self.cache)])
        self.assertEqual(code, 0)
        command = shlex.split(output.getvalue().split('next: ', 1)[1].strip())
        self.assertEqual(command[-1], str(destination))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(command[1:] + ['--scratch', str(self.root / 'cli-verify')]), 0)
