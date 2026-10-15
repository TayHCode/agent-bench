"""Bring your own: contestants.toml, plan, check-files, peek and too-easy flags, no-network (B2)."""

import ast
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_byo import STUB_SRC, UNITTEST, Scratch  # noqa: E402

from agentbench import checkfiles, cli, contestants, cost, peek, plan, report, runner, tasks  # noqa: E402

SRC = Path(__file__).resolve().parents[1] / "src"

TOML = '''
[contestants."cheap"]
cli = "claude-code"
model = "claude-haiku-5-5"

[contestants."strong"]
cli = "claude-code"
model = "claude-sonnet-5-5"
effort = "high"
max_usd = 0.5
max_minutes = 5
files = ["{claude_md}"]
'''


class ContestantsFileTest(Scratch):
    def write(self, text, name="contestants.toml"):
        p = self.tmp / name
        p.write_text(text)
        return p

    def setup_home(self):
        home = self.tmp / "fakehome"
        (home / ".claude").mkdir(parents=True)
        (home / ".claude" / "CLAUDE.md").write_text("Always say PINEAPPLE.\n")
        (home / ".claude" / ".credentials.json").write_text("{}")
        old = os.environ.get("HOME")
        os.environ["HOME"] = str(home)
        self.addCleanup(lambda: os.environ.__setitem__("HOME", old) if old is not None else os.environ.pop("HOME"))
        return home

    def test_loads_defaults_overrides_and_explicit_files(self):
        home = self.setup_home()
        defs, prices = contestants.load(self.write(TOML.format(claude_md=home / ".claude" / "CLAUDE.md")))
        self.assertEqual(list(defs), ["cheap", "strong"])
        self.assertEqual(defs["cheap"]["effort"], "medium")
        self.assertEqual(defs["cheap"]["files"], [])
        self.assertEqual(defs["strong"]["caps"], {"max_usd": 0.5, "max_minutes": 5})
        self.assertEqual(defs["strong"]["files"], [(home / ".claude" / "CLAUDE.md", str(Path(".claude") / "CLAUDE.md"))])
        self.assertEqual(runner.profile_caps("strong", "byo", defs), {"max_tokens": None, "max_fresh_tokens": 100_000, "max_minutes": 5, "max_usd": 0.5})
        self.assertEqual(runner.profile_caps("cheap", "byo", defs), {"max_tokens": None, "max_fresh_tokens": 100_000, "max_minutes": 10, "max_usd": 1.0})

    def test_default_caps_are_100k_fresh_tokens_1_dollar_10_minutes(self):
        self.assertEqual(runner.BYO_CAPS, {"max_tokens": None, "max_fresh_tokens": 100_000, "max_minutes": 10, "max_usd": 1.0})

    def test_mistakes_are_refused_with_a_reason(self):
        home = self.setup_home()
        config_dir = home / ".claude"
        for text, why in [
            ('[contestants.a]\ncli="claude-code"\nmodel="claude-haiku-5-5"\nefort="low"\n', "unknown key"),
            ('[contestants.a]\ncli="vim"\nmodel="x"\n', "cli must be"),
            ('[contestants.a]\ncli="codex"\n', "model is required"),
            ('[contestants.a]\ncli="codex"\nmodel="mystery-1"\n', "no price"),
            ('[contestants.a]\ncli="codex"\nmodel="gpt-6.1-sol"\neffort="extreme"\n', "effort must be"),
            ("", "defines no contestants"),
            (f'[contestants.a]\ncli="claude-code"\nmodel="claude-haiku-5-5"\nfiles=["{config_dir}/.credentials.json"]\n', "never copied"),
            (f'[contestants.a]\ncli="claude-code"\nmodel="claude-haiku-5-5"\nfiles=["{config_dir}"]\n', "not a file"),
            (f'[contestants.a]\ncli="claude-code"\nmodel="claude-haiku-5-5"\nfiles=[{{from="{config_dir}/CLAUDE.md", to="../x"}}]\n', "relative path"),
            (f'[contestants.a]\ncli="claude-code"\nmodel="claude-haiku-5-5"\nfiles=[{{from="{config_dir}/CLAUDE.md", to="{config_dir.name}/.credentials.json"}}]\n', "replace a login"),
            ('[contestants.a]\ncli="claude-code"\nmodel="claude-haiku-5-5"\nfiles=["/etc/hostname"]\n', "not under"),
            ("[contestants.a\n", "not valid TOML"),
        ]:
            with self.subTest(why=why), self.assertRaisesRegex(contestants.ContestantsError, why):
                contestants.load(self.write(text))

    def test_prices_table_adds_a_model_and_leaves_the_builtin_table_alone(self):
        defs, prices = contestants.load(self.write(
            '[contestants.n]\ncli="codex"\nmodel="new-1"\n[prices."new-1"]\ninput=1.0\noutput=5.0\ncache_read=0.1\ncache_write=1.25\n'))
        self.assertIn("new-1", prices["models"])
        self.assertNotIn("new-1", runner.load_prices()["models"])

    def test_config_files_are_copied_into_the_clean_home_and_never_through_the_login_link(self):
        home = self.setup_home()
        defs, prices = contestants.load(self.write(TOML.format(claude_md=home / ".claude" / "CLAUDE.md")))
        self.assertIn("user", runner.claude_command(defs["strong"], 1)[runner.claude_command(defs["strong"], 1).index("--setting-sources") + 1])
        self.assertEqual(runner.claude_command(defs["cheap"], 1)[runner.claude_command(defs["cheap"], 1).index("--setting-sources") + 1], "")
        run_dir = self.tmp / "rd"
        clean = runner.make_clean_home(run_dir)
        creds_before = (home / ".claude" / ".credentials.json").read_text()
        runner.install_config_files(defs["strong"]["files"], clean)
        self.assertEqual((clean / ".claude" / "CLAUDE.md").read_text(), "Always say PINEAPPLE.\n")
        self.assertEqual({p.name for p in (clean / ".claude").iterdir()}, {"CLAUDE.md", ".credentials.json"})
        self.assertEqual((home / ".claude" / ".credentials.json").read_text(), creds_before)

    def test_a_user_contestant_runs_end_to_end_under_the_byo_profile(self):
        self.setup_home()
        defs, prices = contestants.load(self.write(TOML.format(claude_md=self.tmp / "fakehome" / ".claude" / "CLAUDE.md")))
        repo, sha = self.toy()
        _, folder = self.build(repo, sha)
        (folder / "prompt.md").write_text("total(None) crashes\n")
        self.stub(fix_dir=str(folder / "gold"))
        rec = runner.run("toy-null-total", "strong", self.tmp / "runs", self.tmp / "tasks", profile="byo", contestants=defs, prices=prices)
        self.assertTrue(rec["passed"])
        self.assertEqual(rec["cap_profile"], "byo")
        self.assertEqual((rec["caps"]["max_usd"], rec["caps"]["max_minutes"], rec["caps"]["max_fresh_tokens"]), (0.5, 5, 100_000))
        self.assertEqual(rec["effort"], "high")
        self.assertNotIn(str(self.tmp), json.dumps(rec))


class PlanTest(unittest.TestCase):
    def prices(self):
        return runner.load_prices()

    def test_refuses_without_a_ledger_cap(self):
        with self.assertRaisesRegex(plan.PlanError, "--ledger-cap"):
            plan.make_plan(["t"], ["haiku-5-5@claude-code"], None, self.prices(), "byo", 1, None)

    def test_runs_expected_and_worst_case(self):
        p = plan.make_plan(["a", "b", "c"], ["haiku-5-5@claude-code", "sonnet-5-5@claude-code"], None, self.prices(), "byo", 1, 5.0)
        self.assertEqual(p["runs"], 6)
        self.assertAlmostEqual(p["worst"], 6.0)
        self.assertAlmostEqual(p["ceiling"], 5.0)  # the ledger cap bounds the spend
        haiku = plan.expected_each("haiku-5-5@claude-code", runner.CONTESTANTS["haiku-5-5@claude-code"], self.prices(), [])[0]
        sonnet = plan.expected_each("sonnet-5-5@claude-code", runner.CONTESTANTS["sonnet-5-5@claude-code"], self.prices(), [])[0]
        self.assertAlmostEqual(haiku, 0.0058, places=4)
        self.assertAlmostEqual(sonnet, 0.116, places=3)
        self.assertAlmostEqual(p["expected"], 3 * (haiku + sonnet))
        self.assertIn("6 runs", plan.display_plan(p))

    def test_expected_uses_the_median_of_your_earlier_runs(self):
        past = [{"contestant": "x", "status": "ok", "usd_equivalent": v} for v in (0.1, 0.5, 0.2)] + [{"contestant": "x", "status": "error", "usd_equivalent": 9}]
        each, src = plan.expected_each("x", {"price_model": "claude-haiku-5-5"}, self.prices(), past)
        self.assertEqual((each, src), (0.2, "median of your 3 earlier run(s)"))

    def test_asks_above_two_dollars_and_is_silent_below(self):
        low = {"ceiling": 1.5}
        high = {"ceiling": 3.0}
        said = []
        self.assertTrue(plan.confirm(low, out=said.append))
        self.assertFalse(plan.confirm(high, stdin=io.StringIO("y\n"), out=said.append))
        self.assertTrue(plan.confirm(high, yes=True, out=said.append))

        class Tty(io.StringIO):
            def isatty(self):
                return True
        self.assertTrue(plan.confirm(high, stdin=Tty("y\n"), out=said.append))
        self.assertFalse(plan.confirm(high, stdin=Tty("n\n"), out=said.append))
        self.assertFalse(plan.confirm(high, stdin=Tty("\n"), out=said.append))

    def test_unpriced_model_is_named(self):
        defs = {"m": {"cli": "codex", "model": "zz", "price_model": "zz", "effort": "medium", "caps": {}}}
        with self.assertRaisesRegex(plan.PlanError, "zz"):
            plan.make_plan(["t"], ["m"], defs, self.prices(), "byo", 1, 1.0)


class MatrixCliTest(Scratch):
    def home(self):
        os.environ["AGENTBENCH_HOME"] = str(self.tmp / "home")
        self.addCleanup(os.environ.pop, "AGENTBENCH_HOME", None)
        for t in ("a-task", "b-task", "c-task", "d-task"):
            (self.tmp / "home" / "tasks" / t).mkdir(parents=True)
            (self.tmp / "home" / "tasks" / t / "task.toml").write_text('id = "x"\n')

    def test_plan_without_ledger_cap_is_refused_and_default_matrix_is_3_tasks_x_2_contestants_x_1(self):
        self.home()
        self.assertEqual(cli.main(["plan"]), 2)
        said = io.StringIO()
        old, sys.stdout = sys.stdout, said
        try:
            code = cli.main(["plan", "--ledger-cap", "1"])
        finally:
            sys.stdout = old
        self.assertEqual(code, 0)
        text = said.getvalue()
        self.assertIn("3 task(s) x 2 contestant(s) x 1 repeat(s) = 6 runs", text)
        self.assertIn("a-task, b-task, c-task", text)
        self.assertNotIn("d-task", text)
        self.assertIn("100,000 fresh tokens", text.replace("100000", "100,000"))

    def test_a_plan_over_two_dollars_is_declined_without_yes(self):
        self.home()
        old, sys.stdout = sys.stdout, io.StringIO()
        try:
            code = cli.main(["plan", "--ledger-cap", "5"])
            yes = cli.main(["plan", "--ledger-cap", "5", "--yes"])
        finally:
            sys.stdout = old
        self.assertEqual((code, yes), (3, 0))

    def test_matrix_runs_tasks_by_contestants_by_repeats_and_uses_user_defs(self):
        calls = []

        def fake_run(task, cid, out_dir, tasks_dir, caps, profile="m2", contestants=None, prices=None):
            calls.append((task, cid, profile, sorted(contestants)))
            d = Path(out_dir) / f"r{len(calls)}"
            d.mkdir(parents=True)
            rec = {"usd_equivalent": 0.01, "status": "ok", "passed": True, "wall_s": 1, "tokens_total": 1}
            (d / "run.json").write_text(json.dumps(rec))
            return rec
        defs = {"a": {"cli": "codex", "model": "m", "price_model": "claude-haiku-5-5", "effort": "medium", "caps": {}},
                "b": {"cli": "codex", "model": "m", "price_model": "claude-haiku-5-5", "effort": "medium", "caps": {}}}
        code = cli.run_matrix(["t1", "t2"], ["a", "b"], self.tmp / "o", None, 10.0, fake_run, profile="byo", defs=defs, prices={}, repeats=2)
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 8)
        self.assertEqual(calls[0], ("t1", "a", "byo", ["a", "b"]))


class CheckFilesTest(Scratch):
    def files(self, actual, expected, ext="csv"):
        a, e = self.tmp / f"actual.{ext}", self.tmp / f"expected.{ext}"
        a.write_text(actual)
        e.write_text(expected)
        return str(a), str(e)

    def test_csv_keyed_rows_and_the_max_wrong_boundary(self):
        exp = "id,amount\n1,10\n2,20\n3,30\n4,40\n"
        a, e = self.files("id,amount\n4,40\n3,31\n2,20.0\n1,99\n", exp)
        self.assertEqual(checkfiles.compare(a, e, key=("id"))[:2], (2, 4))
        self.assertEqual(checkfiles.main(a, e, key=("id"), max_wrong=2), 0)
        self.assertEqual(checkfiles.main(a, e, key=("id"), max_wrong=1), 1)

    def test_csv_missing_extra_and_duplicate_rows_count(self):
        exp = "id,v\n1,a\n2,b\n"
        a, e = self.files("id,v\n1,a\n3,c\n3,c\n", exp)
        wrong, total, notes = checkfiles.compare(a, e, key=("id"))
        self.assertEqual((wrong, total), (3, 2))
        self.assertTrue(any("missing" in n for n in notes))

    def test_csv_without_key_compares_by_position_and_numbers_as_numbers(self):
        a, e = self.files("x\n1.0\n2\n", "x\n1\n2\n")
        self.assertEqual(checkfiles.compare(a, e)[0], 0)
        a, e = self.files("x\n1\n", "x\n1\n2\n")
        self.assertEqual(checkfiles.compare(a, e)[0], 1)

    def test_csv_wrong_columns_fail_everything(self):
        a, e = self.files("id,w\n1,a\n", "id,v\n1,a\n")
        self.assertEqual(checkfiles.compare(a, e, key=("id"))[0], 1)

    def test_json_objects_and_nested_values(self):
        a, e = self.files('{"a": 1, "b": [1, 2, 3], "c": {"d": "x"}}', '{"a": 1.0, "b": [1, 2, 4], "c": {"d": "y"}}', "json")
        self.assertEqual(checkfiles.compare(a, e)[0], 2)
        a, e = self.files('[{"id": 1, "v": 2}, {"id": 2, "v": 3}]', '[{"id": 2, "v": 3}, {"id": 1, "v": 5}]', "json")
        self.assertEqual(checkfiles.compare(a, e, key=("id"))[0], 1)

    def test_text_counts_differing_lines_ignoring_trailing_space_and_line_endings(self):
        a, e = self.files("one  \r\ntwo\nthree\n", "one\ntwo\nTHREE\n", "txt")
        self.assertEqual(checkfiles.compare(a, e)[0], 1)

    def test_missing_output_file_and_bad_json_fail_cleanly(self):
        _, e = self.files("", "x\n1\n")
        self.assertEqual(checkfiles.main(str(self.tmp / "nope.csv"), e), 1)
        a, e = self.files("{oops", "{}", "json")
        self.assertEqual(checkfiles.main(a, e), 1)

    def test_cli_and_use_as_a_task_check(self):
        a, e = self.files("id,v\n1,a\n", "id,v\n1,a\n")
        r = subprocess.run([sys.executable, "-m", "agentbench.cli", "check-files", a, e, "--key", "id"], capture_output=True, text=True,
                           env=os.environ | {"PYTHONPATH": str(SRC)})
        self.assertEqual(r.returncode, 0, r.stdout)
        # a task whose check is `agentbench check-files ...` finds this install without agentbench on PATH
        root = self.tmp / "tasks" / "d1"
        (root / "repo").mkdir(parents=True)
        (root / "repo" / "in.txt").write_text("x\n")
        (root / "hidden").mkdir()
        (root / "hidden" / "expected.csv").write_text("id,v\n1,a\n")
        (root / "prompt.md").write_text("write clean.csv\n")
        (root / "task.toml").write_text('id = "d1"\ntitle = "t"\nprompt = "prompt.md"\ncheck = ["agentbench", "check-files", "clean.csv", "tests_hidden/expected.csv", "--key", "id"]\n')
        task = tasks.load_task("d1", self.tmp / "tasks")
        work = self.tmp / "w"
        tasks.prepare_workdir(task, work)
        self.assertFalse(tasks.run_check(task, work)[0])
        (work / "clean.csv").write_text("id,v\n1,a\n")
        self.assertTrue(tasks.run_check(task, work)[0])


def tool_use(cmd):
    return json.dumps({"type": "assistant", "message": {"id": "1", "content": [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}})


class PeekTest(Scratch):
    def task(self, remote="git" + "@" + "github.com:Acme/secret-app.git"):
        root = self.tmp / "tasks" / "p1"
        root.mkdir(parents=True, exist_ok=True)
        (root / "manifest.toml").write_text(f'fix_commit = "3f9a2c1d4e5f60718293a4b5c6d7e8f901234567"\nremote_url = "{remote}"\n')
        return {"root": root, "prompt_text": "Fix the bug in checkout.\n"}

    def scan(self, *events, task=None):
        t = task or self.task()
        p = self.tmp / "t.jsonl"
        p.write_text("\n".join(events) + "\n")
        return peek.scan_transcript(p, t)

    def test_each_sign(self):
        t = self.task()
        root = str(t["root"])
        self.assertEqual(self.scan(tool_use(f"ls {root}"), task=t), ["task folder"])
        self.assertEqual(self.scan(tool_use("cat ../hidden/test.py")), ["hidden/"])
        self.assertEqual(self.scan(tool_use("diff gold/cart.py cart.py")), ["gold/"])
        self.assertEqual(self.scan(tool_use("git show 3f9a2c1")), ["fix commit SHA"])
        self.assertEqual(self.scan(tool_use("gh pr list")), ["gh"])
        self.assertEqual(self.scan(tool_use("git fetch https://github.com/acme/secret-app")), ["repo URL"])
        self.assertEqual(self.scan(tool_use("git fetch git" + "@" + "github.com:Acme/secret-app.git")), ["repo URL"])

    def test_task_folder_is_recognised_by_its_resolved_path_too(self):
        # macOS temp folders live behind a symlink (/var -> /private/var); an agent may see either spelling
        real = self.tmp / "real"
        real.mkdir()
        link = self.tmp / "link"
        link.symlink_to(real)
        (real / "manifest.toml").write_text("")
        t = {"root": link, "prompt_text": ""}
        self.assertEqual(self.scan(tool_use(f"ls {real.resolve()}"), task=t), ["task folder"])
        self.assertEqual(self.scan(tool_use(f"ls {link}"), task=t), ["task folder"])

    def test_no_false_positives_for_ordinary_work(self):
        self.assertEqual(self.scan(tool_use("python3 -m unittest discover -s tests_hidden"), tool_use("cat though.txt"), tool_use("git log --oneline"),
                                   tool_use("git show abc1234")), [])

        result = json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "content": "homepage: github.com/acme/secret-app gh pr hidden/"}]}})
        text = json.dumps({"type": "assistant", "message": {"id": "2", "content": [{"type": "text", "text": "see gh pr and hidden/ and gold/"}]}})
        self.assertEqual(self.scan(result, text), [])

    def test_the_prompt_itself_is_not_a_peek(self):
        t = self.task()
        t["prompt_text"] = "Look at gold/ and hidden/ and gh pr, said the prompt."
        self.assertEqual(self.scan(tool_use("echo " + t["prompt_text"]), task=t), [])

    def test_codex_command_events_count_and_their_output_does_not(self):
        cmd = json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": "gh api repos/x", "aggregated_output": "gold/"}})
        agent = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "I will not run gh pr"}})
        self.assertEqual(self.scan(cmd, agent), ["gh"])

    def test_builtin_tasks_use_the_manifest_source_repo(self):
        t = {"root": tasks.DEFAULT_TASKS / "humanize-intcomma-overflow", "prompt_text": ""}
        self.assertEqual(self.scan(tool_use("git clone https://github.com/python-humanize/humanize"), task=t), ["repo URL"])

    def test_a_peeking_run_is_flagged_in_the_record_and_left_out_of_the_report(self):
        repo, sha = self.toy()
        _, folder = self.build(repo, sha)
        (folder / "prompt.md").write_text("total(None) crashes\n")
        self.stub(fix_dir=str(folder / "gold"), command="cat ../../../tasks/toy-null-total/gold/cart.py && gh pr list")
        rec = runner.run("toy-null-total", "haiku-5-5@claude-code", self.tmp / "runs", self.tmp / "tasks", profile="byo")
        self.assertTrue(rec["passed"])
        self.assertTrue(rec["peeked"])
        self.assertEqual(rec["peek_signs"], ["gh", "gold/"])
        self.stub(fix_dir=str(folder / "gold"))
        clean = runner.run("toy-null-total", "sonnet-5-5@claude-code", self.tmp / "runs", self.tmp / "tasks", profile="byo")
        self.assertFalse(clean["peeked"])
        md = report.display_markdown(report.load_runs(self.tmp / "runs"), self.tmp / "tasks")
        self.assertIn("Peeked runs (left out of every table)", md)
        self.assertEqual(report.standings(report.split_peeked(report.load_runs(self.tmp / "runs"))[0])[0]["contestant"], "sonnet-5-5@claude-code")
        self.assertEqual(len(report.standings(report.split_peeked(report.load_runs(self.tmp / "runs"))[0])), 1)
        html = report.display_html(report.load_runs(self.tmp / "runs"), self.tmp / "tasks")
        self.assertTrue("Peeked runs" in html and "runner has no telemetry or uploads" in html)
        self.assertNotIn("owner", html)


def synth(task, cid, passed=True, wall=30.0, fresh=10_000, status="ok", **kw):
    return {"task": task, "contestant": cid, "model": "m", "cli": "x", "effort": "medium", "status": status, "passed": passed and status == "ok",
            "wall_s": wall, "tokens_total": fresh * 5, "tokens_fresh": fresh, "usd_equivalent": 0.01, "cap_reason": None, "started": "t",
            "price_table": "2026-10-09", "effort_seen_in_session": ["medium"], "caps": {"max_usd": 1}, "cap_profile": "byo",
            "check_passed_even_if_capped": passed, "check_output_tail": "", "diff": {"files_changed": 1, "lines_added": 1, "lines_removed": 0, "files": []}} | kw


class TooEasyTest(unittest.TestCase):
    def test_flag_needs_all_passed_none_capped_short_and_cheap_and_two_contestants(self):
        easy = [synth("t", "a"), synth("t", "b")]
        self.assertEqual(report.too_easy_tasks(easy), ["t"])
        self.assertEqual(report.too_easy_tasks([synth("t", "a"), synth("t", "b", passed=False)]), [])
        self.assertEqual(report.too_easy_tasks([synth("t", "a"), synth("t", "b", status="capped")]), [])
        self.assertEqual(report.too_easy_tasks([synth("t", "a"), synth("t", "b", wall=300)]), [])
        self.assertEqual(report.too_easy_tasks([synth("t", "a"), synth("t", "b", fresh=90_000)]), [])
        self.assertEqual(report.too_easy_tasks([synth("t", "a"), synth("t", "a")]), [])  # one contestant cannot be separated from itself
        self.assertEqual(report.too_easy_tasks(easy + [synth("u", "a"), synth("u", "b", passed=False)]), ["t"])

    def test_report_says_so(self):
        runs = [synth("t", "a"), synth("t", "b")]
        self.assertIn("too easy: does not separate contestants", report.display_markdown(runs))
        self.assertIn("too easy: does not separate contestants", report.display_html(runs))
        self.assertNotIn("too easy", report.display_markdown([synth("t", "a"), synth("t", "b", passed=False)]))


class NoNetworkTest(Scratch):
    NET_MODULES = {"socket", "urllib", "http", "requests", "ssl", "ftplib", "smtplib", "xmlrpc", "telnetlib", "asyncio", "aiohttp", "httpx", "webbrowser"}

    def test_no_module_of_agentbench_imports_anything_that_talks_to_a_network(self):
        for path in (SRC / "agentbench").glob("*.py"):
            if path.name == "judge_gemini.py":
                continue  # the optional judge backend: used only with --judge gemini
            for node in ast.walk(ast.parse(path.read_text())):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
                for n in names:
                    self.assertNotIn(n.split(".")[0], self.NET_MODULES, f"{path.name} imports {n}")

    def _task(self):
        repo, sha = self.toy()
        _, folder = self.build(repo, sha)
        (folder / "prompt.md").write_text("total(None) crashes\n")
        return folder

    def test_a_stub_contestant_completes_when_every_socket_connection_fails(self):
        folder = self._task()
        self.stub(fix_dir=str(folder / "gold"))
        real = socket.socket.connect

        def refuse(self, *a, **k):
            raise OSError("network is off")
        socket.socket.connect = refuse
        self.addCleanup(setattr, socket.socket, "connect", real)
        rec = runner.run("toy-null-total", "haiku-5-5@claude-code", self.tmp / "runs", self.tmp / "tasks")
        self.assertTrue(rec["passed"])
        self.assertEqual(rec["status"], "ok")

    def test_a_stub_contestant_completes_in_an_empty_network_namespace(self):
        unshare = shutil.which("unshare")
        if not unshare:
            self.skipTest("unshare is not installed")
        probe = subprocess.run([unshare, "-rn", sys.executable, "-c",
                                "import socket,sys\ntry:\n socket.create_connection(('1.1.1.1', 53), timeout=2)\nexcept OSError: sys.exit(0)\nsys.exit(9)"],
                               capture_output=True, text=True)
        if probe.returncode != 0:
            self.skipTest(f"unshare -rn is not permitted or does not cut the network here (rc={probe.returncode})")
        folder = self._task()
        stub = self.stub(fix_dir=str(folder / "gold"))
        r = subprocess.run([unshare, "-rn", sys.executable, "-m", "agentbench.cli", "run", "--task", "toy-null-total", "--contestant",
                            "haiku-5-5@claude-code", "--out", str(self.tmp / "runs"), "--tasks-dir", str(self.tmp / "tasks")],
                           capture_output=True, text=True, env=os.environ | {"PYTHONPATH": str(SRC), "AGENTBENCH_CLAUDE_BIN": str(stub)})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("passed=True", r.stdout)


class AuditRunnerRegressionTest(Scratch):
    def config(self, extra=""):
        path = self.tmp / "contestants.toml"
        path.write_text('[contestants.mine]\ncli="claude-code"\nmodel="claude-haiku-5-5"\n' + extra)
        return path

    def test_file_contestant_run_plan_matrix_under_every_profile(self):
        from contextlib import redirect_stdout, redirect_stderr
        fixture = Path(__file__).parent / "fixtures"
        self.stub(fix_dir=str((fixture / "median-bug/gold").resolve()))
        path = self.config()
        for profile in runner.PROFILES:
            common = ["--contestants-file", str(path), "--tasks-dir", str(fixture), "--profile", profile]
            for command in ("run", "plan", "matrix"):
                output = io.StringIO()
                args = [command, "--task", "median-bug", "--out", str(self.tmp / f"{profile}-{command}")] + common
                args += ["--contestant", "mine"] if command == "run" else ["--contestants", "mine", "--ledger-cap", "1"]
                with self.subTest(profile=profile, command=command), redirect_stdout(output), redirect_stderr(output):
                    self.assertEqual(cli.main(args), 0, output.getvalue())

        with redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["run", "--task", "median-bug", "--contestant", "mine", "--contestants-file", str(path),
                                       "--tasks-dir", str(fixture), "--out", str(self.tmp / "default")]), 0)

    def test_file_contestant_plan_and_report_describe_both_token_guards(self):
        defs, prices = contestants.load(self.config())
        for profile in ("m2", "m3"):
            value = plan.make_plan(["synthetic-task"], ["mine"], defs, prices, profile, 1, 1)
            text = plan.display_plan(value)
            self.assertIn("100,000 fresh tokens", text)
            run = {"cap_profile": profile, "caps": value["rows"][0]["caps"]}
            description = report.profile_desc(run)
            self.assertIn(f"{profile}: 100k fresh tokens", description)
            if profile == "m3":
                self.assertIn("400,000 total tokens", text)
                self.assertIn("400k total tokens", description)
            else:
                self.assertNotIn("total tokens", text)
                self.assertNotIn("total tokens", description)
            heading = report.leaderboard_groups([run])[0][0]
            self.assertIn("see the Cap profile column", heading)
            self.assertNotIn("cap on total tokens", heading)

    def test_invalid_caps_from_api_cli_and_toml_never_launch(self):
        from contextlib import redirect_stderr
        from unittest.mock import patch
        from agentbench.stream import CapError, Meter
        fixture = Path(__file__).parent / "fixtures"
        self.stub(tokens=5_000_000)
        path = self.config()
        for key in ("max_tokens", "max_fresh_tokens", "max_usd", "max_minutes"):
            for value in (0, -1, float("nan"), float("inf")):
                with self.subTest(key=key, value=value), patch("agentbench.runner.subprocess.Popen") as launch:
                    with self.assertRaisesRegex(CapError, "positive finite"):
                        runner.run("median-bug", "haiku-5-5@claude-code", self.tmp / "runs", fixture,
                                   {key: value, **({"max_fresh_tokens": None} if key == "max_usd" else {})}, profile="m4")
                    launch.assert_not_called()
            for value in (0, -1):
                with self.subTest(key=key, source="CLI"), redirect_stderr(io.StringIO()) as output:
                    code = cli.main(["run", "--task", "median-bug", "--contestant", "mine", "--contestants-file", str(path),
                                     "--tasks-dir", str(fixture), "--" + key.replace("_", "-"), str(value)])
                    self.assertEqual(code, 2)
                    self.assertIn("positive finite", output.getvalue())
                with self.assertRaisesRegex(contestants.ContestantsError, "positive finite"):
                    contestants.load(self.config(f"{key} = {value}\n"))
                path = self.config()
        for kwargs in ({"max_tokens": 0}, {"max_fresh": 0}, {"max_usd": 0}):
            args = {"max_tokens": None, "max_usd": None, "max_fresh": None} | kwargs
            with self.assertRaisesRegex(CapError, "positive finite"):
                Meter().breach(**args)

    def test_tiny_remaining_ledger_is_positive_and_invalid_ledgers_are_refused(self):
        from agentbench.stream import CapError
        seen = []
        def fake(task, cid, out, tasks_dir, caps, **kwargs):
            seen.append(caps["max_usd"])
            return {"usd_equivalent": 0, "status": "ok", "passed": True, "wall_s": 0, "tokens_total": 0}
        defs, prices = contestants.load(self.config())
        self.assertEqual(cli.run_matrix("t", ["mine"], self.tmp / "out", None, 0.00001, runner_run=fake,
                                        profile="m4", defs=defs, prices=prices, say=lambda msg: None), 0)
        self.assertEqual(seen, [0.00001])
        for value in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(CapError):
                cli.run_matrix("t", ["mine"], self.tmp / "out", None, value, runner_run=fake)
            with self.assertRaises(plan.PlanError):
                plan.make_plan(["t"], ["mine"], defs, prices, "m4", 1, value)

    def test_unpriced_usage_and_non_object_json_are_supervised_and_recorded(self):
        fixture = Path(__file__).parent / "fixtures"
        self.stub(model="synthetic-unpriced", tokens=1_000_000, json_noise=[1, [], None], sleep_after_usage=60)
        rec = runner.run("median-bug", "haiku-5-5@claude-code", self.tmp / "runs", fixture,
                         caps={"max_usd": 0.01, "max_fresh_tokens": None}, profile="m4")
        self.assertEqual(rec["status"], "capped")
        self.assertIn("cannot price", rec["cap_reason"])
        self.assertEqual(rec["unpriced_models"], ["synthetic-unpriced"])
        self.assertLess(rec["wall_s"], 10)
        self.assertEqual(len(list((self.tmp / "runs").glob("*/run.json"))), 1)
        from agentbench.stream import CodexMeter, Meter
        meter = CodexMeter(costs := cost.load_prices(), "synthetic-unpriced")
        for event in (1, [], None):
            meter.feed(event)
            Meter(costs).feed(event)
        meter.total = {"input_tokens": 1_000_000}
        self.assertIn("cannot price", meter.breach(None, 0.01))

    def test_matrix_stops_on_unpriced_usage_before_another_run(self):
        defs, prices = contestants.load(self.config())
        calls = []
        def fake(task, cid, out, tasks_dir, caps, **kwargs):
            calls.append(cid)
            return {"usd_equivalent": 0, "status": "capped", "passed": False, "wall_s": 0, "tokens_total": 1_000_000,
                    "unpriced_models": ["synthetic-unpriced"]}
        self.assertEqual(cli.run_matrix("t", ["mine"], self.tmp / "out", None, 1, runner_run=fake, repeats=2,
                                        profile="m4", defs=defs, prices=prices, say=lambda msg: None), 2)
        self.assertEqual(calls, ["mine"])

if __name__ == "__main__":
    unittest.main()
