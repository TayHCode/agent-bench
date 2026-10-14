"""The easy path: python -m agentbench, doctor, demo (free and --real), start, cheapest-first gating, friendly errors.

No paid calls: the "real" agent is a fake CLI script that speaks the same protocol.
"""

import contextlib
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from toyrepo import make_toy  # noqa: E402

from agentbench import cli, doctor, guided, runner  # noqa: E402

SRC = Path(__file__).resolve().parents[1] / "src"
UNITTEST = f"{sys.executable} -m unittest discover -s tests"
FAKE = '''#!{py}
import json, sys
a = sys.argv[1:]
if a[:2] == ["auth", "status"]:
    print(json.dumps({{"loggedIn": {logged_in}, "authMethod": "claude.ai"}}))
    sys.exit(0 if {logged_in} else 1)
if a[:1] == ["--version"]:
    print("9.9.9 (Claude Code)")
    sys.exit(0)
sys.stdin.read()
m = "claude-haiku-5-5"
print(json.dumps({{"type": "assistant", "message": {{"id": "x", "model": m, "content": [], "usage": {{"input_tokens": 100, "cache_creation_input_tokens": 1000, "output_tokens": 50}}}}}}), flush=True)
print(json.dumps({{"type": "result", "subtype": "success", "is_error": False, "total_cost_usd": 0.0, "modelUsage": {{m: {{"inputTokens": 100, "cacheCreationInputTokens": 1000, "cacheReadInputTokens": 0, "outputTokens": 50}}}}}}), flush=True)
'''


class Env(unittest.TestCase):
    """Own AGENTBENCH_HOME and working folder; no real CLIs, no API key."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        env = {"AGENTBENCH_HOME": str(self.tmp / "home"), "AGENTBENCH_CACHE": str(self.tmp / "cache"),
               "AGENTBENCH_CLAUDE_BIN": str(self.tmp / "no-claude"), "AGENTBENCH_CODEX_BIN": str(self.tmp / "no-codex")}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self.cwd = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, self.cwd)

    def fake_claude(self, logged_in=True):
        p = self.tmp / "claude-fake"
        p.write_text(FAKE.format(py=sys.executable, logged_in=logged_in))
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
        os.environ["AGENTBENCH_CLAUDE_BIN"] = str(p)

    def toy(self):
        repo = self.tmp / "toy"
        return repo, make_toy(repo)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = cli.main(list(argv))
            except SystemExit as e:  # argparse and "error: ..." exits
                code = e.code
                if isinstance(code, str):
                    print(code, file=err)
                    code = 1
        return code, out.getvalue(), err.getvalue()


class InstallTest(unittest.TestCase):
    def test_python_dash_m_agentbench_works(self):
        r = subprocess.run([sys.executable, "-m", "agentbench", "--help"], capture_output=True, text=True,
                           env=os.environ | {"PYTHONPATH": str(SRC)})
        self.assertEqual(r.returncode, 0, r.stderr)
        for word in ("doctor", "demo", "start"):
            self.assertIn(word, r.stdout)


class DoctorTest(Env):
    def test_missing_clis_are_notes_not_blockers(self):
        res = doctor.diagnose()
        self.assertEqual(doctor.blockers(res), [])
        notes = {r["name"]: r for r in res if r["level"] == "note"}
        self.assertIn("npm install -g @anthropic-ai/claude-code", notes["claude"]["fix"])
        code, out, _ = self.run_cli("doctor")
        self.assertEqual(code, 0)
        self.assertIn("fix: npm install -g @openai/codex", out)

    def test_logged_out_claude_is_reported_with_the_login_command(self):
        self.fake_claude(logged_in=False)
        claude = next(r for r in doctor.diagnose() if r["name"] == "claude")
        self.assertEqual(claude["level"], "note")
        self.assertIn("not logged in", claude["detail"])
        self.assertEqual(claude["fix"], "claude auth login")

    def test_a_cli_that_cannot_run_is_reported_not_trusted(self):
        broken = self.tmp / "claude-broken"
        broken.write_text("#!/bin/sh\necho 'exec: node: not found' >&2\nexit 127\n")
        broken.chmod(0o755)
        os.environ["AGENTBENCH_CLAUDE_BIN"] = str(broken)
        claude = next(r for r in doctor.diagnose() if r["name"] == "claude")
        self.assertIn("does not run", claude["detail"])
        self.assertIn("npm install", claude["fix"])

    def test_logged_in_claude_is_ok(self):
        self.fake_claude(logged_in=True)
        res = doctor.diagnose()
        self.assertEqual(doctor.available_agents(res), ["claude-code"])

    def test_chosen_agent_that_is_not_ready_is_a_blocker(self):
        self.fake_claude(logged_in=False)
        res = doctor.diagnose(needs={"claude-code"})
        self.assertEqual([r["name"] for r in doctor.blockers(res)], ["claude"])

    def test_exit_code_is_nonzero_only_for_a_blocker(self):
        with mock.patch.object(doctor.shutil, "which", return_value=None):
            code, out, _ = self.run_cli("doctor")
        self.assertEqual(code, 1)
        self.assertIn("BLOCKER", out)
        self.assertIn("apt install git", out) if sys.platform.startswith("linux") else None
        self.assertNotIn("sudo ", out)
        self.assertNotIn("| sh", out)

    def test_old_python_is_a_blocker_with_a_fix(self):
        with mock.patch.object(doctor.sys, "version_info", (3, 9, 1, "final", 0)):
            r = doctor.check_python()
        self.assertEqual(r["level"], "blocker")
        self.assertIn("3.11", r["detail"])

    def test_native_windows_says_use_wsl(self):
        with mock.patch.object(doctor.sys, "platform", "win32"):
            r = doctor.check_platform()
        with mock.patch.object(doctor, "check_platform", return_value=r):
            code, out, _ = self.run_cli("doctor")
            _, _, err = self.run_cli("demo")
        self.assertEqual(r["level"], "blocker")
        self.assertIn("WSL", r["detail"])
        self.assertIn("wsl --install", r["fix"])
        self.assertEqual(code, 1)
        self.assertIn("use WSL", out)
        self.assertIn("fix:   wsl --install", err)

    def test_low_disk_is_a_blocker(self):
        with mock.patch.object(doctor.shutil, "disk_usage", return_value=mock.Mock(free=50 * 1024 * 1024)):
            self.assertEqual(doctor.check_disk(self.tmp)["level"], "blocker")
        with mock.patch.object(doctor.shutil, "disk_usage", return_value=mock.Mock(free=500 * 1024 * 1024)):
            self.assertEqual(doctor.check_disk(self.tmp)["level"], "note")

    def test_api_key_counts_as_logged_in(self):
        self.fake_claude(logged_in=False)
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "example-key"}):
            self.assertTrue(doctor.claude_login()[0])


class DemoTest(Env):
    def test_free_demo_prints_the_table_and_writes_results_html(self):
        code, out, err = self.run_cli("demo")
        self.assertEqual((code, err), (0, ""), out)
        self.assertRegex(out, r"stub-solver\s+pass")
        self.assertRegex(out, r"stub-lazy\s+FAIL")
        self.assertIn("$0.0000", out)
        html = (self.tmp / "results.html").read_text()
        self.assertIn("stub-solver", html)
        self.assertFalse((self.tmp / "home").exists(), "the demo must not write into AGENTBENCH_HOME")

    def test_demo_as_a_subprocess_from_a_fresh_folder(self):
        r = subprocess.run([sys.executable, "-m", "agentbench", "demo"], capture_output=True, text=True, cwd=self.tmp,
                           env=os.environ | {"PYTHONPATH": str(SRC)})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.tmp / "results.html").stat().st_size > 1000)

    def test_real_demo_without_a_logged_in_agent_says_what_to_do(self):
        code, out, err = self.run_cli("demo", "--real")
        self.assertEqual(code, 2)
        self.assertIn("agentbench doctor", err)
        self.assertNotIn("Traceback", err)

    def test_real_demo_shows_the_plan_and_runs_nothing_on_no(self):
        self.fake_claude()
        out = []
        code = guided.demo(real=True, html="r.html", ask=lambda q: "n", say=out.append, interactive=True)
        text = "\n".join(out)
        self.assertEqual(code, 3)
        self.assertIn("claude-haiku-5-5", text)
        self.assertIn("up to $0.05", text)
        self.assertFalse((self.tmp / "r.html").exists())

    def test_real_demo_runs_the_cheapest_contestant_under_five_cents_after_yes(self):
        self.fake_claude()
        seen = []
        real_run = runner.run

        def spy(task, cid, out, tasks_dir, caps, **kw):
            seen.append((cid, caps["max_usd"]))
            return real_run(task, cid, out, tasks_dir, caps, **kw)

        out = []
        orig = cli.run_matrix
        with mock.patch.object(cli, "run_matrix", lambda *a, **kw: orig(*a, **(kw | {"runner_run": spy}))):
            code = guided.demo(real=True, html="r.html", ask=lambda q: "y", say=out.append, interactive=True)
        self.assertEqual(code, 0, out)
        self.assertEqual(seen, [("haiku-5-5@claude-code", 0.05)])
        self.assertIn("haiku-5-5@claude-code", "\n".join(out))
        self.assertTrue((self.tmp / "r.html").exists())

    def test_real_demo_needs_yes_without_a_terminal(self):
        self.fake_claude()
        code, out, err = self.run_cli("demo", "--real")
        self.assertEqual(code, 2)
        self.assertIn("--yes", err)


class GatingTest(Env):
    def matrix(self, results, problem, ids="expensive-one,cheap-one", repeats=1):
        """results: {contestant: [passed, ...]} handed out in order. Returns (calls, problem checks, output)."""
        calls, asked, out = [], [], []
        queue = {k: list(v) for k, v in results.items()}
        defs = {"cheap-one": {"cli": "claude-code", "model": "claude-haiku-5-5", "price_model": "claude-haiku-5-5", "caps": {}},
                "expensive-one": {"cli": "claude-code", "model": "claude-opus-5-5", "price_model": "claude-opus-5-5", "caps": {}}}
        prices = runner.load_prices()

        def fake_run(task, cid, out_dir, tasks_dir, caps, profile="m2", contestants=None, prices=None):
            calls.append(cid)
            return {"usd_equivalent": 0.0, "status": "ok", "passed": queue[cid].pop(0), "wall_s": 1, "tokens_total": 1}

        def problem_of(task, tasks_dir):
            asked.append(task)
            return problem

        code = cli.run_matrix(["t1"], ids, str(self.tmp / "runs"), None, 5.0, fake_run, profile="byo", defs=defs, prices=prices,
                              repeats=repeats, problem_of=problem_of, say=out.append)
        return code, calls, asked, out

    def test_cheapest_runs_first_whatever_the_order_given(self):
        _, calls, _, _ = self.matrix({"cheap-one": [True], "expensive-one": [True]}, None)
        self.assertEqual(calls, ["cheap-one", "expensive-one"])

    def test_broken_task_skips_the_pricier_contestants(self):
        _, calls, asked, out = self.matrix({"cheap-one": [False], "expensive-one": [True]}, "its check fails even on the known fix")
        self.assertEqual(calls, ["cheap-one"])
        self.assertEqual(asked, ["t1"])
        self.assertTrue(any("SKIP" in line and "broken" in line for line in out))

    def test_failing_cheapest_on_a_sound_task_still_runs_everyone(self):
        _, calls, asked, _ = self.matrix({"cheap-one": [False], "expensive-one": [True]}, None)
        self.assertEqual(calls, ["cheap-one", "expensive-one"])
        self.assertEqual(asked, ["t1"])

    def test_passing_cheapest_runs_everyone_without_checking_the_task(self):
        _, calls, asked, _ = self.matrix({"cheap-one": [True], "expensive-one": [False]}, "ignored")
        self.assertEqual(calls, ["cheap-one", "expensive-one"])
        self.assertEqual(asked, [])

    def test_repeats(self):
        _, calls, _, _ = self.matrix({"cheap-one": [True] * 3, "expensive-one": [True] * 3}, None, repeats=3)
        self.assertEqual(calls, ["cheap-one"] * 3 + ["expensive-one"] * 3)

    def test_task_problem_finds_a_task_whose_check_fails_on_the_known_fix(self):
        repo, sha = self.toy()
        code, folder = guided.fromcommit.build(repo, sha, "good", self.tmp / "tasks", check=UNITTEST, out=lambda *_: None)
        self.assertEqual(code, 0)
        self.assertIsNone(cli.task_problem("good", str(self.tmp / "tasks")))
        (folder / "gold" / "cart.py").write_text("raise SystemExit(1)\n")  # the "known fix" no longer fixes anything
        self.assertIn("known fix", cli.task_problem("good", str(self.tmp / "tasks")))

    def test_matrix_command_accepts_repeats_and_free_stubs(self):
        repo, sha = self.toy()
        guided.fromcommit.build(repo, sha, "toy", self.tmp / "home" / "tasks", check=UNITTEST, out=lambda *_: None)
        (self.tmp / "home" / "tasks" / "toy" / "prompt.md").write_text("fix it\n")
        code, out, err = self.run_cli("matrix", "--tasks", "toy", "--contestants", "stub-lazy,stub-solver", "--repeats", "2", "--ledger-cap", "1")
        self.assertEqual(code, 0, err)
        self.assertEqual(out.count("passed=True"), 2)
        self.assertEqual(out.count("passed=False"), 2)


class StartTest(Env):
    def args(self, **kw):
        base = dict(repo=None, commit=None, task=None, agents=None, prompt=None, check=UNITTEST, setup=None, repeats=1, ledger_cap=1.0,
                    tasks_dir=None, html="results.html", no_open=True, yes=True)
        return Namespace(**(base | kw))

    def test_flags_answer_every_question(self):
        repo, sha = self.toy()
        code, out, err = self.run_cli("start", "--repo", str(repo), "--commit", sha, "--agents", "stub", "--check", UNITTEST,
                                      "--prompt", "total(None) raises TypeError", "--yes", "--no-open", "--repeats", "2")
        self.assertEqual((code, err), (0, ""), out)
        self.assertIn("Plan:", out)
        self.assertRegex(out, r"stub-solver\s+2/2 pass")
        self.assertRegex(out, r"stub-lazy\s+0/2 pass")
        self.assertIn("Same run without questions: agentbench start", out)
        self.assertTrue((self.tmp / "results.html").exists())
        prompt = (self.tmp / "home" / "tasks").glob("start-*/prompt.md")
        self.assertEqual(next(prompt).read_text(), "total(None) raises TypeError\n")

    def test_three_questions_are_asked_and_the_defaults_work(self):
        repo, sha = self.toy()
        asked, out = [], []

        def ask(q):
            asked.append(q)
            return {"1": str(repo), "2": "", "3": "stub", "4": "y"}[str(len(asked))]

        code = guided.start(self.args(yes=False), ask=ask, say=out.append, interactive=True)
        self.assertEqual(code, 0, out)
        self.assertEqual(len(asked), 4)  # repo, commit, agents, then the yes/no
        self.assertIn("1/3", asked[0])
        self.assertIn("2/3", asked[1])
        self.assertIn("3/3", asked[2])
        self.assertTrue(any(sha[:8] in line for line in out), "the fix commit is suggested")

    def test_answering_no_runs_nothing(self):
        repo, _ = self.toy()
        out = []
        code = guided.start(self.args(repo=str(repo), commit="HEAD", agents="stub", yes=False), ask=lambda q: "n", say=out.append, interactive=True)
        self.assertEqual(code, 3)
        self.assertFalse((self.tmp / "results.html").exists())
        self.assertFalse((self.tmp / "home" / "runs").exists())

    def test_i_will_write_a_task_prints_how(self):
        repo, _ = self.toy()
        out = []
        answers = iter([str(repo), "w"])
        code = guided.start(self.args(yes=False), ask=lambda q: next(answers), say=out.append, interactive=True)
        self.assertEqual(code, 0)
        self.assertIn("agentbench task from-commit", "\n".join(out))

    def test_missing_answer_without_a_terminal_names_the_flag(self):
        code, _, err = self.run_cli("start", "--repo", str(self.toy()[0]), "--agents", "stub")
        self.assertEqual(code, 2)
        self.assertIn("--commit", err)
        self.assertIn("fix:", err)

    def test_no_yes_and_no_terminal_says_to_add_yes(self):
        repo, sha = self.toy()
        code, _, err = self.run_cli("start", "--repo", str(repo), "--commit", sha, "--agents", "stub", "--check", UNITTEST)
        self.assertEqual(code, 2)
        self.assertIn("--yes", err)

    def test_agents_that_are_not_installed_block_with_the_fix_command(self):
        repo, sha = self.toy()
        code, out, err = self.run_cli("start", "--repo", str(repo), "--commit", sha, "--agents", "haiku-5-5@claude-code", "--yes")
        self.assertEqual(code, 2)
        self.assertIn("BLOCKER", out)
        self.assertIn("npm install -g @anthropic-ai/claude-code", out)
        self.assertNotIn("Traceback", err)

    def test_real_agent_through_a_fake_cli_is_gated_and_priced(self):
        self.fake_claude()
        repo, sha = self.toy()
        code, out, err = self.run_cli("start", "--repo", str(repo), "--commit", sha, "--agents", "haiku-5-5@claude-code", "--check", UNITTEST,
                                      "--yes", "--no-open")
        self.assertEqual((code, err), (0, ""), out)
        self.assertRegex(out, r"haiku-5-5@claude-code\s+FAIL")  # the fake CLI changes nothing
        self.assertIn("claude: 9.9.9", out.replace("claude 9.9.9", "claude: 9.9.9"))

    def test_the_commit_that_is_not_a_fix_is_rejected_with_a_fix_line(self):
        repo, _ = self.toy()
        first = subprocess.run(["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"], capture_output=True, text=True).stdout.strip()
        code, out, err = self.run_cli("start", "--repo", str(repo), "--commit", first, "--agents", "stub", "--yes")
        self.assertEqual(code, 2)
        self.assertIn("fix:", err)
        self.assertNotIn("Traceback", err)


class FriendlyErrorTest(Env):
    def test_failures_print_what_and_the_fix_never_a_trace(self):
        for argv in (["start", "--repo", "/definitely/not/here", "--commit", "x", "--agents", "stub"],
                     ["start", "--repo", ".", "--commit", "x", "--agents", "stub", "--ledger-cap", "0"],
                     ["plan", "--contestants", "nope", "--ledger-cap", "1"]):
            code, _, err = self.run_cli(*argv)
            self.assertNotEqual(code, 0, argv)
            self.assertNotIn("Traceback", err)
            self.assertIn("fix:", err, argv)

    def test_unexpected_errors_are_summarised_and_debug_shows_the_trace(self):
        with mock.patch.object(guided, "demo", side_effect=RuntimeError("boom")):
            code, _, err = self.run_cli("demo")
            self.assertEqual(code, 2)
            self.assertIn("boom", err)
            self.assertIn("--debug", err)
            self.assertNotIn("Traceback", err)
            with self.assertRaises(RuntimeError):
                self.run_cli("demo", "--debug")

    def test_missing_git_is_explained(self):
        what, fix = guided.friendly(FileNotFoundError(2, "No such file", "git"))
        self.assertIn("git", what)
        self.assertTrue(fix)


class TableTest(unittest.TestCase):
    def test_table_leaves_out_peeked_runs_and_sorts_best_first(self):
        def run(cid, passed, **kw):
            return {"contestant": cid, "passed": passed, "status": "ok", "wall_s": 2.0, "tokens_total": 1234, "usd_equivalent": 0.01,
                    "started": "2026-01-01T00:00:00+00:00", "peeked": False} | kw
        text = guided.table([run("b", False), run("a", True), run("c", True, peeked=True)])
        lines = text.splitlines()
        self.assertTrue(lines[2].startswith("a"))
        self.assertTrue(lines[3].startswith("b"))
        self.assertNotIn("\nc ", text)
        self.assertIn("1 run(s) left out", text)


if __name__ == "__main__":
    unittest.main()
