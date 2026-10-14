"""Markdown tables and one self-contained HTML page from runs/*/run.json.

Everything here is plain arithmetic on the saved records: no model judges anything and nothing is fetched.
"""

import json
import math
import re
import tomllib
from html import escape
from pathlib import Path

from .stream import fresh_of
from .tasks import find_task_root, gold_diff, is_doc_path, is_generated_path, is_test_path

LABELS = {
    "opus-5-5@claude-code": "Opus 5.5 · Claude Code",
    "sonnet-5-5@claude-code": "Sonnet 5.5 · Claude Code",
    "haiku-5-5@claude-code": "Haiku 5.5 · Claude Code",
    "astra-6@codex": "Astra 6 · Codex",
    "sol-6.1@codex": "Sol 6.1 · Codex",
    "opus+sonnet-team@claude-code": "Opus + Sonnet team · Claude Code",
    "opus+haiku-swarm@claude-code": "Opus + Haiku swarm · Claude Code",
}
GROUPS = {"opus-5-5@claude-code": "solo", "sonnet-5-5@claude-code": "solo", "haiku-5-5@claude-code": "solo",
          "astra-6@codex": "solo", "sol-6.1@codex": "solo",
          "opus+sonnet-team@claude-code": "team", "opus+haiku-swarm@claude-code": "team"}
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def load_runs(runs_dir="runs"):
    """Every run.json under one directory, or under several (a list of directories)."""
    dirs = [runs_dir] if isinstance(runs_dir, (str, Path)) else list(runs_dir)
    runs = []
    for directory in dirs:
        for path in sorted(Path(directory).glob("*/run.json")):
            try:
                record = json.loads(path.read_text())
                if not isinstance(record, dict) or not record:
                    raise ValueError("expected a nonempty run object")
                judge = path.parent / "judge.json"
                if judge.is_file():
                    record["judge"] = json.loads(judge.read_text())
            except (ValueError, OSError) as error:
                raise ValueError(f"invalid run record in {path.parent.name}/run.json: {error}") from None
            runs.append(record)
    return runs


def label(cid):
    return LABELS.get(cid, cid)


def token_limit_label(limit):
    return f"{limit / 1000:g}k" if limit >= 1000 else f"{limit:g}tokens"


def profile_sort_key(profile):
    match = re.search(r"m4-([0-9.]+)(k|tokens)", profile)
    return float(match[1]) * (1000 if match[2] == "k" else 1) if match else 0


def finished_or_capped(r):
    if r.get("status") == "capped":
        reason = r.get("cap_reason")
        return "capped" + (f": {reason}" if reason else ": reason unavailable")
    return "finished" if r.get("status") == "ok" else str(r.get("status") or "unknown")


def profile_name(r):
    """Cap profile of a run: recorded since M4, otherwise read off its caps (m3: 400k total tokens and 20 min)."""
    if r.get("cap_profile"):
        name = r["cap_profile"]
        # M4's fresh-token limit changed from 300k to 1M. Keep those measurements in
        # separate cells and leaderboards even though both were launched as profile m4.
        if name == "m4" and r.get("caps", {}).get("max_fresh_tokens"):
            return "m4-" + token_limit_label(r["caps"]["max_fresh_tokens"])
        return name
    caps = r.get("caps") or {}
    if caps.get("max_fresh_tokens"):
        return "m4"
    return "m3" if caps.get("max_tokens") == 400_000 and caps.get("max_minutes") == 20 else "m2"


def profile_desc(r):
    """The caps a run was held to, e.g. 'm4: 1000k fresh tokens, 20 min, $3'."""
    caps = r.get("caps") or {}
    toks = ", ".join(f"{token_limit_label(caps[key]).removesuffix('tokens')} {kind} tokens"
                     for key, kind in (("max_fresh_tokens", "fresh"), ("max_tokens", "total")) if caps.get(key)) or "no token cap"
    mins = f", {caps['max_minutes']:g} min" if caps.get("max_minutes") else ""
    usd = f", ${caps['max_usd']:g}" if caps.get("max_usd") else ""
    name = profile_name(r)
    if name.startswith("m4-"):
        name = "m4"
    return f"{name}: {toks}{mins}{usd}"


def fresh_tokens(r):
    """Input + cache writes + output (no cache reads); None when the record has no per-model split."""
    if r.get("tokens_fresh") is not None:
        return r["tokens_fresh"]
    by = r.get("tokens_by_model")
    return None if not by else sum(fresh_of(t) for t in by.values())


def _fresh_cell(x):
    return "" if x is None else f"{x:,.0f}"


def _workers(r):
    if not r.get("team"):
        return ""
    return r.get("workers") or (r.get("subagents") or {}).get("spawned", 0)


def _result(r):
    return "error" if r["status"] not in ("ok", "capped") else "capped" if r["status"] == "capped" else "pass" if r["passed"] else "fail"


def display(runs):
    """Every run, one row each."""
    if not runs:
        return "No runs found.\n"
    rows = ["| Task | Contestant | Cap profile | Result | Wall s | Total tokens | Fresh tokens | $ equiv | Workers | Effort (seen) | Finished or capped |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(runs, key=lambda r: (r["task"], r["caps"]["max_usd"] if r.get("caps") else 0, r["started"])):
        seen = ",".join(r.get("effort_seen_in_session", [])) or "?"
        capped = finished_or_capped(r)
        rows.append(f"| {r['task']} | {r['contestant']} | {profile_desc(r)} | {_result(r)} | {r['wall_s']:.0f} | {r['tokens_total']:,} "
                    f"| {_fresh_cell(fresh_tokens(r))} | ${r['usd_equivalent']:.4f} | {_workers(r)} | {r['effort']} ({seen}) | {capped} |")
    total = sum(r["usd_equivalent"] for r in runs)
    rows += ["", f"Total ${total:.4f} dollar-equivalent over {len(runs)} run(s); prices {runs[0]['price_table']}. "
             "Subscription runs: not billed per token, but they use plan limits."]
    return "\n".join(rows) + "\n"


# ---- aggregation -------------------------------------------------------------------------------------------

def quality(rs):
    """Mean judge score (1-5) over the runs a judge scored, else None. Secondary: never used for ranking or pass/fail."""
    xs = [r["judge"]["quality"] for r in rs if r.get("judge")]
    return sum(xs) / len(xs) if xs else None


def has_judge(runs):
    return any(r.get("judge") for r in runs)


def _q(x):
    return "" if x is None else f"{x:.1f}"


def judge_footnote(runs):
    js = [r["judge"] for r in runs if r.get("judge")]
    names = ", ".join(sorted({j["judge"]["model"] for j in js}))
    return (f"Quality (judge, secondary) = mean 1-5 score from an LLM judge ({names}) over {len(js)} of {len(runs)} runs, from the task prompt and the diff only, "
            "names removed. It is one model's opinion of the change, can be wrong, and never decides pass/fail: the hidden check does.")


def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def cells(runs):
    """{(task, contestant, cap profile): runs in start order}. Runs under different caps are never one cell."""
    out = {}
    for r in sorted(runs, key=lambda r: r["started"]):
        out.setdefault((r["task"], r["contestant"], profile_name(r)), []).append(r)
    return out


def outcome_summary(rs):
    finished = sum(r.get("status") == "ok" for r in rs)
    capped = sum(r.get("status") == "capped" for r in rs)
    errors = len(rs) - finished - capped
    return f"{finished} finished / {capped} capped" + (f" / {errors} error" if errors else "")


def cell_stats(rs):
    return {"outcomes": outcome_summary(rs), "n": len(rs), "passed": sum(1 for r in rs if r["passed"]),
            "check_ok": sum(1 for r in rs if r.get("check_passed_even_if_capped", r["passed"])),
            "capped": sum(1 for r in rs if r["status"] == "capped"),
            "usd": _mean(r["usd_equivalent"] for r in rs), "usd_min": min(r["usd_equivalent"] for r in rs),
            "usd_max": max(r["usd_equivalent"] for r in rs),
            "wall": _mean(r["wall_s"] for r in rs), "wall_min": min(r["wall_s"] for r in rs),
            "wall_max": max(r["wall_s"] for r in rs), "tokens": _mean(r["tokens_total"] for r in rs),
            "fresh": _mean(f for f in map(fresh_tokens, rs) if f is not None) if any(fresh_tokens(r) is not None for r in rs) else None,
            "workers": max((_workers(r) or 0 for r in rs), default=0), "quality": quality(rs)}


def standings(runs):
    """Per contestant over all its runs, best first: pass rate, then dollars per solved run, then wall time."""
    by = {}
    for r in runs:
        by.setdefault(r["contestant"], []).append(r)
    rows = []
    for cid, rs in by.items():
        k = sum(1 for r in rs if r["passed"])
        spent = sum(r["usd_equivalent"] for r in rs)
        task_cells = {}
        for r in rs:
            task_cells.setdefault(r["task"], []).append(r["passed"])
        rows.append({"outcomes": outcome_summary(rs), "contestant": cid, "runs": len(rs), "passed": k, "spent": spent,
                     "check_ok": sum(1 for r in rs if r.get("check_passed_even_if_capped", r["passed"])),
                     "per_solved": spent / k if k else None, "wall": _mean(r["wall_s"] for r in rs),
                     "tokens": _mean(r["tokens_total"] for r in rs),
                     "fresh": _mean(f for f in map(fresh_tokens, rs) if f is not None) if any(fresh_tokens(r) is not None for r in rs) else None,
                     "capped": sum(1 for r in rs if r["status"] == "capped"),
                     "tasks": len(task_cells), "tasks_all_pass": sum(1 for v in task_cells.values() if all(v)),
                     "workers": max((_workers(r) or 0 for r in rs), default=0), "quality": quality(rs)})
    rows.sort(key=lambda x: (-x["passed"] / x["runs"], x["per_solved"] if x["per_solved"] is not None else math.inf, x["wall"]))
    return rows


def leaderboard_groups(runs):
    """Runs split by cap regime so a token-capped run is never ranked against a fresh-token-capped one."""
    fresh_profiles = sorted({profile_name(r) for r in runs if profile_name(r).startswith("m4-") or profile_name(r) == "m4"},
                            key=profile_sort_key)
    byo = [r for r in runs if profile_name(r) == "byo"]
    total = [r for r in runs if not (profile_name(r).startswith("m4-") or profile_name(r) in ("m4", "byo"))]
    groups = []
    for profile in fresh_profiles:
        limit = profile.removeprefix("m4-")
        title = f"M4 rerun: {limit} fresh-token cap, dollars and minutes (limits shown per run)"
        groups.append((title, [r for r in runs if profile_name(r) == profile]))
    groups.extend((("Your runs: cap on fresh tokens, dollars and minutes (see the Cap profile column)", byo),
                   ("Pilot and M3: token caps, dollars and minutes (see the Cap profile column)", total)))
    return [(title, group) for title, group in groups if group]


def task_standings(runs, task):
    rows = []
    for (t, cid, prof), rs in cells(runs).items():
        if t == task:
            rows.append({"outcomes": outcome_summary(rs), "contestant": cid, "profile": prof} | cell_stats(rs))
    rows.sort(key=lambda x: (x["profile"], -x["passed"] / x["n"], x["usd"], x["wall"]))
    return rows


def spread_notes(runs):
    """Cells with repeats where the outcome flipped or the cost moved by 1.5x or more."""
    notes = []
    for (task, cid, prof), rs in sorted(cells(runs).items()):
        if len(rs) < 2:
            continue
        s = cell_stats(rs)
        flipped = 0 < s["passed"] < s["n"]
        ratio = s["usd_max"] / s["usd_min"] if s["usd_min"] else math.inf
        if flipped or ratio >= 1.5:
            notes.append(f"{task} / {label(cid)} ({prof}): {s['passed']}/{s['n']} passed, cost ${s['usd_min']:.3f} to ${s['usd_max']:.3f} "
                         f"({ratio:.1f}x), wall {s['wall_min']:.0f} to {s['wall_max']:.0f} s")
    return notes


# ---- failures and comparison with the real fix --------------------------------------------------------------

def _fail_line(tail):
    """The most telling line of the (truncated) check output, taken by fixed rules."""
    lines = [ANSI.sub("", l).strip() for l in (tail or "").splitlines() if l.strip()]
    for l in lines:
        if l.startswith("[FAIL]"):
            return l[:140]
    for l in lines:
        m = re.match(r"Found (\d+) errors?", l)
        if m:
            return f"ruff still reports {m.group(1)} finding(s)"
    for l in reversed(lines):
        if not l.startswith("[PASS]") and re.search(r"FAILED|AssertionError|Error|error|MISMATCH|mismatch|not ok|fail", l):
            return l[:140]
    return "no failing line in the saved output"


def failure_note(r):
    n = r["diff"]["files_changed"]
    edited = f"{n} file{'s' if n != 1 else ''} edited (+{r['diff']['lines_added']}/-{r['diff']['lines_removed']})"
    check = "passed" if r.get("check_passed_even_if_capped") else "failed"
    if r["status"] == "capped":
        return (f"killed at the cap ({r.get('cap_reason') or 'reason unavailable'}); {edited}; the hidden check {check} on the work left behind"
                + ("" if r.get("check_passed_even_if_capped") else f": {_fail_line(r.get('check_output_tail'))}"))
    if r["status"] == "error":
        return f"the CLI ended in error; {edited}; hidden check {check}"
    return f"finished and stopped, but the hidden check failed ({edited}): {_fail_line(r.get('check_output_tail'))}"


def failures(runs):
    return [r for r in sorted(runs, key=lambda r: (r["task"], r["started"])) if not r["passed"]]


def compare_to_gold(r, gold):
    """Source-file lines changed by the run vs the upstream fix. Plain counts; tests the run added are left out."""
    src = [f for f in (r["diff"].get("files") or []) if not _not_source(f["path"])]
    mine = sum(f["added"] + f["removed"] for f in src)
    theirs = sum(f["added"] + f["removed"] for f in gold)
    gold_paths = {f["path"] for f in gold}
    touched = len(gold_paths & {f["path"] for f in src})
    ratio = mine / theirs if theirs else math.inf
    extra = len({f["path"] for f in src} - gold_paths)
    if touched < len(gold_paths):
        verdict = f"misses {len(gold_paths) - touched} of the fix's files"
    elif 0.5 <= ratio <= 2:
        verdict = "near the real fix" + (f" (+{extra} extra file{'s' if extra != 1 else ''})" if extra else "")
    else:
        verdict = "larger than the real fix" if ratio > 2 else "smaller than the real fix"
    return {"mine": mine, "gold": theirs, "ratio": ratio, "touched": touched, "gold_files": len(gold_paths),
            "extra": extra, "verdict": verdict}


def _not_source(path):
    return is_test_path(path) or is_generated_path(path) or is_doc_path(path)


def task_info(task_id, tasks_dir=None):
    root = find_task_root(task_id, tasks_dir)
    try:
        meta = tomllib.loads((root / "task.toml").read_text())
    except OSError:
        return {"title": task_id, "category": "", "source": "", "manifest": {}, "gold": [], "root": root}
    manifest = tomllib.loads((root / "manifest.toml").read_text()) if (root / "manifest.toml").exists() else {}
    meta["root"] = root
    ignore = set((manifest.get("gold_comparison") or {}).get("ignore", []))
    gold = [f for f in gold_diff(meta) if f["path"] not in ignore and not _not_source(f["path"])] if (root / "gold").is_dir() else []
    return {"title": meta["title"], "category": meta.get("category", ""), "source": meta.get("source", ""),
            "manifest": manifest, "gold": gold, "root": root}


# ---- peeked runs and "too easy" tasks -------------------------------------------------------------------------

def split_peeked(runs):
    """(runs that count, runs flagged `peeked`). A peeked run looked for the answer; it is listed but left out of every table."""
    return [r for r in runs if not r.get("peeked")], [r for r in runs if r.get("peeked")]


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return None if not n else xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def too_easy_tasks(runs):
    """Tasks that do not separate contestants: two or more contestants ran it, every run passed, none was capped, the median run
    took under 2 minutes and 30,000 fresh tokens. Plain arithmetic on the records."""
    out = []
    for task in sorted({r["task"] for r in runs}):
        rs = [r for r in runs if r["task"] == task]
        fresh = [fresh_tokens(r) for r in rs]
        if (len({r["contestant"] for r in rs}) >= 2 and all(r["passed"] and r["status"] != "capped" for r in rs)
                and None not in fresh and _median([r["wall_s"] for r in rs]) < 120 and _median(fresh) < 30_000):
            out.append(task)
    return out


TOO_EASY_NOTE = "too easy: does not separate contestants (every run passed, none was capped, the median run took under 2 minutes and 30k fresh tokens)"


def peeked_section_md(peeked):
    if not peeked:
        return []
    rows = ["## Peeked runs (left out of every table)", "",
            "These runs mentioned the task folder, `hidden/`, `gold/`, the fix commit, `gh ` or the repository URL in something they did. "
            "Their result is not trusted.", "", "| Task | Contestant | Signs | Passed anyway |", "|---|---|---|---|"]
    rows += [f"| {r['task']} | {label(r['contestant'])} | {', '.join(r.get('peek_signs') or [])} | {'yes' if r['passed'] else 'no'} |" for r in peeked]
    return rows + [""]


# ---- markdown ----------------------------------------------------------------------------------------------

def _money(x):
    return "n/a" if x is None else f"${x:.2f}" if x >= 0.1 else f"${x:.3f}"


CMP_HEAD = ["Task", "Contestant", "Cap profile", "Result", "Work passes check", "$", "Wall s", "Fresh tokens", "Total tokens", "Finished or capped"]


def compare_m3_m4(runs):
    """Rows for every task with at least three M4-profile cells, keeping fresh-token limits distinct."""
    by = {(t, cid, prof): rs[-1] for (t, cid, prof), rs in cells(runs).items()}
    m4_count = {}
    for (t, _, prof) in by:
        if prof == "m4" or prof.startswith("m4-"):
            m4_count[t] = m4_count.get(t, 0) + 1
    tasks = sorted(t for t, n in m4_count.items() if n >= 3)  # tasks the M4 matrix really covered, not a stray cell
    m4_profiles = sorted({prof for (_, _, prof) in by if prof == "m4" or prof.startswith("m4-")},
                         key=profile_sort_key)
    cids = sorted({cid for (_, cid, prof) in by if prof in m4_profiles} | {cid for (t, cid, prof) in by if prof == "m3" and t in tasks},
                  key=lambda c: label(c))
    profiles = ["m3", *m4_profiles]
    return [(t, cid, prof, by.get((t, cid, prof))) for t in tasks for cid in cids for prof in profiles
            if (t, cid, "m3") in by or (t, cid, prof) in by or (prof.startswith("m4-") and t in m4_count)]


def _cmp_cells(r):
    if r is None:
        return ["not run", "", "", "", "", "", "not run"]
    return [_result(r), "yes" if r.get("check_passed_even_if_capped", r["passed"]) else "no", _money(r["usd_equivalent"]),
            f'{r["wall_s"]:.0f}', _fresh_cell(fresh_tokens(r)), f'{r["tokens_total"]:,}',
            finished_or_capped(r)]


def display_markdown(runs, tasks_dir=None):
    runs, peeked = split_peeked(runs)
    if not runs and not peeked:
        return "No runs found.\n"
    if not runs:
        return "\n".join(["No run counts: every run peeked.", ""] + peeked_section_md(peeked))
    tasks = sorted({r["task"] for r in runs})
    out = []
    easy = too_easy_tasks(runs)
    if easy:
        out += ["## Too easy", "", *[f"- **{t}**: {TOO_EASY_NOTE}" for t in easy], ""]
    out += peeked_section_md(peeked)
    jq = has_judge(runs)
    qh, qs, qc = (" Quality (judge, secondary)* |", "---|", lambda s: f" {_q(s['quality'])} |") if jq else ("", "", lambda s: "")
    for title, group in leaderboard_groups(runs):
        out += [f"## Leaderboard, {title}", "",
                "| # | Contestant | Passed | Work passes the check | $ spent | $ per solved run | Mean wall s | Mean total tokens | Mean fresh tokens | Max workers | Capped | Finished or capped |" + qh,
                "|---|---|---|---|---|---|---|---|---|---|---|---|" + qs]
        for i, s in enumerate(standings(group), 1):
            out.append(f"| {i} | {label(s['contestant'])} | {s['passed']}/{s['runs']} | {s['check_ok']}/{s['runs']} | {_money(s['spent'])} | {_money(s['per_solved'])} "
                       f"| {s['wall']:.0f} | {s['tokens']:,.0f} | {_fresh_cell(s['fresh'])} | {s['workers'] or ''} | {s['capped']} | {s['outcomes']} |" + qc(s))
        out.append("")
    cmp_rows = compare_m3_m4(runs)
    if cmp_rows:
        out += ["## M3 against M4 (same tasks, separate cap profiles)", "",
                "m3 = cap of 400k total tokens (cache reads included); historical m4 rows used 300k fresh tokens and the completion cells used 1,000,000. "
                "Each cap profile is listed separately; \"not run\" means that task/contestant was not run under that exact profile.", "",
                "| " + " | ".join(CMP_HEAD) + " |", "|" + "---|" * len(CMP_HEAD)]
        for t, cid, prof, r in cmp_rows:
            out.append("| " + " | ".join([t, label(cid), prof] + _cmp_cells(r)) + " |")
        out.append("")
    for t in tasks:
        out += [f"## {t}", "", "| Contestant | Cap profile | Passed | Work passes the check | Mean $ | Mean wall s | Mean total tokens | Mean fresh tokens | Workers | Capped | Finished or capped |" + qh, "|---|---|---|---|---|---|---|---|---|---|---|" + qs]
        for s in task_standings(runs, t):
            out.append(f"| {label(s['contestant'])} | {s['profile']} | {s['passed']}/{s['n']} | {s['check_ok']}/{s['n']} | {_money(s['usd'])} | {s['wall']:.0f} "
                       f"| {s['tokens']:,.0f} | {_fresh_cell(s['fresh'])} | {s['workers'] or ''} | {s['capped'] or ''} | {s['outcomes']} |" + qc(s))
        out.append("")
    if jq:
        out += [f"\\* {judge_footnote(runs)}", ""]
    out += ["## All runs", "", display(runs)]
    return "\n".join(out)


# ---- html --------------------------------------------------------------------------------------------------

CSS = """
:root{color-scheme:light dark;--bg:#fcfcfb;--card:#f4f3f0;--fg:#0b0b0b;--muted:#52514e;--line:#e2e1dc;--success:#2a78d6;--fail:#eb6834;--bar:#2a78d6;--ring:#fcfcfb}
@media(prefers-color-scheme:dark){:root{--bg:#1a1a19;--card:#242423;--fg:#ffffff;--muted:#c3c2b7;--line:#383835;--success:#3987e5;--fail:#d95926;--bar:#3987e5;--ring:#1a1a19}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:980px;margin:0 auto;padding:20px 16px 64px}
h1{font-size:1.7rem;line-height:1.2;margin:.2em 0 .3em}
h2{font-size:1.25rem;margin:2.2em 0 .5em;padding-top:.4em;border-top:1px solid var(--line)}
h3{font-size:1.02rem;margin:1.6em 0 .4em}
p,li{max-width:70ch}
.sub,.note,figcaption{color:var(--muted);font-size:.92rem}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:18px 0}
.tile{background:var(--card);border-radius:10px;padding:12px 14px}
.tile b{display:block;font-size:1.7rem;line-height:1.1;font-variant-numeric:tabular-nums}
.tile span{color:var(--muted);font-size:.85rem}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:10px 0}
table{border-collapse:collapse;width:100%;font-size:.9rem;font-variant-numeric:tabular-nums}
th,td{padding:7px 10px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child,td:first-child,th.l,td.l{text-align:left}
th{font-weight:600;color:var(--muted);font-size:.8rem;border-bottom:2px solid var(--line)}
td.wrap{white-space:normal;min-width:260px}
.pass{color:var(--success);font-weight:600}.fail{color:var(--fail);font-weight:600}
svg{display:block;width:100%;height:auto}
svg text{fill:var(--fg);font:12px system-ui,sans-serif}svg .m{fill:var(--muted)}
svg .grid{stroke:var(--line);stroke-width:1}
.dot{fill:var(--success);stroke:var(--ring);stroke-width:2}
.x{stroke:var(--fail);stroke-width:2.4;stroke-linecap:round}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:.88rem;margin:6px 0}
.legend i{display:inline-block;vertical-align:-2px;margin-right:6px}
.bars .row{margin:10px 0}.bars .top{display:flex;justify-content:space-between;gap:8px;font-size:.9rem}
.track{height:10px;background:var(--card);border-radius:5px;margin-top:4px}
.fill{height:10px;background:var(--bar);border-radius:0 5px 5px 0}
.fill.none{background:var(--fail);width:3px!important}
details{background:var(--card);border-radius:8px;padding:8px 12px;margin:8px 0}summary{cursor:pointer;font-weight:600}
dl{margin:.5em 0}dt{font-weight:600;margin-top:.5em}dd{margin:0;color:var(--muted)}
code{font-size:.88em}
@media(max-width:560px){body{font-size:15px}h1{font-size:1.4rem}th,td{padding:6px 7px}}
"""


def _table(head, rows, left=1, wrap_last=False):
    """head: column names; rows: lists of already-escaped cell strings."""
    th = "".join(f'<th class="{"l" if i < left else ""}">{h}</th>' for i, h in enumerate(head))
    body = ""
    for row in rows:
        tds = "".join(f'<td class="{"wrap l" if wrap_last and i == len(row) - 1 else "l" if i < left else ""}">{c}</td>' for i, c in enumerate(row))
        body += f"<tr>{tds}</tr>"
    return f'<div class="scroll"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def _conclusion_html(conclusion):
    """Render the conclusion's prose, headings and pipe tables without trusting HTML."""
    parts, paragraph = [], []
    lines = [line.strip() for line in conclusion.splitlines()]

    def flush():
        if paragraph:
            block = "\n".join(paragraph)
            parts.append(f"<p>{escape(block)}</p>")
            paragraph.clear()

    def cells(line):
        if line.startswith("|") and line.endswith("|"):
            return [cell.strip().replace(r"\|", "|") for cell in re.split(r"(?<!\\)\|", line[1:-1])]
        return None

    i = 0
    while i < len(lines):
        line = lines[i]
        heading = re.fullmatch(r"(#{1,6})\s+(.+)", line)
        if heading:
            flush()
            level = min(len(heading[1]) + 1, 6)  # nested below the Conclusion heading
            parts.append(f"<h{level}>{escape(heading[2])}</h{level}>")
        else:
            head = cells(line)
            delimiter = cells(lines[i + 1]) if i + 1 < len(lines) else None
            if (head and delimiter and len(head) == len(delimiter)
                    and all(re.fullmatch(r":?-+:?", cell) for cell in delimiter)):
                flush()
                i += 2
                rows = []
                while i < len(lines):
                    row = cells(lines[i])
                    if row is None or len(row) != len(head):
                        break
                    rows.append([escape(cell) for cell in row])
                    i += 1
                parts.append(_table([escape(cell) for cell in head], rows, left=2))
                continue
            if line:
                paragraph.append(line)
            else:
                flush()
        i += 1
    flush()
    return "".join(parts)


def _pass_cell(k, n):
    cls = "pass" if k == n else "fail" if k == 0 else ""
    return f'<span class="{cls}">{k}/{n}</span>'


def _range(lo, hi, fmt):
    return fmt(lo) if fmt(lo) == fmt(hi) else f"{fmt(lo)}–{fmt(hi)}"


def dot_chart(runs, order):
    """Cost (log scale) against outcome: one row per contestant, one mark per run, vertical slot per task."""
    tasks = sorted({r["task"] for r in runs})
    lo, hi = math.log10(0.003), math.log10(1.0)
    left, right, row_h, top = 12, 408, 58, 8
    height = top + row_h * len(order) + 30

    def x(usd):
        return left + (min(max(math.log10(max(usd, 1e-6)), lo), hi) - lo) / (hi - lo) * (right - left)

    parts = [f'<svg viewBox="0 0 420 {height}" role="img" aria-label="Cost of each run on a log scale; filled circle passed, cross failed or capped">']
    for tick in (0.01, 0.1, 1.0):
        gx = x(tick)
        parts.append(f'<line class="grid" x1="{gx:.1f}" x2="{gx:.1f}" y1="{top}" y2="{height - 24}"/>'
                     f'<text class="m" x="{gx:.1f}" y="{height - 8}" text-anchor="middle">${tick:g}</text>')
    for i, cid in enumerate(order):
        y0 = top + i * row_h
        parts.append(f'<text x="{left}" y="{y0 + 13}">{escape(label(cid))}</text>')
        for r in (r for r in runs if r["contestant"] == cid):
            cy = y0 + 24 + tasks.index(r["task"]) * 9
            cx = x(r["usd_equivalent"])
            tip = escape(f"{r['task']} ({profile_name(r)}): {_result(r)}, ${r['usd_equivalent']:.3f}, {r['wall_s']:.0f} s")
            if r["passed"]:
                parts.append(f'<circle class="dot" cx="{cx:.1f}" cy="{cy}" r="4.5"><title>{tip}</title></circle>')
            else:
                parts.append(f'<g><title>{tip}</title><path class="x" d="M{cx - 4:.1f} {cy - 4}L{cx + 4:.1f} {cy + 4}M{cx + 4:.1f} {cy - 4}L{cx - 4:.1f} {cy + 4}"/></g>')
    parts.append("</svg>")
    return "".join(parts)


def bar_rows(stats):
    solved = [s for s in stats if s["per_solved"] is not None]
    top = max((s["per_solved"] for s in solved), default=1) or 1  # all-free runs (the stand-ins) would divide by zero
    rows = ""
    for s in sorted(stats, key=lambda s: (s["per_solved"] is None, s["per_solved"] or 0)):
        if s["per_solved"] is None:
            rows += (f'<div class="row"><div class="top"><span>{escape(label(s["contestant"]))}</span><span>no solved run</span></div>'
                     f'<div class="track"><div class="fill none"></div></div></div>')
        else:
            pct = max(s["per_solved"] / top * 100, 1.5)
            rows += (f'<div class="row"><div class="top"><span>{escape(label(s["contestant"]))}</span>'
                     f'<span>{_money(s["per_solved"])} · {s["passed"]}/{s["runs"]} passed</span></div>'
                     f'<div class="track"><div class="fill" style="width:{pct:.1f}%"></div></div></div>')
    return f'<div class="bars">{rows}</div>'


def method_notes(prices, n_tasks, min_n, max_n, byo=False):
    reps = f"{min_n} run{'s' if min_n != 1 else ''}" if min_n == max_n else f"{min_n} to {max_n} runs"
    return [m.replace("{prices}", escape(prices)).replace("{n_tasks}", str(n_tasks)).replace("{reps}", reps) for m in (METHOD_BYO if byo else METHOD)]


METHOD_BYO = [
    "<b>The unit is model + CLI, not the model alone.</b> Each column bundles a model with that vendor\u2019s agent harness and any config files you listed for it.",
    "<b>Small sample.</b> {n_tasks} task(s) of your own, {reps} per cell. A pass means the run worked once, not that the contestant is reliable. Treat this as a first look at your own work, not a ranking.",
    "<b>Settings held equal:</b> the same effort level for every contestant unless you set otherwise, connectors off, a fresh checkout and a clean HOME per run, the same prompt, one process at a time. Per-run caps on fresh tokens, dollars and minutes are enforced; a run that hits one is killed, marked <i>capped</i> and counts as not passed.",
    "<b>Pass</b> means the run finished inside every cap and the hidden check passed. The hidden check is copied in only after the run. It is <b>not container-isolated</b>: the agent runs as your own user, so a determined agent could look for it. Runs whose transcript shows that (the <i>peeked</i> flag) are left out of every table.",
    "<b>Dollars are dollar-equivalents.</b> Tokens \u00d7 the dated public list prices ({prices}); a subscription is not billed per token but uses plan limits. It is not an invoice.",
    "<b>Privacy.</b> Contestant CLIs send the files they read to their vendors. The runner has no telemetry or uploads. Explicit task preparation downloads pinned public sources; task setup and checks may download dependencies.",
]


METHOD = [
    "<b>The unit is model + CLI, not the model alone.</b> “Opus 5.5 · Claude Code” and “Astra 6 · Codex” each bundle a model with that vendor’s own agent harness, prompts and tools. A difference here can come from either half and this design cannot separate them.",
    "<b>Small sample.</b> {n_tasks} tasks, and {reps} per cell (the n shown in each table). A pass rate of 1/1 or 2/2 says the run worked, not that the contestant is reliable. No significance tests were run and none would be meaningful at this size.",
    "<b>Settings held equal:</b> reasoning effort <code>medium</code> for every contestant (read back from each run’s own session files), connectors and user settings off, a clean HOME per run, the same prompt text, one process at a time. Per-run caps on tokens, dollars and minutes are enforced by the runner; a run that hits one is killed and marked <i>capped</i>, and counts as not passed.",
    "<b>Cap profiles</b> (the “Cap profile” column says which one each run used). <i>m2</i> (pilot): 150,000 total tokens and 10 minutes (400,000 and 15 for the team and swarm), per-contestant dollar caps. <i>m3</i>: 400,000 total tokens (cache reads included), 20 minutes, dollar caps about 3× the pilot’s. Historical <i>m4</i> rows used a 300,000 fresh-token cap; the current default is 1,000,000 fresh tokens. Fresh tokens are input + cache writes + output, without cache reads; total tokens are still recorded. Dollar caps are per contestant. Runs under different profiles are never pooled into one cell or one leaderboard, because a token cap on total tokens mostly measured cache reads.",
    "<b>Pass</b> means the run finished without hitting a cap and the hidden check passed. The hidden check is the upstream test file or cases (or, for a data task, a known-answer file) copied in only after the run; each task\u2019s own manifest says exactly what it checks and what it forgives. Capped runs whose work would have passed are flagged in the failures list.",
    "<b>Dollars are dollar-equivalents.</b> Every run used the owner’s Claude and Codex subscription logins, so no cash was billed per token. The figure is the recorded tokens × the versioned public list prices (table dated {prices}); it is not an invoice, and plan limits were the real cost.",
    "<b>Tokens</b> are summed over every model call in the session files, sub-agents included. <i>Total</i> includes cache reads, which are most of the total for every contestant and are billed at a small fraction of fresh input; <i>fresh</i> is input + cache writes + output. Neither is comparable between Claude Code and Codex, because the two harnesses cache and count differently.",
    "<b>Wall time</b> is measured outside the CLI, from launch to exit, so it includes start-up. Machines and network were shared with other work, so treat differences under about 2× as noise.",
    "<b>Comparison with the real fix</b> counts changed source lines (added plus removed, test files left out) against the upstream pull request. It is a size check, not a quality judgment; no model judged anything.",
    "<b>Tasks</b> are real merged pull requests (fixes after 2026-06-30) from public repositories under permissive licences, plus data tasks built from public-domain government files. Absence of AI authorship in the originals could be checked only from trailers, labels and bot accounts. Whether any model had seen the fixes cannot be ruled out.",
    "Runs lost to a harness fault, runs made against an earlier version of a task, and the difficulty probes on tasks that were dropped are kept out of every table here and are listed in <code>evidence/m2-pilot.md</code> and <code>evidence/m3-tasks.md</code>.",
]


def display_html(runs, tasks_dir=None, conclusion="", title="agent-bench results"):
    runs, peeked = split_peeked(runs)
    if not runs:
        return ("<!doctype html><title>agent-bench</title><p>No runs found." if not peeked
                else "<!doctype html><title>agent-bench</title><p>No run counts: every run peeked.")
    tasks = sorted({r["task"] for r in runs})
    info = {t: task_info(t, tasks_dir) for t in tasks}
    stand = standings(runs)
    order = [s["contestant"] for s in stand]
    n_pass = sum(1 for r in runs if r["passed"])
    total = sum(r["usd_equivalent"] for r in runs)
    prices = runs[0]["price_table"]
    h = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
         f'<title>{escape(title)}</title><style>{CSS}</style></head><body><main>',
         f'<h1>{escape(title)}</h1>',
         f'<p class="sub">{len({r["contestant"] for r in runs})} coding-agent setups (model + CLI) on {len(tasks)} checkable tasks. Dollar figures are '
         f'dollar-equivalents at list price ({escape(prices)} table) from subscription runs. Read “Methodology and limits” before quoting any number.</p>',
         f'<div class="tiles"><div class="tile"><b>{len(runs)}</b><span>runs recorded</span></div>'
         f'<div class="tile"><b>{n_pass}</b><span>passed the hidden check</span></div>'
         f'<div class="tile"><b>{sum(1 for r in runs if r["status"] == "capped")}</b><span>killed at a cap</span></div>'
         f'<div class="tile"><b>${total:.2f}</b><span>dollar-equivalent, all runs</span></div></div>']

    easy = too_easy_tasks(runs)
    if easy:
        h.append("<h2>Too easy</h2><ul>" + "".join(f"<li><b>{escape(t)}</b>: {escape(TOO_EASY_NOTE)}</li>" for t in easy) + "</ul>")
    if peeked:
        h.append("<h2>Peeked runs (left out of every table)</h2><p class='note'>These runs mentioned the task folder, <code>hidden/</code>, "
                 "<code>gold/</code>, the fix commit, <code>gh </code> or the repository URL in something they did. Their result is not trusted.</p>")
        h.append(_table(["Task", "Contestant", "Signs", "Passed anyway"],
                        [[escape(r["task"]), escape(label(r["contestant"])), escape(", ".join(r.get("peek_signs") or [])), "yes" if r["passed"] else "no"]
                         for r in peeked], left=3))

    h.append("<h2>Conclusion</h2>")
    h.append(_conclusion_html(conclusion)
             or "<p class='note'>No conclusion text supplied.</p>")

    h.append("<h2>Leaderboards</h2>")
    h.append('<p class="note"><b>Passed</b> = finished inside every cap and passed the hidden check. <b>Work passes check</b> = the hidden check passed on what the run had written, even when it was killed at a cap. Ranked by share of runs passed, then dollars per solved run (all spend, failures included, divided by passes), then wall time. Runs held to different caps are ranked separately; the task sets differ too (the M4 rerun covers only the three harder tasks), so the two boards are not comparable with each other.</p>')
    QH, QC = (["Quality (judge, secondary)*"], lambda s: [_q(s["quality"])]) if has_judge(runs) else ([], lambda s: [])
    for gtitle, group in leaderboard_groups(runs):
        h.append(f"<h3>{escape(gtitle)}</h3>")
        h.append(_table(["#", "Contestant", "Passed", "Work passes check", "Tasks all-pass", "$ spent", "$ per solved run", "Mean wall s", "Mean total tokens", "Mean fresh tokens", "Workers", "Capped", "Finished or capped"] + QH,
                        [[str(i), escape(label(s["contestant"])), _pass_cell(s["passed"], s["runs"]), f'{s["check_ok"]}/{s["runs"]}', f'{s["tasks_all_pass"]}/{s["tasks"]}',
                          _money(s["spent"]), _money(s["per_solved"]), f'{s["wall"]:.0f}', f'{s["tokens"]:,.0f}', _fresh_cell(s["fresh"]),
                          escape(str(s["workers"] or "")), str(s["capped"] or ""), escape(s["outcomes"])] + QC(s) for i, s in enumerate(standings(group), 1)], left=2))

    if has_judge(runs):
        h.append(f'<p class="note">* {escape(judge_footnote(runs))}</p>')
    cmp_rows = compare_m3_m4(runs)
    if cmp_rows:
        h.append("<h2>M3 against M4</h2>")
        h.append('<p class="note">The same task and contestant under separate cap profiles. <b>m3</b> = cap of 400k <i>total</i> tokens (cache reads included); historical <b>m4</b> rows used 300k fresh tokens and completion cells used 1,000,000. Each profile is listed separately.</p>')
        h.append(_table(CMP_HEAD, [[escape(t), escape(label(cid)), prof] + [f'<span class="{"pass" if c == "pass" else "fail" if c in ("fail", "capped") else ""}">{escape(c)}</span>' if i == 0 else escape(c)
                                                                          for i, c in enumerate(_cmp_cells(r))] for t, cid, prof, r in cmp_rows], left=3))

    h.append("<h2>Cost against outcome</h2>")
    h.append('<figure style="margin:0"><div class="legend"><span><i><svg width="14" height="14" viewBox="0 0 14 14" style="display:inline"><circle class="dot" cx="7" cy="7" r="4.5"/></svg></i>passed</span>'
             '<span><i><svg width="14" height="14" viewBox="0 0 14 14" style="display:inline"><path class="x" d="M3 3L11 11M11 3L3 11"/></svg></i>failed or capped</span></div>'
             + dot_chart(runs, order) +
             f'<figcaption>One mark per run, log-scale dollar-equivalent. Within a row the vertical slot is the task, top to bottom: {escape(", ".join(tasks))}. Hover or long-press a mark for its numbers.</figcaption></figure>')
    h.append("<h3>Cost per solved run</h3>")
    h.append(bar_rows(stand))
    h.append('<p class="note">All spend on a contestant (failed and capped runs included) divided by its passes. Linear scale.</p>')

    h.append("<h2>Per task</h2>")
    for t in tasks:
        i = info[t]
        h.append(f"<h3>{escape(t)}</h3><p class='note'>{escape(i['title'])}"
                 + (f' · <a href="{escape(i["source"])}">source</a>' if i["source"].startswith("http") else "") + "</p>")
        h.append(_table(["Contestant", "Cap profile", "Passed", "Work passes check", "Mean $", "$ range", "Mean wall s", "Wall range", "Mean total tokens", "Mean fresh tokens", "Workers", "Capped", "Finished or capped"] + QH,
                        [[escape(label(s["contestant"])), escape(s["profile"]), _pass_cell(s["passed"], s["n"]), f'{s["check_ok"]}/{s["n"]}', _money(s["usd"]),
                          _range(s["usd_min"], s["usd_max"], _money) if s["n"] > 1 else "",
                          f'{s["wall"]:.0f}', _range(s["wall_min"], s["wall_max"], lambda v: f"{v:.0f}") if s["n"] > 1 else "",
                          f'{s["tokens"]:,.0f}', _fresh_cell(s["fresh"]), escape(str(s["workers"] or "")), str(s["capped"] or ""), escape(s["outcomes"])] + QC(s) for s in task_standings(runs, t)]))

    notes = spread_notes(runs)
    h.append("<h2>Variance between repeats</h2>")
    reps = [c for c in cells(runs).values() if len(c) > 1]
    if reps:
        h.append(f"<p>{len(reps)} of {len(cells(runs))} cells have more than one run. Cells whose outcome flipped or whose cost moved 1.5× or more:</p>")
        h.append("<ul>" + "".join(f"<li>{escape(n)}</li>" for n in notes) + "</ul>" if notes else "<p>None: repeats agreed in outcome and stayed within 1.5× in cost.</p>")
    else:
        h.append("<p>Every cell is a single run, so there is no variance estimate.</p>")

    h.append("<h2>Failed and capped runs</h2>")
    bad = failures(runs)
    if bad:
        h.append(_table(["Task", "Contestant", "Cap profile", "Result", "Finished or capped", "What the output looked like"],
                        [[escape(r["task"]), escape(label(r["contestant"])), escape(profile_name(r)), f'<span class="fail">{_result(r)}</span>', escape(finished_or_capped(r)), escape(failure_note(r))]
                         for r in bad], left=3, wrap_last=True))
    else:
        h.append("<p>None.</p>")

    h.append("<h2>Passing diffs against the real fix</h2>")
    h.append('<p class="note">Source lines changed (added + removed, tests excluded) by each passing run, against the upstream pull request. A size comparison, not a quality verdict; test files, docs and change logs, lockfiles an install wrote, and files a task manifest lists as unrelated to the fix (three type-annotation files in the taskiq pull request) are left out. Data tasks have no code fix to compare.</p>')
    rows = []
    for t in tasks:
        gold = info[t]["gold"]
        if info[t]["category"] == "data" or not gold:
            continue
        for r in sorted((r for r in runs if r["task"] == t and r["passed"]), key=lambda r: (r["contestant"], r["started"])):
            c = compare_to_gold(r, gold)
            rows.append([escape(t), escape(label(r["contestant"])), escape(profile_name(r)), str(c["mine"]), str(c["gold"]), f'{c["ratio"]:.1f}×',
                         f'{c["touched"]}/{c["gold_files"]}', escape(c["verdict"])])
    h.append(_table(["Task", "Contestant", "Cap profile", "Run lines", "Fix lines", "Ratio", "Fix files touched", "Verdict"], rows, left=3) if rows else "<p>No passing runs with a comparable fix.</p>")

    h.append("<h2>All runs</h2>")
    h.append(_table(["Task", "Contestant", "Cap profile", "Result", "Wall s", "Total tokens", "Fresh tokens", "$ equiv", "Workers", "Effort seen", "Capped", "Finished or capped"],
                    [[escape(r["task"]), escape(label(r["contestant"])), escape(profile_desc(r)), f'<span class="{"pass" if r["passed"] else "fail"}">{_result(r)}</span>',
                      f'{r["wall_s"]:.0f}', f'{r["tokens_total"]:,}', _fresh_cell(fresh_tokens(r)), f'${r["usd_equivalent"]:.4f}', escape(str(_workers(r))),
                      escape(",".join(r.get("effort_seen_in_session", [])) or "?"), escape(str(r.get("cap_reason") or "no")), escape(finished_or_capped(r))]
                     for r in sorted(runs, key=lambda r: (r["task"], r["contestant"], r["started"]))], left=3))

    h.append("<h2>Workflow-match check</h2>")
    h.append("<p class='note'>Five descriptive questions per task document whether it resembles real work. These questions are not a scoring gate.</p>")
    for t in tasks:
        wm = info[t]["manifest"].get("workflow_match") or {}
        if not wm:
            continue
        items = "".join(f"<dt>{escape(k.split('_', 1)[0].upper())} · {escape(k.split('_', 1)[1].replace('_', ' '))}</dt><dd>{escape(v)}</dd>" for k, v in wm.items())
        h.append(f"<details><summary>{escape(t)}</summary><dl>{items}</dl>"
                 f"<p class='note'>{escape(info[t]['manifest'].get('why_it_matches_a_real_workflow', ''))}</p></details>")

    h.append("<h2>Methodology and limits</h2><ul>" + "".join(
        f"<li>{m}</li>" for m in method_notes(prices, len(tasks), min(len(c) for c in cells(runs).values()),
                                              max(len(c) for c in cells(runs).values()),
                                              byo=all(profile_name(r) == "byo" for r in runs))) + "</ul>")
    h.append("</main></body></html>")
    return "".join(h)


def write_html(path, runs, tasks_dir=None, conclusion=""):
    Path(path).write_text(display_html(runs, tasks_dir, conclusion))


def recorded_reports(csv_path, conclusion=""):
    """Reproduce compact reports from the released, rounded measurement table.

    Raw sessions are intentionally not shipped. Do not infer hidden-check outcomes
    on capped work, per-file diffs, or timing/token precision absent from this CSV.
    """
    import csv
    columns = [("task", "Task"), ("contestant", "Contestant"), ("cap_profile", "Cap profile"),
               ("result", "Result"), ("wall_s", "Wall s"), ("total_tokens", "Total tokens"),
               ("fresh_tokens", "Fresh tokens"), ("usd_equivalent", "$ equiv"), ("workers", "Workers"),
               ("effort_observed", "Effort (seen)"), ("cap_reason", "Cap reason"),
               ("finished_or_capped", "Finished or capped")]
    with Path(csv_path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        missing = sorted({key for key, _ in columns} - set(reader.fieldnames or []))
        if missing:
            raise ValueError("recorded results CSV missing required columns: " + ", ".join(missing))
        runs = list(reader)
    note = ("Generated from evidence/results.csv, preserving its recorded rounded measurements. "
            "The Finished or capped column records the outcome; cap reasons appear separately in Cap reason. "
            "M2 and M3 are cap-distorted historical rounds. Raw historical sessions are not shipped; "
            "hidden-check outcomes on capped work and per-file diff comparisons cannot be reconstructed from this table. "
            "The three completion cells' check outcomes and finer cost precision are recorded in evidence/m4-conclusion.md. "
            "Dollar-equivalents are not invoices. Each M4 cell is n=1.")
    md = ["# M4 results (including historical rounds)", "", note, ""]
    page = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
            f'<title>M4 results</title><style>{CSS}</style></head><body><main><h1>M4 results (including historical rounds)</h1>',
            f'<p>{escape(note)}</p>']

    def section(title, rows, cols=columns):
        md.extend(["## " + title, "", "| " + " | ".join(label for _, label in cols) + " |",
                   "|" + "---|" * len(cols)])
        values = [[row.get(key, "") for key, _ in cols] for row in rows]
        md.extend("| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ") for v in row) + " |" for row in values)
        md.append("")
        page.append(f"<h2>{escape(title)}</h2>" + _table([label for _, label in cols],
                                                      [[escape(str(v)) for v in row] for row in values], left=3))

    if conclusion:
        nested = re.sub(r"^(#{1,5})(?=\s)", r"#\1", conclusion.strip(), flags=re.M)
        md.extend(["## Conclusion", "", nested, ""])
        page.append("<h2>Conclusion</h2>" + _conclusion_html(conclusion))
    summary = []
    for profile in dict.fromkeys(row["cap_profile"].split(":", 1)[0] for row in runs):
        group = [row for row in runs if row["cap_profile"].startswith(profile + ":")]
        capped = sum(row["result"] == "capped" for row in group)
        summary.append({"profile": profile, "runs": str(len(group)), "passed": str(sum(row["result"] == "pass" for row in group)),
                        "finished_or_capped": f"{len(group) - capped} finished / {capped} capped"})
    section("Recorded rounds", summary, [("profile", "Round"), ("runs", "Runs"), ("passed", "Passed"), ("finished_or_capped", "Finished or capped")])
    section("M3 against M4 (separate cap profiles)", [row for row in runs if row["cap_profile"].startswith(("m3:", "m4:"))])
    for task in sorted({row["task"] for row in runs}):
        section(task, [row for row in runs if row["task"] == task])
    section("All runs", runs)
    page.append("</main></body></html>")
    return "\n".join(md), "".join(page)
