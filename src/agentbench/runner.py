"""Launch one contestant on one task in a clean workdir and clean HOME; record one run.json."""

import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .cost import load_prices, usd
from .peek import scan_transcript
from .stream import CodexMeter, Meter, fresh_of, validate_caps, with_price_model
from .tasks import diff_summary, load_task, prepare_workdir, run_check, run_setup

EFFORT = "medium"
TOOLS = ["Bash", "Read", "Edit", "Write", "Glob", "Grep"]
WORKER = {"description": "General coding worker: edits and tests exactly what the lead asks for.",
          "prompt": "You are a coding worker on a shared repository. Do exactly the sub-task you are given, "
                    "run the relevant checks, and reply with a short summary of what you changed.",
          "tools": TOOLS}
LEAD = ("You are the lead of a small team. Split the work into independent pieces and delegate them to between "
        "{lo} and {hi} sub-agents of type `worker` (Task tool, subagent_type \"worker\"), launching them in parallel "
        "where the pieces are independent. Give each one a precise, self-contained sub-task. Do not do the bulk of "
        "the edits yourself; review the results and run the final checks yourself.")


def _c(cli, model, price_model, max_usd, max_tokens=150_000, max_minutes=10, **extra):
    return {"cli": cli, "model": model, "price_model": price_model, "effort": EFFORT, "max_usd": max_usd,
            "max_tokens": max_tokens, "max_minutes": max_minutes, **extra}


# Every column is "model + CLI". Caps are per run (cost-plan.md); a breach kills the run and records "capped".
CONTESTANTS = {
    "haiku-5-5@claude-code": _c("claude-code", "claude-haiku-5-5", "claude-haiku-5-5", 0.03),
    "sol-6.1@codex": _c("codex", "gpt-6.1-sol", "gpt-6.1-sol", 0.30),
    "sonnet-5-5@claude-code": _c("claude-code", "claude-sonnet-5-5", "claude-sonnet-5-5", 0.40),
    "opus-5-5@claude-code": _c("claude-code", "claude-opus-5-5", "claude-opus-5-5", 0.75),
    "astra-6@codex": _c("codex", "gpt-6-astra", "gpt-6-astra", 1.50),
    "opus+sonnet-team@claude-code": _c("claude-code", "claude-opus-5-5", "claude-opus-5-5", 1.30, 400_000, 15,
                                       team={"worker_model": "claude-sonnet-5-5", "lo": 3, "hi": 5}),
    "opus+haiku-swarm@claude-code": _c("claude-code", "claude-opus-5-5", "claude-opus-5-5", 0.70, 400_000, 15,
                                       team={"worker_model": "claude-haiku-5-5", "lo": 10, "hi": 20}),
}
# Free stand-ins for `agentbench demo` and the tests: they run stubagent.py instead of a CLI and price at $0.
# The solver copies the task's known fix; the lazy one changes nothing. They check the runner, not model ability.
STUB_MODEL = "agentbench-stub"
STUB_PRICE = {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0, "cache_write_5m": 0.0}
STUBS = {
    "stub-solver": _c("claude-code", STUB_MODEL, STUB_MODEL, 0.01, max_minutes=2, stub="solve", caps={"max_usd": 0.01, "max_minutes": 2}),
    "stub-lazy": _c("claude-code", STUB_MODEL, STUB_MODEL, 0.01, max_minutes=2, stub="idle", caps={"max_usd": 0.01, "max_minutes": 2}),
}


def with_stub_price(prices):
    return {**prices, "models": {**prices["models"], STUB_MODEL: STUB_PRICE}}


# M3 (harder tasks): token cap 400k, minute cap 20, dollar caps about 3x the M2 ones. A run is still also cut to what
# is left in the matrix ledger, so these are ceilings, not budgets.
PROFILES = {
    "m2": {},
    "m3": {"max_tokens": 400_000, "max_minutes": 20,
           "max_usd": {"haiku-5-5@claude-code": 0.10, "sol-6.1@codex": 0.60, "sonnet-5-5@claude-code": 0.80,
                       "opus-5-5@claude-code": 1.50, "astra-6@codex": 2.00,
                       "opus+sonnet-team@claude-code": 2.00, "opus+haiku-swarm@claude-code": 1.50}},
}
# M4: M3 killed 13 of 19 runs at 400k total tokens, nearly all cache reads (fresh tokens were 57k to 98k), so the token
# cap measured the cap. The token cap now counts fresh tokens only (input + cache writes + output, no cache reads) at
# 1,000k; total tokens are no longer capped but are still recorded. Dollar caps are at least 2x what the contestant's
# M3 runs cost (highest M3 run: Haiku 0.03, Sol 0.24, Sonnet 0.43, Opus 0.94, Astra 1.32, team 0.85, swarm 0.62).
PROFILES["m4"] = {"max_tokens": None, "max_fresh_tokens": 1_000_000, "max_minutes": 20,
                  "max_usd": {"haiku-5-5@claude-code": 0.30, "sol-6.1@codex": 1.20, "sonnet-5-5@claude-code": 1.50,
    "opus-5-5@claude-code": 3.00, "astra-6@codex": 4.00,
                              "opus+sonnet-team@claude-code": 4.00, "opus+haiku-swarm@claude-code": 3.00}}
# Bring-your-own default: small caps a person can afford, per run. A contestant in contestants.toml may lower or raise them.
BYO_CAPS = {"max_tokens": None, "max_fresh_tokens": 100_000, "max_minutes": 10, "max_usd": 1.0}
PROFILES["byo"] = {}  # caps come from BYO_CAPS and the contestant's own entries (see profile_caps)
CACHE = Path(os.environ.get("AGENTBENCH_CACHE") or Path.home() / ".cache" / "agentbench")


def claude_bin():
    return os.environ.get("AGENTBENCH_CLAUDE_BIN") or shutil.which("claude") or "claude"


def codex_bin():
    return os.environ.get("AGENTBENCH_CODEX_BIN") or shutil.which("codex") or "codex"


def make_clean_home(run_dir):
    """Empty HOME so the owner's settings, memory and skills never load.

    Subscription login is the one thing shared: a symlink to the credentials file only.
    With ANTHROPIC_API_KEY set no credentials are linked at all.
    """
    home = Path(run_dir) / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude.json").write_text('{"hasCompletedOnboarding": true}')
    creds = Path(os.path.expanduser("~")) / ".claude" / ".credentials.json"
    if not os.environ.get("ANTHROPIC_API_KEY") and creds.exists():
        (home / ".claude" / ".credentials.json").symlink_to(creds)
    return home


def install_config_files(files, home):
    """Copy the contestant's explicitly listed config files into its clean HOME (or CODEX_HOME). Nothing else is copied."""
    for src, dest in files:
        target = Path(home) / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        target.unlink(missing_ok=True)  # never write through the login symlink
        shutil.copy2(src, target)


def make_clean_codex_home(run_dir):
    """Empty CODEX_HOME (no config, AGENTS.md, plugins); only the login file is linked."""
    home = Path(run_dir) / "codex"
    home.mkdir(parents=True)
    auth = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "auth.json"
    if auth.exists():
        (home / "auth.json").symlink_to(auth)
    return home


def count_workers(home):
    """Sub-agents that ran, from their session files (also right when a cap killed the run before the summary)."""
    return len(list((Path(home) / ".claude" / "projects").glob("*/*/subagents/agent-*.jsonl")))


def claude_command(c, max_usd):
    if c.get("stub"):
        return [sys.executable, "-m", "agentbench.stubagent"]
    tools = TOOLS + (["Task"] if c.get("team") else [])
    # Settings sources stay off unless the person listed config files for this contestant: then the user level may load.
    sources = "user" if c.get("files") else ""
    cmd = [claude_bin(), "-p", "--model", c["model"], "--effort", c["effort"],
           "--output-format", "stream-json", "--verbose",
           "--setting-sources", sources, "--strict-mcp-config", "--disable-slash-commands",
           "--permission-mode", "dontAsk", "--tools", ",".join(tools), "--allowedTools", ",".join(tools),
           "--max-budget-usd", str(max_usd)]
    if c.get("team"):
        t = c["team"]
        cmd += ["--agents", json.dumps({"worker": WORKER | {"model": t["worker_model"]}}),
                "--append-system-prompt", LEAD.format(lo=t["lo"], hi=t["hi"])]
    return cmd  # the prompt goes in on stdin


def codex_command(c, workdir):
    return [codex_bin(), "exec", "--json", "-m", c["model"], "-c", f"model_reasoning_effort={c['effort']}",
            "-s", "workspace-write", "-c", "sandbox_workspace_write.network_access=true",
            "--add-dir", str(CACHE), "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check",
            "-C", str(workdir), "-"]  # the prompt goes in on stdin


def kill_tree(proc, windows=os.name == "nt"):
    """Kill the CLI and everything it started. POSIX: its process group. Windows has no killpg: taskkill walks the tree."""
    if windows:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def supervise(proc, meter, tail_root, caps, prompt, transcript_path):
    """Feed the prompt, copy stdout to the transcript, watch spend and the clock; kill on a cap.

    Returns (status, reason). The watcher is a thread so a quiet CLI (no output while it thinks) is still capped.
    """
    state = {"status": None, "reason": None}
    stop = threading.Event()
    deadline = time.monotonic() + caps["max_minutes"] * 60

    def kill(why):
        if state["status"] is None:
            state["status"], state["reason"] = "capped", why
            kill_tree(proc)

    def watch():
        while not stop.wait(1.0):
            meter.tail(tail_root)
            why = meter.breach(caps["max_tokens"], caps["max_usd"], caps.get("max_fresh_tokens"))
            if why:
                return kill(why)
            if time.monotonic() > deadline:
                return kill(f"minutes > {caps['max_minutes']}")

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        proc.stdin.write(prompt)
        proc.stdin.close()
    except (BrokenPipeError, OSError):
        pass
    with open(transcript_path, "w") as transcript:
        for line in proc.stdout:
            transcript.write(line)
            try:
                meter.feed(json.loads(line))
            except json.JSONDecodeError:
                continue
            why = meter.breach(caps["max_tokens"], caps["max_usd"], caps.get("max_fresh_tokens"))
            if why:
                kill(why)
                break
    proc.wait()
    stop.set()
    watcher.join(timeout=5)
    meter.tail(tail_root)  # pick up whatever was written after the last poll
    # A fast CLI can exit before the watcher checks usage or a short deadline.
    why = meter.breach(caps["max_tokens"], caps["max_usd"], caps.get("max_fresh_tokens"))
    if not why and time.monotonic() > deadline:
        why = f"minutes > {caps['max_minutes']}"
    if state["status"] is None and why:
        state["status"], state["reason"] = "capped", why
    return state["status"], state["reason"]


def profile_caps(contestant_id, profile="m2", contestants=None):
    """Default per-run caps for a contestant under a named profile (explicit caps passed to run() still win)."""
    c, prof = (contestants or CONTESTANTS)[contestant_id], PROFILES[profile]
    if profile == "byo":
        return validate_caps(BYO_CAPS | c.get("caps", {}))
    caps = (BYO_CAPS.copy() if c.get("user_defined") or "max_tokens" not in c else
            {k: c[k] for k in ("max_tokens", "max_usd", "max_minutes")} | {"max_fresh_tokens": None})
    for k in ("max_tokens", "max_fresh_tokens", "max_minutes"):
        if k in prof:
            caps[k] = prof[k]
    if "max_usd" in prof:
        caps["max_usd"] = prof["max_usd"].get(contestant_id, caps["max_usd"])
    return validate_caps(caps | c.get("caps", {}))


class TaskNotReady(Exception):
    """The task cannot start: its prompt is still a draft, or its setup command failed."""


DRAFT_MARK = "<!-- DRAFT"


def run(task_id, contestant_id, out_dir="runs", tasks_dir=None, caps=None, profile="m2", contestants=None, prices=None):
    """contestants/prices: your own (from contestants.toml); default the built-in table."""
    c = (contestants or CONTESTANTS)[contestant_id]
    validate_caps(caps or {})
    try:
        task = load_task(task_id, tasks_dir)
    except ValueError as e:
        raise TaskNotReady(str(e)) from None
    if task["prompt_text"].lstrip().startswith(DRAFT_MARK):
        raise TaskNotReady("prompt.md is still the draft written by `task from-commit`: edit it to say what is wrong "
                           "(not how it was fixed) and delete the DRAFT line")
    override, caps = caps or {}, profile_caps(contestant_id, profile, contestants)
    if caps["max_tokens"]:  # a task that needs an install can ask for more (only when total tokens are capped)
        caps["max_tokens"] = max(caps["max_tokens"], task.get("max_tokens", 0))
    caps |= override
    validate_caps(caps)
    prices = prices or load_prices()
    if c.get("stub") and STUB_MODEL not in prices["models"]:
        prices = with_stub_price(prices)
    prices = with_price_model(prices, c["model"], c["price_model"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(out_dir).resolve() / f"{task_id}__{contestant_id}__{stamp}"
    for n in range(2, 1000):  # repeats of a fast run can land in the same second
        try:
            run_dir.mkdir(parents=True)
            break
        except FileExistsError:
            run_dir = run_dir.with_name(f"{task_id}__{contestant_id}__{stamp}-{n}")
    workdir = run_dir / "work"
    prepare_workdir(task, workdir)
    CACHE.mkdir(parents=True, exist_ok=True)

    env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "TERM")}
    # Shared download caches live outside the clean HOME so every contestant (and the sandboxed Codex) can write them.
    env |= {"UV_CACHE_DIR": str(CACHE / "uv"), "npm_config_cache": str(CACHE / "npm"), "CI": "1"}
    if c["cli"] == "codex":
        home, codex_home = make_clean_home(run_dir), make_clean_codex_home(run_dir)
        install_config_files(c.get("files", []), codex_home)
        env |= {"HOME": str(home), "CODEX_HOME": str(codex_home)}
        cmd, meter, tail_root = codex_command(c, workdir), CodexMeter(prices, c["model"]), codex_home / "sessions"
    else:
        home = make_clean_home(run_dir)
        install_config_files(c.get("files", []), home)
        env |= {"HOME": str(home), "ENABLE_CLAUDEAI_MCP_SERVERS": "false"}
        if c.get("stub"):
            env |= {"PYTHONPATH": str(Path(__file__).resolve().parents[1]),
                    "AGENTBENCH_STUB_FIX": str(task["root"] / "gold") if c["stub"] == "solve" else ""}
        elif os.environ.get("ANTHROPIC_API_KEY"):
            env["ANTHROPIC_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]
        cmd, meter, tail_root = claude_command(c, caps["max_usd"]), Meter(prices), home / ".claude" / "projects"

    ok, setup_out, _ = run_setup(task, workdir, env)  # installs happen before the clock and the meter start
    if not ok:
        shutil.rmtree(run_dir, ignore_errors=True)
        raise TaskNotReady(f"the task's setup command failed:\n{setup_out}")

    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    t0 = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=workdir, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, start_new_session=True)
    err = []
    drain = threading.Thread(target=lambda: err.append(proc.stderr.read()), daemon=True)
    drain.start()
    status, reason = supervise(proc, meter, tail_root, caps, task["prompt_text"], run_dir / "transcript.jsonl")
    drain.join(timeout=5)
    for pipe in (proc.stdout, proc.stderr):  # close the pipes here, not at garbage collection
        pipe.close()
    wall = time.monotonic() - t0
    (run_dir / "stderr.txt").write_text("".join(err))

    peeks = scan_transcript(run_dir / "transcript.jsonl", task)
    diff = diff_summary(workdir)
    passed, check_out = run_check(task, workdir)
    if status is None and (meter.result or {}).get("subtype") == "error_max_budget_usd":
        status, reason = "capped", f"CLI dollar budget exhausted (${caps['max_usd']:g})"
    if status is None:
        if c["cli"] == "codex":
            status = "ok" if proc.returncode == 0 else "error"
        else:
            status = "ok" if meter.result and not meter.result.get("is_error") else "error"
    tokens = meter.by_model()
    vendor = meter.vendor_by_model()
    priced = {m: t for m, t in tokens.items() if m in prices["models"]}
    tokens_total = sum(sum(t.values()) for t in tokens.values())
    vendor_total = sum(sum(t.values()) for t in vendor.values()) if vendor else None
    effort_seen = sorted(meter.efforts)
    subagents = (meter.result or {}).get("subagent_stats")
    workers = (subagents or {}).get("spawned") or count_workers(home) if c.get("team") else 0
    record = {
        "schema": 2, "agentbench": __version__, "task": task_id, "task_title": task["title"],
        "contestant": contestant_id, "model": c["price_model"], "cli": c["cli"], "effort": c["effort"],
        "effort_seen_in_session": effort_seen, "effort_verified": effort_seen == [c["effort"]],
        "peeked": bool(peeks), "peek_signs": peeks,
        "status": status, "cap_reason": reason, "passed": passed and status == "ok",
        "check_passed_even_if_capped": passed,
        "started": started, "wall_s": round(wall, 1),
        "reported_duration_ms": (meter.result or {}).get("duration_ms"),
        "reported_api_ms": (meter.result or {}).get("duration_api_ms"),
        "cap_profile": profile, "tokens_by_model": tokens, "tokens_total": tokens_total,
        "tokens_fresh": sum(fresh_of(t) for t in tokens.values()),
        "tokens_cache_read": sum(t.get("cache_read", 0) for t in tokens.values()),
        "tokens_source": "session files (orchestrator and sub-agents)" if c["cli"] == "claude-code" else "codex rollout",
        "tokens_vendor_total": vendor_total,
        "tokens_crosscheck_ok": None if vendor_total is None else abs(vendor_total - tokens_total) <= 0.02 * max(vendor_total, 1),
        "usd_equivalent": round(sum(usd(m, t, prices, meter.max_prompt()) for m, t in priced.items()), 5),
        "unpriced_models": sorted(set(tokens) - set(priced)),
        "models_seen": sorted(tokens), "model_as_requested": c["model"] in tokens or c["price_model"] in tokens,
        "vendor_total_cost_usd": (meter.result or {}).get("total_cost_usd"),
        "price_table": prices["version"], "billing": "subscription-run, dollar-equivalent from public prices",
        "team": c.get("team"), "subagents": subagents, "workers": workers,
        "diff": diff, "caps": caps, "check_output_tail": check_out[-400:],
    }
    (run_dir / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    return record
