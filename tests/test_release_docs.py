"""Keep the public task inventory and omitted-pilot evidence honest."""
import csv
from html.parser import HTMLParser
from pathlib import Path
import re
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReportPage(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tables = []
        self.paragraphs = []
        self.heading = ""
        self.in_heading = self.in_cell = self.in_paragraph = False
        self.header_cells = 0
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag in ("h2", "h3"):
            self.heading = ""
            self.in_heading = True
        elif tag == "table":
            self.tables.append((self.heading, []))
        elif tag == "tr":
            self.tables[-1][1].append([])
        elif tag in ("td", "th"):
            self.tables[-1][1][-1].append("")
            self.in_cell = True
            self.header_cells += tag == "th"
        elif tag == "p":
            self.paragraphs.append("")
            self.in_paragraph = True

    def handle_endtag(self, tag):
        if tag in ("h2", "h3"):
            self.in_heading = False
        elif tag in ("td", "th"):
            self.in_cell = False
        elif tag == "p":
            self.in_paragraph = False

    def handle_data(self, data):
        if self.in_heading:
            self.heading += data
        if self.in_cell:
            self.tables[-1][1][-1][-1] += data
        if self.in_paragraph:
            self.paragraphs[-1] += data


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
        self.assertEqual(len(rows), 84)
        removed = [row for row in rows if row['task'] == 'removed-pilot-task']
        self.assertTrue(removed)
        for row in removed:
            self.assertIn('removed to keep the licence trail clean', row['notes'])
            self.assertTrue(row['result'] and row['wall_s'] and row['usd_equivalent'])
        for row in rows:
            self.assertEqual(row['finished_or_capped'], 'capped' if row['cap_reason'] != 'no' else 'finished')
        completion = [row for row in rows if row['cap_profile'].startswith('m4: 1000k fresh tokens')]
        self.assertEqual(len(completion), 3)
        outcomes = {(row['task'], row['contestant']): (row['result'], row['finished_or_capped']) for row in completion}
        self.assertEqual(outcomes, {
            ('werkzeug-apply-conditions', 'astra-6@codex'): ('capped', 'capped'),
            ('mypy-deferred-alias-crash', 'astra-6@codex'): ('pass', 'finished'),
            ('mypy-deferred-alias-crash', 'opus+sonnet-team@claude-code'): ('pass', 'finished'),
        })
        self.assertAlmostEqual(sum(float(row['usd_equivalent']) for row in completion), 3.4716, places=4)
        readme = (ROOT / 'README.md').read_text()
        self.assertIn('1,000,000', readme)
        self.assertIn('M2 has 8 capped runs and M3 has 13', readme)
        self.assertNotIn('Provisional:', readme)
        self.assertIn('14 finished (11 passed and 3 failed) and two were capped', readme)
        for report in ('m2-pilot-results.md', 'm3-results.md', 'm4-results.md'):
            self.assertIn('Finished or capped', (ROOT / 'evidence' / report).read_text())


class CommittedReportTest(unittest.TestCase):
    def assert_no_markdown_table_paragraphs(self, page):
        for paragraph in page.paragraphs:
            self.assertIsNone(re.search(r"(?:^|\n)\s*\|[^\n]*\|", paragraph), paragraph)

    def test_every_markdown_run_is_inside_a_well_formed_table(self):
        import re
        for name, expected in (("m2-pilot", 49), ("m3", 68), ("m4", 84)):
            text = (ROOT / "evidence" / (name + "-results.md")).read_text()
            blocks = re.findall(r"(?:^\|[^\n]*\n)+", text + "\n", re.M)
            self.assertTrue(blocks)
            for block in blocks:
                rows = [line.strip().strip("|").split("|") for line in block.splitlines()]
                self.assertGreaterEqual(len(rows), 2, name)
                self.assertTrue(all(re.fullmatch(r"\s*:?-+:?\s*", cell) for cell in rows[1]), name)
                for row in rows:
                    self.assertEqual(len(row), len(rows[0]), name)
            all_runs = text.split("## All runs", 1)[1]
            rows = [line for line in all_runs.splitlines() if line.startswith("|")]
            self.assertEqual(len(rows) - 2, expected)
            self.assertNotIn("medium (medium) (medium)", text)

    def test_every_html_run_has_its_finished_or_capped_cell(self):
        for name, expected in (("m2-pilot", 49), ("m3", 68), ("m4", 84)):
            text = (ROOT / "evidence" / (name + "-results.html")).read_text()
            parser = ReportPage(text)
            self.assert_no_markdown_table_paragraphs(parser)
            for heading, table in parser.tables:
                for row in table:
                    self.assertEqual(len(row), len(table[0]), (name, heading))
            all_runs = next(table for heading, table in parser.tables if heading == "All runs")
            self.assertEqual(len(all_runs) - 1, expected)
            self.assertEqual(len(all_runs[0]), 12 if name == "m4" else 10)
            self.assertIn("Finished or capped", text)
            self.assertNotIn("Private;", text)
            if name != "m4":
                self.assertIn("cap-distorted", text)
                self.assertNotIn("Private pilot", text)

    def test_conclusion_is_a_real_table_in_generated_and_committed_m4_pages(self):
        from agentbench.report import recorded_reports
        conclusion = (ROOT / "evidence/m4-conclusion.md").read_text()
        rows = [[cell.strip() for cell in line.strip("|").split("|")]
                for line in conclusion.splitlines() if line.startswith("|")]
        expected = [rows[0]] + rows[2:]
        with (ROOT / "evidence/results.csv").open(newline="") as stream:
            recorded = list(csv.DictReader(stream))
        labels = {"Astra 6 · Codex": "astra-6@codex", "Opus + Sonnet team · Claude Code": "opus+sonnet-team@claude-code"}
        for row in expected[1:]:
            match, = [r for r in recorded if r["task"] == row[0] and r["contestant"] == labels[row[1]]
                      and r["cap_profile"].startswith("m4: 1000k")]
            self.assertEqual(row[2], match["result"])
            for cell, key in ((4, "wall_s"), (5, "total_tokens"), (6, "fresh_tokens")):
                self.assertEqual(row[cell].replace(",", ""), match[key])
            self.assertEqual(f"{float(row[7][1:]):.4f}", match["usd_equivalent"])
            self.assertEqual(float(row[8][1:]), float(match["cap_profile"].rsplit("$", 1)[1]))
            self.assertEqual(row[9], match["finished_or_capped"])
        generated = recorded_reports(ROOT / "evidence/results.csv", conclusion)[1]
        for text in (generated, (ROOT / "evidence/m4-results.html").read_text()):
            page = ReportPage(text)
            self.assert_no_markdown_table_paragraphs(page)
            table = next(table for heading, table in page.tables if heading == "Completed M4 cells")
            self.assertEqual(table, expected)
            self.assertEqual(len(table), 4)
            self.assertTrue(all(len(row) == 10 for row in table))
            section = text.split("<h3>Completed M4 cells</h3>", 1)[1].split("</table>", 1)[0]
            self.assertEqual(section.count("<th "), 10)
            self.assertIn("<thead><tr>", section)
            self.assertIn("<tbody><tr>", section)

    def test_conclusion_table_cells_and_heading_are_escaped(self):
        from agentbench.report import recorded_reports
        conclusion = "## <synthetic-title>\n\n| <synthetic-head> | Guard |\n|---|---|\n| <synthetic-cell> & left\\|right | $1 |"
        text = recorded_reports(ROOT / "evidence/results.csv", conclusion)[1]
        page = ReportPage(text)
        self.assert_no_markdown_table_paragraphs(page)
        self.assertEqual(page.tables[0], ("<synthetic-title>", [
            ["<synthetic-head>", "Guard"], ["<synthetic-cell> & left|right", "$1"]]))
        for tag in ("synthetic-title", "synthetic-head", "synthetic-cell"):
            self.assertNotIn(f"<{tag}>", text)
            self.assertIn(f"&lt;{tag}&gt;", text)

    def test_every_recorded_report_table_matches_the_csv(self):
        from agentbench.report import recorded_reports
        with (ROOT / "evidence/results.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        keys = ["task", "contestant", "cap_profile", "result", "wall_s", "total_tokens", "fresh_tokens",
                "usd_equivalent", "workers", "effort_observed", "cap_reason", "finished_or_capped"]
        page = ReportPage(recorded_reports(ROOT / "evidence/results.csv")[1])
        self.assert_no_markdown_table_paragraphs(page)
        for heading, table in page.tables:
            if heading == "Recorded rounds":
                expected = []
                for profile in dict.fromkeys(row["cap_profile"].split(":", 1)[0] for row in rows):
                    group = [row for row in rows if row["cap_profile"].startswith(profile + ":")]
                    capped = sum(row["result"] == "capped" for row in group)
                    expected.append([profile, str(len(group)), str(sum(row["result"] == "pass" for row in group)),
                                     f"{len(group) - capped} finished / {capped} capped"])
            else:
                selected = (rows if heading == "All runs" else
                            [row for row in rows if row["cap_profile"].startswith(("m3:", "m4:"))]
                            if heading == "M3 against M4 (separate cap profiles)" else
                            [row for row in rows if row["task"] == heading])
                expected = [[row[key] for key in keys] for row in selected]
            self.assertEqual(table[1:], expected, heading)

    def test_committed_m4_reports_are_reproducible_from_the_recorded_csv(self):
        from agentbench.report import recorded_reports
        md, html = recorded_reports(ROOT / "evidence/results.csv", (ROOT / "evidence/m4-conclusion.md").read_text())
        self.assertEqual(md, (ROOT / "evidence/m4-results.md").read_text())
        self.assertEqual(html, (ROOT / "evidence/m4-results.html").read_text())

    def test_generator_escapes_workers_and_labels_odd_records_consistently(self):
        from agentbench import report
        run = {"task": "synthetic-task", "contestant": "synthetic-agent", "status": "capped", "passed": False,
               "started": "one", "wall_s": 1, "tokens_total": 1, "tokens_fresh": 1, "usd_equivalent": 0.01,
               "price_table": "synthetic", "effort": "medium", "team": True, "workers": "<synthetic-tag>",
               "cap_profile": "m4", "caps": {"max_fresh_tokens": 500.5, "max_minutes": 1, "max_usd": 1},
               "diff": {"files_changed": 0, "files": [], "lines_added": 0, "lines_removed": 0}, "check_output_tail": ""}
        for status, reason, expected in (("capped", None, "capped: reason unavailable"), ("capped", 123, "capped: 123"),
                                         ("ok", "irrelevant", "finished"), ("error", None, "error")):
            value = run | {"status": status, "cap_reason": reason}
            md = report.display_markdown([value])
            html = report.display_html([value], conclusion=(ROOT / "evidence/m4-conclusion.md").read_text())
            self.assert_no_markdown_table_paragraphs(ReportPage(html))
            self.assertIn("<h3>Completed M4 cells</h3>", html)
            self.assertIn(expected, md); self.assertIn(expected, html)
            self.assertNotIn("<synthetic-tag>", html)
            self.assertIn("&lt;synthetic-tag&gt;", html)
            if status == "error":
                self.assertIn("0 finished / 0 capped / 1 error", md)
                self.assertIn("0 finished / 0 capped / 1 error", html)
            self.assertIn("500.5 fresh tokens", md)
            self.assertIn("Finished or capped", html.split("<h2>Failed and capped runs</h2>", 1)[1])
        self.assertIn("reason unavailable", report.display_html([run]))

    def test_malformed_run_records_have_a_specific_error(self):
        import tempfile
        from agentbench.report import load_runs
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample" / "run.json"
            path.parent.mkdir()
            for contents in ("", "[]", "1", "{}"):
                path.write_text(contents)
                with self.assertRaisesRegex(ValueError, "invalid run record"):
                    load_runs(tmp)
