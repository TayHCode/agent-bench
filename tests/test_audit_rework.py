"""Offline reproductions for the final audit and adjacent report/meter paths."""

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentbench import cli, contestants, cost, runner
from agentbench.report import _conclusion_html
from test_release_docs import ROOT, ReportPage


class ConclusionRegressionTest(unittest.TestCase):
    def test_archived_capped_rows_retain_their_reason_in_html(self):
        for name in ("m2-pilot", "m3"):
            page = ReportPage((ROOT / "evidence" / f"{name}-results.html").read_text())
            rows = next(rows for heading, rows in page.tables if heading == "All runs")
            header = rows[0]
            for row in rows[1:]:
                with self.subTest(report=name, task=row[0], contestant=row[1]):
                    reason = row[header.index("Capped")]
                    outcome = row[header.index("Finished or capped")]
                    if row[header.index("Result")] == "capped":
                        self.assertEqual(outcome, "capped: " + reason)
                    else:
                        self.assertEqual(outcome, "finished")

    def test_recorded_csv_mode_declares_its_scope_and_rejects_missing_columns(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
            cli.main(["report", "--help"])
        self.assertIn("M4", output.getvalue())

    def test_recorded_csv_mode_rejects_missing_columns_with_a_specific_error(self):
        from agentbench.report import recorded_reports
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "incomplete.csv"
            path.write_text("task,result\nsynthetic-task,pass\n")
            with self.assertRaisesRegex(ValueError, "recorded results CSV missing required columns:.*cap_profile"):
                recorded_reports(path)

    def test_recorded_conclusion_heading_is_nested_under_conclusion(self):
        from agentbench.report import recorded_reports
        conclusion = (ROOT / "evidence/m4-conclusion.md").read_text()
        markdown = recorded_reports(ROOT / "evidence/results.csv", conclusion)[0]
        self.assertIn("## Conclusion\n\n### Completed M4 cells", markdown)

    def test_readme_rebuild_preserves_the_committed_conclusion_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.html"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main([
                    "report", "--results-csv", str(ROOT / "evidence/results.csv"),
                    "--html", str(output), "--conclusion", str(ROOT / "evidence/m4-conclusion.md"),
                ]), 0)
            text = output.read_text()
            self.assertEqual(text, (ROOT / "evidence/m4-results.html").read_text())
            table = next(rows for heading, rows in ReportPage(text).tables
                         if heading == "Completed M4 cells")
            self.assertEqual(len(table), 4)
            self.assertTrue(all(len(row) == 10 for row in table))

    def test_conclusion_blocks_do_not_require_empty_line_separators(self):
        lines = ["Prose before.", "## <synthetic-title>",
                 "| Task | Guard |", "|---|---|", "| left\\|right & <value> | $1 |",
                 "Prose after."]
        variants = ["\n".join(lines), "\r\n".join(lines),
                    "\n \t\n".join([lines[0], lines[1], "\n".join(lines[2:5]), lines[5]])]
        for conclusion in variants:
            with self.subTest(conclusion=repr(conclusion)):
                text = _conclusion_html(conclusion)
                page = ReportPage(text)
                self.assertEqual(page.tables, [("<synthetic-title>", [
                    ["Task", "Guard"], ["left|right & <value>", "$1"]])])
                self.assertEqual(page.paragraphs, ["Prose before.", "Prose after."])
                self.assertNotIn("<value>", text)


class PricingAliasRegressionTest(unittest.TestCase):
    def test_pricing_alias_does_not_price_other_models_or_modify_the_shared_table(self):
        from agentbench.stream import CodexMeter, Meter, with_price_model
        prices = cost.load_prices()
        effective = with_price_model(prices, "synthetic-alias", "claude-haiku-5-5")
        self.assertNotIn("synthetic-alias", prices["models"])
        for observed in ("synthetic-alias", "synthetic-other"):
            claude = Meter(effective)
            claude.add("synthetic-message", observed, {"input_tokens": 100, "output_tokens": 50})
            codex = CodexMeter(effective, "synthetic-alias")
            codex.models.add(observed)
            codex.total = {"input_tokens": 100, "output_tokens": 50}
            for meter in (claude, codex):
                with self.subTest(observed=observed, meter=type(meter).__name__):
                    if observed == "synthetic-other":
                        self.assertIn("cannot price", meter.breach(None, 1))
                    else:
                        self.assertIsNone(meter.breach(None, 1))
                        self.assertGreater(meter.usd, 0)

    def test_configured_alias_is_priced_and_guarded_in_both_cli_paths(self):
        fixture = ROOT / "tests/fixtures"
        for harness, priced_model in (("claude-code", "claude-haiku-5-5"), ("codex", "gpt-6.1-sol")):
            for limit, expected_status in ((1, "ok"), (0.000001, "capped")):
                with self.subTest(harness=harness, limit=limit), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    config = root / "contestants.toml"
                    config.write_text(f'[contestants.mine]\ncli="{harness}"\nmodel="synthetic-alias"\n'
                                      f'price_model="{priced_model}"\n')
                    defs, prices = contestants.load(config)
                    stub = root / "stub"
                    if harness == "claude-code":
                        shutil.copy(ROOT / "tests/stub_claude.py", stub)
                        Path(str(stub) + ".json").write_text(json.dumps({
                            "model": "synthetic-alias", "fix_dir": str(fixture / "median-bug/gold"),
                        }))
                        variable = "AGENTBENCH_CLAUDE_BIN"
                    else:
                        stub.write_text(f'#!{sys.executable}\n' + '''import json, os, pathlib, shutil, sys
sys.stdin.read()
shutil.copytree(''' + repr(str(fixture / "median-bug/gold")) + ''', '.', dirs_exist_ok=True)
sessions = pathlib.Path(os.environ['CODEX_HOME']) / 'sessions'
sessions.mkdir(parents=True, exist_ok=True)
events = [{'type': 'turn_context', 'payload': {'model': 'synthetic-alias', 'effort': 'medium'}},
          {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'total_token_usage':
           {'input_tokens': 1000, 'cached_input_tokens': 800, 'output_tokens': 50}}}}]
(sessions / 'rollout-synthetic.jsonl').write_text(''.join(json.dumps(e) + '\\n' for e in events))
print(json.dumps({'type': 'turn.completed', 'usage': {'input_tokens': 1000, 'output_tokens': 50}}), flush=True)
''')
                        stub.chmod(0o755)
                        variable = "AGENTBENCH_CODEX_BIN"
                    with patch.dict(os.environ, {variable: str(stub)}):
                        record = runner.run("median-bug", "mine", root / "runs", fixture,
                                            caps={"max_usd": limit}, contestants=defs, prices=prices)
                    self.assertEqual(record["status"], expected_status, record["cap_reason"])
                    self.assertTrue(record["check_passed_even_if_capped"])
                    self.assertEqual(record["unpriced_models"], [])
                    self.assertEqual(record["models_seen"], ["synthetic-alias"])
                    self.assertTrue(record["model_as_requested"])
                    expected_cost = cost.usd(priced_model, record["tokens_by_model"]["synthetic-alias"], prices)
                    self.assertEqual(record["usd_equivalent"], round(expected_cost, 5))
                    if expected_status == "capped":
                        self.assertIn("usd", record["cap_reason"])
                    self.assertNotIn("synthetic-alias", prices["models"])


class FinalUsageRegressionTest(unittest.TestCase):
    def test_exit_before_the_first_poll_still_checks_the_time_guard(self):
        from agentbench.stream import Meter
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            caps = {"max_tokens": None, "max_fresh_tokens": None, "max_usd": 1, "max_minutes": 0.01}
            proc = SimpleNamespace(stdin=io.StringIO(), stdout=io.StringIO(), wait=lambda: 0)
            with patch("agentbench.runner.time.monotonic", side_effect=[0, 1]):
                status, reason = runner.supervise(proc, Meter(cost.load_prices()), root, caps,
                                                  "synthetic prompt", root / "stdout.jsonl")
            self.assertEqual(status, "capped")
            self.assertEqual(reason, "minutes > 0.01")

    def test_usage_written_only_to_final_session_is_checked_against_every_guard(self):
        from agentbench.stream import CodexMeter, Meter
        for harness in ("claude-code", "codex"):
            for guard, limit, reason in (("max_tokens", 10, "tokens"),
                                         ("max_fresh_tokens", 10, "fresh tokens"),
                                         ("max_usd", 0.000001, "usd"),
                                         ("unknown", 1, "cannot price")):
                with self.subTest(harness=harness, guard=guard), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    model = "synthetic-other" if guard == "unknown" else "claude-haiku-5-5"
                    if harness == "claude-code":
                        meter = Meter(cost.load_prices())
                        events = [{"type": "assistant", "message": {"id": "synthetic-message",
                                  "model": model, "usage": {"input_tokens": 100, "output_tokens": 50}}}]
                    else:
                        meter = CodexMeter(cost.load_prices(), "claude-haiku-5-5")
                        events = [{"type": "turn_context", "payload": {"model": model}},
                                  {"type": "event_msg", "payload": {"type": "token_count", "info":
                                   {"total_token_usage": {"input_tokens": 100, "output_tokens": 50}}}}]
                    (root / "rollout-synthetic.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
                    caps = {"max_tokens": None, "max_fresh_tokens": None, "max_usd": 1, "max_minutes": 1}
                    if guard != "unknown":
                        caps[guard] = limit
                    proc = SimpleNamespace(stdin=io.StringIO(), stdout=io.StringIO(), wait=lambda: 0)
                    status, why = runner.supervise(proc, meter, root, caps, "synthetic prompt", root / "stdout.jsonl")
                    self.assertEqual(status, "capped")
                    self.assertIn(reason, why)


class GenericPrivacyRegressionTest(unittest.TestCase):
    def test_default_scan_covers_private_addresses_and_local_host_names(self):
        from test_export_privacy import PUBLIC_PATTERNS
        for kind, examples in {
            "private network address": ["10" + ".12.34.56", "172" + ".16.2.3", "172" + ".31.2.3", "192" + ".168.2.3"],
            "local hostname": ["synthetic-host" + ".local", "synthetic-host" + ".lan", "synthetic-host" + ".internal"],
        }.items():
            with self.subTest(kind=kind):
                self.assertIn(kind, PUBLIC_PATTERNS)
                for text in examples:
                    self.assertIsNotNone(PUBLIC_PATTERNS[kind].search(text.encode()), text)
        for text in ("127" + ".0.0.1", "1" + ".1.1.1", "172" + ".15.2.3", "172" + ".32.2.3",
                     "10" + ".1.2", "192" + ".168.1.2.3", "10" + ".999.2.3", "1.10" + ".1.2.3"):
            self.assertIsNone(PUBLIC_PATTERNS["private network address"].search(text.encode()), text)

    def test_task_inventory_distinguishes_runnable_and_license_only_directories(self):
        readme = (ROOT / "README.md").read_text()
        tasks = ROOT / "tasks"
        self.assertEqual(len(list(tasks.glob("*/task.toml"))), 9)
        retained = tasks / "scrapy-priority-queues"
        self.assertFalse((retained / "task.toml").exists())
        self.assertTrue((retained / "LICENSE-SOURCE").is_file())
        self.assertIn("licence-only", readme)
        self.assertIn("scrapy-priority-queues", readme)


if __name__ == "__main__":
    unittest.main()
