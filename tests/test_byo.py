"""Bring your own: task from-commit, overlay, setup (B1)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from toyrepo import _git, make_toy  # noqa: E402

from agentbench import fromcommit, runner, tasks  # noqa: E402

STUB_SRC = Path(__file__).resolve().parent / "stub_claude.py"
UNITTEST = "python3 -m unittest discover -s tests"
FAKE_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"  # built at run time so this file holds no secret-shaped string


class Scratch(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.lines = []

    def toy(self, **kw):
        sha = make_toy(self.tmp / "toy", **kw)
        return self.tmp / "toy", sha

    def build(self, repo, sha, task_id="toy-null-total", **kw):
        kw.setdefault("check", UNITTEST)
        code, folder = fromcommit.build(repo, sha, task_id, self.tmp / "tasks", out=self.lines.append, **kw)
        return code, folder

    def stub(self, **cfg):
        """A copy of the stub CLI with its settings next to it; AGENTBENCH_CLAUDE_BIN points at it for this test."""
        path = self.tmp / f"claude-stub-{len(list(self.tmp.glob('claude-stub-*')))}"
        shutil.copy(STUB_SRC, path)
        Path(str(path) + ".json").write_text(json.dumps(cfg))
        os.environ["AGENTBENCH_CLAUDE_BIN"] = str(path)
        self.addCleanup(os.environ.pop, "AGENTBENCH_CLAUDE_BIN", None)
        return path

    def said(self):
        return "\n".join(self.lines)


class FromCommitTest(Scratch):
    def test_builds_a_verified_private_task_without_the_fix_in_it(self):
        repo, sha = self.toy()
        code, folder = self.build(repo, sha)
        self.assertEqual(code, 0, self.said())
        self.assertIn("unfixed fails, fixed passes, both twice", self.said())
        self.assertIn("return round(sum(prices) *", (folder / "repo" / "cart.py").read_text())
        self.assertNotIn("prices or []", (folder / "repo" / "cart.py").read_text())
        self.assertNotIn("none_means_no_prices", (folder / "repo" / "tests" / "test_cart.py").read_text())
        self.assertIn("none_means_no_prices", (folder / "hidden" / "overlay" / "tests" / "test_cart.py").read_text())
        self.assertIn("prices or []", (folder / "gold" / "cart.py").read_text())
        self.assertFalse((folder / "gold" / "tests").exists())
        self.assertFalse((folder / "repo" / ".git").exists())
        manifest = tomllib.loads((folder / "manifest.toml").read_text())
        self.assertIs(manifest["private"], True)
        self.assertEqual(manifest["fix_commit"], sha)
        task = tomllib.loads((folder / "task.toml").read_text())
        self.assertEqual(task["check"], UNITTEST.split())
        self.assertNotIn(".building", " ".join(os.listdir(self.tmp / "tasks")))

    def test_prompt_is_a_draft_without_trailers_and_run_refuses_it(self):
        repo, sha = self.toy()
        _, folder = self.build(repo, sha)
        prompt = (folder / "prompt.md").read_text()
        self.assertTrue(prompt.startswith("<!-- DRAFT"))
        self.assertIn("total() crashes on an empty cart", prompt)
        self.assertNotIn("Signed-off-by", prompt)
        self.stub()
        with self.assertRaises(runner.TaskNotReady):
            runner.run("toy-null-total", "haiku-5-5@claude-code", self.tmp / "runs", self.tmp / "tasks")

    def test_hidden_overlay_is_copied_in_at_check_time_and_a_stub_fix_passes(self):
        repo, sha = self.toy()
        _, folder = self.build(repo, sha)
        (folder / "prompt.md").write_text("total(None) crashes. Make it return 0.\n")
        self.stub(fix_dir=str(folder / "gold"))
        rec = runner.run("toy-null-total", "haiku-5-5@claude-code", self.tmp / "runs", self.tmp / "tasks")
        self.assertTrue(rec["passed"], rec["check_output_tail"])
        self.assertEqual(rec["diff"]["files"][0]["path"], "cart.py")
        self.stub()
        rec = runner.run("toy-null-total", "haiku-5-5@claude-code", self.tmp / "runs2", self.tmp / "tasks")
        self.assertFalse(rec["passed"])

    def test_a_flaky_check_is_rejected(self):
        repo, sha = self.toy()
        counter = self.tmp / "count"
        flaky = f"python3 -c \"import pathlib,sys; p=pathlib.Path(r'{counter}'); n=int(p.read_text() or 0) if p.exists() else 0; p.write_text(str(n+1)); sys.exit(n%2)\""
        code, folder = self.build(repo, sha, check=flaky)
        self.assertEqual(code, 4)
        self.assertIsNone(folder)
        self.assertIn("flaky", self.said())
        self.assertEqual([p.name for p in (self.tmp / "tasks").iterdir()], [])

    def test_a_check_that_passes_on_the_unfixed_tree_is_rejected(self):
        repo, sha = self.toy()
        code, _ = self.build(repo, sha, check="true")
        self.assertEqual(code, 4)
        self.assertIn("PASS on the unfixed tree", self.said())

    def test_a_check_that_fails_on_the_fixed_tree_is_rejected(self):
        repo, sha = self.toy()
        code, _ = self.build(repo, sha, check="false")
        self.assertEqual(code, 4)
        self.assertIn("FAIL on the fixed tree", self.said())

    def test_secret_shaped_string_refuses_to_build_and_never_prints_the_value(self):
        repo, sha = self.toy(extra_files={"config.py": 'K' + 'EY = ' + chr(34) + FAKE_KEY + chr(34) + '\n'})
        code, folder = self.build(repo, sha)
        self.assertEqual(code, 3)
        self.assertIsNone(folder)
        self.assertIn("config.py:1  AWS access key", self.said())
        self.assertNotIn(FAKE_KEY, self.said())
        self.assertEqual(list((self.tmp / "tasks").iterdir()), [])

    def test_allow_secrets_builds_with_a_warning(self):
        repo, sha = self.toy(extra_files={"config.py": 'K' + 'EY = ' + chr(34) + FAKE_KEY + chr(34) + '\n'})
        code, folder = self.build(repo, sha, allow_secrets=True)
        self.assertEqual(code, 0, self.said())
        self.assertIn("kept because of --allow-secrets", self.said())

    def test_secret_named_files_are_left_out_of_the_task(self):
        repo, sha = self.toy(extra_files={".env": "A=1\n", "deploy/server.pem": "x\n", "id_rsa": "x\n", "credentials.json": "{}\n",
                                          "deploy/.env.production": "B=2\n"})
        code, folder = self.build(repo, sha)
        self.assertEqual(code, 0, self.said())
        left = {p.relative_to(folder / "repo").as_posix() for p in (folder / "repo").rglob("*") if p.is_file()}
        self.assertEqual(left, {"cart.py", "README.md", "tests/test_cart.py"})
        self.assertIn("5 secret-named file(s)", self.said())

    def test_remote_url_is_kept_for_the_peek_flag_without_credentials_and_a_local_path_is_not(self):
        repo, sha = self.toy()
        _git(repo, "remote", "add", "origin", "https://someone:" + "test-pass" + "@" + "github.com/acme/app.git")
        _, folder = self.build(repo, sha)
        manifest = tomllib.loads((folder / "manifest.toml").read_text())
        self.assertEqual(manifest["remote_url"], "https://github.com/acme/app.git")
        self.assertNotIn("hunter2pass", (folder / "manifest.toml").read_text())
        _git(repo, "remote", "set-url", "origin", str(self.tmp / "elsewhere.git"))
        _, folder = self.build(repo, sha, task_id="second")
        self.assertNotIn("remote_url", tomllib.loads((folder / "manifest.toml").read_text()))

    def test_merge_commit_needs_base(self):
        repo, sha = self.toy()
        _git(repo, "checkout", "-q", "-b", "side", sha + "~1")
        (repo / "side.txt").write_text("x\n")
        _git(repo, "add", "side.txt")
        _git(repo, "commit", "-q", "-m", "side")
        _git(repo, "checkout", "-q", "main")
        _git(repo, "merge", "-q", "--no-ff", "-m", "merge side", "side")
        with self.assertRaisesRegex(fromcommit.BuildError, "merge commit"):
            self.build(repo, "HEAD")

    def test_commit_without_tests_is_refused_with_a_pointer_to_command_tasks(self):
        repo, sha = self.toy()
        (repo / "cart.py").write_text((repo / "cart.py").read_text() + "\n# more\n")
        _git(repo, "commit", "-qam", "tweak")
        with self.assertRaisesRegex(fromcommit.BuildError, "no test files"):
            self.build(repo, "HEAD")

    def test_bad_inputs(self):
        repo, sha = self.toy()
        with self.assertRaisesRegex(fromcommit.BuildError, "not a commit"):
            self.build(repo, "deadbeef00")
        # TMPDIR may be inside another checkout during release verification.
        # Keep this empty-directory fixture from discovering that parent repo.
        with patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": str(self.tmp.parent)}):
            with self.assertRaisesRegex(fromcommit.BuildError, "not a git repository"):
                self.build(self.tmp, sha)
        with self.assertRaisesRegex(fromcommit.BuildError, "--id"):
            self.build(repo, sha, task_id="../x")
        self.assertEqual(self.build(repo, sha)[0], 0)
        with self.assertRaisesRegex(fromcommit.BuildError, "already exists"):
            self.build(repo, sha)

    def test_prompt_leak_warnings(self):
        sha = "3f9a2c1d" * 5
        self.assertTrue(fromcommit.prompt_leaks(f"fixed in {sha[:8]}", sha, ["tests/test_cart.py"]))
        self.assertTrue(fromcommit.prompt_leaks("see test_cart", sha, ["tests/test_cart.py"]))
        self.assertEqual(fromcommit.prompt_leaks("total(None) crashes", sha, ["tests/test_cart.py"]), [])


class GuessCheckTest(Scratch):
    def repo_with(self, **files):
        for name, text in files.items():
            (self.tmp / name).write_text(text)
        return self.tmp

    def test_pytest_with_and_without_uv(self):
        setup, check, label = fromcommit.guess_check(self.repo_with(**{"pyproject.toml": ""}), ["tests/test_a.py"])
        self.assertEqual((setup, check[:3], label), (None, ["python3", "-m", "pytest"], "pytest"))
        self.assertEqual(check[-1], "tests/test_a.py")
        setup, check, _ = fromcommit.guess_check(self.repo_with(**{"uv.lock": ""}), ["tests/test_a.py"])
        self.assertEqual((setup, check[:2]), (["uv", "sync"], ["uv", "run"]))

    def test_npm_go_cargo_make(self):
        r = self.repo_with(**{"package.json": json.dumps({"scripts": {"test": "vitest"}})})
        self.assertEqual(fromcommit.guess_check(r, ["test/a.test.ts"])[1:], (["npm", "test", "--", "test/a.test.ts"], "npm test"))
        self.assertEqual(fromcommit.guess_check(r, ["test/a.test.ts"])[0][:2], ["npm", "install"])
        (r / "package-lock.json").write_text("{}")
        self.assertEqual(fromcommit.guess_check(r, ["test/a.test.ts"])[0], ["npm", "ci"])
        g = self.tmp / "g"
        g.mkdir()
        (g / "go.mod").write_text("module x\n")
        self.assertEqual(fromcommit.guess_check(g, ["pkg/a_test.go"])[1:], (["go", "test", "./pkg"], "go test"))
        c = self.tmp / "c"
        c.mkdir()
        (c / "Cargo.toml").write_text("[package]\n")
        self.assertEqual(fromcommit.guess_check(c, ["tests/a.rs"])[1:], (["cargo", "test", "--quiet"], "cargo test"))
        m = self.tmp / "m"
        m.mkdir()
        (m / "Makefile").write_text("test:\n\techo hi\n")
        self.assertEqual(fromcommit.guess_check(m, ["t/x.sh"])[1:], (["make", "test"], "make test"))
        with self.assertRaisesRegex(fromcommit.BuildError, "--check"):
            fromcommit.guess_check(self.repo_with(), ["t/x.sh"])


class SetupTest(Scratch):
    def make_task(self, setup):
        root = self.tmp / "tasks" / "t1"
        (root / "repo").mkdir(parents=True)
        (root / "repo" / "tracked.txt").write_text("a\n")
        (root / "hidden").mkdir()
        (root / "prompt.md").write_text("do it\n")
        (root / "task.toml").write_text(f'id = "t1"\ntitle = "t"\nprompt = "prompt.md"\ncheck = ["true"]\nsetup = {json.dumps(setup)}\n')
        return root

    def test_setup_runs_before_the_agent_and_its_files_are_not_the_agents_diff(self):
        self.make_task(["python3", "-c", "import pathlib; pathlib.Path('node_modules').mkdir(); pathlib.Path('node_modules/x').write_text('1'); "
                        "pathlib.Path('tracked.txt').write_text('b\\n')"])
        self.stub()
        rec = runner.run("t1", "haiku-5-5@claude-code", self.tmp / "runs", self.tmp / "tasks")
        self.assertEqual(rec["diff"]["files_changed"], 0)  # install output and the lockfile-style edit are the start state
        self.assertEqual(rec["tokens_total"], 1060)  # only the stub's own tokens are metered
        self.assertTrue((next((self.tmp / "runs").glob("*/work")) / "node_modules" / "x").exists())

    def test_failing_setup_stops_before_the_agent_starts(self):
        self.make_task(["python3", "-c", "import sys; print('boom'); sys.exit(3)"])
        os.environ["AGENTBENCH_CLAUDE_BIN"] = "/nonexistent/claude"
        self.addCleanup(os.environ.pop, "AGENTBENCH_CLAUDE_BIN", None)
        with self.assertRaisesRegex(runner.TaskNotReady, "setup command failed"):
            runner.run("t1", "haiku-5-5@claude-code", self.tmp / "runs", self.tmp / "tasks")
        self.assertEqual(list((self.tmp / "runs").iterdir()), [])

    def test_gold_delete_removes_files_the_real_fix_removed(self):
        root = self.make_task(["true"])
        (root / "gold").mkdir()
        (root / "gold" / "new.txt").write_text("n\n")
        task = tasks.load_task("t1", self.tmp / "tasks") | {"gold_delete": ["tracked.txt"]}
        work = self.tmp / "w"
        tasks.prepare_workdir(task, work)
        tasks.apply_gold(task, work)
        self.assertTrue((work / "new.txt").exists())
        self.assertFalse((work / "tracked.txt").exists())

    def test_agentbench_in_a_check_means_this_install(self):
        self.assertEqual(tasks.resolve_check(["agentbench", "check-files", "a"])[1:3], ["-m", "agentbench.cli"])
        self.assertEqual(tasks.resolve_check(["python3", "x"]), ["python3", "x"])


class KillTreeTest(unittest.TestCase):
    def test_windows_uses_taskkill_on_the_whole_tree_and_posix_kills_the_group(self):
        from unittest import mock
        proc = mock.Mock(pid=4242)
        with mock.patch.object(runner.subprocess, "run") as run, mock.patch.object(runner.os, "killpg", create=True) as killpg:
            runner.kill_tree(proc, windows=True)
            run.assert_called_once()
            self.assertEqual(run.call_args[0][0], ["taskkill", "/T", "/F", "/PID", "4242"])
            killpg.assert_not_called()
            runner.kill_tree(proc, windows=False)
            killpg.assert_called_once_with(4242, runner.signal.SIGKILL)


class CliTest(Scratch):
    def test_cli_builds_into_the_default_tasks_folder_of_agentbench_home(self):
        repo, sha = self.toy()
        env = os.environ | {"AGENTBENCH_HOME": str(self.tmp / "home"), "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
        r = subprocess.run([sys.executable, "-m", "agentbench.cli", "task", "from-commit", str(repo), sha, "--id", "cli-task",
                            "--check", UNITTEST], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.tmp / "home" / "tasks" / "cli-task" / "task.toml").exists())
        again = subprocess.run([sys.executable, "-m", "agentbench.cli", "task", "from-commit", str(repo), sha, "--id", "cli-task"],
                               capture_output=True, text=True, env=env)
        self.assertEqual(again.returncode, 2)
        self.assertIn("already exists", again.stderr)


if __name__ == "__main__":
    unittest.main()
