import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path

from agentbench import cost, report, runner, tasks
from agentbench.stream import CodexMeter, Meter

ROOT = Path(__file__).resolve().parents[1]

FAKE = '''#!/usr/bin/env python3
import json, shutil, sys, time
mode = "{mode}"
def emit(o): print(json.dumps(o), flush=True)
emit({{"type": "system", "subtype": "init"}})
if mode in ("fix", "budget"):
    shutil.copy("{gold}", "stats.py")
if mode == "slow":
    time.sleep(60)
n = 1_100_000 if mode == "runaway" else 1_000
reads = 900_000 if mode == "cachey" else 0  # lots of cache reads, almost nothing fresh
emit({{"type": "assistant", "message": {{"id": "m1", "model": "claude-haiku-5-5", "usage": {{
    "input_tokens": 10, "cache_creation_input_tokens": n, "cache_read_input_tokens": reads, "output_tokens": 50}}}}}})
emit({{"type": "result", "subtype": "error_max_budget_usd" if mode == "budget" else "success",
    "is_error": mode == "budget", "duration_ms": 1234, "duration_api_ms": 900,
    "total_cost_usd": 0.0003, "modelUsage": {{"claude-haiku-5-5": {{"inputTokens": 10,
    "cacheCreationInputTokens": 1000, "cacheReadInputTokens": 0, "outputTokens": 50}}}}}})
'''


def fake_cli(directory, mode):
    path = Path(directory) / f"claude-{mode}"
    path.write_text(FAKE.format(mode=mode, gold=ROOT / "tests/fixtures/median-bug/gold/stats.py"))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


class CostTest(unittest.TestCase):
    def test_haiku_sample(self):
        # Numbers from the M0 sub-agent run; orchestrator writes at 1h, sub-agent writes at 5m.
        p = cost.load_prices()["models"]["claude-haiku-5-5"]
        want = (1245 * p["input"] + 398 * p["output"] + 19937 * p["cache_read"]
                + 8976 * p["cache_write"] + 2038 * p["cache_write_5m"]) / 1e6
        self.assertAlmostEqual(want, 0.00257282, places=8)

    def test_long_context_tier(self):
        t = {"input": 1000, "output": 100}
        base = cost.usd("claude-haiku-5-5", t)
        self.assertAlmostEqual(cost.usd("claude-haiku-5-5", t, prompt_tokens=150_000), base * 5)

    def test_unknown_model(self):
        with self.assertRaises(KeyError):
            cost.usd("nope", {"input": 1})


class MeterTest(unittest.TestCase):
    def test_dedupes_message_ids_and_breaches(self):
        m = Meter()
        ev = {"type": "assistant", "message": {"id": "a", "model": "claude-haiku-5-5",
              "usage": {"input_tokens": 5, "cache_creation_input_tokens": 100, "output_tokens": 10}}}
        m.feed(ev)
        m.feed(ev)
        self.assertEqual(m.tokens, 115)
        self.assertIsNone(m.breach(1000, 1.0))
        self.assertIn("tokens", m.breach(100, 1.0))

    def test_tail_reads_subagent_session_files(self):
        # Sub-agent calls are only in the session files; a growing file must be read incrementally.
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        sub = root / "proj" / "sess" / "subagents"
        sub.mkdir(parents=True)
        line = {"type": "assistant", "message": {"id": "w1", "model": "claude-haiku-5-5", "usage": {
            "input_tokens": 1, "cache_creation_input_tokens": 100, "output_tokens": 5,
            "cache_creation": {"ephemeral_5m_input_tokens": 100, "ephemeral_1h_input_tokens": 0}}}, "perTurnEffort": "medium"}
        m = Meter(cost.load_prices())
        f = sub / "agent-1.jsonl"
        f.write_text(json.dumps(line) + "\n" + json.dumps(line)[:20])
        m.tail(root)
        self.assertEqual(m.tokens, 106)
        self.assertEqual(m.by_model()["claude-haiku-5-5"]["cache_write_5m"], 100)
        self.assertEqual(m.efforts, {"medium"})
        with open(f, "w") as out:
            out.write(json.dumps(line) + "\n" + json.dumps(line | {"message": line["message"] | {"id": "w2"}}) + "\n")
        m._offsets.clear()
        m.tail(root)
        self.assertEqual(m.tokens, 212)
        self.assertIn("tokens", m.breach(200, 1.0))

    def test_codex_meter_reads_rollout_totals_and_effort(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        (root / "2026").mkdir()
        rows = [{"type": "turn_context", "payload": {"model": "gpt-6.1-sol", "effort": "medium"}},
                {"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {
                    "input_tokens": 1000, "cached_input_tokens": 800, "cache_write_input_tokens": 0, "output_tokens": 50}}}}]
        (root / "2026" / "rollout-x.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        m = CodexMeter(cost.load_prices(), "gpt-6.1-sol")
        m.tail(root)
        self.assertEqual(m.efforts, {"medium"})
        self.assertEqual(m.by_model()["gpt-6.1-sol"], {"input": 200, "cache_write": 0, "cache_write_5m": 0, "cache_read": 800, "output": 50})
        self.assertAlmostEqual(m.usd, (200 * 2 + 800 * 0.1 + 50 * 10) / 1e6)


class TaskTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.task = tasks.load_task("median-bug", ROOT / "tests/fixtures")

    def test_hidden_fails_on_bug_and_passes_on_gold(self):
        work = Path(self.tmp) / "w"
        tasks.prepare_workdir(self.task, work)
        self.assertFalse(tasks.run_check(self.task, work)[0])
        shutil.copy(ROOT / "tests/fixtures/median-bug/gold/stats.py", work / "stats.py")
        self.assertTrue(tasks.run_check(self.task, work)[0])

    def test_workdir_is_single_commit_without_hidden_tests(self):
        work = Path(self.tmp) / "w"
        tasks.prepare_workdir(self.task, work)
        self.assertFalse((work / "tests_hidden").exists())
        import subprocess
        n = subprocess.run(["git", "-C", str(work), "rev-list", "--count", "HEAD"], capture_output=True, text=True)
        self.assertEqual(n.stdout.strip(), "1")


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def go(self, mode, **caps):
        os.environ["AGENTBENCH_CLAUDE_BIN"] = fake_cli(self.tmp, mode)
        self.addCleanup(os.environ.pop, "AGENTBENCH_CLAUDE_BIN", None)
        return runner.run("median-bug", "haiku-5-5@claude-code", out_dir=Path(self.tmp) / "runs", tasks_dir=ROOT / "tests/fixtures", caps=caps)

    def test_fix_passes_and_records_json(self):
        r = self.go("fix")
        self.assertTrue(r["passed"])
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["tokens_total"], 1060)
        self.assertGreater(r["usd_equivalent"], 0)
        self.assertEqual(r["diff"]["files_changed"], 1)
        saved = json.loads(next((Path(self.tmp) / "runs").glob("*/run.json")).read_text())
        self.assertNotIn(self.tmp, json.dumps(saved))  # no private paths in the record

    def test_relative_out_dir_gives_absolute_home(self):
        os.environ["AGENTBENCH_CLAUDE_BIN"] = fake_cli(self.tmp, "noop")
        self.addCleanup(os.environ.pop, "AGENTBENCH_CLAUDE_BIN", None)
        cwd = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, cwd)
        runner.run("median-bug", "haiku-5-5@claude-code", out_dir="rel-runs", tasks_dir=ROOT / "tests/fixtures")
        home = next(Path(self.tmp, "rel-runs").glob("*/home"))
        self.assertTrue(home.is_absolute())

    def test_task_can_raise_the_token_cap_but_an_explicit_cap_wins(self):
        tasks_dir = Path(self.tmp) / "tasks"
        shutil.copytree(ROOT / "tests/fixtures/median-bug", tasks_dir / "median-bug")
        toml = tasks_dir / "median-bug/task.toml"
        toml.write_text(toml.read_text() + "\nmax_tokens = 250000\n")
        os.environ["AGENTBENCH_CLAUDE_BIN"] = fake_cli(self.tmp, "noop")
        self.addCleanup(os.environ.pop, "AGENTBENCH_CLAUDE_BIN", None)
        out = Path(self.tmp) / "runs"
        self.assertEqual(runner.run("median-bug", "haiku-5-5@claude-code", out, tasks_dir)["caps"]["max_tokens"], 250_000)
        self.assertEqual(runner.run("median-bug", "haiku-5-5@claude-code", Path(self.tmp) / "runs2", tasks_dir, {"max_tokens": 90_000})["caps"]["max_tokens"], 90_000)

    def test_noop_fails_check(self):
        r = self.go("noop")
        self.assertEqual(r["status"], "ok")
        self.assertFalse(r["passed"])

    def test_token_cap_kills_and_marks_capped(self):
        r = self.go("runaway", max_tokens=100_000)
        self.assertEqual(r["status"], "capped")
        self.assertIn("tokens", r["cap_reason"])
        self.assertFalse(r["passed"])

    def test_cli_budget_stop_is_capped_even_below_the_local_meter_limit(self):
        r = self.go("budget", max_usd=1)
        self.assertLess(r["usd_equivalent"], r["caps"]["max_usd"])
        self.assertEqual(r["status"], "capped")
        self.assertEqual(r["cap_reason"], "CLI dollar budget exhausted ($1)")
        self.assertFalse(r["passed"])
        self.assertTrue(r["check_passed_even_if_capped"])
        saved = json.loads(next((Path(self.tmp) / "runs").glob("*/run.json")).read_text())
        self.assertEqual(saved["status"], "capped")
        self.assertEqual(report.finished_or_capped(saved), "capped: CLI dollar budget exhausted ($1)")


class FreshCapTest(unittest.TestCase):
    """M4: the token cap counts fresh tokens (input + cache writes + output), never cache reads."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def go(self, mode, profile="m4", **caps):
        os.environ["AGENTBENCH_CLAUDE_BIN"] = fake_cli(self.tmp, mode)
        self.addCleanup(os.environ.pop, "AGENTBENCH_CLAUDE_BIN", None)
        out = Path(self.tmp) / f"runs-{mode}-{profile}-{len(caps)}"
        return runner.run("median-bug", "haiku-5-5@claude-code", out_dir=out, tasks_dir=ROOT / "tests/fixtures", caps=caps, profile=profile)

    def test_meter_fresh_excludes_cache_reads_and_breach_ignores_them(self):
        m = Meter(cost.load_prices())
        m.feed({"type": "assistant", "message": {"id": "a", "model": "claude-haiku-5-5", "usage": {
            "input_tokens": 5, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 900_000, "output_tokens": 10}}})
        self.assertEqual((m.tokens, m.fresh), (900_115, 115))
        self.assertIsNone(m.breach(None, None, 300_000))
        self.assertIn("tokens 900115 > 400000", m.breach(400_000, None))
        self.assertIn("fresh tokens 115 > 100", m.breach(None, None, 100))

    def test_codex_fresh_is_uncached_input_plus_output(self):
        m = CodexMeter(cost.load_prices(), "gpt-6.1-sol")
        m.total = {"input_tokens": 1_000_000, "cached_input_tokens": 990_000, "output_tokens": 2_000}
        self.assertEqual((m.tokens, m.fresh), (1_002_000, 12_000))
        self.assertIsNone(m.breach(None, None, 300_000))
        self.assertIn("fresh tokens 12000 > 10000", m.breach(None, None, 10_000))

    def test_m4_profile_caps(self):
        want = {"haiku-5-5@claude-code": 0.30, "sol-6.1@codex": 1.20, "sonnet-5-5@claude-code": 1.50, "opus-5-5@claude-code": 3.00,
                "astra-6@codex": 4.00, "opus+sonnet-team@claude-code": 4.00, "opus+haiku-swarm@claude-code": 3.00}
        m3_dearest = {"haiku-5-5@claude-code": 0.026, "sol-6.1@codex": 0.24, "sonnet-5-5@claude-code": 0.43, "opus-5-5@claude-code": 0.94,
                      "astra-6@codex": 1.32, "opus+sonnet-team@claude-code": 0.85, "opus+haiku-swarm@claude-code": 0.62}
        for cid, usd in want.items():
            c = runner.profile_caps(cid, "m4")
            self.assertEqual((c["max_fresh_tokens"], c["max_minutes"], c["max_usd"], c["max_tokens"]), (1_000_000, 20, usd, None), cid)
            self.assertGreaterEqual(usd, 2 * m3_dearest[cid], cid)
        self.assertIsNone(runner.profile_caps("opus-5-5@claude-code", "m3")["max_fresh_tokens"])

    def test_run_with_900k_cache_reads_is_not_capped_under_m4_but_is_under_m3(self):
        r = self.go("cachey")
        self.assertEqual(r["status"], "ok")
        self.assertEqual((r["tokens_total"], r["tokens_fresh"], r["tokens_cache_read"]), (901_060, 1_060, 900_000))
        self.assertEqual(r["cap_profile"], "m4")
        self.assertIsNone(r["caps"]["max_tokens"])
        old = self.go("cachey", profile="m3")
        self.assertEqual(old["status"], "capped")
        self.assertIn("tokens", old["cap_reason"])

    def test_fresh_runaway_is_killed_by_the_fresh_cap(self):
        r = self.go("runaway", max_usd=2)
        self.assertEqual(r["status"], "capped")
        self.assertIn("fresh tokens", r["cap_reason"])
        self.assertFalse(r["passed"])

    def test_dollar_cap_still_stops_a_cache_heavy_runaway(self):
        # 900k cache reads are not "fresh", so only the dollar cap can stop this one.
        r = self.go("cachey", max_usd=0.0001)
        self.assertEqual(r["status"], "capped")
        self.assertTrue(r["cap_reason"].startswith("usd "), r["cap_reason"])

    def test_minute_cap_still_kills_a_quiet_run(self):
        import time
        t0 = time.monotonic()
        r = self.go("slow", max_minutes=0.02)
        self.assertEqual(r["status"], "capped")
        self.assertTrue(r["cap_reason"].startswith("minutes "), r["cap_reason"])
        self.assertLess(time.monotonic() - t0, 30)


class VerifyAndMatrixTest(unittest.TestCase):
    def test_verify_task_proves_start_fails_and_gold_passes(self):
        scratch = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, scratch)
        res = tasks.verify_task(tasks.load_task("median-bug", ROOT / "tests/fixtures"), scratch)
        self.assertTrue(res["start_fails"])
        self.assertTrue(res["gold_passes"])

    def test_every_pilot_task_has_the_required_files(self):
        for task_dir in sorted((ROOT / "tasks").iterdir()):
            if not (task_dir / "task.toml").is_file():  # historical licence-only directory
                continue
            with self.subTest(task=task_dir.name):
                for name in ("task.toml", "prompt.md", "manifest.toml", "LICENSE-SOURCE"):
                    self.assertTrue((task_dir / name).exists(), name)
                if (task_dir / "snapshot.toml").exists():
                    import tomllib
                    recipe = tomllib.loads((task_dir / "snapshot.toml").read_text())
                    self.assertTrue(recipe["gold_paths"])
                    self.assertTrue(recipe.get("hidden_files") or recipe.get("pristine_tests"))
                elif (task_dir / "data_recipe.toml").exists():  # data task built by its own preparer
                    self.assertTrue(any((task_dir / "hidden").iterdir()), "hidden")
                else:
                    for sub in ("repo", "hidden", "gold"):
                        self.assertTrue(any((task_dir / sub).iterdir()), sub)
                import tomllib
                m = tomllib.loads((task_dir / "manifest.toml").read_text())
                self.assertTrue(m["source_url"].startswith("https://"))
                self.assertEqual(len(m["workflow_match"]), 5)
                if (task_dir / "repo").exists():
                    self.assertNotIn(".git", [p.name for p in (task_dir / "repo").iterdir()])

    def test_every_task_manifest_records_source_date_licence_and_ai_check(self):
        import tomllib
        for task_dir in sorted((ROOT / "tasks").iterdir()):
            if not (task_dir / "task.toml").is_file():
                continue
            with self.subTest(task=task_dir.name):
                m = tomllib.loads((task_dir / "manifest.toml").read_text())
                for key in ("source_url", "licence", "base_commit", "fix_commit", "fix_merged", "fix_author",
                            "ai_authorship_check", "hidden_check", "why_it_matches_a_real_workflow"):
                    self.assertTrue(m.get(key), key)
                self.assertIs(m["fix_after_2026_06_30"], True)
                self.assertTrue(all(m["workflow_match"].values()))
                task = tomllib.loads((task_dir / "task.toml").read_text())
                self.assertTrue(any(part.startswith("tests_hidden") for part in task["check"]), task["check"])

    def test_no_task_file_is_hidden_from_git_by_an_ignore_rule(self):
        # An upstream .gitignore inside repo/ once hid a needed file (humanize _version.py), and a typeshed stub folder
        # called venv/ was hidden the same way: a fresh worktree then lacked it. Everything under tasks/ must be tracked.
        import subprocess
        out = subprocess.run(["git", "-C", str(ROOT), "status", "--short", "--ignored", "--", "tasks"],
                             capture_output=True, text=True).stdout
        ignored = [l for l in out.splitlines() if l.startswith("!!") and "__pycache__" not in l]
        self.assertEqual(ignored, [])

    def test_humanize_recipe_records_the_version_stub(self):
        import tomllib
        recipe = tomllib.loads((ROOT / "tasks/humanize-intcomma-overflow/snapshot.toml").read_text())
        self.assertTrue(recipe["version_stub"])

    def test_taskiq_template_retains_its_required_tag(self):
        import tomllib
        template = tomllib.loads((ROOT / "tasks/taskiq-lazy-logging/task.toml").read_text())
        self.assertEqual(template["git_tag"], "v0.0.1")


    def test_matrix_cuts_per_run_cap_to_ledger_and_stops_near_it(self):
        from agentbench import cli
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out)
        seen = []

        def fake_run(task, cid, out_dir, tasks_dir, caps, profile="m2"):
            seen.append((cid, caps["max_usd"]))
            d = Path(out_dir) / f"{cid}-{len(seen)}"
            d.mkdir(parents=True)
            rec = {"usd_equivalent": 0.95, "status": "ok", "passed": True, "wall_s": 1, "tokens_total": 1}
            (d / "run.json").write_text(json.dumps(rec))
            return rec

        code = cli.run_matrix("median-bug", "opus-5-5@claude-code,astra-6@codex,sol-6.1@codex", out, None, 1.0, fake_run)
        self.assertEqual(code, 2)
        self.assertEqual(seen, [("sol-6.1@codex", 0.30)])


    def test_m3_profile_raises_token_minute_and_dollar_caps(self):
        m2 = runner.profile_caps("opus-5-5@claude-code")
        m3 = runner.profile_caps("opus-5-5@claude-code", "m3")
        self.assertEqual((m2["max_tokens"], m2["max_minutes"], m2["max_usd"]), (150_000, 10, 0.75))
        self.assertEqual((m3["max_tokens"], m3["max_minutes"], m3["max_usd"]), (400_000, 20, 1.5))
        for cid in runner.CONTESTANTS:
            self.assertGreaterEqual(runner.profile_caps(cid, "m3")["max_usd"], runner.profile_caps(cid)["max_usd"])


    def test_matrix_under_m3_uses_m3_caps_and_report_reads_several_dirs(self):
        from agentbench import cli
        a, b = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, a)
        self.addCleanup(shutil.rmtree, b)
        seen = []

        def fake_run(task, cid, out_dir, tasks_dir, caps, profile="m2"):
            seen.append((cid, caps["max_usd"], profile))
            d = Path(out_dir) / "r1"
            d.mkdir(parents=True)
            rec = {"usd_equivalent": 0.01, "status": "ok", "passed": True, "wall_s": 1, "tokens_total": 1}
            (d / "run.json").write_text(json.dumps(rec))
            return rec

        cli.run_matrix("median-bug", "haiku-5-5@claude-code", a, None, 10.0, fake_run, profile="m3")
        self.assertEqual(seen, [("haiku-5-5@claude-code", 0.10, "m3")])
        (b / "r2").mkdir()
        (b / "r2" / "run.json").write_text(json.dumps({"usd_equivalent": 0.02}))
        self.assertEqual(len(report.load_runs([a, b])), 2)


    def _donee_workdir(self):
        task = tasks.load_task("irs-donee-matching")
        scratch = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, scratch)
        tasks.prepare_workdir(task, scratch / "w")
        tasks.apply_gold(task, scratch / "w")
        return task, scratch / "w"


    def test_donee_check_allows_three_wrong_rows_and_not_four(self):
        import csv
        task, work = self._donee_workdir()
        rows = list(csv.reader(open(work / "matched.csv", newline="", encoding="utf-8")))
        one_rows = [i for i, r in enumerate(rows) if i and r[4] == "one"]
        for n, expect in ((0, True), (3, True), (4, False)):
            bad = [list(r) for r in rows]
            for i in one_rows[:n]:
                bad[i][8] = "Y" if bad[i][8] == "N" else "N"
            with open(work / "matched.csv", "w", newline="", encoding="utf-8") as f:
                csv.writer(f, lineterminator="\n").writerows(bad)
            passed, out = tasks.run_check(task, work)
            self.assertEqual(passed, expect, (n, out))


    def test_donee_check_rejects_a_matcher_that_ignores_revocations_or_guesses(self):
        import csv
        task, work = self._donee_workdir()
        rows = list(csv.reader(open(work / "matched.csv", newline="", encoding="utf-8")))
        no_status = [r[:8] + ["N", ""] if i else r for i, r in enumerate(rows)]
        guess = [list(r) for r in rows]
        for r in guess[1:]:
            if r[4] == "many":
                r[3], r[4] = "00-0000000", "one"
        for name, data in (("no status", no_status), ("guessing", guess)):
            with open(work / "matched.csv", "w", newline="", encoding="utf-8") as f:
                csv.writer(f, lineterminator="\n").writerows(data)
            self.assertFalse(tasks.run_check(task, work)[0], name)


    def test_codex_command_uses_medium_effort_network_and_clean_config(self):
        c = runner.CONTESTANTS["astra-6@codex"]
        cmd = runner.codex_command(c, "/w")
        self.assertIn("model_reasoning_effort=medium", cmd)
        self.assertIn("sandbox_workspace_write.network_access=true", cmd)
        self.assertIn("--ignore-user-config", cmd)
        self.assertEqual(cmd[cmd.index("-m") + 1], "gpt-6-astra")


    def test_team_command_names_worker_model_and_size(self):
        cmd = runner.claude_command(runner.CONTESTANTS["opus+haiku-swarm@claude-code"], 0.7)
        agents = json.loads(cmd[cmd.index("--agents") + 1])
        self.assertEqual(agents["worker"]["model"], "claude-haiku-5-5")
        prompt = cmd[cmd.index("--append-system-prompt") + 1]
        self.assertIn("between 10 and 20", prompt)
        self.assertIn("Task", cmd[cmd.index("--tools") + 1])
        solo = runner.claude_command(runner.CONTESTANTS["opus-5-5@claude-code"], 0.7)
        self.assertNotIn("--agents", solo)
        self.assertEqual(solo[solo.index("--effort") + 1], "medium")



class ReportTest(unittest.TestCase):
    def test_table(self):
        run = {"task": "median-bug", "model": "claude-opus-5-5", "cli": "claude-code", "effort": "medium",
               "contestant": "opus-5-5@claude-code", "status": "ok", "passed": True, "wall_s": 41.2,
               "tokens_total": 12345, "usd_equivalent": 0.0123, "cap_reason": None, "started": "t",
               "price_table": "2026-10-09", "effort_seen_in_session": ["medium"], "caps": {"max_usd": 0.75}}
        team = run | {"contestant": "opus+haiku-swarm@claude-code", "started": "u", "team": {"lo": 10, "hi": 20},
                      "subagents": {"spawned": 11}, "status": "capped", "cap_reason": "tokens 9 > 5",
                      "caps": {"max_usd": 0.7}}
        out = report.display([run, team])
        self.assertIn("| median-bug | opus-5-5@claude-code | m2: no token cap, $0.75 | pass | 41 | 12,345 |  | $0.0123 |  | medium (medium) | finished |", out)

        self.assertIn("| opus+haiku-swarm@claude-code | m2: no token cap, $0.7 | capped | 41 | 12,345 |  | $0.0123 | 11 | medium (medium) | capped: tokens 9 > 5 |", out)
        self.assertEqual(report.display([]), "No runs found.\n")


def synth(task, cid, passed=True, usd=0.1, status="ok", started="t1", files=None, **kw):
    run = {"task": task, "contestant": cid, "model": "m", "cli": "x", "effort": "medium", "status": status, "passed": passed and status == "ok",
           "wall_s": 30.0, "tokens_total": 50_000, "usd_equivalent": usd, "cap_reason": "tokens 9 > 5" if status == "capped" else None,
           "started": started, "price_table": "2026-10-09", "effort_seen_in_session": ["medium"], "caps": {"max_usd": 1},
           "check_passed_even_if_capped": passed, "check_output_tail": "E   AssertionError: expected 3 got 2",
           "diff": {"files_changed": 1, "lines_added": 4, "lines_removed": 1,
                    "files": files if files is not None else [{"path": "stats.py", "added": 4, "removed": 1}]}}
    return run | kw


class CompareProfilesTest(unittest.TestCase):
    def test_m3_and_m4_side_by_side_with_missing_cells_shown(self):
        m3 = {"max_tokens": 400_000, "max_minutes": 20, "max_usd": 3}
        m4 = {"max_fresh_tokens": 300_000, "max_minutes": 20, "max_usd": 3}
        runs = [synth(t, c, caps=m3, started="a") for t in ("t1", "t2", "t3") for c in ("a@x", "b@x", "c@x", "d@x")]
        runs += [synth(t, c, caps=m4, started="b", cap_profile="m4") for t in ("t1", "t2", "t3") for c in ("a@x", "b@x", "c@x")]
        m4_1m = {"max_fresh_tokens": 1_000_000, "max_minutes": 20, "max_usd": 1.5}
        runs += [synth("t1", "a@x", caps=m4_1m, started="c", cap_profile="m4")]
        rows = report.compare_m3_m4(runs)
        self.assertEqual({t for t, *_ in rows}, {"t1", "t2", "t3"})
        self.assertEqual([r[2] for r in rows if r[:2] == ("t1", "d@x")], ["m3", "m4-300k", "m4-1000k"])
        self.assertIsNone([r[3] for r in rows if r[:3] == ("t1", "d@x", "m4-300k")][0])
        self.assertIsNone([r[3] for r in rows if r[:3] == ("t1", "d@x", "m4-1000k")][0])
        md = report.display_markdown(runs)
        self.assertIn("| t1 | d@x | m4-300k | not run |  |  |  |  |  | not run |", md)
        self.assertIn("| t1 | d@x | m4-1000k | not run |  |  |  |  |  | not run |", md)
        groups = report.leaderboard_groups(runs)
        self.assertEqual([title.split(":", 1)[0] for title, _ in groups[:2]], ["M4 rerun", "M4 rerun"])
        self.assertEqual([len(group) for _, group in groups[:2]], [9, 1])
        self.assertEqual(report.compare_m3_m4([synth("t1", "a@x", caps=m3)]), [])


class ReportPageTest(unittest.TestCase):
    def setUp(self):
        self.runs = [
            synth("median-bug", "opus-5-5@claude-code", usd=0.2, started="a"),
            synth("median-bug", "opus-5-5@claude-code", usd=0.5, started="b", passed=False),
            synth("median-bug", "haiku-5-5@claude-code", usd=0.01, started="c"),
            synth("median-bug", "opus+haiku-swarm@claude-code", usd=0.4, status="capped", started="d", team={"lo": 10, "hi": 20}, workers=7),
        ]

    def test_standings_rank_pass_rate_then_cost_per_solved(self):
        order = [s["contestant"] for s in report.standings(self.runs)]
        self.assertEqual(order, ["haiku-5-5@claude-code", "opus-5-5@claude-code", "opus+haiku-swarm@claude-code"])
        opus = report.standings(self.runs)[1]
        self.assertEqual((opus["passed"], opus["runs"]), (1, 2))
        self.assertAlmostEqual(opus["per_solved"], 0.7)
        self.assertIsNone(report.standings(self.runs)[2]["per_solved"])

    def test_spread_notes_flag_flips_and_cost_swings(self):
        notes = report.spread_notes(self.runs)
        self.assertEqual(len(notes), 1)
        self.assertIn("1/2 passed", notes[0])
        self.assertIn("2.5x", notes[0])

    def test_failure_note_says_what_it_looked_like(self):
        capped = report.failure_note(self.runs[3])
        self.assertIn("killed at the cap (tokens 9 > 5)", capped)
        self.assertIn("hidden check passed on the work left behind", capped)
        tail = "[PASS] a\n[FAIL] pyproject ruff select contains \"G\"\nselect=[]\n[PASS] b"
        self.assertIn('[FAIL] pyproject ruff select contains "G"', report.failure_note(synth("t", "c", status="capped", passed=False, check_output_tail=tail)))
        self.assertIn("ruff still reports 7 finding(s)", report.failure_note(synth("t", "c", passed=False, check_output_tail="x\nFound 7 errors.\n[PASS] y")))
        failed = report.failure_note(self.runs[1])
        self.assertIn("AssertionError: expected 3 got 2", failed)

    def test_gold_comparison_is_plain_line_counts_without_tests(self):
        gold = [{"path": "src/a.py", "added": 5, "removed": 3}]
        near = synth("t", "c", files=[{"path": "src/a.py", "added": 6, "removed": 4}, {"path": "tests/test_a.py", "added": 40, "removed": 0}])
        res = report.compare_to_gold(near, gold)
        self.assertEqual((res["mine"], res["gold"]), (10, 8))
        self.assertTrue(res["verdict"].startswith("near"))
        self.assertIn("larger", report.compare_to_gold(synth("t", "c", files=[{"path": "src/a.py", "added": 60, "removed": 0}]), gold)["verdict"])
        self.assertIn("misses 1", report.compare_to_gold(synth("t", "c", files=[{"path": "src/b.py", "added": 8, "removed": 0}]), gold)["verdict"])

    def test_lockfiles_and_manifest_ignored_gold_files_do_not_count(self):
        gold = [{"path": "src/a.py", "added": 5, "removed": 3}]
        run = synth("t", "c", files=[{"path": "src/a.py", "added": 5, "removed": 3}, {"path": "package-lock.json", "added": 1221, "removed": 0}])
        self.assertEqual(report.compare_to_gold(run, gold)["mine"], 8)
        info = report.task_info("taskiq-lazy-logging")
        self.assertIn("taskiq/acks.py", info["manifest"]["gold_comparison"]["ignore"])
        self.assertEqual(info["gold"], [])

    def test_docs_changelogs_and_data_driven_test_cases_are_not_source_lines(self):
        for path in ("docs/quickstart.rst", "CHANGES.rst", "changelog/5093.bugfix.rst"):
            self.assertTrue(tasks.is_doc_path(path), path)
        for path in ("test-data/unit/check-overloading.test", "tests/test_apply_range.py"):
            self.assertTrue(tasks.is_test_path(path), path)
        for path in ("src/werkzeug/http.py", "mypy/subtypes.py", "pyproject.toml"):
            self.assertFalse(tasks.is_doc_path(path) or tasks.is_test_path(path), path)
        info = report.task_info("werkzeug-apply-conditions")
        self.assertEqual(info["gold"], [])
        mypy = report.task_info("mypy-deferred-alias-crash")
        self.assertEqual(mypy["gold"], [])

    def test_method_notes_follow_the_data(self):
        notes = " ".join(report.method_notes("2026-10-09", 7, 1, 2))
        self.assertIn("7 tasks, and 1 to 2 runs per cell", notes)
        self.assertIn("2026-10-09", notes)
        self.assertIn("1 run per cell", " ".join(report.method_notes("p", 3, 1, 1)))

    def test_gold_diff_counts_the_real_fix_lines(self):
        files = tasks.gold_diff(tasks.load_task("median-bug", ROOT / "tests/fixtures"))
        self.assertEqual([f["path"] for f in files], ["stats.py"])
        self.assertGreater(files[0]["added"] + files[0]["removed"], 0)

    def test_html_is_one_self_contained_page_with_every_section(self):
        out = report.display_html(self.runs, conclusion="First paragraph.\n\nSecond one.")
        for heading in ("Conclusion", "Leaderboards", "Cost against outcome", "Cost per solved run", "Per task",
                        "Variance between repeats", "Failed and capped runs", "Passing diffs against the real fix",
                        "Workflow-match check", "Methodology and limits"):
            self.assertIn(f">{heading}<", out)
        self.assertIn("<svg", out)
        self.assertIn("prefers-color-scheme:dark", out)
        self.assertIn("width=device-width", out)
        self.assertIn("<p>Second one.</p>", out)
        for external in ("<script", "<link", "@import", " src=", "url(http"):
            self.assertNotIn(external, out)
        self.assertNotIn(str(Path.home()), out)  # no private paths
        self.assertIn("Opus + Haiku swarm", out)

    def test_cap_profile_is_read_from_caps_and_runs_under_different_caps_are_separate_cells(self):
        m3 = synth("t", "c@x", started="a", caps={"max_tokens": 400_000, "max_minutes": 20, "max_usd": 1.5})
        m4 = synth("t", "c@x", started="b", cap_profile="m4", tokens_fresh=50_000,
                   caps={"max_tokens": None, "max_fresh_tokens": 1_000_000, "max_minutes": 20, "max_usd": 3.0})
        pilot = synth("t", "c@x", started="c", caps={"max_tokens": 150_000, "max_minutes": 10, "max_usd": 0.75})
        self.assertEqual([report.profile_name(r) for r in (m3, m4, pilot)], ["m3", "m4-1000k", "m2"])
        self.assertEqual(report.profile_desc(m3), "m3: 400k total tokens, 20 min, $1.5")
        self.assertEqual(report.profile_desc(m4), "m4: 1000k fresh tokens, 20 min, $3")
        self.assertEqual(len(report.cells([m3, m4, pilot])), 3)
        md = report.display_markdown([m3, m4, pilot])
        self.assertIn("## Leaderboard, M4 rerun", md)
        self.assertIn("## Leaderboard, Pilot and M3", md)
        self.assertIn("m4: 1000k fresh tokens, 20 min, $3 |", md)
        self.assertIn("Finished or capped", md)
        self.assertIn("Finished or capped", report.display_html([m3, m4, pilot]))

    def test_run_table_marks_finished_and_capped_rows(self):
        finished = synth("t", "c@x", started="a", status="ok", passed=False, cap_reason=None)
        capped = synth("t", "d@x", started="b", status="capped", passed=False,
                       cap_reason="fresh tokens 1000001 > 1000000")
        md = report.display([finished, capped])
        self.assertIn("| Finished or capped |", md)
        self.assertIn("| finished |", md)
        self.assertIn("| capped: fresh tokens 1000001 > 1000000 |", md)

    def test_fresh_tokens_from_record_or_per_model_split(self):
        split = {"claude-haiku-5-5": {"input": 10, "cache_write": 100, "cache_write_5m": 5, "cache_read": 9_000, "output": 20}}
        self.assertEqual(report.fresh_tokens(synth("t", "c@x", tokens_by_model=split)), 135)
        self.assertEqual(report.fresh_tokens(synth("t", "c@x", tokens_fresh=7, tokens_by_model=split)), 7)
        self.assertIsNone(report.fresh_tokens(synth("t", "c@x")))

    def test_html_escapes_text(self):
        out = report.display_html([synth("t<b>", "x@y")])
        self.assertNotIn("t<b>", out)

    def test_markdown_has_leaderboards_and_run_table(self):
        md = report.display_markdown(self.runs)
        self.assertIn("## Leaderboard, Pilot and M3", md)
        self.assertIn("| 1 | Haiku 5.5 · Claude Code | 1/1 |", md)
        self.assertIn("## median-bug", md)
        self.assertIn("## All runs", md)

    def test_backfill_adds_files_and_workers_from_saved_checkout(self):
        import subprocess
        from agentbench.backfill import backfill
        runs = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, runs)
        d = runs / "r1"
        work = d / "work"
        tasks.prepare_workdir(tasks.load_task("median-bug", ROOT / "tests/fixtures"), work)
        (work / "stats.py").write_text((work / "stats.py").read_text() + "\n# edit\n")
        subprocess.run(["git", "-C", str(work), "add", "-A"], check=True)
        sub = d / "home" / ".claude" / "projects" / "p" / "s" / "subagents"
        sub.mkdir(parents=True)
        (sub / "agent-1.jsonl").write_text("{}\n")
        (sub / "agent-2.jsonl").write_text("{}\n")
        rec = synth("median-bug", "opus+haiku-swarm@claude-code", team={"lo": 10, "hi": 20}, started="z") | {"diff": {"files_changed": 1, "lines_added": 2, "lines_removed": 0}}
        (d / "run.json").write_text(json.dumps(rec))
        self.assertEqual(backfill(runs), 1)
        saved = json.loads((d / "run.json").read_text())
        self.assertEqual(saved["workers"], 2)
        self.assertEqual([f["path"] for f in saved["diff"]["files"]], ["stats.py"])
        self.assertEqual(backfill(runs), 0)


if __name__ == "__main__":
    unittest.main()
