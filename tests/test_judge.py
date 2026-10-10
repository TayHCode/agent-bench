"""Optional judge: blind packets, backends (stub, command, Gemini against a local recorded response), costs, caps, report column."""

import contextlib
import io
import json
import os
import shutil
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_byo import Scratch  # noqa: E402
from test_byo_b2 import synth  # noqa: E402

from agentbench import cli, judge, report, runner  # noqa: E402

HAIKU, SONNET = "haiku-5-5@claude-code", "sonnet-5-5@claude-code"
RECORDED = {"candidates": [{"content": {"role": "model", "parts": [{"text": json.dumps(
    {"scores": {"approach": 5, "minimal": 4, "no_unrelated": 5, "follows_prompt": 4}, "reason": "Fixes the None case at the source."})}]}}],
    "usageMetadata": {"promptTokenCount": 1000, "candidatesTokenCount": 40, "thoughtsTokenCount": 160}}
COMMAND = """import json, sys
p = json.load(sys.stdin)
s = 3 + p["seed"] % 2
print(json.dumps({"scores": {k: s for k in p["rubric"]}, "reason": "from " + p["id"]}))
"""


class Recorder(BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        Recorder.seen.append((self.path, dict(self.headers), json.loads(body)))
        out = json.dumps(RECORDED).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


class JudgeBase(Scratch):
    def setUp(self):
        super().setUp()
        repo, sha = self.toy()
        _, folder = self.build(repo, sha)
        (folder / "prompt.md").write_text("total(None) crashes\n")
        self.folder = folder
        extra = self.tmp / "fix2"
        shutil.copytree(folder / "gold", extra)
        (extra / "NOTES.txt").write_text("unrelated\n")
        self.runs = self.tmp / "runs"
        for cid, fix in ((HAIKU, folder / "gold"), (SONNET, extra)):
            self.stub(fix_dir=str(fix))
            runner.run("toy-null-total", cid, self.runs, self.tmp / "tasks")
        self.dirs = sorted(self.runs.glob("*/run.json"))

    def judge(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(["judge", "--runs", str(self.runs), "--tasks-dir", str(self.tmp / "tasks"), *args])
        return code, out.getvalue(), err.getvalue()

    def verdicts(self):
        return {p.parent.name: json.loads(p.read_text()) for p in self.runs.glob("*/judge.json")}


class PacketTest(JudgeBase):
    def packets(self, seed=0):
        items = judge.blinded_order(judge.finished_runs([self.runs]), seed)
        return [judge.build_packet(d, r, bid, seed, self.tmp / "tasks", 60_000) for bid, d, r in items]

    def test_packet_has_prompt_and_diff_but_no_hidden_tests_gold_names_or_paths(self):
        for pk in self.packets():
            blob = json.dumps(pk)
            self.assertIn("total(None) crashes", pk["prompt"])
            self.assertIn("prices or []", pk["diff"])
            self.assertNotIn("none_means_no_prices", blob)  # the hidden test the runner copied into work/
            self.assertNotIn("tests_hidden", blob)
            for secret in ("haiku", "sonnet", "claude-code", str(self.tmp)):
                self.assertNotIn(secret, blob.lower() if secret.islower() else blob)
            self.assertRegex(pk["id"], r"^sample-\d$")

    def test_unrelated_edit_is_visible_to_the_judge(self):
        self.assertEqual(sum("NOTES.txt" in p["diff"] for p in self.packets()), 1)

    def test_order_is_shuffled_with_a_fixed_seed_and_the_rubric_order_follows_the_seed(self):
        a = [p["id"] for p in self.packets(0)]
        self.assertEqual(a, [p["id"] for p in self.packets(0)])
        order = lambda seed: [p["prompt"].index(f"- {k}:") for p in self.packets(seed)[:1] for k in judge.RUBRIC]
        self.assertEqual(order(0), order(0))
        self.assertTrue(any(order(0) != order(s) for s in range(1, 8)))

    def test_diff_is_cut_at_the_limit(self):
        d, r = judge.finished_runs([self.runs])[0]
        self.assertIn("diff cut at 50", judge.build_packet(d, r, "sample-1", 0, self.tmp / "tasks", 50)["diff"])


class VerdictTest(unittest.TestCase):
    def test_valid_and_invalid(self):
        s, why = judge.parse_verdict('noise ```json\n{"scores": {"approach": 5, "minimal": 3.6, "no_unrelated": 1, "follows_prompt": 2}, "reason": "ok\\nline"}```')
        self.assertEqual((s["minimal"], why), (4, "ok line"))
        for bad in ("no json", '{"scores": {"approach": 5}}', '{"scores": {"approach": 9, "minimal": 1, "no_unrelated": 1, "follows_prompt": 1}}',
                    '{"scores": {"approach": true, "minimal": 1, "no_unrelated": 1, "follows_prompt": 1}}'):
            with self.assertRaises(judge.JudgeError):
                judge.parse_verdict(bad)


class StubAndCommandTest(JudgeBase):
    def test_stub_writes_judge_json_and_leaves_run_json_alone(self):
        before = {p: p.read_bytes() for p in self.dirs}
        code, out, _ = self.judge("--judge", "stub")
        self.assertEqual(code, 0, out)
        v = self.verdicts()
        self.assertEqual(len(v), 2)
        for d in v.values():
            self.assertEqual(set(d["scores"]), set(judge.RUBRIC))
            self.assertTrue(all(1 <= x <= 5 for x in d["scores"].values()))
            self.assertEqual((d["judge"]["model"], d["cost_usd"], d["secondary"]), ("stub", 0, True))
            self.assertEqual(len(d["prompt_hash"]), 16)
            self.assertNotIn("haiku", json.dumps(d))
        self.assertEqual(before, {p: p.read_bytes() for p in self.dirs})
        self.assertIn("pass/fail", out)

    def test_existing_judge_json_is_kept_unless_forced(self):
        self.judge("--judge", "stub")
        first = (next(self.runs.glob("*/judge.json"))).stat().st_mtime_ns
        self.assertIn("0 run(s) to judge", self.judge("--judge", "stub")[1])
        self.assertEqual(first, next(self.runs.glob("*/judge.json")).stat().st_mtime_ns)
        self.assertIn("2 run(s) to judge", self.judge("--judge", "stub", "--force")[1])

    def test_command_backend_gets_a_blind_packet_on_stdin(self):
        script = self.tmp / "j.py"
        script.write_text(COMMAND)
        self.assertEqual(self.judge("--judge", f"{sys.executable} {script}")[0], 0)
        for d in self.verdicts().values():
            self.assertTrue(d["reason"].startswith("from sample-"))
            self.assertEqual(d["judge"]["model"], "command:" + Path(sys.executable).name)

    def test_a_bad_answer_is_reported_and_stores_nothing(self):
        code, _, err = self.judge("--judge", f"{sys.executable} -c \"print('hello')\"")
        self.assertEqual((code, self.verdicts()), (1, {}))
        self.assertIn("no verdict JSON", err)

    def test_agreement_between_two_seeds(self):
        script = self.tmp / "j.py"
        script.write_text(COMMAND)  # scores 3 on even seeds, 4 on odd ones
        code, out, _ = self.judge("--judge", f"{sys.executable} {script}", "--agree", "2")
        self.assertEqual(code, 0, out)
        rep = json.loads((self.runs / "judge-agreement.json").read_text())
        self.assertEqual((rep["runs"], rep["item_exact_agreement"], rep["mean_abs_item_diff"]), (2, 0.0, 1.0))
        self.assertEqual(rep["runs_quality_off_by_1_or_more"], 2)
        self.assertIn("agreement over 2", out)

    def test_unknown_task_is_skipped_not_fatal(self):
        code, out, _ = self.judge("--judge", "stub", "--tasks-dir", str(self.tmp / "nowhere"))
        self.assertEqual((code, self.verdicts()), (0, {}))
        self.assertIn("skip", out)


class GeminiTest(JudgeBase):
    def setUp(self):
        super().setUp()
        Recorder.seen = []
        self.srv = HTTPServer(("127.0.0.1", 0), Recorder)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        self.cfg = self.tmp / "judge.toml"
        self.cfg.write_text(f'[gemini]\nmodel = "gemini-2.5-pro"\nbase_url = "http://127.0.0.1:{self.srv.server_port}"\nprice_in = 1.0\nprice_out = 10.0\nmax_output_tokens = 1000\n')
        os.environ["GEMINI_API_KEY"] = "test-key-123"
        self.addCleanup(os.environ.pop, "GEMINI_API_KEY", None)

    def gem(self, *args):
        return self.judge("--judge", "gemini", "--judge-file", str(self.cfg), *args)

    def test_dry_run_estimates_and_calls_nothing(self):
        code, out, _ = self.gem("--dry-run")
        self.assertEqual((code, Recorder.seen, self.verdicts()), (0, [], {}))
        self.assertRegex(out, r"estimated cost up to \$0\.0\d+")
        self.assertIn("sends the task prompt and the contestant's diff", out)

    def test_paid_judge_needs_a_cap_and_a_key(self):
        code, _, err = self.gem()
        self.assertEqual((code, Recorder.seen), (2, []))
        self.assertIn("--max-usd", err)
        del os.environ["GEMINI_API_KEY"]
        code, _, err = self.gem("--max-usd", "1")
        self.assertEqual((code, Recorder.seen), (2, []))
        self.assertIn("GEMINI_API_KEY", err)

    def test_recorded_response_gives_scores_cost_and_the_key_stays_in_the_header(self):
        code, out, _ = self.gem("--max-usd", "1")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(Recorder.seen), 2)
        path, headers, body = Recorder.seen[0]
        self.assertEqual(path, "/v1beta/models/gemini-2.5-pro:generateContent")
        self.assertEqual({k.lower(): v for k, v in headers.items()}["x-goog-api-key"], "test-key-123")
        self.assertEqual(body["generationConfig"]["maxOutputTokens"], 1000)
        self.assertNotIn("test-key-123", json.dumps(body))
        for d in self.verdicts().values():
            self.assertEqual((d["quality"], d["tokens_in"], d["tokens_out"]), (4.5, 1000, 200))
            self.assertAlmostEqual(d["cost_usd"], 1000 * 1.0 / 1e6 + 200 * 10.0 / 1e6)
            self.assertEqual(d["judge"], {"backend": "gemini", "model": "gemini-2.5-pro"})
        self.assertNotIn("test-key-123", out + "".join(p.read_text() for p in self.runs.glob("*/judge.json")))

    def test_hard_cap_stops_before_a_call_that_could_pass_it(self):
        code, out, _ = self.gem("--max-usd", "0.0001")
        self.assertEqual((code, Recorder.seen, self.verdicts()), (0, [], {}))
        self.assertIn("STOP", out)

    def test_http_error_is_reported(self):
        self.cfg.write_text(self.cfg.read_text().replace(str(self.srv.server_port), "1"))
        code, _, err = self.gem("--max-usd", "1")
        self.assertEqual((code, self.verdicts()), (1, {}))
        self.assertIn("Gemini API call failed", err)


class ReportColumnTest(unittest.TestCase):
    def runs(self, judged):
        j = {"judge": {"backend": "gemini", "model": "gemini-2.5-pro"}, "quality": 4.0}
        return [synth("t", "a", **({"judge": j} if judged else {})), synth("t", "b", **({"judge": j | {"quality": 2.0}} if judged else {}))]

    def test_column_and_footnote_only_when_a_judge_ran(self):
        for render in (report.display_markdown, report.display_html):
            plain, judged = render(self.runs(False)), render(self.runs(True))
            self.assertNotIn("Quality (judge, secondary)", plain)
            self.assertIn("Quality (judge, secondary)", judged)
            self.assertIn("gemini-2.5-pro", judged)
            self.assertIn("can be wrong", judged)
            self.assertIn("never decides pass/fail", judged)
        self.assertIn("| 4.0 |", report.display_markdown(self.runs(True)))

    def test_load_runs_attaches_judge_json(self):
        import tempfile
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        (d / "r1").mkdir()
        (d / "r1" / "run.json").write_text(json.dumps(synth("t", "a")))
        self.assertNotIn("judge", report.load_runs(d)[0])
        (d / "r1" / "judge.json").write_text(json.dumps({"quality": 3.5}))
        self.assertEqual(report.load_runs(d)[0]["judge"]["quality"], 3.5)


if __name__ == "__main__":
    unittest.main()
