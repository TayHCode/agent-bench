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

from agentbench import checkfiles, cli, contestants, peek, plan, report, runner, tasks  # noqa: E402

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
        self.assertEqual({p.name for p in (clean / ".claude").iterdir()}, {"CLAUDE.md", ".credentials.json"})  # nothing else copied
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
        self.assertAlmostEqual(p["worst"], 6.0)  # 6 runs x $1 cap
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
        self.assertFalse(plan.confirm(high, stdin=io.StringIO("y\n"), out=said.append))  # not a terminal: no
        self.assertTrue(plan.confirm(high, yes=True, out=said.append))

        class Tty(io.StringIO):
            def isatty(self):
                return True
        self.assertTrue(plan.confirm(high, stdin=Tty("y\n"), out=said.append))
        self.assertFalse(plan.confirm(high, stdin=Tty("n\n"), out=said.append))
        self.assertFalse(plan.confirm(high, stdin=Tty("\n"), out=said.append))  # enter alone is no

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
        self.assertEqual((code, yes), (3, 0))  # stdin is not a terminal under test

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
        a, e = self.files("id,amount\n4,40\n3,31\n2,20.0\n1,99\n", exp)  # reordered; 2 rows wrong
        self.assertEqual(checkfiles.compare(a, e, key=("id"))[:2], (2, 4))
        self.assertEqual(checkfiles.main(a, e, key=("id"), max_wrong=2), 0)
        self.assertEqual(checkfiles.main(a, e, key=("id"), max_wrong=1), 1)

    def test_csv_missing_extra_and_duplicate_rows_count(self):
        exp = "id,v\n1,a\n2,b\n"
        a, e = self.files("id,v\n1,a\n3,c\n3,c\n", exp)
        wrong, total, notes = checkfiles.compare(a, e, key=("id"))
        self.assertEqual((wrong, total), (3, 2))  # row 2 missing, row 3 extra, row 3 duplicated
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
        self.assertFalse(tasks.run_check(task, work)[0])  # no clean.csv yet
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
        # reading about the URL in a file is a tool *result*, not something the agent did
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
        self.assertTrue("Peeked runs" in html and "runner has no telemetry or uploads" in html)  # the bring-your-own methodology, not the pilot text
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
        self.assertEqual(report.too_easy_tasks([synth("t", "a"), synth("t", "b", wall=300)]), [])  # median 165 s
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


if __name__ == "__main__":
    unittest.main()
