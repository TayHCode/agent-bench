"""The easy path: `agentbench demo` and `agentbench start`, plus the terminal results table and friendly errors.

Everything that asks a question takes `ask` (a function returning the answer) and `say` (a function that prints), so the
tests drive it without a terminal. Flags answer every question, so nothing here needs a person at the keyboard.
"""

import os
import re
import shlex
import shutil
import sys
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path

from . import contestants as contestants_file
from . import doctor, fromcommit
from .cost import load_prices
from .plan import PlanError, display_plan, make_plan
from .report import display_html, load_runs, split_peeked
from .runner import CONTESTANTS, STUBS, with_stub_price
from .tasks import agentbench_home, user_tasks_dir
from .toy import PROMPT as TOY_PROMPT, make_toy

DEFAULT_PAIR = ["haiku-5-5@claude-code", "sonnet-5-5@claude-code"]  # one cheap, one strong, when there is no contestants.toml
DEMO_REAL_CAP = 0.05
START_LEDGER_CAP = 1.0
STUB_NOTE = ("stub-solver copies the known fix and stub-lazy changes nothing: they test the pipeline, not any model. "
             "Run `agentbench start` to compare real agents on your own code.")


class FriendlyError(Exception):
    """What happened, and the one command that fixes it."""

    def __init__(self, what, fix=None):
        super().__init__(what)
        self.what, self.fix = what, fix


def friendly(e, debug=False):
    """(what, fix) for an exception a person can act on, or None when it is an unexpected bug."""
    if isinstance(e, FriendlyError):
        return e.what, e.fix
    if isinstance(e, fromcommit.BuildError):
        return str(e), "agentbench doctor"
    if isinstance(e, PlanError):
        return str(e), "add --ledger-cap 1 (the most you are willing to spend, in dollars)"
    if isinstance(e, contestants_file.ContestantsError):
        return str(e), "fix the contestants.toml named above (see the Contestants section of the README)"
    if isinstance(e, FileNotFoundError) and getattr(e, "filename", None) == "git":
        return "git is not installed", doctor.git_fix()
    if isinstance(e, PermissionError):
        return f"permission denied: {e.filename or e}", "pick a folder you own (set AGENTBENCH_HOME=SOME/FOLDER) and run again"
    if isinstance(e, KeyboardInterrupt):
        return "stopped by you (Ctrl-C). Nothing is left running", "agentbench start   (run again whenever you like)"
    return None




def table(runs):
    """A plain-text table, one row per contestant: result, time, tokens and dollar-equivalent. Peeked runs are left out."""
    kept, peeked = split_peeked(runs)
    if not kept:
        return "No finished runs to show."
    by = {}
    for r in sorted(kept, key=lambda r: r["started"]):
        by.setdefault(r["contestant"], []).append(r)
    rows = [("Contestant", "Result", "Time", "Tokens", "$ equiv")]
    for cid, rs in sorted(by.items(), key=lambda kv: (-sum(r["passed"] for r in kv[1]) / len(kv[1]), kv[0])):
        ok = sum(1 for r in rs if r["passed"])
        capped = sum(1 for r in rs if r["status"] == "capped")
        result = ("pass" if ok else "FAIL") if len(rs) == 1 else f"{ok}/{len(rs)} pass"
        if capped:
            result += f" ({capped} capped)"
        rows.append((cid, result, f"{sum(r['wall_s'] for r in rs) / len(rs):.1f}s",
                     f"{round(sum(r['tokens_total'] for r in rs) / len(rs)):,}", f"${sum(r['usd_equivalent'] for r in rs):.4f}"))
    widths = [max(len(r[i]) for r in rows) for i in range(5)]
    lines = ["  ".join(c.ljust(w) if i in (0, 1) else c.rjust(w) for i, (c, w) in enumerate(zip(r, widths))).rstrip() for r in rows]
    lines.insert(1, "  ".join("-" * w for w in widths))
    if peeked:
        lines.append(f"({len(peeked)} run(s) left out: the agent looked at hidden files)")
    return "\n".join(lines)


def write_results(runs, html_path, tasks_dir, title):
    Path(html_path).write_text(display_html(runs, str(tasks_dir), "", title))


def open_file(path):
    """Show the page in the default browser when there is a desktop to show it on; otherwise do nothing (the table is already printed)."""
    opener = "open" if sys.platform == "darwin" else "xdg-open" if (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")) else None
    if opener and shutil.which(opener):
        subprocess.Popen([opener, str(Path(path).resolve())], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def say_results(runs, html_path, say):
    say("")
    say(table(runs))
    say("")
    say(f"Full report: {html_path}")




def yes_no(question, assume_yes, ask, say, interactive):
    """True to go ahead. Without --yes and without a terminal the answer is no, with the flag that would make it yes."""
    if assume_yes:
        say(f"{question} yes (--yes)")
        return True
    if not interactive:
        raise FriendlyError("this needs a yes/no answer and there is no terminal to ask on", "add --yes to accept the plan above")
    return ask(f"{question} [y/N] ").strip().lower() in ("y", "yes")


def interactive_default():
    return sys.stdin.isatty()


def need(value, flag, interactive, prompt, ask, default=None):
    """The flag's value, else ask (with a default); with no terminal a missing flag is an error naming the flag."""
    if value:
        return value
    if not interactive:
        raise FriendlyError(f"{flag} is missing and there is no terminal to ask on", f"add {flag} VALUE (see `agentbench start --help`)")
    suffix = f" [{default}]" if default else ""
    return ask(f"{prompt}{suffix} ").strip() or default or ""




def user_contestants():
    """(defs, prices) from ~/.agentbench/contestants.toml if it exists, else the built-in table."""
    path = agentbench_home() / "contestants.toml"
    if path.exists():
        return contestants_file.load(path)
    return CONTESTANTS, load_prices()


def with_stubs(ids, defs, prices):
    """Contestant table and prices that also know the stub-* ids, when any is chosen."""
    if any(i in STUBS for i in ids):
        return {**defs, **STUBS}, with_stub_price(prices)
    return defs, prices


def cheapest_real(defs, prices, results):
    """The cheapest solo contestant whose CLI is installed and logged in, or None."""
    from .cli import cheapest_first
    usable = [i for i, c in defs.items() if c["cli"] in doctor.available_agents(results) and not c.get("team")]
    return cheapest_first(usable, defs, prices)[0] if usable else None


def build_toy(tmp, say):
    repo = Path(tmp) / "toy"
    sha = make_toy(repo)
    tasks = Path(tmp) / "tasks"
    say("1/3  Building a toy task: a small repo, a bug, and a hidden test that proves it is fixed ...")
    code, task = fromcommit.build(repo, sha, "toy-null-total", tasks, check=f"{shlex.quote(sys.executable)} -m unittest discover -s tests",
                                  out=lambda *_: None)
    if code:
        raise FriendlyError("could not build the toy task on this machine", "agentbench doctor")
    (task / "prompt.md").write_text(TOY_PROMPT)
    return tasks


def demo(real=False, html="results.html", yes=False, ask=input, say=print, interactive=None):
    from .cli import run_matrix
    interactive = interactive_default() if interactive is None else interactive
    for r in doctor.blockers([doctor.check_platform(), doctor.check_python(), doctor.check_git()]):
        raise FriendlyError(r["detail"], r["fix"])
    defs, prices, ids, cap = dict(STUBS), with_stub_price(load_prices()), list(STUBS), 1.0
    if real:
        base, base_prices = user_contestants()
        found = doctor.diagnose()
        pick = cheapest_real(base, base_prices, found)
        if not pick:
            raise FriendlyError("no agent is installed and logged in, so there is nothing real to run",
                                "agentbench doctor   (it prints the exact install and login commands; `agentbench demo` without --real is free)")
        defs = {pick: {**base[pick], "caps": {"max_usd": DEMO_REAL_CAP, "max_minutes": 5}}}
        prices, ids, cap = base_prices, [pick], DEMO_REAL_CAP
    with tempfile.TemporaryDirectory(prefix="agentbench-demo-") as tmp:
        tasks = build_toy(tmp, say)
        if real:
            say(f"2/3  Plan: run the cheapest available agent once on the toy task, capped at ${DEMO_REAL_CAP:.2f}.")
            say(display_plan(make_plan(["toy-null-total"], ids, defs, prices, "byo", 1, cap)))
            if not yes_no("Run it for real?", yes, ask, say, interactive):
                say("Nothing was run. `agentbench demo` (without --real) is free.")
                return 3
        else:
            say("2/3  Running two free stand-in agents on it (no model, no network, $0) ...")
        out = Path(tmp) / "runs"
        code = run_matrix(["toy-null-total"], ids, str(out), str(tasks), cap, profile="byo", defs=defs, prices=prices,
                          say=lambda *a, **k: None)
        runs = load_runs(out)
        say("3/3  Results:")
        write_results(runs, html, tasks, "agent-bench demo")
        say_results(runs, html, say)
    if not real:
        say(STUB_NOTE)
    say("Next: agentbench doctor, then agentbench start")
    return code




def suggest_commits(repo, limit=5):
    """Recent commits that fix something with a test: they touch a test file and a non-test file. [(sha, subject)]."""
    r = fromcommit.git(repo, "log", "-n", "300", "--no-merges", "--name-only", "--format=%x00%H%x09%s", check=False)
    found = []
    for block in r.split("\x00")[1:]:
        head, *names = block.splitlines()
        names = [n for n in names if n.strip()]
        sha, _, subject = head.partition("\t")
        if any(fromcommit.is_test_path(n) for n in names) and any(not fromcommit.is_test_path(n) for n in names):
            found.append((sha, subject))
        if len(found) == limit:
            break
    return found


def pick_commit(repo, answer, say):
    """A commit SHA from the answer: a number from the suggestions, a SHA, or None for 'I'll write a task'."""
    if re.fullmatch(r"(?i)w(rite.*)?|i.?ll write.*", answer.strip()):
        return None
    choices = suggest_commits(repo)
    if answer.strip().isdigit() and 1 <= int(answer) <= len(choices):
        return choices[int(answer) - 1][0]
    return answer.strip()


def write_your_own(say):
    mine = sorted(d.name for d in user_tasks_dir().glob("*") if (d / "task.toml").exists() and not d.name.startswith("."))
    say("To write your own task you need a past fix that came with a test:")
    say("  agentbench task from-commit PATH/TO/REPO FIX_COMMIT --id my-task")
    say("then edit ~/.agentbench/tasks/my-task/prompt.md (say what is wrong, not how it was fixed) and run:")
    say("  agentbench start --task my-task --agents haiku-5-5@claude-code,sonnet-5-5@claude-code")
    if mine:
        say(f"Tasks you already have: {', '.join(mine)}")


def choose_agents(answer, found):
    """-> (contestant ids, defs, prices). 'stub' means the two free stand-ins."""
    base, base_prices = user_contestants()
    if answer.strip() == "stub":
        ids = list(STUBS)
    elif answer.strip():
        ids = [i.strip() for i in answer.split(",") if i.strip()]
    else:
        ids = default_agents(base, found)
    unknown = [i for i in ids if i not in base and i not in STUBS]
    if unknown:
        raise FriendlyError(f"unknown agent(s) {unknown}; known: {sorted(base)} or 'stub'", "agentbench start --agents haiku-5-5@claude-code,sonnet-5-5@claude-code")
    defs, prices = with_stubs(ids, base, base_prices)
    return ids, defs, prices


def default_agents(base, found):
    """Two agents to compare: from contestants.toml, else a cheap and a strong Claude. Only ones that can run, when any can."""
    wanted = list(base)[:2] if (agentbench_home() / "contestants.toml").exists() else [i for i in DEFAULT_PAIR if i in base]
    usable = [i for i in wanted if base[i]["cli"] in doctor.available_agents(found)]
    return usable or wanted


def start(a, ask=input, say=print, interactive=None):
    from .cli import cheapest_first, run_matrix
    interactive = interactive_default() if interactive is None else interactive
    say("agentbench start: compare coding agents on a bug your repo already fixed.")
    existing = a.task.split(",") if a.task else None
    repo = commit = None
    if not existing:
        repo = Path(need(a.repo, "--repo", interactive, "1/3  Which repository? (path to a git repo)", ask, ".")).expanduser().resolve()
        if not repo.is_dir() or fromcommit.git(repo, "rev-parse", "--git-dir", check=False).strip() == "":
            raise FriendlyError(f"{repo} is not a git repository", "cd into your project (or pass --repo PATH) and run `agentbench start` again")
        commit = a.commit
        if not commit:
            options = suggest_commits(repo) if interactive else []
            for n, (sha, subject) in enumerate(options, 1):
                say(f"  {n}) {sha[:8]}  {subject[:70]}")
            first = options[0][0] if options else None
            answer = need(None, "--commit", interactive, "2/3  Which past fix? Number, commit SHA, or w to write your own task", ask, "1" if first else None)
            commit = pick_commit(repo, answer, say)
            if commit is None:
                write_your_own(say)
                return 0
        commit = fromcommit.resolve(repo, commit)[0]
    found = doctor.diagnose()
    answer = need(a.agents, "--agents", interactive, "3/3  Which agents to compare? (comma list, or 'stub' for free stand-ins)", ask,
                  ",".join(default_agents(user_contestants()[0], found)))
    ids, defs, prices = choose_agents(answer, found)
    needs = {defs[i]["cli"] for i in ids if not defs[i].get("stub")}
    results = doctor.diagnose(needs)
    say("")
    say(doctor.display(results))
    if doctor.blockers(results):
        raise FriendlyError("not ready to run: see the BLOCKER line(s) above", "run the fix command printed under each BLOCKER, then `agentbench start` again")
    if existing:
        tasks, tasks_dir = existing, a.tasks_dir
    else:
        task_id, tasks_dir = build_task(repo, commit, a, say), a.tasks_dir or str(user_tasks_dir())
        tasks = [task_id]
    ids = cheapest_first(ids, defs, prices)
    plan = make_plan(tasks, ids, defs, prices, "byo", a.repeats, a.ledger_cap)
    say("")
    say(display_plan(plan))
    say(f"Cheapest first: {ids[0]} runs first" + (f"; the others ({', '.join(ids[1:])}) are skipped on a task only if that task proves broken." if len(ids) > 1 else "."))
    if not yes_no("Go ahead?", a.yes, ask, say, interactive):
        say("Nothing was run.")
        return 3
    out = agentbench_home() / "runs" / ("start-" + datetime.now().strftime("%Y%m%dT%H%M%S"))
    code = run_matrix(tasks, ids, str(out), tasks_dir, a.ledger_cap, profile="byo", defs=defs, prices=prices, repeats=a.repeats)
    runs = load_runs(out) if out.is_dir() else []
    if not runs:
        raise FriendlyError("no run finished", "agentbench doctor")
    write_results(runs, a.html, tasks_dir or user_tasks_dir(), "agent-bench results")
    say_results(runs, a.html, say)
    if interactive and not a.no_open:
        open_file(a.html)
    again = ["agentbench start", *(["--repo", shlex.quote(str(repo)), "--commit", commit[:12]] if repo else ["--task", ",".join(tasks)]),
             *(["--check", shlex.quote(a.check)] if a.check else []), "--agents", ",".join(ids), "--ledger-cap", f"{a.ledger_cap:g}", "--yes"]
    say("Same run without questions: " + " ".join(again))
    return code


def build_task(repo, commit, a, say):
    sha, base_sha = fromcommit.resolve(repo, commit, None)
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", repo.name).strip("-.") or "repo"
    task_id = f"start-{name}-{sha[:7]}"
    tasks_dir = Path(a.tasks_dir or user_tasks_dir())
    if (tasks_dir / task_id / "task.toml").exists():
        say(f"Reusing the task built earlier from this commit: {task_id}")
        return task_id
    say(f"Building a task from {sha[:8]} (the bug's start state, a hidden test, and a check that proves the fix) ...")
    log = []
    tasks_dir.mkdir(parents=True, exist_ok=True)
    code, folder = fromcommit.build(repo, sha, task_id, tasks_dir, None, a.check, a.setup, False, False, out=log.append)
    if code:
        what = "\n".join(l for l in log if not l.startswith(("files:", "verifying")))[-1200:] or "the task could not be built"
        fix = {3: "remove the secret-shaped strings, or build from a commit without them",
               4: "agentbench start ... --check 'YOUR TEST COMMAND' --setup 'YOUR INSTALL COMMAND'  (the guess was wrong)"}.get(code, "agentbench doctor")
        raise FriendlyError(what, fix)
    verified = next((l for l in log if l.startswith("verified:")), "verified")
    say(verified)
    prompt = a.prompt or clean_prompt(folder / "prompt.md")
    (folder / "prompt.md").write_text(prompt.rstrip() + "\n")
    for w in fromcommit.prompt_leaks(prompt, sha, [p.relative_to(folder / "hidden" / "overlay").as_posix()
                                                    for p in (folder / "hidden" / "overlay").rglob("*") if p.is_file()]):
        say(f"WARNING: {w}. Pass --prompt 'what is wrong, in your words' to change it.")
    if not a.prompt:
        say("The agent's instructions came from the commit message. Pass --prompt 'TEXT' to write your own (say what is wrong, not how you fixed it).")
    return task_id


def clean_prompt(path):
    return "".join(l for l in path.read_text().splitlines(keepends=True) if not l.lstrip().startswith("<!-- DRAFT"))
