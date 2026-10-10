import argparse
import shlex
import sys
import tempfile
from pathlib import Path

from .backfill import backfill
from .report import load_runs, display_html, display_markdown
from . import checkfiles, contestants, doctor, fromcommit, guided
from .prepare import PrepareError, prepare_task
from .cost import load_prices, usd
from .plan import TYPICAL, PlanError, confirm, make_plan, display_plan
from .runner import CONTESTANTS, PROFILES, STUBS, TaskNotReady, profile_caps, run
from .tasks import DEFAULT_TASKS, agentbench_home, load_task, user_tasks_dir, verify_task


def cheapest_first(ids, defs=None, prices=None):
    """Contestant ids ordered by what a typical small fix costs at list price (stable for ties)."""
    known, prices = defs or CONTESTANTS, prices or load_prices()
    return sorted(ids, key=lambda i: usd(known[i]["price_model"], TYPICAL, prices) if known[i]["price_model"] in prices["models"] else 0.0)


def task_problem(task_id, tasks_dir, scratch=None):
    """None if the task is sound (the unfixed start fails its check, the known fix passes); else why it is broken. Free: no model runs."""
    try:
        task = load_task(task_id, tasks_dir)
        with tempfile.TemporaryDirectory(prefix="agentbench-verify-") as tmp:
            res = verify_task(task, scratch or Path(tmp) / "v")
    except (ValueError, OSError) as e:
        return f"it could not be checked ({e})"
    if res["setup_failed"]:
        return "its setup command fails"
    if not res["gold_passes"]:
        return "its check fails even on the known fix"
    if not res["start_fails"]:
        return "its check passes without any fix"
    return None


def run_matrix(task, contestants, out, tasks_dir, ledger_cap, runner_run=run, profile="m2", defs=None, prices=None, repeats=1,
               problem_of=task_problem, say=lambda msg: print(msg, flush=True)):
    """Sequential runs, cheapest contestant first. Per-run dollar cap is cut to what is left in the ledger; stops at 90% spent.

    The pricier contestants are skipped on a task only when the cheapest one did not pass AND the task proves broken
    (problem_of: the check fails on the known fix, or passes on the unfixed start). Otherwise everyone runs.
    task: one task id or a list; contestants: 'all', a comma list or a list; defs/prices: your own contestants.toml.
    """
    tasks = [task] if isinstance(task, str) else list(task)
    if isinstance(contestants, str):
        ids = sorted(defs or CONTESTANTS, key=lambda i: profile_caps(i, profile, defs)["max_usd"]) if contestants == "all" else contestants.split(",")
    else:
        ids = list(contestants)
    ids = cheapest_first(ids, defs, prices)
    extra = {} if defs is None else {"contestants": defs, "prices": prices}
    errors = 0
    for t in tasks:
        for n, cid in enumerate(ids):
            results = []
            for _ in range(repeats):
                spent = sum(r["usd_equivalent"] for r in load_runs(out))
                if spent >= 0.9 * ledger_cap:
                    say(f"STOP: ${spent:.3f} spent, within 10% of the ${ledger_cap} ledger cap; not running {cid}")
                    return 2
                left = ledger_cap - spent
                caps = {"max_usd": min(profile_caps(cid, profile, defs)["max_usd"], round(left, 4))}
                try:
                    rec = runner_run(t, cid, out, tasks_dir, caps, profile=profile, **extra)
                except TaskNotReady as e:
                    print(f"error: task {t}: {e}", file=sys.stderr)
                    return 2
                results.append(rec)
                say(f"{t} / {cid}: {rec['status']}, passed={rec['passed']}{' (PEEKED: left out of the report)' if rec.get('peeked') else ''}, "
                      f"{rec['wall_s']}s, {rec['tokens_total']:,} tokens, "
                      f"${rec['usd_equivalent']:.4f} (ledger ${spent + rec['usd_equivalent']:.3f}/{ledger_cap})")
                errors = errors + 1 if rec["status"] == "error" else 0
                if errors >= 2:
                    say("STOP: two runs in a row ended in error")
                    return 1
            if n == 0 and len(ids) > 1 and not any(r["passed"] for r in results):
                why = problem_of(t, tasks_dir)
                if why:
                    say(f"SKIP: {t} is broken ({why}); not spending on {', '.join(ids[1:])}. Fix the task, then run again.")
                    break
    return 0


from .guided import DEFAULT_PAIR  # noqa: E402  one cheap, one strong, when there is no contestants.toml


def add_matrix_args(p):
    p.add_argument("--task", help="one task (the older form; defaults to every built-in contestant under the m2 profile)")
    p.add_argument("--tasks", help="comma list of task ids (default: the first 3 in your tasks folder)")
    p.add_argument("--contestants", help="comma list of ids, or 'all' (default: the first 2 in contestants.toml, else Haiku and Sonnet in Claude Code)")
    p.add_argument("--contestants-file", help="your contestants.toml (default: ~/.agentbench/contestants.toml if it exists)")
    p.add_argument("--repeats", type=int, default=1, help="runs per task and contestant (default 1)")
    p.add_argument("--out", help="run records folder (default: ~/.agentbench/runs; 'runs' with --task)")
    p.add_argument("--tasks-dir")
    p.add_argument("--profile", choices=sorted(PROFILES), help="cap profile (default byo: 100k fresh tokens, $1, 10 min per run; m2 with --task)")
    p.add_argument("--ledger-cap", type=float, help="most you will spend in total (USD equivalent); required")


def select(a):
    """-> (tasks, contestant ids, defs, prices, profile, out, tasks_dir) from the shared plan/matrix arguments."""
    cfile = a.contestants_file or (agentbench_home() / "contestants.toml" if (agentbench_home() / "contestants.toml").exists() else None)
    defs = prices = None
    if cfile:
        defs, prices = contestants.load(cfile)
    legacy = bool(a.task) and not a.tasks
    profile = a.profile or ("m2" if legacy and not defs else "byo")
    known = defs or CONTESTANTS
    if a.contestants == "all" or (legacy and not a.contestants and not defs):
        ids = sorted(known, key=lambda i: profile_caps(i, profile, defs)["max_usd"])
    elif a.contestants:
        ids = a.contestants.split(",")
    else:
        ids = list(defs)[:2] if defs else DEFAULT_PAIR
    if bad := [i for i in ids if i not in known and i not in STUBS]:
        raise SystemExit(f"error: unknown contestant(s) {bad}; known: {sorted(known)} and {sorted(STUBS)}\nfix: agentbench plan --contestants {sorted(known)[0]} --ledger-cap 1")
    if any(i in STUBS for i in ids):  # the free stand-ins are always available by id
        defs, prices = guided.with_stubs(ids, defs or CONTESTANTS, prices or load_prices())
    base = Path(a.tasks_dir) if a.tasks_dir else None
    if a.tasks:
        tasks = a.tasks.split(",")
    elif a.task:
        tasks = [a.task]
    else:
        listing = sorted(d.name for d in (base or user_tasks_dir()).glob("*") if (d / "task.toml").exists() and not d.name.startswith("."))
        if not listing:
            raise SystemExit("error: no tasks yet. Build one with: agentbench task from-commit REPO FIX_COMMIT --id NAME")
        tasks = listing[:3]
    out = a.out or ("runs" if legacy else str(agentbench_home() / "runs"))
    return tasks, ids, defs, prices, profile, out, a.tasks_dir


def do_plan(a, then_run):
    """Print the plan, ask above $2, and (for matrix) run it. Returns an exit code."""
    tasks, ids, defs, prices, profile, out, tasks_dir = select(a)
    try:
        p = make_plan(tasks, ids, defs, prices or load_prices(), profile, a.repeats, a.ledger_cap, load_runs(out) if Path(out).is_dir() else [])
    except PlanError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(display_plan(p))
    if not confirm(p, getattr(a, "yes", False)):
        return 3
    if not then_run:
        return 0
    code = run_matrix(tasks, ids, out, tasks_dir, a.ledger_cap, profile=profile, defs=defs, prices=prices, repeats=a.repeats)
    shown = "~/" + Path(out).resolve().relative_to(Path.home()).as_posix() if Path(out).resolve().is_relative_to(Path.home()) else out
    print(f"Report: agentbench report --runs {shown} --html results.html")
    return code


def main(argv=None):
    """Run a command. Failures print what happened and the one command that fixes it; --debug shows the full trace instead."""
    argv = list(sys.argv[1:] if argv is None else argv)
    debug = "--debug" in argv
    argv = [x for x in argv if x != "--debug"]
    try:
        return _main(argv)
    except (SystemExit, BrokenPipeError):
        raise
    except Exception as e:
        if debug:
            raise
        what, fix = guided.friendly(e) or (f"something went wrong: {e}", "agentbench doctor   (or re-run with --debug and share the trace)")
        print(f"error: {what}\nfix:   {fix}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        what, fix = guided.friendly(KeyboardInterrupt())
        print(f"stopped: {what}\nfix:   {fix}", file=sys.stderr)
        return 130


def _main(argv):
    ap = argparse.ArgumentParser(prog="agentbench", epilog="New here? agentbench doctor, then agentbench demo, then agentbench start. Add --debug to any command for a full error trace.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="check this machine (python, git, claude/codex installed and logged in, disk) and print the fix for each problem")
    d = sub.add_parser("demo", help="free 30-second demo: a toy task, two stand-in agents, a results table and results.html")
    d.add_argument("--real", action="store_true", help="run the cheapest logged-in real agent once on the toy task, capped at $0.05 (asks first)")
    d.add_argument("--yes", action="store_true", help="skip the yes/no question of --real")
    d.add_argument("--html", default="results.html", help="where to write the report page (default results.html)")
    st = sub.add_parser("start", help="guided: pick a repo, a past fix and agents; it checks, builds the task, shows the cost, asks, runs, prints the table")
    st.add_argument("--repo", help="your git repository (default: ask, suggesting the current folder)")
    st.add_argument("--commit", help="a commit that fixed a bug and added a test (default: ask, with suggestions)")
    st.add_argument("--task", help="comma list of tasks you already built, instead of --repo/--commit")
    st.add_argument("--agents", help="comma list of contestant ids, or 'stub' for the free stand-ins (default: ask)")
    st.add_argument("--prompt", help="what is wrong, in your words (default: the commit message)")
    st.add_argument("--check", help="test command, if the guess is wrong")
    st.add_argument("--setup", help="install command run once before the agent starts")
    st.add_argument("--repeats", type=int, default=1, help="runs per agent and task (default 1)")
    st.add_argument("--ledger-cap", type=float, default=guided.START_LEDGER_CAP, help="most you will spend, USD equivalent (default 1)")
    st.add_argument("--tasks-dir")
    st.add_argument("--html", default="results.html", help="where to write the report page (default results.html)")
    st.add_argument("--no-open", action="store_true", help="do not open the report in a browser")
    st.add_argument("--yes", action="store_true", help="accept the plan without asking")
    from .judge import add_arguments as add_judge_arguments, main as judge_main
    add_judge_arguments(sub.add_parser("judge", help="optional secondary quality score from an LLM judge (never decides pass/fail)"))
    r = sub.add_parser("run", help="run one contestant on one task")
    r.add_argument("--task", required=True)
    r.add_argument("--contestant", required=True, help="a built-in contestant, or one from --contestants-file")
    r.add_argument("--contestants-file", help="your contestants.toml")
    r.add_argument("--out", default="runs")
    r.add_argument("--tasks-dir")
    r.add_argument("--max-tokens", type=int)
    r.add_argument("--max-fresh-tokens", type=int, help="cap on input + cache writes + output (cache reads not counted)")
    r.add_argument("--max-usd", type=float)
    r.add_argument("--max-minutes", type=float)
    r.add_argument("--profile", choices=sorted(PROFILES), default="m2", help="cap profile (m3 = 400k total tokens, 20 min; m4 = 300k fresh tokens, 20 min)")
    v = sub.add_parser("verify", help="prove a task: unfixed start fails the check, real fix passes")
    v.add_argument("--task", required=True)
    v.add_argument("--tasks-dir")
    v.add_argument("--scratch", default="runs/_verify")
    m = sub.add_parser("matrix", help="run tasks x contestants one at a time, under a total dollar cap (shows the plan first)")
    add_matrix_args(m)
    m.add_argument("--yes", action="store_true", help="accept a plan that can spend more than $2")
    pl = sub.add_parser("plan", help="show runs and expected and worst-case dollar-equivalent before running anything")
    add_matrix_args(pl)
    pl.add_argument("--yes", action="store_true", help="accept a plan that can spend more than $2")
    cf = sub.add_parser("check-files", help="stock comparer for data tasks: ACTUAL against EXPECTED (csv, json, text)")
    cf.add_argument("actual")
    cf.add_argument("expected")
    cf.add_argument("--format", choices=["csv", "json", "text"], help="default: from the expected file's extension")
    cf.add_argument("--key", help="column(s), comma separated, that identify a row (csv, or json list of objects)")
    cf.add_argument("--max-wrong", type=int, default=0, help="wrong rows or values allowed (default 0)")
    p = sub.add_parser("report", help="markdown leaderboards and run table; --html writes the one-file results page")
    p.add_argument("--runs", nargs="+", default=["runs"], help="one or more run directories")
    p.add_argument("--html", help="write the self-contained HTML page to this file")
    p.add_argument("--md", help="also write the markdown to this file")
    p.add_argument("--conclusion", help="text file for the Conclusion section (paragraphs separated by a blank line)")
    p.add_argument("--tasks-dir")
    p.add_argument("--title", default="agent-bench results", help="title of the HTML page")
    t = sub.add_parser("task", help="build your own tasks").add_subparsers(dest="task_cmd", required=True)
    prep = t.add_parser("prepare", help="download pinned public inputs for a built-in task (no model call)")
    prep.add_argument("task_id")
    prep.add_argument("--cache-dir", help="download cache for data tasks (default: ~/.cache/agentbench/inputs)")
    prep.add_argument("--tasks-dir", help="destination (default: user task directory)")
    fc = t.add_parser("from-commit", help="turn a past fix (a commit with a test) in your own repo into a private, verified task")
    fc.add_argument("repo", help="path to the git repository")
    fc.add_argument("fix_commit", help="the commit that fixed it")
    fc.add_argument("--id", required=True, help="name of the new task")
    fc.add_argument("--tasks-dir", help="where tasks live (default: ~/.agentbench/tasks)")
    fc.add_argument("--base", help="start tree for a merge commit (default: the commit's parent)")
    fc.add_argument("--check", help="test command, if the guess is wrong; hidden test files are copied over the tree before it runs")
    fc.add_argument("--setup", help="install command run once before the agent starts (not billed to the contestant)")
    fc.add_argument("--allow-secrets", action="store_true", help="build even if secret-shaped strings are found")
    fc.add_argument("--keep-failed", action="store_true", help="keep the half-built folder when verification rejects the task")
    b = sub.add_parser("backfill", help="add per-file diff and worker counts to run.json files that predate them")
    b.add_argument("--runs", default="runs")
    a = ap.parse_args(argv)
    if a.cmd == "doctor":
        return doctor.main()
    if a.cmd == "demo":
        return guided.demo(a.real, a.html, a.yes)
    if a.cmd == "start":
        if a.repeats < 1 or a.ledger_cap <= 0:
            raise guided.FriendlyError("--repeats must be 1 or more and --ledger-cap above 0", "agentbench start --repeats 1 --ledger-cap 1")
        return guided.start(a)
    if a.cmd == "judge":
        return judge_main(a)
    if a.cmd == "task":
        if a.task_cmd == "prepare":
            if not any((DEFAULT_TASKS / a.task_id / name).is_file() for name in ("snapshot.toml", "data_recipe.toml")):
                print("error: this task has no public reconstruction recipe", file=sys.stderr)
                return 2
            try:
                built = prepare_task(DEFAULT_TASKS / a.task_id, a.tasks_dir or user_tasks_dir(), a.cache_dir)
            except (PrepareError, OSError, ValueError) as e:
                print(f"error: {e}", file=sys.stderr)
                return 2
            verify_command = ["agentbench", "verify", "--task", built.name]
            if a.tasks_dir:
                verify_command += ["--tasks-dir", a.tasks_dir]
            print(f"prepared {built.name}\nnext: {shlex.join(verify_command)}")
            return 0
        try:
            code, _ = fromcommit.build(a.repo, a.fix_commit, a.id, a.tasks_dir or user_tasks_dir(), a.base, a.check, a.setup,
                                       a.allow_secrets, a.keep_failed)
        except fromcommit.BuildError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        return code
    if a.cmd == "verify":
        try:
            res = verify_task(load_task(a.task, a.tasks_dir), a.scratch)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print(f"{res['task']}: start fails check={res['start_fails']}, real fix passes check={res['gold_passes']}")
        if not (res["start_fails"] and res["gold_passes"]):
            print(res["start_output_tail"], res["gold_output_tail"], sep="\n---\n")
        return 0 if res["start_fails"] and res["gold_passes"] else 1
    if a.cmd in ("matrix", "plan"):
        return do_plan(a, then_run=a.cmd == "matrix")
    if a.cmd == "check-files":
        return checkfiles.main(a.actual, a.expected, a.format, a.key, a.max_wrong)
    if a.cmd == "backfill":
        print(f"{backfill(a.runs)} run record(s) updated")
        return 0
    if a.cmd == "report":
        runs = load_runs(a.runs)
        md = display_markdown(runs, a.tasks_dir)
        if a.html:
            conclusion = Path(a.conclusion).read_text() if a.conclusion else ""
            Path(a.html).write_text(display_html(runs, a.tasks_dir, conclusion, a.title))
        if a.md:
            Path(a.md).write_text(md)
        sys.stdout.write(md)
        return 0
    caps = {k: v for k, v in (("max_tokens", a.max_tokens), ("max_fresh_tokens", a.max_fresh_tokens), ("max_usd", a.max_usd),
                              ("max_minutes", a.max_minutes)) if v is not None}
    defs = prices = None
    if a.contestants_file:
        defs, prices = contestants.load(a.contestants_file)
    if a.contestant not in (defs or CONTESTANTS) and a.contestant not in STUBS:
        print(f"error: unknown contestant {a.contestant!r}; known: {sorted(defs or CONTESTANTS)}\nfix:   agentbench run --task {a.task} --contestant {sorted(defs or CONTESTANTS)[0]}", file=sys.stderr)
        return 2
    if a.contestant in STUBS:
        defs, prices = guided.with_stubs([a.contestant], defs or CONTESTANTS, prices or load_prices())
    try:
        rec = run(a.task, a.contestant, a.out, a.tasks_dir, caps, profile=a.profile, contestants=defs, prices=prices)
    except TaskNotReady as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"{rec['task']} / {rec['contestant']}: {rec['status']}, passed={rec['passed']}, "
          f"{rec['wall_s']}s, {rec['tokens_total']:,} tokens, ${rec['usd_equivalent']:.4f}")
    return 0 if rec["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
